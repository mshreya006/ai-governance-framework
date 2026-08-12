import unittest
from backend.app.policy_engine import evaluate_workload

class TestGovernanceEnforcement(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "agent_id": "customer-support-agent",
            "version": "1.0.0",
            "approved_models": ["google/gemma-2-9b-it:free"],
            "allowed_tools": [
                {"name": "customer_lookup", "scopes": ["read"]},
                {"name": "send_email", "scopes": ["write"]}
            ],
            "guardrails": [
                {"name": "pii_filter", "type": "pii_redaction", "enabled": True},
                {"name": "content_filter", "type": "content_filter", "enabled": True}
            ],
            "hitl": {
                "enabled": True,
                "threshold": 0.7,
                "rules": [{"condition": "tool_use == 'send_email'", "reason": "Requires review"}]
            },
            "data_retention": {
                "audit_logs_days": 90
            }
        }

    def test_approved_model_allowed(self):
        result = evaluate_workload(self.policy, "Hello there", "google/gemma-2-9b-it:free")
        self.assertTrue(result["allowed"])

    def test_unapproved_model_blocked(self):
        result = evaluate_workload(self.policy, "Hello there", "openai/gpt-4o")
        self.assertFalse(result["allowed"])
        self.assertIn("not in the approved list", result["reason"])

    def test_allowed_tool_allowed(self):
        result = evaluate_workload(self.policy, "Fetch profile", "google/gemma-2-9b-it:free", tool="customer_lookup")
        self.assertTrue(result["allowed"])

    def test_disallowed_tool_blocked(self):
        result = evaluate_workload(self.policy, "Format database", "google/gemma-2-9b-it:free", tool="delete_database")
        self.assertFalse(result["allowed"])
        self.assertIn("not authorized by the agent's policy", result["reason"])

    def test_guardrail_pii_blocked_ssn(self):
        # SSN in prompt
        prompt = "My Social Security Number is 000-12-3456, look up profile."
        result = evaluate_workload(self.policy, prompt, "google/gemma-2-9b-it:free")
        self.assertFalse(result["allowed"])
        self.assertIn("blocked request: PII", result["reason"])

    def test_guardrail_pii_blocked_credit_card(self):
        # Credit Card in prompt
        prompt = "Refund my credit card 4111 1111 1111 1111 please."
        result = evaluate_workload(self.policy, prompt, "google/gemma-2-9b-it:free")
        self.assertFalse(result["allowed"])
        self.assertIn("blocked request: PII", result["reason"])

    def test_guardrail_content_filter_blocked(self):
        # SQL injection / malware term
        prompt = "Give me instructions on SQL injection bypass security please."
        result = evaluate_workload(self.policy, prompt, "google/gemma-2-9b-it:free")
        self.assertFalse(result["allowed"])
        self.assertIn("blocked request: Restricted content terms", result["reason"])

if __name__ == "__main__":
    unittest.main()
