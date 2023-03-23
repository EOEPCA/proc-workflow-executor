import unittest
import warnings
from os import path
import json

from workflow_executor import helpers


class ErrorMessageTestCase(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore', ResourceWarning)

    def test_error_message_without_usage_report(self):

        test_folder_path = path.dirname(__file__)
        usage_report_file = path.join(test_folder_path, f"data/error_message_test/usage_report.json")
        error_messages_file = path.join(test_folder_path, f"data/error_message_test/error_message_templates.json")
        usage_report = None

        with open(error_messages_file, "r") as stream:
            error_messages = stream.read()

        k8s_error_msg = "Job has reached the specified backoff limit"
        namespace= "testnamespace"
        workflow_name = "s-expression"
        error_msg = helpers.generate_error_message_from_message_template(
            kubernetes_error=k8s_error_msg, error_message_templates=error_messages,
            usage_report=usage_report, namespace=namespace, workflow_name=workflow_name)

        print(error_msg)

        self.assertEqual(error_msg, "Unexpected application error occurred. ( exit codes:  , namespace: testnamespace, workflow_name: s-expression )")



    def test_error_message_with_usage_report(self):

        test_folder_path = path.dirname(__file__)
        usage_report_file = path.join(test_folder_path, f"data/error_message_test/usage_report.json")
        error_messages_file = path.join(test_folder_path, f"data/error_message_test/error_message_templates.json")

        with open(usage_report_file, "r") as stream:
            usage_report = stream.read()

        with open(error_messages_file, "r") as stream:
            error_messages = stream.read()

        k8s_error_msg = "Job has reached the specified backoff limit"
        namespace= "testnamespace"
        workflow_name = "s-expression"
        error_msg = helpers.generate_error_message_from_message_template(
            kubernetes_error=k8s_error_msg, error_message_templates=error_messages,
            usage_report=usage_report, namespace=namespace, workflow_name=workflow_name)

        print(error_msg)

        self.assertEqual(error_msg, "Unexpected application error occurred. ( exit codes:  [{\"step_1\": 0}, {\"step_2\": 0}, {\"step_3\": 33}], namespace: testnamespace, workflow_name: s-expression )")

if __name__ == '__main__':
    unittest.main()
