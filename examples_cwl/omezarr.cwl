#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool

requirements:
  DockerRequirement:
    dockerPull: labshare/polus-ome-zarr-converter-plugin:compute-0.2.1
  InlineJavascriptRequirement: {}

inputs:
  filePattern:
    type: string
    inputBinding:
      prefix: --filePattern
  inpDir:
    type: Directory
    inputBinding:
      prefix: --inpDir
  outDir:
    type: Directory
    inputBinding:
      prefix: --outDir

outputs:
  outDir:
    type: Directory
    outputBinding:
      glob: $(inputs.outDir.dirname.replace('/', "") + "/*")
    streamable: true

baseCommand:
- python3
- /opt/executables/main.py
