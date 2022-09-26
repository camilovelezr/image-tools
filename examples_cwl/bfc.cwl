class: CommandLineTool
cwlVersion: v1.2
requirements:
  DockerRequirement:
    dockerPull: labshare/polus-basic-flatfield-correction-plugin:1.2.6
baseCommand: ["python3", "/main.py"]
inputs:
  darkfield:
    inputBinding:
      prefix: --darkfield
    type: boolean
  filePattern:
    inputBinding:
      prefix: --filePattern
    type: string
  groupBy:
    inputBinding:
      prefix: --groupBy
    type: string?
  inpDir:
    inputBinding:
      prefix: --inpDir
    type: Directory
  outDir:
    inputBinding:
      prefix: --outDir
    type: Directory
  photobleach:
    inputBinding:
      prefix: --photobleach
    type: boolean
outputs:
  outDir:
    type: Directory
