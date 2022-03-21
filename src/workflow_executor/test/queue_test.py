import requests
import json

url = "http://127.0.0.1:8000/prepare"


for i in range(0, 6):
  payload = json.dumps({
    "runID": f"abc123abc123{i}",
    "serviceID": "vegetation-index",
    "cwl": "$graph:\r\n  - baseCommand: vegetation-index\r\n    class: CommandLineTool\r\n    hints:\r\n      DockerRequirement:\r\n        dockerPull: eoepca/vegetation-index:0.2\r\n    id: clt\r\n    inputs:\r\n      inp1:\r\n        inputBinding:\r\n          position: 1\r\n          prefix: --input_reference\r\n        type: Directory\r\n      inp2:\r\n        inputBinding:\r\n          position: 2\r\n          prefix: --aoi\r\n        type: string\r\n    outputs:\r\n      results:\r\n        outputBinding:\r\n          glob: .\r\n        type: Directory\r\n    requirements:\r\n      ResourceRequirement:\r\n        ramMax: 4096\r\n        coresMax: 2\r\n        tmpdirMax: 5120\r\n        outdirMax: 5120\r\n      EnvVarRequirement:\r\n        envDef:\r\n          PATH: /opt/anaconda/envs/env_vi/bin:/opt/anaconda/envs/env_vi/bin:/home/fbrito/.nvm/versions/node/v10.21.0/bin:/opt/anaconda/envs/notebook/bin:/opt/anaconda/bin:/usr/share/java/maven/bin:/opt/anaconda/bin:/opt/anaconda/envs/notebook/bin:/opt/anaconda/bin:/usr/share/java/maven/bin:/opt/anaconda/bin:/opt/anaconda/condabin:/opt/anaconda/envs/notebook/bin:/opt/anaconda/bin:/usr/lib64/qt-3.3/bin:/usr/share/java/maven/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/home/fbrito/.local/bin:/home/fbrito/bin:/home/fbrito/.local/bin:/home/fbrito/bin\r\n          PREFIX: /opt/anaconda/envs/env_vi\r\n    stderr: std.err\r\n    stdout: std.out\r\n  - class: Workflow\r\n    doc: Vegetation index processor, the greatest\r\n    id: vegetation-index\r\n    inputs:\r\n      aoi:\r\n        doc: Area of interest in WKT\r\n        label: Area of interest\r\n        type: string\r\n      input_reference:\r\n        doc: EO product for vegetation index\r\n        label: EO product for vegetation index\r\n        type: Directory[]\r\n    label: Vegetation index\r\n    outputs:\r\n      - id: wf_outputs\r\n        outputSource:\r\n          - node_1/results\r\n        type:\r\n          items: Directory\r\n          type: array\r\n    requirements:\r\n      - class: ScatterFeatureRequirement\r\n    steps:\r\n      node_1:\r\n        in:\r\n          inp1: input_reference\r\n          inp2: aoi\r\n        out:\r\n          - results\r\n        run: '#clt'\r\n        scatter: inp1\r\n        scatterMethod: dotproduct\r\ncwlVersion: v1.0"
  })
  headers = {
    'Content-Type': 'application/json'
  }

  response = requests.request("POST", url, headers=headers, data=payload)
  print(response.text)
