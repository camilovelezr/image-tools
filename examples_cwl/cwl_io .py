from polus.plugins import plugins
from polus.data import collections
from cwltool.factory import Factory
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.builder import Builder

data = collections.MaricRatBrain2019
# p = plugins.BasicFlatfieldCorrectionPlugin.new_schema()
p = plugins.OmeZarrConverter.to_compute()
p.filePattern = data.subset.intensity.patterns["all"].pattern
p.inpDir = "/Users/camilovelezr/cwl_io/input"
p.outDir = "/Users/camilovelezr/cwl_io/output"
# p.darkfield = False
# p.photobleach = False
# p.save_cwl_io("/Users/camilovelezr/omezarr.yml")
# p.save_cwl("/Users/camilovelezr/omezarr.cwl")
lc = LoadingContext({"debug": True})
args = p._cwl_io()
rc = RuntimeContext({"no_read_only": True})
fac = Factory(loading_context=lc, runtime_context=rc)
plugin_cwl = fac.make("/Users/camilovelezr/polus-plugins/examples_cwl/omezarr.cwl")
# args["entrypoint"] = "python3 ../main.py"
result = plugin_cwl(**args)
