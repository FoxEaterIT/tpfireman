import json
import os
import tempfile
import unittest
from unittest import mock

import timeout_store


class TimeoutStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patcher = mock.patch.multiple(timeout_store, APP_DIR=self.temp.name,
                                           STORE_PATH=os.path.join(self.temp.name, "request_timeout.json"))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_missing_timeout_defaults_to_five_minutes(self):
        self.assertEqual(timeout_store.get_timeout(), 300)

    def test_edit_persists_positive_seconds(self):
        self.assertEqual(timeout_store.set_timeout("42.5"), 42.5)
        self.assertEqual(timeout_store.get_timeout(), 42.5)

    def test_invalid_values_are_rejected(self):
        for value in ("0", "-1", "nan", "inf", "nope"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                timeout_store.set_timeout(value)

    def test_damaged_file_is_not_silently_ignored(self):
        with open(timeout_store.STORE_PATH, "w", encoding="utf-8") as stream:
            json.dump({}, stream)
        with self.assertRaises(RuntimeError):
            timeout_store.get_timeout()


if __name__ == "__main__":
    unittest.main()
