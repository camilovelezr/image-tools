#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool

requirements:
  DockerRequirement:
    dockerPull: labshare/polus-basic-flatfield-correction-plugin:1.2.6
  EnvVarRequirement:
    envDef:
      HOME: /
  InitialWorkDirRequirement:
    listing:
    - entryname: $(inputs.outDir)
      writable: true
      entry: "$({class: 'Directory', listing: []})"
  InlineJavascriptRequirement: {}

inputs:
  darkfield:
    type: boolean
    inputBinding:
      prefix: --darkfield
  filePattern:
    type: string
    inputBinding:
      prefix: --filePattern
  groupBy:
    type: string?
    inputBinding:
      prefix: --groupBy
  inpDir:
    type: Directory
    inputBinding:
      prefix: --inpDir
  outDir:
    type: Directory
    inputBinding:
      prefix: --outDir
    streamable: true
  photobleach:
    type: boolean
    inputBinding:
      prefix: --photobleach

outputs:
  outDir:
    type:
      type: array
      items:
      - File
      - Directory
    outputBinding:
      glob: $("."+inputs.outDir.path + "/*")
