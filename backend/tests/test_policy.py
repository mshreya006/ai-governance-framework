import unittest
import yaml
from pydantic import ValidationError
from backend.app.schemas import PolicySchema
from backend.app.policy_engine import validate_policy_yaml

class TestPolicyValidation(unittest.TestCase):
    def setUp(self):
        self.valid_yaml = """
        agent_id: "customer-support-agent"
        version: "1.0.0"
        description: "Valid test policy"
        approved_models:
          - "google/gemma-2-9b-it:free"
        allowed_tools:
          - name: "customer_lookup"
            description: "Read customer profile"
            scopes:
              - "read"
        guardrails:
          - name: "pii_filter"
            type: "pii_redaction"
            enabled: true
        hitl:
          enabled: true
          threshold: 0.7
          rules:
            - condition: "tool_use == 'send_email'"
              reason: "Human approval needed for email"
        data_retention:
          audit_logs_days: 90
          pii_masking: true
        regulatory_frameworks:
          - "NIST_AI_RMF"
        """

    def test_valid_policy_passes(self):
        try:
            data = validate_policy_yaml(self.valid_yaml)
            self.assertEqual(data["agent_id"], "customer-support-agent")
            self.assertEqual(data["version"], "1.0.0")
        except Exception as e:
            self.fail(f"Valid policy failed validation: {e}")

    def test_missing_required_fields_fails(self):
        # Missing approved_models
        invalid_yaml = """
        agent_id: "customer-support-agent"
        version: "1.0.0"
        hitl:
          enabled: true
        data_retention:
          audit_logs_days: 90
        """
        with self.assertRaises((ValidationError, ValueError)):
            validate_policy_yaml(invalid_yaml)

    def test_invalid_tool_scope_fails(self):
        # Scope is 'write-admin' instead of 'read' or 'write'
        invalid_yaml = """
        agent_id: "customer-support-agent"
        version: "1.0.0"
        approved_models:
          - "google/gemma-2-9b-it:free"
        allowed_tools:
          - name: "delete_db"
            scopes:
              - "write-admin"
        hitl:
          enabled: false
        data_retention:
          audit_logs_days: 90
        """
        with self.assertRaises((ValidationError, ValueError)):
            validate_policy_yaml(invalid_yaml)

    def test_invalid_agent_id_fails(self):
        # Special characters in agent_id
        invalid_yaml = self.valid_yaml.replace('agent_id: "customer-support-agent"', 'agent_id: "support$agent!"')
        with self.assertRaises((ValidationError, ValueError)):
            validate_policy_yaml(invalid_yaml)

    def test_empty_approved_models_fails(self):
        # Approved models list is empty
        invalid_yaml = self.valid_yaml.replace('- "google/gemma-2-9b-it:free"', '')
        with self.assertRaises((ValidationError, ValueError)):
            validate_policy_yaml(invalid_yaml)

if __name__ == "__main__":
    unittest.main()
