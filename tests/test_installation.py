import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class InstallationChecks(unittest.TestCase):
    def test_installer_copies_app_and_adds_per_user_bin_to_path(self):
        script = (ROOT / "install.ps1").read_text(encoding="utf-8")
        self.assertIn('"Programs\\tpfireman"', script)
        self.assertIn('"tpfireman.bat"', script)
        self.assertIn('Copy-Item -LiteralPath $sourceMainPath', script)
        self.assertIn('Copy-Item -LiteralPath $sourceAuthPath', script)
        self.assertIn('Get-Command python', script)
        self.assertIn('Join-Path $scriptDir "update.ps1"', script)
        self.assertIn('FoxEaterIT/tpfireman', (ROOT / "update.ps1").read_text(encoding="utf-8"))
        self.assertIn('tpfireman-source.zip', (ROOT / "update.ps1").read_text(encoding="utf-8"))
        self.assertIn('Copy-Item -LiteralPath $sourceUninstallPath', script)
        self.assertIn('Copy-Item -LiteralPath $sourceVersionPath', script)
        self.assertIn('Copy-Item -LiteralPath $sourceUpdatePath', script)
        self.assertIn('Copy-Item -LiteralPath $sourceReadmePath', script)
        self.assertIn('SetEnvironmentVariable("Path", $newPath, "User")', script)
        self.assertIn('Administrator)) {', script)
        self.assertLess(script.index("$sourceWrapperPath"), script.index('$oldPath ='))

    def test_wrapper_resolves_main_relative_to_wrapper_and_forwards_arguments(self):
        wrapper = (ROOT / "bin" / "tpfireman.bat").read_text(encoding="utf-8")
        self.assertIn('"%APP_DIR%\\main.py" %*', wrapper)
        self.assertIn('"%APP_DIR%\\uninstall.ps1"', wrapper)
        self.assertIn('"%APP_DIR%\\VERSION"', wrapper)
        self.assertIn('"%APP_DIR%\\update.ps1"', wrapper)
        self.assertIn('powershell -NoProfile -ExecutionPolicy Bypass', wrapper)
        self.assertIn("exit /b", wrapper)

    def test_version_file_and_uninstaller_remove_application_and_all_user_data(self):
        self.assertRegex((ROOT / "VERSION").read_text(encoding="utf-8").strip(), r"^\d+\.\d+\.\d+$")
        uninstaller = (ROOT / "uninstall.ps1").read_text(encoding="utf-8")
        self.assertIn('Type YES to continue', uninstaller)
        self.assertIn('Remove-Item -LiteralPath $installPath -Recurse -Force', uninstaller)
        self.assertIn('Remove-Item -LiteralPath $dataPath -Recurse -Force', uninstaller)
        self.assertIn('including auth profiles, were removed', uninstaller)

    def test_powershell_scripts_are_parseable_when_powershell_is_available(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            self.skipTest("PowerShell is not available in this environment")
        for script_name in ("install.ps1", "uninstall.ps1", "update.ps1"):
            with self.subTest(script=script_name):
                result = subprocess.run(
                    [powershell, "-NoProfile", "-Command",
                     "$scriptPath = $env:TPFIREMAN_PARSE_PATH; $tokens = $null; $errors = $null; [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors) | Out-Null; if ($errors.Count -eq 0) { exit 0 } else { $errors | Out-String | Write-Error; exit 1 }"],
                    env={**os.environ, "TPFIREMAN_PARSE_PATH": str(ROOT / script_name)},
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    @unittest.skipUnless(os.name == "nt", "Requires Windows")
    def test_wrapper_usage_invokes_python_without_changing_current_directory(self):
        wrapper = ROOT / "bin" / "tpfireman.bat"
        with tempfile.TemporaryDirectory() as working_directory:
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", str(wrapper), "auth", "unknown"],
                cwd=working_directory, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: tpfireman auth", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Requires a Windows non-administrator account")
    def test_current_windows_token_is_not_elevated(self):
        import ctypes
        from ctypes import wintypes

        class TOKEN_ELEVATION(ctypes.Structure):
            _fields_ = [("TokenIsElevated", wintypes.DWORD)]

        token = wintypes.HANDLE()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi32.OpenProcessToken.restype = wintypes.BOOL
        advapi32.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        advapi32.GetTokenInformation.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        self.assertTrue(advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)))
        try:
            elevation = TOKEN_ELEVATION()
            returned = wintypes.DWORD()
            self.assertTrue(advapi32.GetTokenInformation(token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(returned)))
            self.assertEqual(elevation.TokenIsElevated, 0, "Run this test in a standard, non-elevated Windows terminal")
        finally:
            kernel32.CloseHandle(token)


if __name__ == "__main__":
    unittest.main()
