from polus.plugins import plugins
from polus.data import collections
from cwltool.factory import Factory
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.builder import Builder

data = collections.MaricRatBrain2019
p = plugins.BasicFlatfieldCorrectionPlugin.to_compute()
p.filePattern = data.subset.intensity.patterns["all"].pattern
p.inpDir = "/Users/camilovelezr/cwl_io/input"
p.outDir = "/Users/camilovelezr/cwl_io/output"
p.darkfield = False
p.photobleach = False
# p.run(gpus=None)
# p.save_cwl_io("/Users/camilovelezr/bfcio.yml")
# p.save_cwl("/Users/camilovelezr/cwl_io/bfc.cwl")
lc = LoadingContext({"debug": True})
rc = RuntimeContext({"streaming_allowed": "True"})
fac = Factory(loading_context=lc, runtime_context=rc)
plugin_cwl = fac.make("/Users/camilovelezr/polus-plugins/examples_cwl/bfc.cwl")
args = p._cwl_io()
# args["entrypoint"] = "python3, ../main.py"
result = plugin_cwl(**args)
