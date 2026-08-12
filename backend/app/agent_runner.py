import os
import logging
import requests
from typing import Dict, Any, Optional
from backend.app import config

logger = logging.getLogger(__name__)

# --- Mock Enterprise Agent Tools ---

def run_customer_lookup(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: customer_lookup (Scope: read)"""
    customer_id = args.get("customer_id", "Unknown")
    # Simulate DB lookup
    db = {
        "12345": {"name": "Alice Smith", "tier": "Gold", "status": "Active", "email": "alice@example.com"},
        "67890": {"name": "Bob Jones", "tier": "Bronze", "status": "Suspended", "email": "bob@example.com"}
    }
    profile = db.get(str(customer_id), {"name": "Guest Customer", "tier": "Standard", "status": "Active", "email": "guest@example.com"})
    return {
        "status": "success",
        "data": profile
    }

def run_send_email(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: send_email (Scope: write)"""
    recipient = args.get("recipient", "customer@example.com")
    subject = args.get("subject", "Support Update")
    body = args.get("body", "")
    
    return {
        "status": "success",
        "message": f"Email successfully dispatched to {recipient} with subject '{subject}'.",
        "details": {"recipient": recipient, "subject": subject, "body_length": len(body)}
    }

def run_credit_score_check(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: credit_score_check (Scope: read)"""
    ssn = args.get("ssn", "000-00-0000")
    # Simulate bureau inquiry
    if ssn.startswith("111"):
        score = 820  # Excellent
    elif ssn.startswith("999"):
        score = 450  # Poor
    else:
        score = 710  # Good
        
    return {
        "status": "success",
        "credit_score": score,
        "risk_tier": "Low" if score >= 700 else ("Medium" if score >= 600 else "High")
    }

def run_approve_loan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: approve_loan (Scope: write)"""
    loan_amount = float(args.get("amount", 0))
    credit_score = int(args.get("credit_score", 600))
    
    approved = loan_amount < 50000 or credit_score >= 700
    
    return {
        "status": "success",
        "approved": approved,
        "loan_id": "LN-98317-X",
        "terms": "Interest rate: 5.5% APR" if approved else "Rejection reason: High risk profile."
    }

def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch and execute tool by name."""
    if tool_name == "customer_lookup":
        return run_customer_lookup(tool_args)
    elif tool_name == "send_email":
        return run_send_email(tool_args)
    elif tool_name == "credit_score_check":
        return run_credit_score_check(tool_args)
    elif tool_name == "approve_loan":
        return run_approve_loan(tool_args)
    else:
        raise ValueError(f"Tool {tool_name} execution logic not defined.")

# --- LLM Connection & Runner ---

def call_openrouter_llm(model: str, system_prompt: str, user_prompt: str) -> str:
    """Connects to OpenRouter's free model APIs."""
    api_key = config.OPENROUTER_API_KEY
    
    # If API key is missing, fall back to mock response to allow zero-cost out-of-the-box local testing
    if not api_key:
        logger.warning("OPENROUTER_API_KEY is not configured. Falling back to local mock completion.")
        return generate_mock_llm_response(model, system_prompt, user_prompt)
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "AI Governance Framework Control Center"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        res_data = response.json()
        choices = res_data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return "Error: Empty response from LLM."
    except Exception as e:
        logger.error(f"OpenRouter LLM Request failed: {e}")
        # Return fallback mock to prevent system crash
        return generate_mock_llm_response(model, system_prompt, user_prompt) + f"\n\n*(OpenRouter API call failed: {e}. Output generated via local engine fallback)*"

def generate_mock_llm_response(model: str, system_prompt: str, user_prompt: str) -> str:
    """Fallback generator simulating natural LLM outputs for tool workflows."""
    import json
    
    # Extract tool context if present in the system prompt
    tool_data = ""
    if "TOOL_RESULT" in system_prompt:
        try:
            tool_data = system_prompt.split("TOOL_RESULT:")[1].strip()
        except Exception:
            pass

    response_text = f"[MOCK LLM RESPONSE - {model}]\n"
    response_text += f"System context active: Enforcing governance parameters.\n"
    
    if tool_data:
        response_text += f"Processed Tool Execution output:\n{tool_data}\n\n"
        response_text += f"Response: I have checked the records. Based on the tool output, the request is completed successfully."
    else:
        response_text += f"Response: I received your request: '{user_prompt}'. All checks passed. I am ready to process your query."
        
    return response_text

def run_agent_workflow(
    agent_id: str,
    prompt: str,
    model: str,
    tool: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes the actual agent workload.
    1. Runs tools if specified
    2. Packages tool outputs into system prompt
    3. Requests response from LLM
    """
    tool_result = None
    if tool:
        args = tool_args or {}
        try:
            tool_result = execute_tool(tool, args)
        except Exception as e:
            logger.error(f"Tool {tool} execution failed: {e}")
            tool_result = {"status": "error", "message": str(e)}

    # Construct LLM system context
    system_prompt = (
        f"You are the Core Agent logic for '{agent_id}'.\n"
        f"You operate under active governance policies. Do not deviate from tool outputs.\n"
    )
    if tool_result:
        system_prompt += (
            f"\nTOOL_RESULT: {json_to_str(tool_result)}\n"
            "An automated backend database tool was executed on your behalf. The resulting data is provided above in JSON format under 'TOOL_RESULT'. "
            "You MUST use this data to answer the user's prompt directly. Do not tell the user you cannot look up information—the lookup has already been completed successfully and provided to you!"
        )

    llm_response = call_openrouter_llm(model, system_prompt, prompt)
    
    return {
        "llm_response": llm_response,
        "tool_executed": tool,
        "tool_result": tool_result
    }

def json_to_str(data: Any) -> str:
    import json
    return json.dumps(data)
