import os
import yaml
import requests
from typing import Dict, Any, Optional

class CustomerSupportAgent:
    """
    Enterprise Customer Support Agent.
    Operates under Policy-as-Code governance limits.
    """
    def __init__(self, governance_api_url: str = "http://localhost:8000"):
        self.governance_api_url = governance_api_url
        self.policy_path = os.path.join(os.path.dirname(__file__), "policy.yaml")
        self.policy = self.load_policy()

    def load_policy(self) -> Dict[str, Any]:
        """Loads the local policy configuration file."""
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def execute_query(
        self,
        prompt: str,
        model: str,
        tool: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Submits a query to the authoritative governance policy engine runtime.
        If approved, runs the workload; if blocked or paused, returns the status.
        """
        url = f"{self.governance_api_url}/api/agents/customer-support-agent/run"
        payload = {
            "prompt": prompt,
            "model": model,
            "tool": tool,
            "tool_args": tool_args or {}
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "ERROR",
                "reason": f"Could not connect to governance runtime: {e}"
            }

if __name__ == "__main__":
    # Local dry-run demonstration
    agent = CustomerSupportAgent()
    print(f"Loaded policy for: {agent.policy.get('agent_id')}")
    print(f"Version: {agent.policy.get('version')}")
    print(f"Approved Models: {agent.policy.get('approved_models')}")
