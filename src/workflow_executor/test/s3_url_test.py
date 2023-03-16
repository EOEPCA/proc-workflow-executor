import unittest
import warnings
from os import path
import json
class MyTestCase(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore', ResourceWarning)




    def test_S3_url_with_projectid(self):

        test_folder_path = path.dirname(__file__)
        s3_access_json_file = path.join(test_folder_path, f"data/s3_access_test/s3_access_with_projectId.json")

        with open(s3_access_json_file, "r") as stream:
            s3_access_json = json.load(stream)

        bucketname = s3_access_json["storage"]["credentials"]["bucketname"]
        projectid = s3_access_json["storage"]["credentials"]["projectid"] if "projectid" in s3_access_json["storage"]["credentials"] else None


        s3_url = f"s3://{ projectid+':' if projectid else ''}{bucketname}"

        self.assertEqual(s3_url, "s3://fake-project-id:dev-test")



    def test_S3_url_without_projectid(self):

        test_folder_path = path.dirname(__file__)
        s3_access_json_file = path.join(test_folder_path, f"data/s3_access_test/s3_access_without_projectId.json")

        with open(s3_access_json_file, "r") as stream:
            s3_access_json = json.load(stream)

        bucketname = s3_access_json["storage"]["credentials"]["bucketname"]
        projectid = s3_access_json["storage"]["credentials"]["projectid"] if "projectid" in s3_access_json["storage"]["credentials"] else None


        s3_url = f"s3://{ projectid+':' if projectid else ''}{bucketname}"

        self.assertEqual(s3_url, "s3://dev-test")


if __name__ == '__main__':
    unittest.main()
