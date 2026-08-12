import os
import sys
import unittest

# Set the test database path BEFORE importing database client to ensure isolation
os.environ["LOCAL_DB_PATH"] = "concurrency_test_database.json"

# Add project root to python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from backend.app.main import app, seed_initial_data
from backend.app.database import db

class TestAPIConcurrency(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.agent_id = "customer-support-agent"
        # Reset database state before each test to prevent test pollution
        if not db.use_dynamodb:
            db._write_local_db({})
        seed_initial_data()

    def tearDown(self):
        if not db.use_dynamodb:
            db._write_local_db({})

    def run_single_request(self, index: int):
        """Simulates a workload run request."""
        payload = {
            "prompt": f"Hello. This is request number {index}. Please help me lookup order.",
            "model": "google/gemma-2-9b-it:free",
            "tool": "customer_lookup",
            "tool_args": {"customer_id": "12345"}
        }
        response = self.client.post(f"/api/agents/{self.agent_id}/run", json=payload)
        return response.status_code, response.json()

    def test_concurrent_workloads(self):
        # Fire 15 requests concurrently to verify the local JSON db file lock works
        # and there are no concurrent read/write crashes.
        num_requests = 15
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.run_single_request, i): i 
                for i in range(num_requests)
            }
            
            for future in as_completed(futures):
                try:
                    status_code, data = future.result()
                    results.append((status_code, data))
                except Exception as e:
                    self.fail(f"Thread execution failed with error: {e}")

        # Assert all requests completed with 200 OK (ALLOWED workload)
        self.assertEqual(len(results), num_requests)
        for status_code, data in results:
            self.assertEqual(status_code, 200)
            self.assertEqual(data["status"], "ALLOWED")
            self.assertIn("llm_response", data)

if __name__ == "__main__":
    unittest.main()
