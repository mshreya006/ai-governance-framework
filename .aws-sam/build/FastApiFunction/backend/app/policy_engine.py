import re
import yaml
from typing import Dict, Any, List, Tuple
from backend.app.schemas import PolicySchema

def validate_policy_yaml(yaml_content: str) -> Dict[str, Any]:
    """
    Parses YAML and validates it against the PolicySchema.
    Raises ValidationError or yaml.YAMLError on failure.
    """
    data = yaml.safe_load(yaml_content)
    if not isinstance(data, dict):
        raise ValueError("Invalid YAML: must represent a dictionary")
    # This validates structure and triggers Pydantic field validators
    PolicySchema(**data)
    return data

def detect_drift(git_policy: Dict[str, Any], runtime_policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares the Git policy against the currently enforced runtime policy.
    Returns a drift analysis report detailing the differences.
    """
    differences = []

    # Helper function for recursive comparison
    def compare(git_val: Any, rt_val: Any, path: str):
        if type(git_val) != type(rt_val):
            differences.append({
                "field": path,
                "git_value": git_val,
                "runtime_value": rt_val,
                "diff_type": "type_mismatch"
            })
            return

        if isinstance(git_val, dict):
            # Check for keys in git but not in runtime
            for k in git_val:
                if k not in rt_val:
                    differences.append({
                        "field": f"{path}.{k}" if path else k,
                        "git_value": git_val[k],
                        "runtime_value": None,
                        "diff_type": "missing_in_runtime"
                    })
                else:
                    compare(git_val[k], rt_val[k], f"{path}.{k}" if path else k)
            
            # Check for keys in runtime but not in git
            for k in rt_val:
                if k not in git_val:
                    differences.append({
                        "field": f"{path}.{k}" if path else k,
                        "git_value": None,
                        "runtime_value": rt_val[k],
                        "diff_type": "extra_in_runtime"
                    })

        elif isinstance(git_val, list):
            # Sort or match items to compare. For lists of models/frameworks, simple set comparison is best
            if all(isinstance(x, (str, int, float)) for x in git_val) and all(isinstance(x, (str, int, float)) for x in rt_val):
                git_set = set(git_val)
                rt_set = set(rt_val)
                if git_set != rt_set:
                    differences.append({
                        "field": path,
                        "git_value": sorted(list(git_set)),
                        "runtime_value": sorted(list(rt_set)),
                        "diff_type": "value_mismatch"
                    })
            else:
                # List of dicts (e.g. allowed_tools, guardrails, hitl rules)
                # Convert to string/json representation for comparison
                git_str = json_canonical_str(git_val)
                rt_str = json_canonical_str(rt_val)
                if git_str != rt_str:
                    differences.append({
                        "field": path,
                        "git_value": git_val,
                        "runtime_value": rt_val,
                        "diff_type": "structure_mismatch"
                    })
        else:
            if git_val != rt_val:
                differences.append({
                    "field": path,
                    "git_value": git_val,
                    "runtime_value": rt_val,
                    "diff_type": "value_mismatch"
                })

    def json_canonical_str(obj: Any) -> str:
        import json
        return json.dumps(obj, sort_keys=True)

    compare(git_policy, runtime_policy, "")

    return {
        "is_drifted": len(differences) > 0,
        "differences": differences,
        "agent_id": git_policy.get("agent_id"),
        "git_version": git_policy.get("version"),
        "runtime_version": runtime_policy.get("version")
    }

def analyze_sentiment(text: str) -> float:
    """
    Computes a simple deterministic sentiment score between 0.0 (furious) and 1.0 (very happy).
    Used to check if sentiment falls below HITL thresholds.
    """
    score = 1.0
    text_lower = text.lower()
    
    # Highly negative phrases/words
    negative_words = [
        "angry", "furious", "terrible", "worst", "unacceptable", "sucks", 
        "hate", "awful", "bad", "disappointed", "refund", "escalate", 
        "complaint", "poor", "broken", "useless", "scam"
    ]
    
    for word in negative_words:
        # Subtract 0.25 for every match, floor at 0.0
        matches = len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
        score -= 0.25 * matches
        
    return max(0.0, score)

def evaluate_workload(policy: Dict[str, Any], prompt: str, model: str, tool: str = None) -> Dict[str, Any]:
    """
    Evaluates an AI workload request against a policy.
    Returns:
        {
            "allowed": bool,
            "hitl_required": bool,
            "reason": str,
            "details": dict
        }
    """
    # 1. Model Approval Check
    approved_models = policy.get("approved_models", [])
    if model not in approved_models:
        return {
            "allowed": False,
            "hitl_required": False,
            "reason": f"Model '{model}' is not in the approved list for this agent.",
            "details": {"approved_models": approved_models, "requested_model": model}
        }

    # 2. Tool Scope Check
    if tool:
        allowed_tools = policy.get("allowed_tools", [])
        tool_entry = next((t for t in allowed_tools if t["name"] == tool), None)
        if not tool_entry:
            return {
                "allowed": False,
                "hitl_required": False,
                "reason": f"Tool '{tool}' is not authorized by the agent's policy.",
                "details": {"allowed_tools": [t["name"] for t in allowed_tools]}
            }
        
        # Tools are authorized. Scopes are also checked during execution (write scope defaults to HITL in rules)

    # 3. Guardrails Check
    guardrails = policy.get("guardrails", [])
    for guardrail in guardrails:
        if not guardrail.get("enabled", True):
            continue
            
        g_name = guardrail.get("name")
        g_type = guardrail.get("type")
        
        if g_type == "pii_redaction":
            # Match Social Security Numbers (SSN): 000-00-0000
            ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
            # Match Credit Cards: 16 digits
            cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
            
            if re.search(ssn_pattern, prompt) or re.search(cc_pattern, prompt):
                return {
                    "allowed": False,
                    "hitl_required": False,
                    "reason": f"Guardrail '{g_name}' blocked request: PII (SSN or Credit Card) detected.",
                    "details": {"guardrail": g_name, "type": g_type}
                }
                
        elif g_type == "content_filter":
            # Simple content check for inappropriate/banned words
            banned_terms = ["malware", "exploit", "bypass security", "sql injection"]
            for term in banned_terms:
                if term in prompt.lower():
                    return {
                        "allowed": False,
                        "hitl_required": False,
                        "reason": f"Guardrail '{g_name}' blocked request: Restricted content terms detected.",
                        "details": {"guardrail": g_name, "type": g_type, "triggered_term": term}
                    }

    # 4. Human-In-The-Loop (HITL) Check
    hitl_config = policy.get("hitl", {})
    if hitl_config.get("enabled", True):
        # A. Sentiment-based HITL Trigger
        threshold = hitl_config.get("threshold")
        if threshold is not None:
            sentiment = analyze_sentiment(prompt)
            if sentiment < threshold:
                return {
                    "allowed": True,
                    "hitl_required": True,
                    "reason": f"Escalated sentiment score ({sentiment:.2f}) fell below the HITL threshold ({threshold}).",
                    "details": {"hitl_type": "sentiment", "sentiment": sentiment, "threshold": threshold}
                }
        
        # B. Rule-based HITL Trigger
        rules = hitl_config.get("rules", [])
        for rule in rules:
            condition = rule.get("condition", "")
            reason = rule.get("reason", "HITL trigger matched")
            
            # Simple parser for rules: "tool_use == 'send_email'"
            if "tool_use ==" in condition:
                target_tool = condition.split("==")[1].strip().strip("'").strip('"')
                if tool == target_tool:
                    return {
                        "allowed": True,
                        "hitl_required": True,
                        "reason": f"HITL Rule triggered: {reason}",
                        "details": {"hitl_type": "rule", "condition": condition, "tool": tool}
                    }

    # Allowed and no HITL required
    return {
        "allowed": True,
        "hitl_required": False,
        "reason": "Request successfully passed all governance policy checks.",
        "details": {}
    }
