import unittest
from backend.app.policy_engine import evaluate_workload, analyze_sentiment

class TestHitlEnforcement(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "agent_id": "customer-support-agent",
            "version": "1.0.0",
            "approved_models": ["google/gemma-2-9b-it:free"],
            "allowed_tools": [
                {"name": "customer_lookup", "scopes": ["read"]},
                {"name": "send_email", "scopes": ["write"]}
            ],
            "guardrails": [],
            "hitl": {
                "enabled": True,
                "threshold": 0.7,
                "rules": [
                    {"condition": "tool_use == 'send_email'", "reason": "Requires review"}
                ]
            },
            "data_retention": {
                "audit_logs_days": 90
            }
        }

    def test_sentiment_score_calculation(self):
        # Good/neutral sentiment
        self.assertEqual(analyze_sentiment("Hello, I would like to ask about my order status."), 1.0)
        
        # Negative sentiment keywords (furious, bad, broken)
        self.assertLess(analyze_sentiment("I am furious because your service is bad and the item is broken!"), 0.5)

    def test_sentiment_triggers_hitl(self):
        # Angry prompt sentiment score should fall below 0.7 threshold
        prompt = "I am so disappointed and angry! This service is terrible and unacceptable. Escalating this now!"
        result = evaluate_workload(self.policy, prompt, "google/gemma-2-9b-it:free")
        
        self.assertTrue(result["allowed"])
        self.assertTrue(result["hitl_required"])
        self.assertIn("sentiment score", result["reason"])

    def test_rule_triggers_hitl_on_tool(self):
        # Requesting send_email triggers the HITL rule
        result = evaluate_workload(
            policy=self.policy,
            prompt="Send confirmation email to user.",
            model="google/gemma-2-9b-it:free",
            tool="send_email"
        )
        
        self.assertTrue(result["allowed"])
        self.assertTrue(result["hitl_required"])
        self.assertIn("HITL Rule triggered", result["reason"])

    def test_no_hitl_for_normal_request(self):
        # Standard support query with allowed read-tool should pass directly
        result = evaluate_workload(
            policy=self.policy,
            prompt="Can you check customer balance?",
            model="google/gemma-2-9b-it:free",
            tool="customer_lookup"
        )
        
        self.assertTrue(result["allowed"])
        self.assertFalse(result["hitl_required"])

if __name__ == "__main__":
    unittest.main()
