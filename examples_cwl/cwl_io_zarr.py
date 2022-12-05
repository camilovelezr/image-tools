from polus.plugins import plugins, get_plugin
from polus.data import collections
from cwltool.factory import Factory
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.builder import Builder

data = collections.MaricRatBrain2019
# p = plugins.OmeZarrConverter.to_compute()  # type: ignore
# p = plugins.OmeZarrConverter  # type: ignore
p = get_plugin("OmeZarrConverter", "0.2.0").to_compute()
p.filePatter = data.subset.intensity.patterns["all"].pattern
p.inpDir = "/Users/camilovelezr/cwl_io/input"
p.outDir = "/Users/camilovelezr/cwl_io/output"
# p.run(gpus=None)
# p.darkfield = False
# p.photobleach = False
# p.save_cwl_io("/Users/camilovelezr/polus-plugins/examples_cwl/omezarr_entry.yml")
# p.save_cwl("/Users/camilovelezr/polus-plugins/examples_cwl/omezarr_entry.cwl")
lc = LoadingContext({"debug": True})
args = p._cwl_io()
rc = RuntimeContext({"no_read_only": True, "outdir": "ThisIsARelativePath/zarr"})
fac = Factory(loading_context=lc, runtime_context=rc)
plugin_cwl = fac.make(
    "/Users/camilovelezr/polus-plugins/examples_cwl/omezarr_entry.cwl"
)
result = plugin_cwl(**args)
