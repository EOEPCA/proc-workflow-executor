$graph:
- class: Workflow
  doc: Main stage manager
  id: main
  inputs:
    ADES_STAGEIN_AWS_ACCESS_KEY_ID:
      type: string?
    ADES_STAGEIN_AWS_SECRET_ACCESS_KEY:
      type: string?
    ADES_STAGEIN_AWS_SERVICEURL:
      type: string?
    ADES_STAGEOUT_AWS_ACCESS_KEY_ID:
      type: string?
    ADES_STAGEOUT_AWS_PROFILE:
      type: string?
    ADES_STAGEOUT_AWS_REGION:
      type: string?
    ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY:
      type: string?
    ADES_STAGEOUT_AWS_SERVICEURL:
      type: string?
    ADES_STAGEOUT_OUTPUT:
      type: string?
    aws_profiles_location:
      type: File?
    lat_max:
      doc: Input maximum latitude
      id: lat_max
      label: lat_max
      type: float[]
    lat_min:
      doc: Input minimum latitude
      id: lat_min
      label: lat_min
      type: float[]
    lon_max:
      doc: Input maximum longitude
      id: lon_max
      label: lon_max
      type: float[]
    lon_min:
      doc: Input minimum longitude
      id: lon_min
      label: lon_min
      type: float[]
    process:
      type: string?
  label: macro-cwl
  outputs:
    s3_catalog_output:
      id: s3_catalog_output
      outputSource:
      - node_stage_out/s3_catalog_output
      type: string
    wf_outputs:
      outputSource:
      - node_stage_out/wf_outputs_out
      type: Directory[]
  requirements:
    InlineJavascriptRequirement: {}
    ScatterFeatureRequirement: {}
    SubworkflowFeatureRequirement: {}
  steps:
    node_stage_out:
      in:
        ADES_STAGEOUT_AWS_ACCESS_KEY_ID: ADES_STAGEOUT_AWS_ACCESS_KEY_ID
        ADES_STAGEOUT_AWS_PROFILE: ADES_STAGEOUT_AWS_PROFILE
        ADES_STAGEOUT_AWS_REGION: ADES_STAGEOUT_AWS_REGION
        ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY: ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY
        ADES_STAGEOUT_AWS_SERVICEURL: ADES_STAGEOUT_AWS_SERVICEURL
        ADES_STAGEOUT_OUTPUT: ADES_STAGEOUT_OUTPUT
        aws_profiles_location: aws_profiles_location
        process: process
        wf_outputs: on_stage/wf_outputs
      out:
      - s3_catalog_output
      - wf_outputs_out
      run:
        arguments:
        - copy
        - -v
        - -r
        - '4'
        - -o
        - $( inputs.ADES_STAGEOUT_OUTPUT + "/" + inputs.process )
        - -res
        - $( inputs.process + ".res" )
        - valueFrom: "${\n    if( !Array.isArray(inputs.wf_outputs) )\n    {\n   \
            \     return inputs.wf_outputs.path + \"/catalog.json\";\n    }\n    var\
            \ args=[];\n    for (var i = 0; i < inputs.wf_outputs.length; i++)\n \
            \   {\n        args.push(inputs.wf_outputs[i].path + \"/catalog.json\"\
            );\n    }\n    return args;\n}\n"
        baseCommand: Stars
        class: CommandLineTool
        cwlVersion: v1.0
        doc: Run Stars for staging results
        hints:
          DockerRequirement:
            dockerPull: terradue/stars:1.0.0-beta.11
        id: stars
        inputs:
          ADES_STAGEOUT_AWS_ACCESS_KEY_ID:
            type: string?
          ADES_STAGEOUT_AWS_PROFILE:
            type: string?
          ADES_STAGEOUT_AWS_REGION:
            type: string?
          ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY:
            type: string?
          ADES_STAGEOUT_AWS_SERVICEURL:
            type: string?
          ADES_STAGEOUT_OUTPUT:
            type: string?
          aws_profiles_location:
            type: File?
          process:
            type: string?
          wf_outputs:
            type: Directory[]
        outputs:
          s3_catalog_output:
            outputBinding:
              outputEval: ${  return inputs.ADES_STAGEOUT_OUTPUT + "/" + inputs.process
                + "/catalog.json"; }
            type: string
          wf_outputs_out:
            outputBinding:
              glob: .
            type: Directory[]
        requirements:
          EnvVarRequirement:
            envDef:
              AWS_ACCESS_KEY_ID: $(inputs.ADES_STAGEOUT_AWS_ACCESS_KEY_ID)
              AWS_SECRET_ACCESS_KEY: $(inputs.ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY)
              AWS__ServiceURL: $(inputs.ADES_STAGEOUT_AWS_SERVICEURL)
              AWS__SignatureVersion: '2'
              PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          InlineJavascriptRequirement: {}
          ResourceRequirement: {}
    on_stage:
      in:
        lat_max: lat_max
        lat_min: lat_min
        lon_max: lon_max
        lon_min: lon_min
      out:
      - wf_outputs
      run: '#testapp'
- class: Workflow
  doc: testapp
  id: testapp
  inputs:
    lat_max:
      doc: Input maximum latitude
      label: lat_max
      type: float[]
    lat_min:
      doc: Input minimum latitude
      label: lat_min
      type: float[]
    lon_max:
      doc: Input maximum longitude
      label: lon_max
      type: float[]
    lon_min:
      doc: Input minimum longitude
      label: lon_min
      type: float[]
  label: lable inputs
  outputs:
  - id: wf_outputs
    outputSource:
    - step_1/results
    type: Directory[]
  requirements:
  - class: ScatterFeatureRequirement
  steps:
    step_1:
      in:
        lat_max: lat_max
        lat_min: lat_min
        lon_max: lon_max
        lon_min: lon_min
      out:
      - results
      run: '#clt'
      scatter:
      - lon_min
      - lon_max
      - lat_min
      - lat_max
      scatterMethod: flat_crossproduct
- arguments:
  - --lon_min
  - valueFrom: $( inputs.lon_min )
  - --lon_max
  - valueFrom: $( inputs.lon_max )
  - --lat_min
  - valueFrom: $( inputs.lat_min )
  - --lat_max
  - valueFrom: $( inputs.lat_max )
  baseCommand: testapp
  class: CommandLineTool
  id: clt
  inputs:
    lat_max:
      type: float
    lat_min:
      type: float
    lon_max:
      type: float
    lon_min:
      type: float
  outputs:
    results:
      outputBinding:
        glob: .
      type: Directory
  requirements:
    DockerRequirement:
      dockerPull: docker.test/testapp:1.0.0
    EnvVarRequirement:
      envDef:
        PATH: /srv/conda/envs/model-env/bin:/srv/conda/bin:/srv/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    InlineJavascriptRequirement: {}
    ResourceRequirement: {}
$namespaces:
  s: https://schema.org/
cwlVersion: v1.0
s:softwareVersion: 1.0.1
schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf