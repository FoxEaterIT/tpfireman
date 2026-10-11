"""Live integration tests against JSONPlaceholder; requires an internet connection."""
import json
import subprocess
import sys
import unittest
from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "main.py"
BASE_URL = "https://jsonplaceholder.typicode.com/posts"


class JSONPlaceholderTests(unittest.TestCase):
    def run_client(self, method, url, payload=None):
        input_text = ""
        if payload is not None:
            input_text = "y\n" + json.dumps(payload) + "\n"
        return subprocess.run(
            [sys.executable, str(MAIN), method, url],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def assert_success_status(self, result, status):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Status Code: {}".format(status), result.stdout)

    def test_get(self):
        result = self.run_client("GET", BASE_URL + "/1")
        self.assert_success_status(result, 200)
        self.assertIn('"id": 1', result.stdout)

    def test_post(self):
        result = self.run_client(
            "POST", BASE_URL,
            {"title": "tpfireman test", "body": "integration test", "userId": 1},
        )
        self.assert_success_status(result, 201)
        self.assertIn('"id": 101', result.stdout)

    def test_put(self):
        result = self.run_client(
            "PUT", BASE_URL + "/1",
            {"id": 1, "title": "tpfireman test", "body": "integration test", "userId": 1},
        )
        self.assert_success_status(result, 200)
        self.assertIn('"title": "tpfireman test"', result.stdout)

    def test_patch(self):
        result = self.run_client(
            "PATCH", BASE_URL + "/1", {"title": "tpfireman patch test"}
        )
        self.assert_success_status(result, 200)
        self.assertIn('"title": "tpfireman patch test"', result.stdout)

    def test_delete(self):
        result = self.run_client("DELETE", BASE_URL + "/1")
        self.assert_success_status(result, 200)
        self.assertIn("{}", result.stdout)


if __name__ == "__main__":
    unittest.main()
