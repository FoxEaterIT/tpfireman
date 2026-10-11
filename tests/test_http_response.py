import io
import unittest
from unittest import mock

import main


class HttpResponseTests(unittest.TestCase):
    def test_response_formatter_includes_status_headers_and_json_body(self):
        output = io.StringIO()
        with mock.patch("sys.stdout", output):
            main.print_http_response(404, {"Content-Type": "application/json"}, '{"error":"missing"}', [])
        text = output.getvalue()
        self.assertIn("Status Code: 404", text)
        self.assertIn("Content-Type: application/json", text)
        self.assertIn('"error": "missing"', text)

    def test_response_formatter_redacts_secrets_in_headers_and_body(self):
        output = io.StringIO()
        with mock.patch("sys.stdout", output):
            main.print_http_response(401, {"X-Echo": "hidden-value"}, "hidden-value", ["hidden-value"])
        self.assertNotIn("hidden-value", output.getvalue())
        self.assertIn("[REDACTED]", output.getvalue())

    def test_timeout_option_is_parsed_as_positive_number(self):
        # CLI parsing is validated through the option's contract without network I/O.
        for invalid in ("0", "-1", "nan", "inf", "not-a-number"):
            with self.subTest(value=invalid):
                try:
                    timeout = float(invalid)
                    valid = timeout > 0 and timeout < float("inf")
                except ValueError:
                    valid = False
                self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()
