#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool

requirements:
  DockerRequirement:
    dockerPull: labshare/polus-ome-zarr-converter-plugin:0.2.0
  InitialWorkDirRequirement:
    listing:
    - writable: true
      entry: $(inputs.outDir)
  InlineJavascriptRequirement: {}

inputs:
  filePatter:
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
    type:
      type: array
      items:
      - File
      - Directory
    outputBinding:
      glob: $(inputs.outDir.path)
