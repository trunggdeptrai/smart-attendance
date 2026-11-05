"""Kiểm thử đăng nhập: băm mật khẩu và chặn truy cập khi chưa đăng nhập."""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth import check_credentials, hash_password, verify_password  # noqa: E402


class HashTests(unittest.TestCase):
    def test_hash_is_salted_and_verifiable(self):
        first, second = hash_password("matkhau"), hash_password("matkhau")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("matkhau", first))
        self.assertFalse(verify_password("sai", first))
        self.assertNotIn("matkhau", first)

    def test_malformed_hash_rejected(self):
        self.assertFalse(verify_password("x", "khong-hop-le"))
        self.assertFalse(verify_password("x", None))

    def test_check_credentials(self):
        config = {"username": "admin", "password_hash": hash_password("abc@")}
        self.assertTrue(check_credentials("admin", "abc@", config))
        self.assertTrue(check_credentials(" admin ", "abc@", config))
        self.assertFalse(check_credentials("admin", "abc", config))
        self.assertFalse(check_credentials("root", "abc@", config))
        self.assertFalse(check_credentials("admin", "abc@", None))


class AppGateTests(unittest.TestCase):
    def setUp(self):
        os.environ["SMART_ATTENDANCE_ADMIN_USER"] = "admin"
        os.environ["SMART_ATTENDANCE_ADMIN_PASSWORD_HASH"] = hash_password("abc@")

    def _app(self):
        from streamlit.testing.v1 import AppTest

        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)

    def test_app_shows_only_login_form_before_login(self):
        at = self._app().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.title[0].value, "SMART ATTENDANCE")
        self.assertEqual(len(at.text_input), 2)
        self.assertNotIn("Trang tổng quan", [t.value for t in at.title])

    def test_wrong_then_right_password(self):
        at = self._app().run()
        at.text_input[0].input("admin")
        at.text_input[1].input("sai")
        at.button[0].click().run()
        self.assertTrue(any("Sai tên đăng nhập" in e.value for e in at.error))
        at.text_input[0].input("admin")
        at.text_input[1].input("abc@")
        at.button[0].click().run()
        self.assertEqual(at.session_state["auth_user"], "admin")
        self.assertEqual(len(at.exception), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
