import os

# import rm_client
import sys
from pprint import pprint

import yaml
from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
import boto3


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


def retrieveLogs(controllerUid, namespace):
    # create an instance of the API class
    apiclient = get_api_client()
    api_instance = client.BatchV1Api(api_client=apiclient)
    core_v1 = client.CoreV1Api(api_client=apiclient)

    # controllerUid = api_response.metadata.labels["controller-uid"]
    pod_label_selector = "controller-uid=" + controllerUid
    pods_list = core_v1.list_namespaced_pod(
        namespace=namespace, label_selector=pod_label_selector, timeout_seconds=10
    )
    pod_name = pods_list.items[0].metadata.name
    try:
        # For whatever reason the response returns only the first few characters unless
        # the call is for `_return_http_data_only=True, _preload_content=False`
        calrissian_log = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            _return_http_data_only=True,
            _preload_content=False,
            container="calrissian"
        ).data.decode("utf-8")

        output_log = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            _return_http_data_only=True,
            _preload_content=False,
            container="sidecar-container-output"
        ).data.decode("utf-8")

        usage_log = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            _return_http_data_only=True,
            _preload_content=False,
            container="sidecar-container-usage"
        ).data.decode("utf-8")

        return calrissian_log, output_log, usage_log

    except client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->read_namespaced_pod_log: %s\n" % e)
        raise e


def storeLogs(logs, path):
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


def getS3Resource(aws_access_key_id,aws_secret_access_key,endpoint_url,region_name,bucket_name, resource_key):

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
