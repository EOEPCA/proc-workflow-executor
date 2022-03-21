import os
import signal
import time
from celery import Celery, states

from workflow_executor import prepare, client, result, clean, helpers, execute
from typing import Optional
from pydantic import BaseModel
import json
from kubernetes.client.rest import ApiException


app = Celery(__name__)
app.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
app.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")


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
    registerResultUrl: Optional[str] = None
    workspaceResource: Optional[str] = None
    workflowIdHashtag: Optional[str] = None

def sanitize_k8_parameters(value: str):
    value = value.replace("_", "-").lower()
    while value.endswith("-"):
        value = value[:-1]
    return value

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

@app.task(name="create_task")
def create_task(task_type):
    time.sleep(int(task_type) * 10)
    return True


@app.task(name="prepare_resources_task",bind=True)
def prepare_resources_task(self,json_payload,prepare_id):

    def mark_as_fail(*args):
        print("marking failed")
        self.update_state(state=states.FAILURE)


    signal.signal(signal.SIGTERM, mark_as_fail)

    for i in range(30):
        print(f"I am demo task {i}")
        time.sleep(1)

    return {"prepareID": prepare_id}

    content = PrepareContent(**json.loads(json_payload))


    print(content.serviceID)
    state = client.State()
    print("Prepare POST")


    # TODO create an enum class
    default_tmpVolumeSize = "4Gi"
    default_outputVolumeSize = "5Gi"

    tmpVolumeSize = os.getenv("VOLUME_TMP_SIZE", default_tmpVolumeSize)
    outputVolumeSize = os.getenv("VOLUME_OUTPUT_SIZE", default_outputVolumeSize)

    volumeName = sanitize_k8_parameters(f"{content.serviceID}-volume")
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
        job_namespace_labels = None

    print("namespace: %s" % prepare_id)
    print(f"tmpVolumeSize: {tmpVolumeSize}")
    print(f"outputVolumeSize: {outputVolumeSize}")
    print("volume_name: %s" % volumeName)

    try:
        resp_status = prepare.run(
            namespace=prepare_id,
            tmpVolumeSize=tmpVolumeSize,
            outputVolumeSize=outputVolumeSize,
            volumeName=volumeName,
            state=state,
            storage_class_name=storage_class_name,
            imagepullsecrets=image_pull_secrets,
            ades_namespace=ades_namespace,
            job_namespace_labels=job_namespace_labels
        )
    except ApiException as e:
        #response.status_code = e.status
        print(e.status)
    return {"prepareID": prepare_id}