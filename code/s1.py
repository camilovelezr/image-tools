from polus.data import Collection
from polus.plugins import Plugin
from polus.plugins import plugins
import polus.plugins as pp
import polus.data
from pathlib import Path

data = Collection("MaricRatBrain2019")

# plugins.refresh()

print(plugins.list)

bf = plugins.BasicFlatfieldCorrectionPlugin


bf.inpDir = Path("/media/camilovelezr/D/Axle/input")

bf.outDir = Path("/media/camilovelezr/D/Axle/output")
bf.filePattern = "S1_R{r}_C1-C11_A1_y0{yy}_x0{xx}_c0{cc}.ome.tif"
bf.darkfield = False
bf.photobleach = True

# print(bf.__dict__)
