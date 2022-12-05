
# Steps to reproduce cwl current status/errors
## 1. Install polus-plugins in new env
## 2. In a python shell run:
```
from pathlib import Path
import polus.plugins as pp
manifest = Path("/examples_cwl/manifests/omezarr.json") # replace by local abs path
pp.submit_plugin(manifest)
```
## 3. From `formats/polus-ome-zarr-converter-plugin` run `./build-docker.sh`
## 4. In `cwl_io.py`, modify `inpDir` and `outDir` to reflect local absolute paths. 
`inpDir` in my local machine contains:
```
S1 R1 C1-C11 A1 y005 x008 c000.ome.tif S1 R1 C1-C11 A1 y005 x008 c002.ome.tif S1 R1 C1-C11 A1 y005 x008 c004.ome.tif
S1 R1_C1-C11 A1 y005 x008 c001.ome.tif S1 R1 C1-C11 A1 y005 x008 c003.ome.tif
```
## 4. In `cwl_io.py`, modify line 21 to reflect the path of `examples_cwl/omezarr.cwl`
## 6. Run and debug `cwl_io.py`