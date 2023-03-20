import unittest
import warnings
from os import path
import json

from workflow_executor import helpers


class ErrorMessageTestCase(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore', ResourceWarning)

    def test_error_message(self):

        test_folder_path = path.dirname(__file__)
        usage_report_file = path.join(test_folder_path, f"data/error_message_test/usage_report.json")

        with open(usage_report_file, "r") as stream:
            usage_report = stream.read()

        error_msg = helpers.generate_error_message_from_usage_report(usage_report)

        print(error_msg)


        self.assertEqual(error_msg, "Unexpected application error occurred.\nstep_1: 0\nstep_2: 0\nstep_3: 33")


if __name__ == '__main__':
    unittest.main()
