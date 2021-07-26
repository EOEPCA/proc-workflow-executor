import os
import shutil
import unittest
from os import path
from fastapi.testclient import TestClient
from workflow_executor import fastapiserver as app
from workflow_executor import clean
from pprint import pprint
from pytest_kind import KindCluster
import time
import warnings


class FastApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore', ResourceWarning)
        print("Creating kubernetes test cluster")
        cls.cluster = KindCluster("workflow-executor-test-cluster")
        cls.cluster.create()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.environ["KUBECONFIG"] = f"{THIS_DIR}/{cls.cluster.kubeconfig_path}"

    @classmethod
    def tearDownClass(cls):
        print("Deleting kubernetes test cluster")
        cls.cluster.delete()

        try:
            THIS_DIR = os.path.dirname(os.path.abspath(__file__))
            shutil.rmtree(f'{THIS_DIR}/.pytest-kind')
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))

    def setUp(self):
        app_name="vegetation-index"
        #app_name="s-expression"
        self.client = TestClient(app.app)
        self.serviceID = "vegetation-index"
        self.runID = "abc123abc123"
        self.prepareId = "vegetation-indexabc123abc123"

        test_folder_path = os.path.dirname(__file__)
        cwl = path.join(test_folder_path, f"{app_name}_test/{app_name}.cwl")
        inputs = path.join(test_folder_path, f"{app_name}_test/inputs.json")

        f = open(cwl, "r")
        self.cwl_content = f.read()
        f.close()

        f = open(inputs, "r")
        self.inputs_content = f.read()
        f.close()

        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.environ["STORAGE_HOST"] = "https://nx10438.your-storageshare.de/"
        os.environ["STORAGE_USERNAME"] = "eoepca-demo-storage"
        os.environ["STORAGE_APIKEY"] = "FakeApiKey"
        os.environ["STORAGE_CLASS"] = "glusterfs-storage"
        os.environ["IMAGE_PULL_SECRETS"] = f"{THIS_DIR}/{app_name}_test/imagepullsecrets.json"
        os.environ["ADES_POD_ENV_VARS"] = f"{THIS_DIR}/{app_name}_test/pod_env_vars.yaml"
        os.environ["ADES_CWL_INPUTS"] = f"{THIS_DIR}/{app_name}_test/wfinputs.yaml"


    def test_step1_get_root(self):
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Hello": "World"}

    def test_step2_post_prepare(self):
        response = self.client.post(
            "/prepare",
            json={
                "runID": self.runID,
                "serviceID": self.serviceID,
                "cwl": self.cwl_content,
            },
        )
        assert response.status_code == 201
        assert response.json() == {"prepareID": self.prepareId}

    def test_step3_get_prepare(self):
        response = self.client.get(f"/prepare/{self.prepareId}")

        attempts = 0
        while response.status_code != 200 and attempts < 3:
            attempts += 1
            response = self.client.get(f"/prepare/{self.prepareId}")
            time.sleep(1)

    def test_step4_post_execute(self):
        content = {
            "runID": self.runID,
            "serviceID": self.serviceID,
            "prepareID": self.prepareId,
            "cwl": self.cwl_content,
            "inputs": self.inputs_content,
            "userIdToken": "",
            "registerResultUrl": "",
            "username": ""
        }

        pprint(content)


        #### This part of the test cannot be done because it is not possible to bound pvc with kindtest
        # # this delay/retry is a workaround
        # # for further details check https://github.com/kubernetes/kubernetes/issues/66689#issuecomment-460748704
        # for i in range(0, 2):
        #     while True:
        #         response = self.client.post("/execute", json=content)
        #         if response.status_code == 403:
        #             print("response 403, retrying in 2 seconds")
        #             time.sleep(2)
        #             continue
        #         break
        #     break
        # assert response.status_code == 201
        #
        # print(response.json())
        # assert response.json() == {'jobID': f"wf-{self.runID}"}

        time.sleep(40)
        status = 200
        while status == 200:
            response = self.client.get(f"/status/{self.serviceID}/{self.runID}/{self.prepareId}/{self.runID}")
            pprint(response)
            status = response.status_code
            time.sleep(2)
        pprint(response)


    def test_step5_post_clean(self):
        clean.run(self.prepareId)



if __name__ == "__main__":
    unittest.main()
