"""Tests for scripts/audit_boot_control.py.

Run: python3 -m unittest discover tests/audit
The build-layer tests compile a tiny host ELF with `cc` and skip without one.
"""

import contextlib
import importlib.util
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "audit_boot_control", ROOT / "scripts" / "audit_boot_control.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

MARK_VALID = "esp_ota_mark_app_valid_cancel_rollback"
CC = shutil.which("cc")


class AuditTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.project = self.tmp / "play"
        self.write("main/app.c", "void app_main(void) {}\n")

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, content, root=None):
        path = (root or self.project) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
        return path

    def run_audit(self, *extra_args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = audit.main([str(self.project), *extra_args])
        return code, out.getvalue()

    def build_layer(self, linked_symbols, cref_lines):
        """Create build/<app>.elf defining linked_symbols and a map with cref."""
        build = self.project / "build"
        build.mkdir()
        source = self.tmp / "elf.c"
        source.write_text(
            "".join(f"void {name}(void) {{}}\n" for name in linked_symbols)
            + "int main(void) { return 0; }\n")
        subprocess.run([CC, str(source), "-o", str(build / "play.elf")], check=True)
        (build / "play.map").write_text(
            "Memory Configuration\n\nCross Reference Table\n\n"
            "Symbol                                            File\n"
            + "\n".join(cref_lines) + "\n")

    def test_clean_project_passes(self):
        code, out = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("OK:", out)
        self.assertIn("build layer skipped", out)

    def test_mark_valid_in_component_blocks(self):
        self.write("components/cloud/cloud.c", f"void go(void) {{ {MARK_VALID}(); }}\n")
        code, out = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("BLOCKER", out)
        self.assertIn("components/cloud/cloud.c", out)

    def test_mark_valid_in_managed_component_blocks(self):
        self.write("managed_components/vendor__sdk/src/ota.cpp",
                   f"void go() {{ {MARK_VALID} (); }}\n")
        code, out = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("managed_components/vendor__sdk/src/ota.cpp", out)

    def test_mark_valid_in_extra_component_dir_blocks(self):
        extra = self.tmp / "shared_components"
        self.write("net/net.c", f"void go(void) {{ {MARK_VALID}(); }}\n", root=extra)
        self.assertEqual(self.run_audit()[0], 0)
        code, out = self.run_audit("--extra", str(extra))
        self.assertEqual(code, 1)
        self.assertIn("shared_components/net/net.c", out)

    def test_comments_and_longer_identifiers_are_ignored(self):
        self.write("main/notes.c",
                   f"// never call {MARK_VALID}() here\n"
                   f"/* {MARK_VALID}(); */\n"
                   f"void my_{MARK_VALID}_wrapper(void);\n")
        code, out = self.run_audit()
        self.assertEqual(code, 0, out)

    def test_build_directory_sources_are_skipped(self):
        self.write("build/generated.c", f"void go(void) {{ {MARK_VALID}(); }}\n")
        self.assertEqual(self.run_audit()[0], 0)

    def test_prebuilt_library_blocks(self):
        self.write("components/sdk/lib/libsdk.a",
                   b"!<arch>\n\0\0" + MARK_VALID.encode() + b"\0tail")
        code, out = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("prebuilt library", out)

    def test_set_boot_partition_is_allowed_only_in_launcher_contract(self):
        self.write("components/launcher_contract/launcher_contract.c",
                   "void f(void) { esp_ota_set_boot_partition(0); }\n")
        code, out = self.run_audit()
        self.assertEqual(code, 0)
        self.assertNotIn("REVIEW", out)

        self.write("main/update.c", "void g(void) { esp_ota_set_boot_partition(0); }\n")
        code, out = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("REVIEW: esp_ota_set_boot_partition in play/main/update.c", out)

    def test_lookalike_component_name_is_not_allowed(self):
        self.write("components/my_launcher_contract_fork/boot.c",
                   "void f(void) { esp_ota_set_boot_partition(0); }\n")
        _, out = self.run_audit()
        self.assertIn("REVIEW: esp_ota_set_boot_partition in play/components/my_launcher_contract_fork", out)

    def test_own_ota_path_gets_rollback_state_note(self):
        self.write("main/update.c", "void g(void) { esp_ota_begin(0, 0, 0); }\n")
        _, out = self.run_audit()
        self.assertIn("ESP_ERR_OTA_ROLLBACK_INVALID_STATE", out)

    @unittest.skipUnless(CC, "needs a host C compiler")
    def test_linked_dependency_blocks_and_names_the_library(self):
        self.build_layer(
            [MARK_VALID],
            [f"{MARK_VALID:<50}esp-idf/app_update/libapp_update.a(esp_ota_ops.c.obj)",
             f"{'':<50}esp-idf/cloud/libcloud.a(cloud.c.obj)"])
        code, out = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("libcloud.a(cloud.c.obj) (linked into play.elf)", out)
        self.assertNotIn("libapp_update.a", out)

    @unittest.skipUnless(CC, "needs a host C compiler")
    def test_unlinked_source_finding_is_demoted(self):
        self.write("components/cloud/cloud.c", f"void go(void) {{ {MARK_VALID}(); }}\n")
        self.build_layer([], [])
        code, out = self.run_audit()
        self.assertEqual(code, 0, out)
        self.assertIn("not linked into play.elf", out)
        self.assertNotIn("BLOCKER", out)

    @unittest.skipUnless(CC, "needs a host C compiler")
    def test_launcher_contract_linking_set_boot_partition_is_fine(self):
        self.build_layer(
            ["esp_ota_set_boot_partition"],
            [f"{'esp_ota_set_boot_partition':<50}esp-idf/app_update/libapp_update.a(esp_ota_ops.c.obj)",
             f"{'':<50}esp-idf/launcher_contract/liblauncher_contract.a(launcher_contract.c.obj)"])
        code, out = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("OK:", out)

    def test_missing_project_is_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(audit.main([str(self.tmp / "nope")]), 2)


if __name__ == "__main__":
    unittest.main()
