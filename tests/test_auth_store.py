import unittest
from unittest import mock
import auth_store


class AuthStoreTests(unittest.TestCase):
    def test_unknown_auth_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            auth_store._profile_by("missing", [])

    def test_profile_name_lookup_is_case_insensitive(self):
        profile = {"id": "abc", "name": "Work", "type": "Bearer"}
        self.assertIs(auth_store._profile_by("work", [profile]), profile)

    def test_delete_requires_confirmation_for_named_profiles(self):
        profile = {"id": "1", "name": "a", "type": "Bearer"}
        with mock.patch.object(auth_store, "_read", return_value=[profile]), \
             mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(auth_store, "_write") as write:
            auth_store.auth_command(["auth", "delete", "a"])
            write.assert_not_called()

    def test_list_never_displays_secret_fields(self):
        profile = {"id": "abc", "name": "Work", "type": "Bearer", "secret": "encrypted-value"}
        with mock.patch.object(auth_store, "_read", return_value=[profile]), \
             mock.patch("builtins.print") as printer:
            auth_store.auth_command(["auth", "list"])
        output = " ".join(str(call.args[0]) for call in printer.call_args_list)
        self.assertNotIn("encrypted-value", output)

    @mock.patch("sys.platform", "linux")
    def test_dpapi_is_platform_limited(self):
        with self.assertRaisesRegex(RuntimeError, "Windows DPAPI"):
            auth_store._crypt("secret")

    def test_basic_username_and_password_are_not_echoed(self):
        answers = iter(["username", "secret"])
        with mock.patch.object(auth_store, "_prompt", side_effect=lambda *args, **kwargs: next(answers)) as prompt:
            values = auth_store._collect("Basic")
        self.assertTrue(prompt.call_args_list[0].kwargs.get("hidden", prompt.call_args_list[0].args[1] if len(prompt.call_args_list[0].args) > 1 else False))
        self.assertTrue(prompt.call_args_list[1].kwargs.get("hidden", prompt.call_args_list[1].args[1] if len(prompt.call_args_list[1].args) > 1 else False))

        self.assertEqual(values["username"], "username")
        self.assertEqual(values["password"], "secret")


if __name__ == "__main__":
    unittest.main()
