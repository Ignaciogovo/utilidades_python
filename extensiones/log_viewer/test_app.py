import os
import unittest

os.environ.update(
    SECRET_KEY="test-secret-key-with-at-least-thirty-two-characters",
    ADMIN_USERNAME="admin",
    ADMIN_PASSWORD="correct-horse-battery",
    COOKIE_SECURE="false",
)

from app import app


class LoginTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_login_protects_dashboard_and_logout(self):
        for stylesheet in ("retro.css", "classic.css"):
            response = self.client.get(f"/static/{stylesheet}")
            self.assertEqual(response.status_code, 200)
            response.close()
        self.assertEqual(self.client.get("/").status_code, 302)
        self.client.get("/login")
        with self.client.session_transaction() as session:
            csrf = session["csrf"]

        response = self.client.post("/login", data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "correct-horse-battery",
        })
        self.assertEqual(response.status_code, 302)
        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("retro.css", dashboard.get_data(as_text=True))
        classic = self.client.get("/?theme=classic").get_data(as_text=True)
        self.assertIn("classic.css", classic)
        dark = self.client.get("/?theme=retro").get_data(as_text=True)
        self.assertIn("retro.css", dark)

        with self.client.session_transaction() as session:
            csrf = session["csrf"]
        response = self.client.post("/logout", data={"csrf_token": csrf})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)


if __name__ == "__main__":
    unittest.main()
