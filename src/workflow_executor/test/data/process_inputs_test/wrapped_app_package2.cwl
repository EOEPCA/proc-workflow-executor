$graph:
- $namespaces:
    cwltool: http://commonwl.org/cwltool#
  class: Workflow
  doc: Main stage manager
  hints:
    cwltool:Secrets:
      secrets:
      - ADES_STAGEIN_AWS_SERVICEURL
      - ADES_STAGEIN_AWS_REGION
      - ADES_STAGEIN_AWS_ACCESS_KEY_ID
      - ADES_STAGEIN_AWS_SECRET_ACCESS_KEY
      - ADES_STAGEOUT_AWS_SERVICEURL
      - ADES_STAGEOUT_AWS_ACCESS_KEY_ID
      - ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY
      - ADES_STAGEOUT_AWS_REGION
  id: main
  inputs:
    ADES_STAGEIN_AWS_ACCESS_KEY_ID:
      type: string?
    ADES_STAGEIN_AWS_REGION:
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
    aoi:
      doc: Area of interest expressed as Well-known text
      id: aoi
      label: Area of interest expressed as Well-known text
      type: string?
    aws_profiles_location:
      type: File?
    filter_threshold_size:
      doc: Filter raster polygons smaller than a provided threshold size (in pixels)
      id: filter_threshold_size
      label: Filter threshold
      type: string
    input_reference:
      doc: Input products reference list (ordered as pre and post event)
      id: input_reference
      label: Input products reference list (ordered as pre and post event)
      type: string[]
    process:
      type: string?
    reference_asset:
      doc: Reference asset to be used in the u,v displacement computation
      id: reference_asset
      label: Reference asset
      type:
      - symbols:
        - 1.nir
        - 1.red
        - 2.nir
        - 2.red
        type: enum
    reference_asset2:
      doc: Reference asset to be used in the u,v displacement computation
      id: reference_asset
      label: Reference asset
      symbols:
      - 1.nir
      - 1.red
      - 2.nir
      - 2.red
      type: enum

    threshold:
      doc: Threshold as negative decimal for the binarization of NDVIpost - NDVIpre
      id: threshold
      label: NDVI threshold
      type: string
  label: macro-cwl
  outputs:
    StacCatalogUri:
      outputSource:
      - node_stage_out/s3_catalog_output
      type: string
    results:
      id: results
      outputSource:
      - node_stage_out/results_out
      type: Directory
    s3_catalog_output:
      id: s3_catalog_output
      outputSource:
      - node_stage_out/s3_catalog_output
      type: string
  requirements:
    ScatterFeatureRequirement: {}
    SubworkflowFeatureRequirement: {}
  steps:
    node_stage_in:
      in:
        ADES_STAGEIN_AWS_ACCESS_KEY_ID: ADES_STAGEIN_AWS_ACCESS_KEY_ID
        ADES_STAGEIN_AWS_REGION: ADES_STAGEIN_AWS_REGION
        ADES_STAGEIN_AWS_SECRET_ACCESS_KEY: ADES_STAGEIN_AWS_SECRET_ACCESS_KEY
        ADES_STAGEIN_AWS_SERVICEURL: ADES_STAGEIN_AWS_SERVICEURL
        input: input_reference
      out:
      - input_reference_out
      run:
        baseCommand:
        - /bin/bash
        - stagein.sh
        class: CommandLineTool
        cwlVersion: v1.0
        doc: Run Stars for staging input data
        hints:
          DockerRequirement:
            dockerPull: terradue/stars:2.10.16
          cwltool:Secrets:
            secrets:
            - ADES_STAGEIN_AWS_SERVICEURL
            - ADES_STAGEIN_AWS_REGION
            - ADES_STAGEIN_AWS_ACCESS_KEY_ID
            - ADES_STAGEIN_AWS_SECRET_ACCESS_KEY
        id: stars
        inputs:
          ADES_STAGEIN_AWS_ACCESS_KEY_ID:
            type: string?
          ADES_STAGEIN_AWS_REGION:
            type: string?
          ADES_STAGEIN_AWS_SECRET_ACCESS_KEY:
            type: string?
          ADES_STAGEIN_AWS_SERVICEURL:
            type: string?
          input:
            type: string?
        outputs:
          input_reference_out:
            outputBinding:
              glob: .
            type: Directory
        requirements:
          EnvVarRequirement:
            envDef:
              Credentials__StacCatalog__Password: 198orY14Y1qWiwBj
              Credentials__StacCatalog__UriPrefix: https://supervisor.charter.uat.esaportal.eu
              Credentials__StacCatalog__Username: stars
              PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          InitialWorkDirRequirement:
            listing:
            - entry: "#!/bin/bash\n    export AWS__ServiceURL=$(inputs.ADES_STAGEIN_AWS_SERVICEURL)\n\
                \    export AWS__Region=$(inputs.ADES_STAGEIN_AWS_REGION)\n    export\
                \ AWS__AuthenticationRegion=$(inputs.ADES_STAGEIN_AWS_REGION)\n  \
                \  export AWS_ACCESS_KEY_ID=$(inputs.ADES_STAGEIN_AWS_ACCESS_KEY_ID)\n\
                \    export AWS_SECRET_ACCESS_KEY=$(inputs.ADES_STAGEIN_AWS_SECRET_ACCESS_KEY)\n\
                \    set -x \n    res=0\n    input='$( inputs.input )'\n    \n   \
                \ [ \"\\${input}\" != \"null\" ] && {\n\n        IFS='#' read -r -a\
                \ reference <<< '$( inputs.input )'\n        input_len=\\${#reference[@]}\n\
                \n        [[ \\${input_len} == 2 ]] && {\n            IFS=',' read\
                \ -r -a assets <<< \\${reference[1]}\n            af=\" \"\n     \
                \       for asset in \\${assets[@]}\n            do \n           \
                \   af=\"\\${af} -af \\${asset}\"\n            done\n        } ||\
                \ {\n          af=\"--empty\"\n        }\n        Stars copy --stop-on-error\
                \ -v -rel -r '4' \\${af} -o ./ \\${reference[0]}\n        res=$?\n\
                \    }\n    rm -fr stagein.sh\n    exit \\${res}"
              entryname: stagein.sh
          InlineJavascriptRequirement: {}
          ResourceRequirement: {}
      scatter: input
      scatterMethod: dotproduct
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
        wf_outputs: on_stage/results
      out:
      - s3_catalog_output
      - s3_catalog_output
      - results_out
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
        - valueFrom: "${\n    if( !Array.isArray(inputs.wf_outputs) ) \n    {\n  \
            \      return inputs.wf_outputs.path + \"/catalog.json\";\n    }\n   \
            \ var args=[];\n    for (var i = 0; i < inputs.wf_outputs.length; i++)\
            \ \n    {\n        args.push(inputs.wf_outputs[i].path + \"/catalog.json\"\
            );\n    }\n    return args;\n}\n"
        baseCommand:
        - /bin/bash
        - stageout.sh
        class: CommandLineTool
        cwlVersion: v1.0
        doc: Run Stars for staging results
        hints:
          DockerRequirement:
            dockerPull: terradue/stars:2.10.16
          cwltool:Secrets:
            secrets:
            - ADES_STAGEOUT_AWS_SERVICEURL
            - ADES_STAGEOUT_AWS_REGION
            - ADES_STAGEOUT_AWS_ACCESS_KEY_ID
            - ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY
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
            type: Directory
        outputs:
          results_out:
            outputBinding:
              glob: .
            type: Directory
          s3_catalog_output:
            outputBinding:
              outputEval: ${  return inputs.ADES_STAGEOUT_OUTPUT + "/" + inputs.process
                + "/catalog.json"; }
            type: string
        requirements:
          EnvVarRequirement:
            envDef:
              PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          InitialWorkDirRequirement:
            listing:
            - entry: '#!/bin/bash

                export AWS__ServiceURL=$(inputs.ADES_STAGEOUT_AWS_SERVICEURL)

                export AWS__Region=$(inputs.ADES_STAGEOUT_AWS_REGION)

                export AWS__AuthenticationRegion=$(inputs.ADES_STAGEOUT_AWS_REGION)

                export AWS_ACCESS_KEY_ID=$(inputs.ADES_STAGEOUT_AWS_ACCESS_KEY_ID)

                export AWS_SECRET_ACCESS_KEY=$(inputs.ADES_STAGEOUT_AWS_SECRET_ACCESS_KEY)

                Stars $@'
              entryname: stageout.sh
          InlineJavascriptRequirement: {}
          ResourceRequirement: {}
    on_stage:
      in:
        aoi: aoi
        filter_threshold_size: filter_threshold_size
        input_reference: node_stage_in/input_reference_out
        reference_asset: reference_asset
        threshold: threshold
      out:
      - results
      run: '#ndvicd'
- class: Workflow
  doc: The service makes a co-registration of two optical calibrated datasets acquired
    before and after an event. Later, it derives a binary change mask from the NDVI
    difference by using a threshold and a spatial filter. The output is a binary map
    representing the NDVI loss, given in raster and vector formats.
  id: ndvicd
  inputs:
    aoi:
      doc: Area of interest expressed as Well-known text
      label: Area of interest expressed as Well-known text
      type: string?
    filter_threshold_size:
      doc: Filter raster polygons smaller than a provided threshold size (in pixels)
      label: Filter threshold
      type: string
    input_reference:
      doc: Input products reference list (ordered as pre and post event)
      label: Input products reference list (ordered as pre and post event)
      type: Directory[]
    reference_asset:
      doc: Reference asset to be used in the u,v displacement computation
      label: Reference asset
      type:
      - symbols:
        - 1.nir
        - 1.red
        - 2.nir
        - 2.red
        type: enum
    threshold:
      doc: Threshold as negative decimal for the binarization of NDVIpost - NDVIpre
      label: NDVI threshold
      type: string
  label: NDVI Change Detection
  outputs:
    results:
      outputSource:
      - step_2/results
      type: Directory
  steps:
    step_1:
      in:
        aoi: aoi
        input_reference: input_reference
        reference_asset: reference_asset
        threshold: threshold
      out:
      - results
      run: '#ndvi_cd'
    step_2:
      in:
        filter_threshold_size: filter_threshold_size
        raster_stac: step_1/results
      out:
      - results
      run: '#qgis_processing'
- baseCommand: ndvi-change-detection
  class: CommandLineTool
  hints:
    DockerRequirement:
      dockerPull: docker.terradue.com/scombi-do:dev0.8.0
  id: ndvi_cd
  inputs:
    aoi:
      inputBinding:
        position: 2
        prefix: --aoi
      type: string?
    input_reference:
      type:
        inputBinding:
          position: 1
          prefix: --input_reference
        items: Directory
        type: array
    reference_asset:
      inputBinding:
        position: 3
        prefix: --reference_asset
      type:
        symbols:
        - 1.nir
        - 1.red
        - 2.nir
        - 2.red
        type: enum
    threshold:
      inputBinding:
        position: 4
        prefix: --threshold
      type: string
  outputs:
    results:
      outputBinding:
        glob: .
      type: Directory
  requirements:
    EnvVarRequirement:
      envDef:
        APP_DOCKER_IMAGE: docker.terradue.com/scombi-do:dev0.8.0
        APP_NAME: ndvi-change-detection
        APP_PACKAGE: app-ndvi-change-detection.dev.0.8.0
        APP_VERSION: 0.8.0
        PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/srv/conda/envs/env_scombi_do/bin
        _PROJECT: CPE
    ResourceRequirement:
      coresMax: 4
      ramMax: 24576
  stderr: std.err
  stdout: std.out
- arguments:
  - --param
  - polygonize=true
  - valueFrom: ${ if (inputs.filter_threshold_size != "-1") { return ["--param threshold="
      + inputs.filter_threshold_size]; } else { return ""; } }
  - --raster-stac
  - $( inputs.raster_stac )
  - --raster-asset
  - ndvi_change
  baseCommand:
  - /bin/bash
  - run.sh
  class: CommandLineTool
  id: qgis_processing
  inputs:
    filter_threshold_size:
      type: string
    raster_stac:
      type: Directory
  outputs:
    results:
      outputBinding:
        glob: .
      type: Directory
  requirements:
    DockerRequirement:
      dockerPull: docker.terradue.com/qgis-processing:0.3.0-develop
    EnvVarRequirement:
      envDef:
        PROJ_LIB: /opt/conda/envs/env_qgis/share/proj
        PYTHONPATH: /app:/opt/conda/envs/env_qgis/share/qgis/python:/opt/conda/envs/env_qgis/share/qgis/python/plugin:/opt/conda/envs/env_qgis/lib/python3.10/site-packages
    InitialWorkDirRequirement:
      listing:
      - entry: "#!/bin/bash\nqgis-processing --processing \"com:sievepolygonize\"\
          \ $@ \n\nrm -fr .local .config .cache run.sh"
        entryname: run.sh
    InlineJavascriptRequirement: {}
$namespaces:
  s: https://schema.org/
cwlVersion: v1.0
s:softwareVersion: 0.1.1
schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf