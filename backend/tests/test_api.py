import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.store import NoteStore
from fakes import DynamoDouble, RedisDouble


class DeviceApiTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            is_production_like=False, cors_origins=["http://localhost:3050"],
            flush_idle_seconds=60, flush_max_seconds=300, cache_ttl_seconds=86400, max_notes=100,
        )
        self.table = DynamoDouble()
        self.repository = NoteStore(RedisDouble(), self.table, self.settings, clock=lambda: 1000)
        # Tests inject service doubles without starting the AWS-only runtime lifespan.
        app.state.settings = self.settings
        app.state.session_key = "test-key-containing-at-least-32-bytes"
        app.state.store = self.repository
        self.first = TestClient(app)
        self.second = TestClient(app)
        self.addCleanup(self.first.close)
        self.addCleanup(self.second.close)

    def test_cookie_is_http_only_and_two_devices_do_not_share_notes(self):
        response = self.first.get("/api/workspace")
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=lax", response.headers["set-cookie"])
        first_workspace = response.json()["workspace_id"]
        self.first.put(f"/api/notes/{uuid4()}", json={"title": "Private draft"})
        second = self.second.get("/api/workspace").json()
        self.assertNotEqual(first_workspace, second["workspace_id"])
        self.assertEqual(second["notes"], [])

    def test_idempotent_upsert_and_delete_keep_empty_workspace(self):
        self.first.get("/workspace")
        note_id = str(uuid4())
        for _ in range(2):
            saved = self.first.put(f"/notes/{note_id}", json={"title": "Draft"})
            self.assertEqual(saved.status_code, 200)
            self.assertIn("x-noteos-revision", saved.headers)
        self.assertEqual(len(self.first.get("/notes").json()), 1)
        for _ in range(2):
            response = self.first.delete(f"/notes/{note_id}")
            self.assertEqual(response.status_code, 204)
            self.assertIn("x-noteos-revision", response.headers)
        workspace = self.first.get("/workspace").json()
        self.assertFalse(workspace["is_new"])
        self.assertEqual(workspace["notes"], [])
        self.assertEqual(self.table.writes, [])

    def test_validation_and_origin_reject_invalid_writes(self):
        self.first.get("/workspace")
        note_id = str(uuid4())
        invalid = self.first.put(f"/notes/{note_id}", json={"title": "Draft", "color": "invalid"})
        self.assertEqual(invalid.status_code, 422)
        cross_site = self.first.put(
            f"/notes/{note_id}", json={"title": "Draft"}, headers={"Origin": "https://other.example"}
        )
        self.assertEqual(cross_site.status_code, 403)

    def test_sync_status_only_reports_persisted_after_dynamodb_flush(self):
        self.first.get("/workspace")
        self.first.put(f"/notes/{uuid4()}", json={"title": "Draft"})
        buffered = self.first.get("/workspace").json()
        self.assertEqual(buffered["status"], "buffered")
        self.assertEqual(buffered["persisted_revision"], 0)
        self.repository.clock = lambda: 1030
        self.repository.flush_due_workspaces()
        self.assertEqual(self.first.get("/workspace").json()["status"], "buffered")
        self.repository.clock = lambda: 1060
        self.repository.flush_due_workspaces()
        persisted = self.first.get("/workspace").json()
        self.assertEqual(persisted["status"], "persisted")
        self.assertEqual(persisted["revision"], persisted["persisted_revision"])


if __name__ == "__main__":
    unittest.main()
