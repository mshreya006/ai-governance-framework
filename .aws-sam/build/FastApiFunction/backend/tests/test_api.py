import os
import sys
import unittest

# Set the test database path BEFORE importing database client to ensure isolation
os.environ["LOCAL_DB_PATH"] = "test_database.json"

# Add project root to python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi.testclient import TestClient
from backend.app.main import app, seed_initial_data
from backend.app.database import db

class TestGovernanceAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.agent_id = "customer-support-agent"
        # Reset database state before each test to prevent test pollution
        if not db.use_dynamodb:
            db._write_local_db({})
        seed_initial_data()

    def tearDown(self):
        # Clean up database state after run
        if not db.use_dynamodb:
            db._write_local_db({})

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")

    def test_get_agents(self):
        response = self.client.get("/api/agents")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_deploy_policy_unauthorized(self):
        payload = {
            "agent_id": self.agent_id,
            "commit_sha": "testcommit1234567890",
            "policy_yaml": "agent_id: invalid"
        }
        response = self.client.post("/api/policies/deploy", json=payload)
        self.assertEqual(response.status_code, 401)

    def test_deploy_policy_invalid_schema_fails(self):
        payload = {
            "agent_id": self.agent_id,
            "commit_sha": "testcommit1234567890",
            "policy_yaml": "agent_id: customer-support-agent\nversion: 1.0.0"
        }
        headers = {"X-Deploy-Token": "dev-token-12345"}
        response = self.client.post("/api/policies/deploy", json=payload, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Validation Failed", response.json()["detail"])

    def test_deploy_policy_success_and_historical_retrieve(self):
        valid_yaml = """
        agent_id: "customer-support-agent"
        version: "2.1.0"
        description: "Updated support policy"
        approved_models:
          - "google/gemma-2-9b-it:free"
        allowed_tools:
          - name: "customer_lookup"
            scopes: ["read"]
        guardrails: []
        hitl:
          enabled: false
        data_retention:
          audit_logs_days: 30
          pii_masking: false
        regulatory_frameworks: []
        """
        commit_sha = "c3a8e2d49b209e9eef27b3"
        payload = {
            "agent_id": self.agent_id,
            "commit_sha": commit_sha,
            "policy_yaml": valid_yaml
        }
        headers = {"X-Deploy-Token": "dev-token-12345"}
        
        response = self.client.post("/api/policies/deploy", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200)

        history_url = f"/api/policies/{self.agent_id}/{commit_sha}"
        response = self.client.get(history_url)
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["commit_sha"], commit_sha)
        self.assertEqual(res_data["policy_json"]["version"], "2.1.0")

    def test_drift_simulation_and_revert(self):
        valid_yaml = """
        agent_id: "customer-support-agent"
        version: "1.0.0"
        approved_models: ["google/gemma-2-9b-it:free"]
        allowed_tools: []
        guardrails: []
        hitl: { enabled: false }
        data_retention: { audit_logs_days: 90 }
        """
        headers = {"X-Deploy-Token": "dev-token-12345"}
        self.client.post("/api/policies/deploy", json={
            "agent_id": self.agent_id,
            "commit_sha": "gitsha123456",
            "policy_yaml": valid_yaml
        }, headers=headers)

        # 1. Initially check drift - should be False
        response = self.client.get(f"/api/agents/{self.agent_id}/drift")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_drifted"])

        # 2. Simulate drift
        drift_yaml = valid_yaml.replace('approved_models: ["google/gemma-2-9b-it:free"]', 'approved_models: ["google/gemma-2-9b-it:free", "meta-llama/llama-3-8b-instruct:free"]')
        response = self.client.post(f"/api/agents/{self.agent_id}/policy/drift-simulate", json={
            "policy_yaml": drift_yaml
        })
        self.assertEqual(response.status_code, 200)

        # 3. Check drift - should be True
        response = self.client.get(f"/api/agents/{self.agent_id}/drift")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_drifted"])

        # 4. Revert drift
        response = self.client.post(f"/api/agents/{self.agent_id}/policy/drift-revert")
        self.assertEqual(response.status_code, 200)

        # 5. Check drift again - should be False
        response = self.client.get(f"/api/agents/{self.agent_id}/drift")
        self.assertFalse(response.json()["is_drifted"])

if __name__ == "__main__":
    unittest.main()
