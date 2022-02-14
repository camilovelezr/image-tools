import pathlib
import json
import typing
import logging
import enum
import re
import pprint
import os
from os.path import basename
import uuid
import signal
import random
import requests
from urllib.parse import urlparse, urljoin
from alive_progress import alive_it

from typing import Union
from python_on_whales import docker

from pydantic import BaseModel, Extra, errors, validator
from pydantic.error_wrappers import ValidationError
import github
from polus._plugins._plugin_model import Input as WippInput
from polus._plugins._plugin_model import Output as WippOutput
from polus._plugins._plugin_model import WIPPPluginManifest

"""
Set up logging for the module
"""
logging.basicConfig(
    format="%(asctime)s - %(name)-8s - %(levelname)-8s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
logger = logging.getLogger("polus.plugins")
logger.setLevel(logging.INFO)


class IOKeyError(Exception):
    pass


"""
Initialize the Github interface
"""


def init_github(auth=None):

    if auth is None:

        # Try to get an auth key from an environment variable
        auth = os.environ.get("GITHUB_AUTH", None)

        if auth is None:
            gh = github.Github()
            logger.warning("Initialized Github connection with no user token.")
            return gh
        else:
            logger.debug("Found auth token in GITHUB_AUTH environment variable.")

    else:
        logger.debug("Github auth token supplied as input.")

    gh = github.Github(login_or_token=auth)
    logger.debug(
        f"Initialized Github connection with token for user: {gh.get_user().login}"
    )

    return gh


"""
Plugin Fetcher Class
"""
PLUGINS = {}
VERSIONS = {}


class _Plugins(object):
    def __getattribute__(cls, name):
        if name in PLUGINS.keys():
            return PLUGINS[name].copy()
        return object.__getattribute__(cls, name)

    def __len__(self):
        return len(self.list)

    def __repr__(self):
        return pprint.pformat(self.list)

    @property
    def list(self):
        output = list(PLUGINS.keys())
        output.sort()
        return output

    def get_plugin(self, name: str, version: typing.Optional[str] = None):
        """Returns a plugin object.

        Return a plugin object with the option to specify a version. The specified version's manifest must exist in manifests folder.

        Args:
            name: Name of the plugin.
            version: Optional version of the plugin, must follow semver.

        Returns:
            Plugin object
        """
        if version is None:
            return getattr(self, name)
        else:
            return submit_plugin(VERSIONS[name][version])

    def refresh(self, force: bool = False):
        """Refresh the plugin list

        This should be optimized, since it will become noticeably slow when
        there are many plugins.
        """

        organizations = list(PLUGIN_DIR.iterdir())

        for org in organizations:

            if org.is_file():
                continue

            for file in org.iterdir():

                with open(file, "r") as fr:
                    plugin = submit_plugin(json.load(fr))

                # Add version and path to VERSIONS
                if plugin.__class__.__name__ not in VERSIONS.keys():
                    VERSIONS[plugin.__class__.__name__] = {}

                VERSIONS[plugin.__class__.__name__][plugin.version.version] = file

                if not force:
                    # Create the entry if it doesn't exist
                    if plugin.__class__.__name__ not in PLUGINS.keys():
                        PLUGINS[plugin.__class__.__name__] = plugin

                    # If the entry exists, update it if the current version is newer
                    elif PLUGINS[plugin.__class__.__name__] < plugin:
                        PLUGINS[plugin.__class__.__name__] = plugin

                    # Add the current version to the list of available versions
                    if (
                        plugin.version
                        not in PLUGINS[plugin.__class__.__name__].versions
                    ):
                        PLUGINS[plugin.__class__.__name__].versions.append(
                            plugin.version
                        )
                else:  # if Force. All plugins are rewritten
                    PLUGINS[plugin.__class__.__name__] = plugin

                    # Add the current version to the list of available versions
                    if (
                        plugin.version
                        not in PLUGINS[plugin.__class__.__name__].versions
                    ):
                        PLUGINS[plugin.__class__.__name__].versions.append(
                            plugin.version
                        )


plugins = _Plugins()
get_plugin = plugins.get_plugin

"""
Paths and Fields
"""
# Location to store any discovered plugin manifests
PLUGIN_DIR = pathlib.Path(__file__).parent.joinpath("manifests")

# Fields that must be in a plugin manifest
REQUIRED_FIELDS = [
    "name",
    "version",
    "description",
    "author",
    "containerId",
    "inputs",
    "outputs",
    "ui",
]

"""
Enums for validating plugin input, output, and ui components
"""
WIPP_TYPES = {
    "collection": pathlib.Path,
    "pyramid": pathlib.Path,
    "csvCollection": pathlib.Path,
    "genericData": pathlib.Path,
    "stitchingVector": pathlib.Path,
    "notebook": pathlib.Path,
    "tensorflowModel": pathlib.Path,
    "tensorboardLogs": pathlib.Path,
    "pyramidAnnotation": pathlib.Path,
    "integer": int,
    "number": float,
    "string": str,
    "boolean": bool,
    "array": str,
    "enum": enum.Enum,
}


class OutputTypes(str, enum.Enum):
    """This is needed until the json schema is updated"""

    collection = "collection"
    pyramid = "pyramid"
    csvCollection = "csvCollection"
    genericData = "genericData"
    stitchingVector = "stitchingVector"
    notebook = "notebook"
    tensorflowModel = "tensorflowModel"
    tensorboardLogs = "tensorboardLogs"
    pyramidAnnotation = "pyramidAnnotation"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class InputTypes(str, enum.Enum):
    """This is needed until the json schema is updated"""

    collection = "collection"
    pyramid = "pyramid"
    csvCollection = "csvCollection"
    genericData = "genericData"
    stitchingVector = "stitchingVector"
    notebook = "notebook"
    tensorflowModel = "tensorflowModel"
    tensorboardLogs = "tensorboardLogs"
    pyramidAnnotation = "pyramidAnnotation"
    integer = "integer"
    number = "number"
    string = "string"
    boolean = "boolean"
    array = "array"
    enum = "enum"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


""" Plugin and Input/Output Classes """


class Version(BaseModel):
    version: str

    def __init__(self, version):

        super().__init__(version=version)

    @validator("version")
    def semantic_version(cls, value):

        version = value.split(".")

        assert (
            len(version) == 3
        ), "Version must follow semantic versioning. See semver.org for more information."

        return value

    @property
    def major(self):
        return self.version.split(".")[0]

    @property
    def minor(self):
        return self.version.split(".")[1]

    @property
    def patch(self):
        return self.version.split(".")[2]

    def __lt__(self, other):

        assert isinstance(other, Version), "Can only compare version objects."

        if other.major > self.major:
            return True
        elif other.major == self.major:
            if other.minor > self.minor:
                return True
            elif other.minor == self.minor:
                if other.patch > self.patch:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def __gt__(self, other):

        return other < self

    def __eq__(self, other):

        return (
            other.major == self.major
            and other.minor == self.minor
            and other.patch == self.patch
        )


class IOBase(BaseModel):

    type: typing.Any
    options: typing.Optional[dict] = None
    value: typing.Optional[typing.Any] = None
    id: typing.Optional[typing.Any] = None

    def _validate(self):

        value = self.value

        if value is None:

            if self.required:
                raise TypeError(
                    f"The input value ({self.name}) is required, but the value was not set."
                )

            else:
                return

        if self.type == InputTypes.enum:
            try:
                if isinstance(value, str):
                    value = enum.Enum(self.name, self.options["values"])[value]
                elif not isinstance(value, enum.Enum):
                    raise ValueError

            except KeyError:
                logging.error(
                    f"Value ({value}) is not a valid value for the enum input ({self.name}). Must be one of {self.options['values']}."
                )
                raise
        else:

            value = WIPP_TYPES[self.type](value)

            if isinstance(value, pathlib.Path):

                value = value.absolute()
                assert value.exists(), f"{value} is invalid or does not exist"
                assert value.is_dir(), f"{value} is not a valid directory"

        super().__setattr__("value", value)

    def __setattr__(self, name, value):

        if name not in ["value", "id"]:
            # Don't permit any other values to be changed
            raise TypeError(f"Cannot set property: {name}")

        super().__setattr__(name, value)

        if name == "value":
            self._validate()


class Output(WippOutput, IOBase):
    """Required until JSON schema is fixed"""

    type: OutputTypes


class Input(WippInput, IOBase):
    """Required until JSON schema is fixed"""

    type: InputTypes

    def __init__(self, **data):

        super().__init__(**data)

        if self.description is None:
            logger.warning(
                f"The input ({self.name}) is missing the description field. This field is not required but should be filled in."
            )


# class RunSettings(object):

#     gpu: typing.Union[int, typing.List[int], None] = -1
#     gpu: typing.Union[int, None] = -1
#     mem: int = -1


class Plugin(WIPPPluginManifest):
    """Required until json schema is fixed"""

    version: Version
    inputs: typing.List[Input]
    outputs: typing.List[Output]
    versions: typing.List[Version] = []
    id: uuid.UUID

    class Config:
        extra = Extra.allow
        allow_mutation = False

    def __init__(self, **data):

        data["id"] = uuid.uuid4()

        super().__init__(**data)

        self.Config.allow_mutation = True
        self._io_keys = {i.name: i for i in self.inputs}
        self._io_keys.update({o.name: o for o in self.outputs})
        # self.Config.allow_mutation = False

        if self.author == "":
            logger.warning(
                f"The plugin ({self.name}) is missing the author field. This field is not required but should be filled in."
            )

    @validator("version", pre=True)
    def cast_version(cls, value):

        return Version(version=value)

    @property
    def organization(self):
        return self.containerId.split("/")[0]

    def run(
        self,
        gpus: Union[None, str, int] = "all",
        **kwargs,
    ):

        inp_dirs = []
        out_dirs = []

        for i in self.inputs:
            if isinstance(i.value, pathlib.Path):
                inp_dirs.append(str(i.value))

        for o in self.outputs:
            if isinstance(o.value, pathlib.Path):
                out_dirs.append(str(o.value))

        inp_dirs_dict = {x: f"/data/inputs/input{n}" for (n, x) in enumerate(inp_dirs)}
        out_dirs_dict = {
            x: f"/data/outputs/output{n}" for (n, x) in enumerate(out_dirs)
        }

        mnts_in = [
            [f"type=bind,source={k},target={v},readonly"]  # must be a list of lists
            for (k, v) in inp_dirs_dict.items()
        ]
        mnts_out = [
            [f"type=bind,source={k},target={v}"]  # must be a list of lists
            for (k, v) in out_dirs_dict.items()
        ]

        mnts = mnts_in + mnts_out
        args = []

        for i in self.inputs:
            i._validate()
            args.append(f"--{i.name}")

            if isinstance(i.value, pathlib.Path):
                args.append(inp_dirs_dict[str(i.value)])

            else:
                args.append(str(i.value))

        for o in self.outputs:
            o._validate()
            args.append(f"--{o.name}")

            if isinstance(o.value, pathlib.Path):
                args.append(out_dirs_dict[str(o.value)])
            else:
                args.append(str(o.value))

        container_name = f"polus{random.randint(10, 99)}"

        def sig(
            signal, frame
        ):  # signal handler to kill container when KeyboardInterrupt
            print(f"Exiting container {container_name}")
            docker.kill(container_name)

        signal.signal(
            signal.SIGINT, sig
        )  # make of sig the handler for KeyboardInterrupt
        if gpus is None:
            logger.info(
                "Running container without GPU. %s version %s"
                % (self.__class__.__name__, self.version.version)
            )
            d = docker.run(
                self.containerId,
                args,
                name=container_name,
                remove=True,
                mounts=mnts,
                **kwargs,
            )
            print(d)
        else:
            logger.info(
                "Running container with GPU: --gpus %s. %s version %s"
                % (gpus, self.__class__.__name__, self.version.version)
            )
            d = docker.run(
                self.containerId,
                args,
                gpus=gpus,
                name=container_name,
                remove=True,
                mounts=mnts,
                **kwargs,
            )
            print(d)

    def __getattribute__(self, name):
        if name != "_io_keys" and hasattr(self, "_io_keys"):
            if name in self._io_keys:
                value = self._io_keys[name].value
                if isinstance(value, enum.Enum):
                    value = value.name
                return value

        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name != "_io_keys" and hasattr(self, "_io_keys"):
            if name in self._io_keys:
                logger.info(
                    "Value of %s in %s set to %s"
                    % (name, self.__class__.__name__, value)
                )
                self._io_keys[name].value = value
                return
            else:
                raise IOKeyError(
                    "Attempting to set %s in %s but %s is not a valid I/O parameter"
                    % (name, self.__class__.__name__, name)
                )

        super().__setattr__(name, value)

    def __lt__(self, other):

        return self.version < other.version

    def __gt__(self, other):

        return other.version < self.version


def is_valid_manifest(plugin: dict) -> bool:
    """Validates basic attributes of a plugin manifest.

    Args:
        plugin: A parsed plugin json file

    Returns:
        True if the plugin has the minimal json fields
    """

    fields = list(plugin.keys())

    try:
        for field in REQUIRED_FIELDS:
            assert field in fields, f"Missing json field, {field}, in plugin manifest."
    except AssertionError:
        return False

    return True


def submit_plugin(
    manifest: typing.Union[str, dict, pathlib.Path],
    refresh: bool = False,
) -> Plugin:
    """Parses a plugin and returns a Plugin object.

    This function accepts a plugin manifest as a string, a dictionary (parsed
    json), or a pathlib.Path object pointed at a plugin manifest.

    Args:
        manifest:
        A plugin manifest. It can be a url, a dictionary,
        a path to a JSON file or a string that can be parsed as a dictionary

    Returns:
        A Plugin object populated with information from the plugin manifest.
    """

    """ Convert to dictionary if pathlib.Path or str, validate manifest """
    if isinstance(manifest, pathlib.Path):
        assert (
            manifest.suffix == ".json"
        ), "Plugin manifest must be a json file with .json extension."

        with open(manifest, "r") as fr:
            manifest = json.load(fr)

    elif isinstance(manifest, str):
        if urlparse(manifest).netloc == "":
            manifest = json.loads(manifest)
        else:
            manifest = requests.get(manifest).json()
    if not isinstance(manifest, dict):
        raise ValueError("invalid manifest")

    """ Create a Plugin subclass """
    replace_chars = "()<>-_"
    plugin_name = manifest["name"]
    for char in replace_chars:
        plugin_name = plugin_name.replace(char, " ")
    plugin_name = plugin_name.title().replace(" ", "")
    plugin_class = type(plugin_name, (Plugin,), {})

    # Parse the manifest
    plugin = plugin_class(**manifest)

    # Get Major/Minor/Patch versions
    out_name = (
        plugin.__class__.__name__
        + f"_M{plugin.version.major}m{plugin.version.minor}p{plugin.version.patch}.json"
    )

    # Save the manifest if it doesn't already exist in the database
    org_path = PLUGIN_DIR.joinpath(plugin.organization.lower())
    org_path.mkdir(exist_ok=True, parents=True)
    if not org_path.joinpath(out_name).exists():
        with open(org_path.joinpath(out_name), "w") as fw:
            json.dump(manifest, fw, indent=4)

    # Refresh plugins list if refresh = True
    if refresh:
        plugins.refresh()

    # Return in case additional QA checks should be made
    return plugin


def add_plugin(
    user: str,
    branch: str,
    plugin: str,
    repo: str = "polus-plugins",
    manifest_name: str = "plugin.json",
):
    """Add plugin from GitHub.

    This function adds a plugin hosted on GitHub and returns a Plugin object.

    Args:
        user: GitHub username
        branch: GitHub branch
        plugin: Plugin's name
        repo: Name of GitHub repository, default is `polus-plugins`
        manifest_name: Name of manifest file, default is `plugin.json`

    Returns:
        A Plugin object populated with information from the plugin manifest.
    """
    l = [user, repo, branch, plugin, manifest_name]
    u = "/".join(l)
    url = urljoin("https://raw.githubusercontent.com", u)
    logger.info("Adding %s" % url)
    return submit_plugin(url, refresh=True)


def scrape_manifests(
    repo: typing.Union[str, github.Repository.Repository],
    gh: github.Github,
    min_depth: int = 1,
    max_depth: typing.Optional[int] = None,
    return_invalid: bool = False,
) -> typing.Union[list, typing.Tuple[list, list]]:

    if max_depth is None:
        max_depth = min_depth
        min_depth = 0

    assert max_depth >= min_depth, "max_depth is smaller than min_depth"

    if isinstance(repo, str):
        repo = gh.get_repo(repo)

    contents = list(repo.get_contents(""))
    next_contents = []
    valid_manifests = []
    invalid_manifests = []

    for d in range(0, max_depth):

        for content in alive_it(contents, title=f"{repo.full_name}: {d}"):

            if content.type == "dir":
                next_contents.extend(repo.get_contents(content.path))
            elif content.name.endswith(".json"):
                if d >= min_depth:
                    manifest = json.loads(content.decoded_content)
                    if is_valid_manifest(manifest):
                        valid_manifests.append(manifest)
                    else:
                        invalid_manifests.append(manifest)

        contents = next_contents.copy()
        next_contents = []

    if return_invalid:
        return valid_manifests, invalid_manifests
    else:
        return valid_manifests


def _error_log(val_err, manifest, fct):

    report = []

    for err in val_err.args[0]:
        if isinstance(err, list):
            err = err[0]

        if isinstance(err, AssertionError):
            report.append(
                "The plugin ({}) failed an assertion check: {}".format(
                    manifest["name"], err.args[0]
                )
            )
            logger.critical(f"{fct}: {report[-1]}")
        elif isinstance(err.exc, errors.MissingError):
            report.append(
                "The plugin ({}) is missing fields: {}".format(
                    manifest["name"], err.loc_tuple()
                )
            )
            logger.critical(f"{fct}: {report[-1]}")
        elif errors.ExtraError:
            if err.loc_tuple()[0] in ["inputs", "outputs", "ui"]:
                report.append(
                    "The plugin ({}) had unexpected values in the {} ({}): {}".format(
                        manifest["name"],
                        err.loc_tuple()[0],
                        manifest[err.loc_tuple()[0]][err.loc_tuple()[1]]["name"],
                        err.exc.args[0][0].loc_tuple(),
                    )
                )
            else:
                report.append(
                    "The plugin ({}) had an error: {}".format(
                        manifest["name"], err.exc.args[0][0]
                    )
                )
            logger.critical(f"{fct}: {report[-1]}")
        else:
            logger.warning(
                "{}: Uncaught manifest Error in ({}): {}".format(
                    fct,
                    manifest["name"],
                    str(val_err).replace("\n", ", ").replace("  ", " "),
                )
            )


def update_polus_plugins(gh_auth: typing.Optional[str] = None):

    logger.info("Updating polus plugins.")
    # Get all manifests
    valid, invalid = scrape_manifests(
        "polusai/polus-plugins", init_github(gh_auth), 2, 3, True
    )
    manifests = valid.copy()
    manifests.extend(invalid)
    logger.info("Submitting %s plugins." % len(manifests))

    for manifest in manifests:

        try:
            plugin = submit_plugin(manifest)

            """ Parsing checks specific to polus-plugins """
            error_list = []

            # Check that plugin version matches container version tag
            container_name, version = tuple(plugin.containerId.split(":"))
            version = Version(version=version)
            organization, container_name = tuple(container_name.split("/"))
            try:
                assert (
                    plugin.version == version
                ), f"containerId version ({version}) does not match plugin version ({plugin.version})"
            except AssertionError as err:
                error_list.append(err)

            # Check to see that the plugin is registered to Labshare
            try:
                assert organization in [
                    "polusai",
                    "labshare",
                ], "All polus plugin containers must be under the Labshare organization."
            except AssertionError as err:
                error_list.append(err)

            # Checks for container name, they are somewhat related to our
            # Jenkins build
            try:
                assert container_name.startswith(
                    "polus"
                ), "containerId name must begin with polus-"
            except AssertionError as err:
                error_list.append(err)

            try:
                assert container_name.endswith(
                    "plugin"
                ), "containerId name must end with -plugin"
            except AssertionError as err:
                error_list.append(err)

            if len(error_list) > 0:
                raise ValidationError(error_list, plugin.__class__)

        except ValidationError as val_err:
            _error_log(val_err, manifest, "update_polus_plugins")


def update_nist_plugins(gh_auth: typing.Optional[str] = None):

    # Parse README links
    gh = init_github(gh_auth)
    repo = gh.get_repo("usnistgov/WIPP")
    contents = repo.get_contents("plugins")
    readme = [r for r in contents if r.name == "README.md"][0]
    pattern = re.compile(
        r"\[manifest\]\((https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*))\)"
    )
    matches = pattern.findall(str(readme.decoded_content))
    logger.info("Updating NIST plugins.")
    for match in alive_it(matches, title="NIST Manifests"):
        url_parts = match[0].split("/")[3:]
        plugin_repo = gh.get_repo("/".join(url_parts[:2]))
        manifest = json.loads(
            plugin_repo.get_contents("/".join(url_parts[4:])).decoded_content
        )

        try:
            submit_plugin(manifest)

        except ValidationError as val_err:
            _error_log(val_err, manifest, "update_nist_plugins")


class Registry:
    """Class that contains methods to interact with the REST API of WIPP Registry."""

    def __init__(self, registry_url: str, username: str, password: str):

        self.registry_url = registry_url
        self.username = username
        self.password = password

    def get_current_schema(
        self,
        verify: bool = True,
    ):
        """Return current schema in WIPP"""
        response = requests.get(
            urljoin(
                self.registry_url,
                "rest/template-version-manager/global/?title=res-md.xsd",
            ),
            verify=verify,
        )
        if response.ok:
            return response.json()[0]["current"]
        else:
            response.raise_for_status()

    def upload_data(
        self,
        filepath,
        schema_id,
        verify: bool = True,
    ):
        """Upload data to registry"""
        with open(filepath, "r") as file_reader:
            xml_content = file_reader.read()

        data = {
            "title": basename(filepath),
            "template": schema_id,
            "xml_content": xml_content,
        }

        response = requests.post(
            urljoin(self.registry_url, "rest/data/"),
            data,
            auth=(self.username, self.password),
            verify=verify,
        )
        response_code = response.status_code

        if response_code != 201:
            print(
                "Error uploading file (%s), code %s"
                % (data["title"], str(response_code))
            )
            response.raise_for_status()

        return response.json()

    def publish_data(
        self,
        data,
        verify: bool = True,
    ):
        """Publish to public workspace"""
        data_publish_id = data["id"] + "/publish/"
        response = requests.patch(
            urljoin(self.registry_url, "rest/data/" + data_publish_id),
            auth=(self.username, self.password),
            verify=verify,
        )
        response_code = response.status_code

        if response_code != 200:
            print(
                "Error publishing data (%s), code %s"
                % (data["title"], str(response_code))
            )
            response.raise_for_status()

    def get_resource_by_pid(self, pid, verify: bool = True):
        """Return current resource."""
        response = requests.get(pid, verify=verify)
        return response.json()

    def patch_resource(
        self,
        pid,
        version,
        verify: bool = True,
    ):
        """Patch resource."""
        # Get current version of the resource
        current_resource = self.get_resource_by_pid(pid, verify)

        data = {
            "version": version,
        }
        response = requests.patch(
            urljoin(self.registry_url, "rest/data/" + data["id"]),
            data,
            auth=(self.username, self.password),
            verify=verify,
        )
        response_code = response.status_code

        if response_code != 200:
            print(
                "Error publishing data (%s), code %s"
                % (data["title"], str(response_code))
            )
            response.raise_for_status()


# def _update_schema(gh_auth: typing.Optional[str] = None):

#     gh = init_github(gh_auth)
#     repo = gh.get_repo("usnistgov/WIPP-Plugins-base-templates")

#     content = repo.get_content(
#         "plugin-manifest/schema/wipp-plugin-manifest-schema.json"
#     )
_Plugins().refresh()  # calls the refresh method when library is imported
