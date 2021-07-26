import os
import unittest
from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
from pprint import pprint
from pytest_kind import KindCluster
import time

class MyTestCase(unittest.TestCase):
    def test_something(self):
        print("Creating kubernetes test cluster")
        cluster = KindCluster("workflow-executor-test-cluster")
        cluster.create()
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        os.environ["KUBECONFIG"] = f"{THIS_DIR}/{cluster.kubeconfig_path}"

        print(f"load_kube_config: {os.environ['KUBECONFIG']}")
        f = open(os.environ["KUBECONFIG"], 'r')
        content = f.read()
        print(content)
        f.close()
        config.load_kube_config(config_file=os.environ['KUBECONFIG'])
        my_api_config = client.ApiClient()

        v1 = client.CoreV1Api()
        print("Listing pods with their IPs:")
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

        print("Deleting kubernetes test cluster")
        cluster.delete()
        #self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
