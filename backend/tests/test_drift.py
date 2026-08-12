import unittest
from backend.app.policy_engine import detect_drift

class TestPolicyDriftDetection(unittest.TestCase):
    def setUp(self):
        self.base_policy = {
            "agent_id": "customer-support-agent",
            "version": "1.0.0",
            "approved_models": ["google/gemma-2-9b-it:free", "meta-llama/llama-3-8b-instruct:free"],
            "allowed_tools": [
                {"name": "customer_lookup", "scopes": ["read"]},
                {"name": "send_email", "scopes": ["write"]}
            ],
            "guardrails": [
                {"name": "pii_filter", "type": "pii_redaction", "enabled": True}
            ],
            "hitl": {
                "enabled": True,
                "threshold": 0.7,
                "rules": [{"condition": "tool_use == 'send_email'", "reason": "Requires review"}]
            },
            "data_retention": {
                "audit_logs_days": 90,
                "pii_masking": True
            },
            "regulatory_frameworks": ["NIST_AI_RMF"]
        }

    def test_no_drift_normally(self):
        # Compare base policy with a copy of itself
        runtime_policy = dict(self.base_policy)
        report = detect_drift(self.base_policy, runtime_policy)
        self.assertFalse(report["is_drifted"])
        self.assertEqual(len(report["differences"]), 0)

    def test_drift_detected_on_threshold_change(self):
        # Modify HITL threshold from 0.7 to 0.9 in runtime
        runtime_policy = dict(self.base_policy)
        runtime_policy["hitl"] = {
            "enabled": True,
            "threshold": 0.9,  # Changed
            "rules": [{"condition": "tool_use == 'send_email'", "reason": "Requires review"}]
        }
        
        report = detect_drift(self.base_policy, runtime_policy)
        self.assertTrue(report["is_drifted"])
        self.assertEqual(len(report["differences"]), 1)
        diff = report["differences"][0]
        self.assertEqual(diff["field"], "hitl.threshold")
        self.assertEqual(diff["git_value"], 0.7)
        self.assertEqual(diff["runtime_value"], 0.9)

    def test_drift_detected_on_approved_models_change(self):
        # Modify approved models list in runtime (remove one model)
        runtime_policy = dict(self.base_policy)
        runtime_policy["approved_models"] = ["google/gemma-2-9b-it:free"] # Removed meta-llama
        
        report = detect_drift(self.base_policy, runtime_policy)
        self.assertTrue(report["is_drifted"])
        diff = report["differences"][0]
        self.assertEqual(diff["field"], "approved_models")
        self.assertIn("meta-llama/llama-3-8b-instruct:free", diff["git_value"])
        self.assertNotIn("meta-llama/llama-3-8b-instruct:free", diff["runtime_value"])

    def test_drift_detected_on_added_field_in_runtime(self):
        # Add regulatory tag in runtime
        runtime_policy = dict(self.base_policy)
        runtime_policy["regulatory_frameworks"] = ["NIST_AI_RMF", "ISO_42001"] # Added ISO
        
        report = detect_drift(self.base_policy, runtime_policy)
        self.assertTrue(report["is_drifted"])
        diff = report["differences"][0]
        self.assertEqual(diff["field"], "regulatory_frameworks")

if __name__ == "__main__":
    unittest.main()
