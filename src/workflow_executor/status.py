import os
from pprint import pprint
import time
import kubernetes.client
from kubernetes.client.rest import ApiException
from kubernetes import client, config
from workflow_executor import helpers

ADES_LOGS_PATH = "/var/www/_run/res"


def run(namespace, workflow_name, service_id, run_id, state=None):
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
            status = {"status": "Running", "error": ""}
            pprint(status)
            return status
        elif api_response.status.succeeded:
            controller_uid = api_response.metadata.labels["controller-uid"]

            # Retrieving and storing CALRISSIAN logs
            calrissian_log = helpers.retrieveLogs(controllerUid=controller_uid, namespace=namespace,
                                                  container="calrissian")
            helpers.storeLogs(
                calrissian_log, os.path.join(ADES_LOGS_PATH, f"{namespace}_calrissian.log")
            )

            # Retrieving and storing OUTPUT logs
            output_log_file = os.path.join(ADES_LOGS_PATH, f"{namespace}_output.json")
            try:
                output_log = helpers.retrieveLogs(controllerUid=controller_uid, namespace=namespace,
                                                      container="sidecar-container-output")
            except Exception as e:
                # if the python kubernetes is encountering
                ades_stageout_output = os.getenv("ADES_STAGEOUT_OUTPUT")
                output_log = f"{ades_stageout_output}/{service_id}/catalog.json"
            helpers.storeLogs(output_log, output_log_file)

            # Retrieving and storing USAGE logs
            usage_log = helpers.retrieveLogs(controllerUid=controller_uid, namespace=namespace,
                                                  container="sidecar-container-usage")
            helpers.storeLogs(
                usage_log, os.path.join(ADES_LOGS_PATH, f"{namespace}_usage.json")
            )

            # returning Success status
            status = {"status": "Success", "error": ""}

        elif api_response.status.failed:

            controller_uid = api_response.metadata.labels["controller-uid"]

            # Retrieving and storing CALRISSIAN logs
            calrissian_log = helpers.retrieveLogs(controllerUid=controller_uid, namespace=namespace,
                                                  container="calrissian")
            helpers.storeLogs(
                calrissian_log, os.path.join(ADES_LOGS_PATH, f"{namespace}_calrissian.log")
            )

            # returning Failed status
            status = {
                "status": "Failed",
                "error": api_response.status.conditions[0].message,
            }

        pprint(status)
        return status

    except ApiException as e:
        print("Exception when calling get status: %s\n" % e)
        raise e
