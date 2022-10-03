import os
from kubernetes.client.rest import ApiException
ADES_LOGS_PATH = "/var/www/_run/res"

def run(namespace):
    # create an instance of the API class
    try:
        output_file = os.path.join(ADES_LOGS_PATH, f"{namespace}_output.json")
        with open(output_file) as output_log:
            return output_log.read()
    except FileNotFoundError as e:
        print(f"File '{namespace}_output.json' does not exist.")
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
