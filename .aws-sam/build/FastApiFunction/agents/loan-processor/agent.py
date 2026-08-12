import os
import yaml
import requests
from typing import Dict, Any, Optional

class LoanProcessorAgent:
    """
    Enterprise Loan Processor Agent.
    Operates under strict regulatory Policy-as-Code limits.
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

    def process_loan_request(
        self,
        prompt: str,
        model: str,
        tool: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Submits a query to the authoritative governance policy engine runtime.
        Runs financial credit checks and evaluates loan terms.
        """
        url = f"{self.governance_api_url}/api/agents/loan-processor-agent/run"
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
    agent = LoanProcessorAgent()
    print(f"Loaded policy for: {agent.policy.get('agent_id')}")
    print(f"Version: {agent.policy.get('version')}")
    print(f"Approved Models: {agent.policy.get('approved_models')}")
