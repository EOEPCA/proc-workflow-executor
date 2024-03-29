import json
import os
import tempfile
import uvicorn
from fastapi import FastAPI, Form, File, status, Response, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from workflow_executor import prepare, client, result, clean, helpers, execute
from workflow_executor import status as ades_status
from pydantic import BaseModel
from kubernetes.client.rest import ApiException
from pprint import pprint
import yaml
from typing import Optional
from botocore.exceptions import ClientError

# import rm_client
from fastapi.exceptions import RequestValidationError, HTTPException

app = FastAPI(
    title="the title",
    description="the config",
    version="2.5.0",
    openapi_url="/api",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


class Error:
    def __init__(self):
        self.err = {"error": {"code": 0, "message": ""}}

    def set_error(self, code, msg):
        self.err["error"]["code"] = code
        self.err["error"]["message"] = msg

    def __str__(self):
        return self.err


class PrepareContent(BaseModel):
    serviceID: Optional[str] = None
    runID: Optional[str] = None
    cwl: Optional[str] = None


class ExecuteContent(PrepareContent):
    prepareID: Optional[str] = None
    cwl: Optional[str] = None
    inputs: Optional[str] = None
    username: Optional[str] = None
    userIdToken: Optional[str] = None
    bearerToken: Optional[str] = None
    registerResultUrl: Optional[str] = None
    workspaceResource: Optional[str] = None
    workflowIdHashtag: Optional[str] = None


def sanitize_k8_parameters(value: str):
    value = value.replace("_", "-").lower()
    while value.endswith("-"):
        value = value[:-1]
    return value


@app.get("/")
def read_root():
    return {"Hello": "World"}


"""
Executes namespace preparation
"""


@app.post("/prepare", status_code=status.HTTP_201_CREATED)
def read_prepare(content: PrepareContent, response: Response):
    state = client.State()
    print("Prepare POST")

    prepare_id = sanitize_k8_parameters(f"{content.serviceID}{content.runID}")
    if len(prepare_id) > 63:
        prepare_id = shorten_namespace(
            sanitize_k8_parameters(content.serviceID),
            sanitize_k8_parameters(content.runID),
        )

    # TODO create an enum class
    default_tmpVolumeSize = "4Gi"
    default_outputVolumeSize = "5Gi"

    tmpVolumeSize = os.getenv("VOLUME_TMP_SIZE", default_tmpVolumeSize)
    outputVolumeSize = os.getenv("VOLUME_OUTPUT_SIZE", default_outputVolumeSize)

    volume_name_prefix = "volume"
    storage_class_name = os.getenv("STORAGE_CLASS", None)
    cwlResourceRequirement = helpers.getCwlResourceRequirement(content.cwl)

    if cwlResourceRequirement:
        if "tmpdirMax" in cwlResourceRequirement:
            print(
                f"setting tmpdirMax to {cwlResourceRequirement['tmpdirMax']} as specified in the CWL"
            )
            tmpVolumeSize = f"{cwlResourceRequirement['tmpdirMax']}Mi"
        if "outdirMax" in cwlResourceRequirement:
            print(
                f"setting outdirMax to {cwlResourceRequirement['outdirMax']} as specified in the CWL"
            )
            outputVolumeSize = f"{cwlResourceRequirement['outdirMax']}Mi"

    ades_namespace = os.getenv("ADES_NAMESPACE", None)

    # image pull secrets
    image_pull_secrets_json = os.getenv("IMAGE_PULL_SECRETS", None)

    if image_pull_secrets_json is not None:
        with open(image_pull_secrets_json) as json_file:
            image_pull_secrets = json.load(json_file)
    else:
        image_pull_secrets = {}

    # job_namespace_labels
    job_namespace_labels_json = os.getenv("ADES_JOB_NAMESPACE_LABELS", None)
    if job_namespace_labels_json is not None:
        job_namespace_labels = json.loads(job_namespace_labels_json)
    else:
        job_namespace_labels = {}

    # this label is usefull to link the k8s job to the zooproject process
    job_namespace_labels["processid"] = content.runID

    print("namespace: %s" % prepare_id)
    print(f"tmpVolumeSize: {tmpVolumeSize}")
    print(f"outputVolumeSize: {outputVolumeSize}")
    print("volume_name: %s" % volume_name_prefix)

    try:
        resp_status = prepare.run(
            namespace=prepare_id,
            tmpVolumeSize=tmpVolumeSize,
            outputVolumeSize=outputVolumeSize,
            volumeName=volume_name_prefix,
            state=state,
            storage_class_name=storage_class_name,
            imagepullsecrets=image_pull_secrets,
            ades_namespace=ades_namespace,
            job_namespace_labels=job_namespace_labels
        )
    except ApiException as e:
        response.status_code = e.status

    return {"prepareID": prepare_id}


"""
Returns prepare status
"""


@app.get("/prepare/{prepare_id}", status_code=status.HTTP_200_OK)
def read_prepare(prepare_id: str, response: Response):
    state = client.State()
    print("Prepare GET")
    namespace = prepare_id
    # volumeName = sanitize_k8_parameters(f"{content.serviceID}volume")

    try:
        resp_status = prepare.get(namespace=namespace, state=state)
    except ApiException as e:
        response.status_code = e.status

    print(resp_status)
    if resp_status["status"] == "pending":
        response.status_code = status.HTTP_100_CONTINUE

    return resp_status
    # 200 done
    # 100 ripassa dopo
    # 500 error


"""
Executes workflow
"""


@app.post("/execute", status_code=status.HTTP_201_CREATED)
def read_execute(content: ExecuteContent, response: Response):
    # {"runID": "runID-123","serviceID": "service-id-123", "prepareID":"uuid" ,"cwl":".......","inputs":".........."}

    state = client.State()
    print("Execute POST")

    namespace = content.prepareID
    cwl_content = content.cwl
    workflowIdHashtag = content.workflowIdHashtag
    inputs_content = json.loads(content.inputs)
    volume_name_prefix = "volume"
    workflow_name = sanitize_k8_parameters(f"wf-{content.runID}")
    mount_folder = "/workflow"

    # cwl_wrapper config
    cwl_wrapper_config = dict()
    cwl_wrapper_config["maincwl"] = os.getenv("ADES_WFEXEC_MAINCWL", None)
    cwl_wrapper_config["stagein"] = os.getenv("ADES_WFEXEC_STAGEIN_CWL", None)
    cwl_wrapper_config["stageout"] = os.getenv("ADES_WFEXEC_STAGEOUT_CWL", None)
    cwl_wrapper_config["rulez"] = os.getenv("ADES_WFEXEC_RULEZ_CWL", None)

    # read ADES config variables
    with open(os.getenv("ADES_CWL_INPUTS", None)) as f:
        cwl_inputs = yaml.load(f, Loader=yaml.FullLoader)

    # read ADES config variables
    if os.getenv("ADES_POD_ENV_VARS"):
        with open(os.getenv("ADES_POD_ENV_VARS", None)) as f:
            pod_env_vars = yaml.load(f, Loader=yaml.FullLoader)
    else:
        pod_env_vars = dict()

        # read ADES pod node selectors
    if os.getenv("ADES_POD_NODESELECTORS"):
        with open(os.getenv("ADES_POD_NODESELECTORS")) as f:
            pod_nodeselectors = yaml.load(f, Loader=yaml.FullLoader)
    else:
        pod_nodeselectors = dict()

    # read USE_RESOURCE_MANAGER variable
    useResourceManagerStageOut = os.getenv("USE_RESOURCE_MANAGER", False)
    useResourceManagerStageOut = str(useResourceManagerStageOut).lower() in [
        "true",
        "1",
        "y",
        "yes",
    ]

    if content.username is not None:
        resource_manager_user = content.username
        pod_env_vars["_USERNAME"] = resource_manager_user

    # read RESOURCE MANAGER stageout variables
    userIdToken=None
    bearerToken=None
    if useResourceManagerStageOut:
        # retrieving bearerToken
        bearerToken = content.bearerToken
        if bearerToken is None:
            #bearerToken was not provided, trying to retrieve userIdToken
            userIdToken = content.userIdToken
            if userIdToken is None:
                e = Error()
                e.set_error(12, "Bearer token or User-Id-Token header is missing or is invalid")
                response.status_code = status.HTTP_400_BAD_REQUEST
                return e

        # retrieving resource manager workspace prefix
        rmWorkspacePrefix = os.getenv("RESOURCE_MANAGER_WORKSPACE_PREFIX", "rm-user")

        # retrieving rm endpoint and user
        resource_manager_endpoint = os.getenv("RESOURCE_MANAGER_ENDPOINT", None)

        platform_domain = os.getenv("ADES_PLATFORM_DOMAIN", None)

        if resource_manager_endpoint is None:
            e = Error()
            e.set_error(12, "Resource Manager endpoint is missing or is invalid")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return e

        if platform_domain is None:
            e = Error()
            e.set_error(12, "Platform domain is missing or is invalid")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return e

        if resource_manager_user is None:
            e = Error()
            e.set_error(12, "Username is missing or is invalid")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return e

        # temporary naming convention for resource mananeger workspace name: "rm-user-<username>"
        workspace_id = f"{rmWorkspacePrefix}-{resource_manager_user}".lower()

        # retrieve workspace details
        try:
            response = helpers.getResourceManagerWorkspaceDetails(
                resource_manager_endpoint=resource_manager_endpoint,
                platform_domain=platform_domain,
                workspace_name=workspace_id,
                access_token=bearerToken,
                user_id_token=userIdToken
            )
        except UnboundLocalError as e:
            # UnboundLocalError: local variable 'ticket' referenced before assignment
            error_message = "401 (Unauthorized) Error retrieving workspace access details. Please check your Resource "\
                            "Manager endpoint configuration."
            e = Error()
            e.set_error(12, error_message)
            response.status_code = response.status_code
            return e

        if response.status_code != 200:
            print(response.text)
            e = Error()
            e.set_error(12, f"Error retrieving workspace details. {response.text}")
            response.status_code = response.status_code
            return e
        workspaceDetails = response.json()

        try:
            endpoint = workspaceDetails["storage"]["credentials"]["endpoint"]
            access = workspaceDetails["storage"]["credentials"]["access"]
            bucketname = workspaceDetails["storage"]["credentials"]["bucketname"]
            projectid = workspaceDetails["storage"]["credentials"]["projectid"] if "projectid" in \
                                                                                 workspaceDetails["storage"][
                                                                                     "credentials"] else None
            secret = workspaceDetails["storage"]["credentials"]["secret"]
            region = workspaceDetails["storage"]["credentials"]["region"] if "region" in workspaceDetails["storage"][
                "credentials"] else None

            cwl_inputs["STAGEOUT_AWS_SERVICEURL"] = endpoint
            cwl_inputs["STAGEOUT_AWS_ACCESS_KEY_ID"] = access
            cwl_inputs["STAGEOUT_AWS_SECRET_ACCESS_KEY"] = secret
            if region:
                cwl_inputs["STAGEOUT_AWS_REGION"] = region
            cwl_inputs["STAGEOUT_OUTPUT"] = f"s3://{projectid + ':' if projectid else ''}{bucketname}"

        except KeyError:
            e = Error()
            e.set_error(
                12, "Resource Manager access credentials are missing or are invalid"
            )
            response.status_code = status.HTTP_400_BAD_REQUEST
            return e

    for k, v in cwl_inputs.items():
        inputs_content["inputs"].append(
            {
                "id": "ADES_" + k,
                "dataType": "string",
                "value": v,
                "mimeType": "",
                "href": "",
            }
        )

    inputs_content["inputs"].append(
        {
            "id": "job",
            "dataType": "string",
            "value": workflow_name,
            "mimeType": "",
            "href": "",
        }
    )

    inputs_content["inputs"].append(
        {
            "id": "outputfile",
            "dataType": "string",
            "value": f"{workflow_name}.res",
            "mimeType": "",
            "href": "",
        }
    )

    default_max_ram_value = "1G"
    default_max_cores_value = "2"
    max_ram = os.getenv("JOB_MAX_RAM", default_max_ram_value)
    max_cores = os.getenv("JOB_MAX_CORES", default_max_cores_value)

    cwlResourceRequirement = helpers.getCwlResourceRequirement(cwl_content)
    if cwlResourceRequirement:
        if "ramMax" in cwlResourceRequirement:
            print(
                f"setting ramMax to {cwlResourceRequirement['ramMax']}Mi as specified in the CWL"
            )
            max_ram = f"{cwlResourceRequirement['ramMax']}Mi"
        if "coresMax" in cwlResourceRequirement:
            print(
                f"setting coresMax to {cwlResourceRequirement['coresMax']} as specified in the CWL"
            )
            max_cores = str(cwlResourceRequirement["coresMax"])

    print(f"inputs_content")
    pprint(inputs_content)
    # inputcwlfile is input_json + cwl_file
    # create 2 temp files
    with tempfile.NamedTemporaryFile(mode="w") as cwl_file, tempfile.NamedTemporaryFile(
            mode="w"
    ) as input_json:
        cwl_file.write(cwl_content)
        cwl_file.flush()
        cwl_file.seek(0)

        input_json.write(json.dumps(inputs_content))
        input_json.flush()
        input_json.seek(0)

        print(cwl_file.name)
        print(input_json.name)

        try:
            resp_status = execute.run(
                state=state,
                cwl_document=cwl_file.name,
                job_input_json=input_json.name,
                volume_name_prefix=volume_name_prefix,
                mount_folder=mount_folder,
                namespace=namespace,
                workflow_name=workflow_name,
                cwl_wrapper_config=cwl_wrapper_config,
                pod_env_vars=pod_env_vars,
                pod_nodeselectors=pod_nodeselectors,
                max_ram=max_ram,
                max_cores=max_cores,
                workflowIdHashtag=workflowIdHashtag
            )
        except ApiException as e:
            print(e.body)
            response.status_code = e.status
            response.body = e.body
            resp_status = {"status": "failed", "error": e.body}
        except ValueError as ve:
            print(str(ve))
            response.status_code = 400
            response.body = str(ve)
            resp_status = {"status": "failed", "error": str(ve)}

    return {"jobID": workflow_name}


"""
Returns workflow status
"""


@app.get(
    "/status/{service_id}/{run_id}/{prepare_id}/{job_id}",
    status_code=status.HTTP_200_OK,
)
def read_getstatus(
        service_id: str, run_id: str, prepare_id: str, job_id: str, response: Response
):
    namespace = prepare_id
    workflow_name = sanitize_k8_parameters(f"wf-{run_id}")

    keepworkspaceiffailedString = os.getenv("JOB_KEEPWORKSPACE_IF_FAILED", "True")
    keepworkspaceiffailed = str(keepworkspaceiffailedString).lower() in [
        "true",
        "1",
        "y",
        "yes",
    ]

    state = client.State()
    print("Status GET")

    resp_status = None
    from fastapi import status

    try:
        resp_status = ades_status.run(namespace=namespace, workflow_name=workflow_name)

        if resp_status["status"] == "Running":
            response.status_code = status.HTTP_200_OK
            status = {"percent": 50, "msg": "running"}
        elif resp_status["status"] == "Success":
            response.status_code = status.HTTP_200_OK
            status = {"percent": 100, "msg": "done"}
        elif resp_status["status"] == "Failed":
            e = Error()

            k8s_error_message = resp_status["error"]
            usage_report = resp_status["usage_log"] if "usage_log" in resp_status else None
            error_message_templates = helpers.get_error_message_templates()

            # if an error message template list is provided, we will modify the error msg returned
            # by k8s with a more human-readable msg
            error_msg = helpers.generate_error_message_from_message_template(
                kubernetes_error=k8s_error_message, error_message_templates=error_message_templates,
                usage_report=usage_report, namespace=namespace, workflow_name=workflow_name)
            e.set_error(12, error_msg)


            # if keepworkspaceiffailed is false, namespace will be discarded
            if not keepworkspaceiffailed:
                print("Removing Workspace")
                clean_job_status = clean_job(namespace)
                if isinstance(clean_job_status, Error):
                    return clean_job_status
                else:
                    pprint(clean_job_status)
                print("Removing Workspace Success")

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=e.err
            )

    except ApiException as err:
        e = Error()
        e.set_error(12, err.body)

        # if keepworkspaceiffailed is false, namespace will be discarded
        if not keepworkspaceiffailed:
            print("Removing Workspace")
            clean_job_status = clean_job(namespace)
            if isinstance(clean_job_status, Error):
                return clean_job_status
            else:
                pprint(clean_job_status)
            print("Removing Workspace Success")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=e.err
        )

    return status


"""
Returns workflow result
"""


@app.get(
    "/result/{service_id}/{run_id}/{prepare_id}/{job_id}",
    status_code=status.HTTP_200_OK,
)
def read_getresult(
        service_id: str, run_id: str, prepare_id: str, job_id: str, response: Response
):
    namespace = prepare_id
    keepworkspaceiffailedString = os.getenv("JOB_KEEPWORKSPACE_IF_FAILED", "True")
    keepworkspaceiffailed = str(keepworkspaceiffailedString).lower() in [
        "true",
        "1",
        "y",
        "yes",
    ]

    print("Result GET")

    try:
        resp_status = result.run(
            namespace=namespace
        )
        print("getresult success")

        # removing wf_outputs
        result_json = json.loads(resp_status)
        if "wf_outputs" in result_json:
            del result_json["wf_outputs"]

        json_compatible_item_data = {"wf_output": json.dumps(result_json)}
        print("wf_output json: ")
        pprint(json_compatible_item_data)
        print("job success")

        keepworkspaceString = os.getenv("JOB_KEEPWORKSPACE", "False")
        keepworkspace = str(keepworkspaceString).lower() in ["true", "1", "y", "yes"]

        if not keepworkspace:
            print("Removing Workspace")
            clean_job_status = clean_job(namespace)
            if isinstance(clean_job_status, Error):
                return clean_job_status
            else:
                pprint(clean_job_status)
            print("Removing Workspace Success")

    except ApiException as err:
        e = Error()
        e.set_error(12, err.body)
        print(err.body)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if not keepworkspaceiffailed:
            print("Removing Workspace")
            clean_job_status = clean_job(namespace)
            if isinstance(clean_job_status, Error):
                return clean_job_status
            else:
                pprint(clean_job_status)
            print("Removing Workspace Success")

        return e

    return JSONResponse(content=json_compatible_item_data)


"""
Registers results
"""


@app.post("/register", status_code=status.HTTP_201_CREATED)
def read_register_results(content: ExecuteContent, response: Response):
    try:
        # read USE_RESOURCE_MANAGER variable
        useResourceManagerStageOut = os.getenv("USE_RESOURCE_MANAGER", False)
        useResourceManagerStageOut = str(useResourceManagerStageOut).lower() in [
            "true",
            "1",
            "y",
            "yes",
        ]

        # read RESOURCE MANAGER stageout variables
        if useResourceManagerStageOut:

            userIdToken = None
            bearerToken = None

            # retrieving bearerToken
            bearerToken = content.bearerToken
            if bearerToken is None:
                # bearerToken was not provided, trying to retrieve userIdToken
                userIdToken = content.userIdToken
                if userIdToken is None:
                    e = Error()
                    e.set_error(12, "Bearer token or User-Id-Token header is missing or is invalid")
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return e

            # retrieving resource manager workspace prefix
            rmWorkspacePrefix = os.getenv(
                "RESOURCE_MANAGER_WORKSPACE_PREFIX", "rm-user"
            )

            # retrieving rm endpoint and user
            resource_manager_endpoint = os.getenv("RESOURCE_MANAGER_ENDPOINT", None)
            resource_manager_user = content.username

            platform_domain = os.getenv("ADES_PLATFORM_DOMAIN", None)

            if resource_manager_endpoint is None:
                e = Error()
                e.set_error(12, "Resource Manager endpoint is missing or is invalid")
                response.status_code = status.HTTP_400_BAD_REQUEST
                return e

            if platform_domain is None:
                e = Error()
                e.set_error(12, "Platform domain is missing or is invalid")
                response.status_code = status.HTTP_400_BAD_REQUEST
                return e

            if resource_manager_user is None:
                e = Error()
                e.set_error(12, "Username is missing or is invalid")
                response.status_code = status.HTTP_400_BAD_REQUEST
                return e

            # temporary naming convention for resource mananeger workspace name: "rm-user-<username>"
            workspace_id = f"{rmWorkspacePrefix}-{resource_manager_user}".lower()

            # register results
            registrationDetails = helpers.registerResults(
                resource_manager_endpoint=resource_manager_endpoint,
                platform_domain=platform_domain,
                workspace_name=workspace_id,
                result_url=content.registerResultUrl,
                user_id_token=userIdToken,
                access_token=bearerToken
            )

    except ApiException as err:
        e = Error()
        e.set_error(12, err.body)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return e


"""
Returns workspace details
"""


@app.post(
    "/workspace_details",
    status_code=status.HTTP_200_OK,
)
def read_workspace_details(content: ExecuteContent, response: Response):
    print(content)
    # retrieving userIdToken
    userIdToken = content.userIdToken
    if userIdToken is None:
        e = Error()
        e.set_error(12, "User Id Token is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    # retrieving resource manager workspace prefix
    rmWorkspacePrefix = os.getenv(
        "RESOURCE_MANAGER_WORKSPACE_PREFIX", "rm-user"
    )

    # retrieving rm endpoint and user
    resource_manager_endpoint = os.getenv("RESOURCE_MANAGER_ENDPOINT", None)
    resource_manager_user = content.username

    platform_domain = os.getenv("ADES_PLATFORM_DOMAIN", None)

    if resource_manager_endpoint is None:
        e = Error()
        e.set_error(12, "Resource Manager endpoint is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    if platform_domain is None:
        e = Error()
        e.set_error(12, "Platform domain is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    if resource_manager_user is None:
        e = Error()
        e.set_error(12, "Username is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    # temporary naming convention for resource mananeger workspace name: "rm-user-<username>"
    workspace_id = f"{rmWorkspacePrefix}-{resource_manager_user}".lower()

    # get workspace details
    response = helpers.getResourceManagerWorkspaceDetails(
        resource_manager_endpoint=resource_manager_endpoint,
        platform_domain=platform_domain,
        workspace_name=workspace_id,
        user_id_token=userIdToken
    )

    if response.status_code != 200:
        print(response.text)
        e = Error()
        e.set_error(12, f"Error retrieving workspace details. {response.text}")
        response.status_code = response.status_code
        return e

    workspaceDetails = response.json()

    return JSONResponse(content=workspaceDetails["storage"]["credentials"])


"""
Returns workspace details
"""


@app.post(
    "/workspace_resource",
    status_code=status.HTTP_200_OK,
)
def read_workspace_resource(content: ExecuteContent, response: Response):
    print(content)
    # retrieving userIdToken
    userIdToken = content.userIdToken
    if userIdToken is None:
        e = Error()
        e.set_error(12, "User Id Token is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    workspaceResource = content.workspaceResource
    if workspaceResource is None:
        e = Error()
        e.set_error(12, "Workspace resource is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    # retrieving resource manager workspace prefix
    rmWorkspacePrefix = os.getenv(
        "RESOURCE_MANAGER_WORKSPACE_PREFIX", "rm-user"
    )

    # retrieving rm endpoint and user
    resource_manager_endpoint = os.getenv("RESOURCE_MANAGER_ENDPOINT", None)
    resource_manager_user = content.username

    platform_domain = os.getenv("ADES_PLATFORM_DOMAIN", None)

    if resource_manager_endpoint is None:
        e = Error()
        e.set_error(12, "Resource Manager endpoint is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    if platform_domain is None:
        e = Error()
        e.set_error(12, "Platform domain is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    if resource_manager_user is None:
        e = Error()
        e.set_error(12, "Username is missing or is invalid")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return e

    # temporary naming convention for resource mananeger workspace name: "rm-user-<username>"
    workspace_id = f"{rmWorkspacePrefix}-{resource_manager_user}".lower()

    # get workspace details
    response = helpers.getResourceManagerWorkspaceDetails(
        resource_manager_endpoint=resource_manager_endpoint,
        platform_domain=platform_domain,
        workspace_name=workspace_id,
        user_id_token=userIdToken
    )

    if response.status_code != 200:
        print(response.text)
        e = Error()
        e.set_error(12, f"Error retrieving workspace details. {response.text}")
        response.status_code = response.status_code
        return e

    credentials = response.json()["storage"]["credentials"]
    print(credentials)
    try:
        response = helpers.getS3Resource(aws_access_key_id=credentials["access"],
                                         aws_secret_access_key=credentials["secret"],
                                         endpoint_url=credentials["endpoint"],
                                         region_name=credentials["region"],
                                         bucket_name=credentials["bucketname"],
                                         resource_key=workspaceResource)

        print(response)
        return Response(content=response, media_type="application/text")
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            e = Error()
            e.set_error(12, f"No such key {workspaceResource}. Requested object is missing from the bucket ")
            response.status_code = response.status_code
            return e
        else:
            e = Error()
            e.set_error(12,
                        f"Error retrieving workspace resource. {ex.response['Error']['Code']}: {ex.response['Error']['Message']}")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return e


@app.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
)
def read_dismiss_job(job_id: str, response: Response):
    label_selector = f"processid={job_id}"

    # retrieve the namespace to delete from jobid
    namespace_list = helpers.get_namespace_list_from_label(label_selector=label_selector)

    if len(namespace_list.items) == 0:
        # no namespaces found
        dismiss_response_json = {
            "jobID": job_id,
            "status": "not_found",
            "message": "Job not found"
        }
        response.status_code = status.HTTP_404_NOT_FOUND
        return JSONResponse(status_code=404, content=dismiss_response_json)

    else:
        # namespace found
        namespace_name = namespace_list.items[0].metadata.name
        print(f"Removing namespace: {namespace_name}")
        clean_status = clean_job(namespace_name)
        print(clean_status)
        dismiss_response_json = {
            "jobID": job_id,
            "status": "dismissed",
            "message": "Job dismissed"
        }
        print(f"Removing namespace done")
    return JSONResponse(content=dismiss_response_json)


"""
Removes Kubernetes namespace
"""


def clean_job(namespace: str):
    clean_status = {}
    try:
        clean_status = clean.run(namespace=namespace)
        return clean_status
    except ApiException as err:
        if err.status == 404:
            # the namespace does not exist or has already been deleted
            print("Namespace not found.")
        else:
            e = Error()
            e.set_error(12, err.body)
            print(err.body)
            return e


"""
Shortens namespace name to respect K8 64 chars limit
"""


def shorten_namespace(serviceId, runId):
    new_namespace = f"{serviceId}{runId}"
    while len(new_namespace) > 63:
        serviceId = serviceId[:-1]
        while serviceId.endswith("-"):
            serviceId = serviceId[:-1]
        new_namespace = f"{serviceId}{runId}"

    return new_namespace


def main():
    print("DEBuG MODE")
    uvicorn.run(app)


if __name__ == "__main__":
    main()
