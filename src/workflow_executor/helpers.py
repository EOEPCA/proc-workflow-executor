import os

# import rm_client
import sys
from pprint import pprint
import yaml
from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
import boto3
from tenacity import retry, wait_fixed, stop_after_attempt
from string import Template
from . import eoepcaclient
import json


def get_api_client():
    proxy_url = os.getenv("HTTP_PROXY", None)

    if proxy_url:
        print("Setting proxy: {}".format(proxy_url))
        my_api_config = Configuration()
        my_api_config.host = proxy_url
        my_api_config.proxy = proxy_url
        my_api_config = client.ApiClient(my_api_config)
    elif 'KUBECONFIG' in os.environ and os.environ["KUBECONFIG"]:
        # this is needed because kubernetes-python does not consider
        # the KUBECONFIG env variable
        config.load_kube_config(config_file=os.environ["KUBECONFIG"])
        my_api_config = client.ApiClient()
    else:
        # if nothing is specified, kubernetes-python will use the file
        # in ~/.kube/config
        config.load_kube_config()
        my_api_config = client.ApiClient()

    return my_api_config


def create_configmap_object(source, namespace, configmap_name, dataname):
    configmap_dict = dict()
    with open(source) as f:
        source_content = f.read()
    configmap_dict[dataname] = source_content
    # Configurate ConfigMap metadata
    metadata = client.V1ObjectMeta(
        deletion_grace_period_seconds=30,
        name=configmap_name,
        namespace=namespace,
    )
    # Instantiate the configmap object
    configmap = client.V1ConfigMap(
        api_version="v1", kind="ConfigMap", data=configmap_dict, metadata=metadata
    )
    return configmap


def create_configmap(source, namespace, configmap_name, dataname):
    configmap = create_configmap_object(
        source=source,
        namespace=namespace,
        configmap_name=configmap_name,
        dataname=dataname,
    )
    api_client = get_api_client()
    api_instance = client.CoreV1Api(api_client)
    print("Creating configmap")
    try:
        api_response = api_instance.create_namespaced_config_map(
            namespace=namespace,
            body=configmap,
            pretty=True,
        )
        pprint(api_response)

    except ApiException as e:
        print(
            "Exception when calling CoreV1Api->create_namespaced_config_map: %s\n" % e
        )
        raise e


def getCwlWorkflowId(cwl_path):
    print("parsing cwl to retrieve the Workflow Id")
    with open(cwl_path, "r") as stream:
        try:
            graph = yaml.load(stream, Loader=yaml.FullLoader)["$graph"]
        except yaml.YAMLError as exc:
            print(exc, file=sys.stderr)

    for item in graph:
        if item.get("class") == "Workflow":
            return item.get("id")


def getCwlResourceRequirement(cwl_content):
    if not cwl_content:
        return None

    print("parsing cwl to retrieve the ResourceRequirements")
    try:
        graph = yaml.load(cwl_content, Loader=yaml.FullLoader)["$graph"]
    except yaml.YAMLError as exc:
        print(exc, file=sys.stderr)

    # TODO if the CWL has several CommandLineTool classes what do we do?
    # here it bails after the first one having expressed the requirements
    for item in graph:
        if item.get("class") == "CommandLineTool":
            try:
                return item["requirements"]["ResourceRequirement"]
            except KeyError:
                return None


@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(3))
def retrieve_logs(controller_uid, namespace, container="calrissian"):
    """
    Retrieves logs of a namespace job by container id.
    Default container id is set to 'calrissian'
    """

    # create an instance of the API class
    apiclient = get_api_client()
    core_v1 = client.CoreV1Api(api_client=apiclient)

    # controllerUid = api_response.metadata.labels["controller-uid"]
    pod_label_selector = "controller-uid=" + controller_uid
    pods_list = core_v1.list_namespaced_pod(
        namespace=namespace, label_selector=pod_label_selector, timeout_seconds=10
    )

    # instantiating log array
    log_array = []

    # ordering pods in creation time ascending order
    # ascending means the earliest date is shown first, the latest date is shown last
    pods_list.items.sort(key=lambda pod: pod.metadata.creation_timestamp)

    # iterate through pods to retrieve their logs
    for pod in pods_list.items:
        pod_name = pod.metadata.name
        try:
            # For whatever reason the response returns only the first few characters unless
            # the call is for `_return_http_data_only=True, _preload_content=False`
            log = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                _return_http_data_only=True,
                _preload_content=False,
                container=container
            ).data.decode("utf-8")
            log_array.append(log)

        except client.rest.ApiException as e:
            print("Exception when calling CoreV1Api->read_namespaced_pod_log: %s\n" % e)
            raise e
        except Exception as e:
            print("Exception when retrieving pod log: %s\n" % e)
            raise e
    return log_array


def store_logs(logs, path):
    f = open(path, "a")
    f.write(logs)
    f.close()


def getResourceManagerWorkspaceDetails(
        resource_manager_endpoint, platform_domain, workspace_name, user_id_token=None
):
    print("getResourceManagerWorkspaceDetails start")

    print("Registering client")
    demo = eoepcaclient.DemoClient(platform_domain)
    demo.register_client()
    demo.save_state()
    print("Client succesfully registered")

    print("Calling workspace api")
    workspace_access_token = None
    response, workspace_access_token = demo.workspace_get_details(
        service_base_url=resource_manager_endpoint,
        workspace_name=workspace_name,
        id_token=user_id_token,
        access_token=workspace_access_token,
    )
    print("getResourceManagerWorkspaceDetails end")
    return response


def registerResults(
        resource_manager_endpoint,
        platform_domain,
        workspace_name,
        result_url,
        user_id_token=None,
):
    print("registerResults start")

    print("Registering client")
    demo = eoepcaclient.DemoClient(platform_domain)
    demo.register_client()
    demo.save_state()
    print("Client succesfully registered")

    print("Calling workspace api")
    workspace_access_token = None
    response, workspace_access_token = demo.workspace_register(
        service_base_url=resource_manager_endpoint,
        workspace_name=workspace_name,
        result_url=result_url,
        id_token=user_id_token,
        access_token=workspace_access_token,
    )
    registration_details = response.json()
    print(json.dumps(registration_details, indent=2))

    print("registerResults end")
    return registration_details


def getS3Resource(aws_access_key_id, aws_secret_access_key, endpoint_url, region_name, bucket_name, resource_key):
    prefix = f"s3://{bucket_name}/"
    if resource_key.startswith(prefix):
        resource_key = resource_key[len(prefix):]

    session = boto3.session.Session()
    s3_client = session.client(
        service_name='s3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url,
        region_name=region_name
    )
    obj = s3_client.get_object(Bucket=bucket_name, Key=resource_key)
    return obj['Body'].read().decode('utf-8')


def get_namespace_list_from_label(label_selector):
    # retrieve the namespace to delete from jobid
    apiclient = get_api_client()
    api_instance = client.CoreV1Api(api_client=apiclient)
    try:
        namespace_list = api_instance.list_namespace(label_selector=label_selector)
    except ApiException as e:
        print("Exception when calling dismiss: %s\n" % e)
        raise e
    return namespace_list


def cast_string_to_type(string_to_cast, type_string):
    try:
        if type_string == "string":
            casted_value = string_to_cast
        elif type_string == "boolean":
            casted_value = bool(string_to_cast)
        else:
            # Python doesn’t provide an explicit “double” data type.
            # However, it provides the float type that behaves the same and has the same precision as doubles
            if type_string == "double":
                type_string = "float"

            # Python doesn’t provide an explicit “long” data type.
            # However, it provides the int type that behaves the same
            # A long is an integer type value that has unlimited length.
            if type_string == "long":
                type_string = "int"

            casted_value = eval(f"{type_string}({string_to_cast})")
        return casted_value
    except NameError:
        raise ValueError(f"Could not cast string value {string_to_cast} to type {type_string}")


def generate_error_message_from_message_template(kubernetes_error, error_message_templates=None, usage_report=None, namespace=None, workflow_name=None):

    if error_message_templates is None:
        return kubernetes_error

    try:
        error_message_templates_json = json.loads(error_message_templates)

        steps_exit_codes = ''
        if usage_report:
            # create a json from the exit codes
            steps_exit_codes = ', '.join(
                [f"{{\"{step['name']}\": {step['exit_code']}}}" for step in json.loads(usage_report)["children"]])
            steps_exit_codes = f"[{steps_exit_codes}]"

        error_msg_template = Template(error_message_templates_json[kubernetes_error])
        error_msg = error_msg_template.substitute(steps_exit_codes=steps_exit_codes, namespace=namespace, workflow_name=workflow_name)
        return error_msg
    except:
        return kubernetes_error




def get_error_message_templates():
    file_path = "/opt/error_message_templates/error_message_templates.json"

    if os.path.isfile(file_path):
        with open(file_path, "r") as stream:
            error_message_templates = stream.read()
        return error_message_templates
    else:
        return None