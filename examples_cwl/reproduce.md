# Steps to reproduce cwl current status/errors
## 1. Install polus-plugins in new env
## 2. In a python shell run:
```
import polus.plugins as pp
pp.submit_plugin("https://raw.githubusercontent.com/PolusAI/polus-plugins/compute/formats/polus-ome-zarr-converter-plugin/plugin.json")
```
## 3. 