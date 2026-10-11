import os
import tempfile
import unittest
from unittest import mock

import main


class ExportTests(unittest.TestCase):
    def test_export_writes_to_selected_path_and_pretty_prints_json(self):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, "nested", "result.txt")
            os.mkdir(os.path.dirname(target))
            result = main.export_response("GET", "https://example.com", '{"ok":true}', 200, target)
            self.assertEqual(result, target)
            with open(target, encoding="utf-8") as stream:
                contents = stream.read()
            self.assertIn('"ok": true', contents)
            self.assertIn("Status Code: 200", contents)

    def test_existing_file_requires_confirmation_and_decline_preserves_it(self):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, "response.txt")
            with open(target, "w", encoding="utf-8") as stream:
                stream.write("original")
            with mock.patch("builtins.input", return_value="n"):
                result = main.export_response("GET", "https://example.com", "new", 200, target)
            self.assertIsNone(result)
            with open(target, encoding="utf-8") as stream:
                self.assertEqual(stream.read(), "original")

    def test_existing_file_is_overwritten_only_after_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, "response.txt")
            with open(target, "w", encoding="utf-8") as stream:
                stream.write("original")
            with mock.patch("builtins.input", return_value="y"):
                main.export_response("GET", "https://example.com", "new", 200, target)
            with open(target, encoding="utf-8") as stream:
                self.assertIn("new", stream.read())
                self.assertNotIn("original", stream.read())


if __name__ == "__main__":
    unittest.main()
