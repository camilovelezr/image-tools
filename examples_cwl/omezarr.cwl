#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool

requirements:
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
  out:
    type: Directory

baseCommand:
- python3
- /opt/executables/main.py

hints:
  DockerRequirement:
    dockerPull: labshare/polus-ome-zarr-converter-plugin:compute-0.2.1
