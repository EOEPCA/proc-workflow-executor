import json
import os
import sys
import time
from os import path
from pprint import pprint
import pkg_resources
import yaml
from jinja2 import Template
from kubernetes import client
from kubernetes.client.rest import ApiException

from workflow_executor import helpers


def run(
    namespace, mount_folder, volume_name_prefix, workflow_name, outputfile, state=None
):

    # create an instance of the API class
    apiclient = helpers.get_api_client()
    api_instance = client.BatchV1Api(api_client=apiclient)
    pretty = True

    try:
        api_response = api_instance.read_namespaced_job_status(
            name=workflow_name, namespace=namespace, pretty=pretty
        )

        controller_uid = api_response.metadata.labels["controller-uid"]
        calrissian_log, output_log, usage_log = helpers.retrieveLogs(controller_uid, namespace)

        pprint(output_log)
        return output_log

    except ApiException as e:
        print("Exception when calling get result: %s\n" % e)
        raise e






def is_ready(podstatus) -> bool:
    """Check if the Pod is in the ready state.

    Returns:
        True if in the ready state; False otherwise.
    """

    # if there is no status, the pod is definitely not ready
    status = podstatus.status
    if status is None:
        return False

    # check the pod phase to make sure it is running. a pod in
    # the 'failed' or 'success' state will no longer be running,
    # so we only care if the pod is in the 'running' state.
    phase = status.phase
    if phase.lower() != "running":
        return False

    for cond in status.conditions:
        # we only care about the condition type 'ready'
        if cond.type.lower() != "ready":
            continue

        # check that the readiness condition is True
        return cond.status.lower() == "true"

    # Catchall
    return False
