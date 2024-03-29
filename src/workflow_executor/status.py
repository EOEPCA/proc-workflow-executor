import os
from pprint import pprint
import time
import kubernetes.client
from kubernetes.client.rest import ApiException
from kubernetes import client, config
from workflow_executor import helpers

ADES_LOGS_PATH = "/var/www/_run/res"


def run(namespace, workflow_name):
    # create an instance of the API class
    apiclient = helpers.get_api_client()
    api_instance = client.BatchV1Api(api_client=apiclient)
    pretty = True

    print("## JOB STATUS")

    try:
        api_response = api_instance.read_namespaced_job_status(
            name=workflow_name, namespace=namespace, pretty=pretty
        )

        if api_response.status.active:
            status = {"status": "Running", "error": "", "usage_log": ""}
            pprint(status)
            return status
        elif api_response.status.succeeded:
            controller_uid = api_response.metadata.labels["controller-uid"]

            # Retrieving and storing CALRISSIAN logs
            calrissian_log_array = helpers.retrieve_logs(controller_uid=controller_uid, namespace=namespace,
                                                   container="calrissian")

            for idx, calrissian_log_attempt in enumerate(calrissian_log_array):
                helpers.store_logs(
                    calrissian_log_attempt, os.path.join(ADES_LOGS_PATH, f"{namespace}_{idx}_calrissian.log")
                )

            # Retrieving and storing OUTPUT logs
            output_log_file = os.path.join(ADES_LOGS_PATH, f"{namespace}_output.json")
            output_log = helpers.retrieve_logs(controller_uid=controller_uid, namespace=namespace,
                                               container="sidecar-container-output")[-1]
            helpers.store_logs(output_log, output_log_file)

            # Retrieving and storing USAGE logs
            usage_log = helpers.retrieve_logs(controller_uid=controller_uid, namespace=namespace,
                                              container="sidecar-container-usage")[-1]
            helpers.store_logs(
                usage_log, os.path.join(ADES_LOGS_PATH, f"{namespace}_usage.json")
            )

            # returning Success status
            status = {
                "status": "Success",
                "error": "",
                "usage_log": usage_log if usage_log is not None else ''
            }

        elif api_response.status.failed:

            controller_uid = api_response.metadata.labels["controller-uid"]

            # Retrieving and storing CALRISSIAN logs
            calrissian_log_array = helpers.retrieve_logs(controller_uid=controller_uid, namespace=namespace,
                                                   container="calrissian")
            for idx, calrissian_log_attempt in enumerate(calrissian_log_array):
                helpers.store_logs(
                    calrissian_log_attempt, os.path.join(ADES_LOGS_PATH, f"{namespace}_{idx}_calrissian.log")
                )

            # Retrieving and storing USAGE logs
            usage_log = helpers.retrieve_logs(controller_uid=controller_uid, namespace=namespace,
                                              container="sidecar-container-usage")[-1]
            helpers.store_logs(
                usage_log, os.path.join(ADES_LOGS_PATH, f"{namespace}_usage.json")
            )

            # returning Failed status
            status = {
                "status": "Failed",
                "error": api_response.status.conditions[0].message,
                "usage_log": usage_log if usage_log is not None else ''
            }

        pprint(status)
        return status

    except ApiException as e:
        if e.status == 404:
            # the  namespace does not exist or has been deleted
            status = {
                "status": "Failed",
                "error": "namespace not found",
                "usage_log": ""
            }
            return status

        print("Exception when calling get status: %s\n" % e)
        raise e
    except Exception as e:
        print("Exception when calling get status:: %s\n" % e)
        raise e
