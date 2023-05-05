import unittest
from workflow_executor import execute
from workflow_executor import helpers
import warnings
import os
from os import path


class CastingInputTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore', ResourceWarning)

    def test_cast_string_to_float(self):
        string_to_cast = "9.00000000"
        casted = helpers.cast_string_to_type(string_to_cast, "float")

        type_of_casted_value = str(type(casted))
        print(type_of_casted_value)
        print('Float Value =', casted)

        self.assertEqual(type_of_casted_value, "<class 'float'>")  # add assertion here

    def test_cast_string_to_double(self):
        string_to_cast = "9.00000000"
        casted = helpers.cast_string_to_type(string_to_cast, "double")

        type_of_casted_value = str(type(casted))
        print(type_of_casted_value)
        print('Double Value =', casted)

        self.assertEqual(type_of_casted_value, "<class 'float'>")  # add assertion here

    def test_cast_string_to_integer(self):
        string_to_cast = "9"
        casted = helpers.cast_string_to_type(string_to_cast, "int")

        type_of_casted_value = str(type(casted))
        print(type_of_casted_value)
        print('integer Value =', casted)

        self.assertEqual(type_of_casted_value, "<class 'int'>")  # add assertion here

    def test_cast_string_to_long(self):
        string_to_cast = "9"
        casted = helpers.cast_string_to_type(string_to_cast, "long")

        type_of_casted_value = str(type(casted))
        print(type_of_casted_value)
        print('integer Value =', casted)

        self.assertEqual(type_of_casted_value, "<class 'int'>")

    def test_cast_string_to_boolean(self):
        string_to_cast = "1"
        casted = helpers.cast_string_to_type(string_to_cast, "boolean")

        type_of_casted_value = str(type(casted))
        print(type_of_casted_value)
        print('Boolean value =', casted)

        self.assertEqual(type_of_casted_value, "<class 'bool'>")  # add assertion here

    def test_cast_string_to_string(self):
        string_to_cast = "ENC[AES256_GCM,data:h8/iEYN6qskqWxwHdI0R1VHFTHnAg8D2VTG5NLZjUqr2PSSi," \
                         "iv:vSUDMwXyFzFtw6ull36yPCxfadXgUJm0kLtwLdfoFDs=,tag:WwErVlj4+DVUSHO0gSGnAw==,type:str]"
        casted = helpers.cast_string_to_type(string_to_cast, "string")

        type_of_casted_value = str(type(casted))
        print(type_of_casted_value)
        print('String Value =', casted)

        self.assertEqual(type_of_casted_value, "<class 'str'>")  # add assertion here

    def test_process_inputs(self):
        test_folder_path = os.path.dirname(__file__)
        cwl = path.join(test_folder_path, f"data/process_inputs_test/wrapped_app_package.cwl")
        inputs = path.join(test_folder_path, f"data/process_inputs_test/inputs.json")

        processed_inputs = execute.process_inputs(cwl_document=cwl, job_input_json_file=inputs)
        print(processed_inputs)

        self.assertEqual(True, True)

    def test_process_inputs2(self):
        test_folder_path = os.path.dirname(__file__)
        cwl = path.join(test_folder_path, f"data/process_inputs_test/wrapped_app_package2.cwl")
        inputs = path.join(test_folder_path, f"data/process_inputs_test/inputs2.json")

        processed_inputs = execute.process_inputs(cwl_document=cwl, job_input_json_file=inputs)
        print(processed_inputs)

        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
