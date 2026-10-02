import unittest

from app.identity import device_identity, digest


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.key = "a-test-signing-key-with-at-least-32-bytes"

    def test_signed_cookie_restores_same_device(self):
        identity, cookie, fresh = device_identity(None, self.key)
        self.assertTrue(fresh)
        self.assertEqual(device_identity(cookie, self.key), (identity, cookie, False))

    def test_new_devices_and_forged_cookies_have_separate_workspaces(self):
        first, cookie, _ = device_identity(None, self.key)
        second, _, _ = device_identity(None, self.key)
        forged, _, fresh = device_identity(cookie[:-1] + "x", self.key)
        self.assertTrue(fresh)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, forged)

    def test_ip_hashes_are_separate_from_device_identity(self):
        ip = digest(self.key, "ip", "192.0.2.1")
        self.assertNotIn("192.0.2.1", ip)
        self.assertNotEqual(ip, digest(self.key, "workspace", "192.0.2.1"))


if __name__ == "__main__":
    unittest.main()
