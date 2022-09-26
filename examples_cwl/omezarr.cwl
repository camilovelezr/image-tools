class: CommandLineTool
cwlVersion: v1.2
baseCommand: ["python3", "/opt/executables/main.py"]
hints:
  DockerRequirement:
    dockerPull: labshare/polus-ome-zarr-converter-plugin:compute-0.2.1
requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - {entry: "$({class: 'Directory', listing: []})", entryname: $(inputs.outDir.location), writable: true}
inputs:
  filePattern:
    inputBinding:
      prefix: --filePattern
    type: string
  inpDir:
    inputBinding:
      prefix: --inpDir
    type: Directory
  outDir:
    inputBinding:
      prefix: --outDir
    type: Directory
outputs:
  out:
    type: Directory
    outputBinding:
      glob: "$(inputs.outDir.path)"
