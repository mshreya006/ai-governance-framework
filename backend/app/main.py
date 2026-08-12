import os
import uuid
import yaml
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from decimal import Decimal

from backend.app import config
from backend.app.database import db
from backend.app.policy_engine import (
    validate_policy_yaml,
    detect_drift,
    evaluate_workload
)
from backend.app.agent_runner import run_agent_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

app = FastAPI(
    title="AI Governance Framework API",
    description="Production-ready policy enforcement, drift detection, versioning, and HITL approvals for AI workloads.",
    version="1.0.0"
)

# CORS Configuration for Frontend Access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to the frontend CloudFront domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mangum Handler for AWS Lambda Deployment
handler = Mangum(app)

# --- Pydantic Request/Response Models ---

class DeployPolicyRequest(BaseModel):
    agent_id: str
    commit_sha: str
    policy_yaml: str

class DriftSimulateRequest(BaseModel):
    policy_yaml: str

class ExecuteWorkloadRequest(BaseModel):
    prompt: str
    model: str
    tool: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None

class HitlDecisionRequest(BaseModel):
    decision: str  # APPROVED or REJECTED

# --- Helper Functions for Auditing & Seeding ---

def write_audit_log(agent_id: str, event_type: str, severity: str, message: str, details: Dict[str, Any] = None, commit_sha: str = None):
    """Utility to write governance ledger entries."""
    timestamp = datetime.now(timezone.utc).isoformat()
    log_id = str(uuid.uuid4())
    audit_item = {
        "log_id": log_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "severity": severity,
        "message": message,
        "commit_sha": commit_sha,
        "details": details or {}
    }
    db.put_item(f"AGENT#{agent_id}", f"AUDIT#{timestamp}#{log_id}", audit_item)
    logger.info(f"AUDIT LOG [{event_type}][{severity}]: {message}")

def seed_initial_data():
    """Reads tracked policy files from repo and seeds the database."""
    agents = [
        {"id": "customer-support-agent", "dir": "customer-support"},
        {"id": "loan-processor-agent", "dir": "loan-processor"}
    ]
    
    # Resolve absolute path to repo root from main.py location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    for agent in agents:
        agent_id = agent["id"]
        policy_path = os.path.join(repo_root, "agents", agent["dir"], "policy.yaml")
        
        # Check if already seeded in database
        existing = db.get_item(f"AGENT#{agent_id}", "POLICY#runtime")
        if existing:
            logger.info(f"Agent '{agent_id}' is already initialized in database.")
            continue
            
        if os.path.exists(policy_path):
            try:
                with open(policy_path, "r") as f:
                    policy_yaml = f.read()  
                
                # Validate and parse
                policy_json = validate_policy_yaml(policy_yaml)
                commit_sha = "initial-git-commit-sha-000000000000"
                timestamp = datetime.now(timezone.utc).isoformat()
                
                # Write Policy records
                policy_record = {
                    "agent_id": agent_id,
                    "commit_sha": commit_sha,
                    "policy_content": policy_yaml,
                    "policy_json": policy_json,
                    "timestamp": timestamp,
                    "updated_by": "System Seeding",
                    "version_tag": "latest_git"
                }
                
                # Seed latest_git, runtime, and the commit specific SK
                db.put_item(f"AGENT#{agent_id}", "POLICY#latest_git", policy_record)
                
                # For runtime active record
                runtime_record = dict(policy_record)
                runtime_record["version_tag"] = "runtime"
                db.put_item(f"AGENT#{agent_id}", "POLICY#runtime", runtime_record)
                
                # For historical audit specific record
                db.put_item(f"AGENT#{agent_id}", f"POLICY#{commit_sha}", policy_record)
                
                # Log success
                write_audit_log(
                    agent_id=agent_id,
                    event_type="POLICY_DEPLOYMENT",
                    severity="INFO",
                    message=f"Agent '{agent_id}' successfully bootstrapped with policy version {policy_json.get('version')}.",
                    details={"commit_sha": commit_sha, "policy_version": policy_json.get("version")},
                    commit_sha=commit_sha
                )
            except Exception as e:
                logger.error(f"Failed to bootstrap agent '{agent_id}' policy: {e}")
        else:
            logger.warning(f"Seeding skipped: policy file not found at {policy_path}")

# Run seeding on startup
@app.on_event("startup")
def startup_event():
    seed_initial_data()

# --- Endpoints ---

@app.get("/api/health")
def get_health():
    """Checks the health and status of backend and database layer."""
    db_status = "DynamoDB Mode" if db.use_dynamodb else "Local File Mode"
    return {
        "status": "OK",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status
    }

@app.get("/api/agents")
def get_agents():
    """Lists all governed agents, their active versions, and drift compliance."""
    agent_ids = ["customer-support-agent", "loan-processor-agent"]
    results = []
    
    for agent_id in agent_ids:
        runtime_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#runtime")
        git_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#latest_git")
        
        # Lazy-seeding failsafe: trigger bootstrap if records are missing (e.g. serverless cold starts)
        if not runtime_policy or not git_policy:
            try:
                logger.info(f"Policies for '{agent_id}' missing. Running lazy-seeding...")
                seed_initial_data()
                runtime_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#runtime")
                git_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#latest_git")
            except Exception as e:
                logger.error(f"Failed to execute lazy seeding for '{agent_id}': {e}")
                
        if not runtime_policy or not git_policy:
            continue
            
        rt_json = runtime_policy.get("policy_json", {})
        git_json = git_policy.get("policy_json", {})
        
        # Calculate drift
        drift_report = detect_drift(git_json, rt_json)
        
        results.append({
            "agent_id": agent_id,
            "name": agent_id.replace("-", " ").title(),
            "active_version": rt_json.get("version", "0.0.0"),
            "git_commit": runtime_policy.get("commit_sha", "unknown"),
            "is_drifted": drift_report["is_drifted"],
            "drift_fields_count": len(drift_report["differences"]),
            "approved_models": rt_json.get("approved_models", []),
            "allowed_tools": [t["name"] for t in rt_json.get("allowed_tools", [])],
            "last_deployed": runtime_policy.get("timestamp")
        })
        
    return results

@app.get("/api/agents/{agent_id}/policy")
def get_agent_policy(agent_id: str, version: str = "runtime"):
    """Fetches the YAML policy text and JSON details for an agent."""
    # version can be 'runtime', 'latest_git', or a specific commit SHA
    sk = f"POLICY#{version}"
    policy_item = db.get_item(f"AGENT#{agent_id}", sk)
    if not policy_item:
        raise HTTPException(
            status_code=404, 
            detail=f"Policy version '{version}' for agent '{agent_id}' not found."
        )
    return {
        "agent_id": agent_id,
        "version_tag": version,
        "commit_sha": policy_item.get("commit_sha"),
        "timestamp": policy_item.get("timestamp"),
        "updated_by": policy_item.get("updated_by"),
        "policy_yaml": policy_item.get("policy_content"),
        "policy_json": policy_item.get("policy_json")
    }

@app.get("/api/policies/{agent_id}/{commit_sha}")
def get_policy_by_commit(agent_id: str, commit_sha: str):
    """Retrieve policy content active for a specific historical commit SHA."""
    return get_agent_policy(agent_id, commit_sha)

@app.get("/api/agents/{agent_id}/versions")
def get_agent_policy_versions(agent_id: str):
    """Lists all historical versions of policy deployments stored in the DB."""
    policy_items = db.query_items(f"AGENT#{agent_id}", "POLICY#")
    versions = []
    
    for item in policy_items:
        sk = item.get("SK", "")
        # Filter out virtual pointers and keep specific commit records
        if sk.endswith("runtime") or sk.endswith("latest_git"):
            continue
            
        p_json = item.get("policy_json", {})
        versions.append({
            "commit_sha": item.get("commit_sha"),
            "version": p_json.get("version"),
            "timestamp": item.get("timestamp"),
            "updated_by": item.get("updated_by")
        })
        
    # Sort descending by timestamp
    versions.sort(key=lambda x: x["timestamp"], reverse=True)
    return versions

@app.post("/api/policies/deploy")
def deploy_policy(payload: DeployPolicyRequest, x_deploy_token: Optional[str] = Header(None)):
    """CI/CD deployment endpoint to register a new policy from Git push."""
    # Verify token
    if not x_deploy_token or x_deploy_token != config.BACKEND_DEPLOY_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid deployment token."
        )
        
    try:
        # Validate schema & syntax
        policy_json = validate_policy_yaml(payload.policy_yaml)
    except Exception as e:
        # Write validation failed log
        write_audit_log(
            agent_id=payload.agent_id,
            event_type="POLICY_VALIDATION",
            severity="ERROR",
            message=f"Policy validation failed for commit {payload.commit_sha[:8]}: {str(e)}",
            details={"error": str(e)},
            commit_sha=payload.commit_sha
        )
        raise HTTPException(status_code=400, detail=f"Policy Validation Failed: {e}")

    timestamp = datetime.now(timezone.utc).isoformat()
    policy_record = {
        "agent_id": payload.agent_id,
        "commit_sha": payload.commit_sha,
        "policy_content": payload.policy_yaml,
        "policy_json": policy_json,
        "timestamp": timestamp,
        "updated_by": "CI/CD Pipeline",
        "version_tag": "latest_git"
    }

    # Store policy records
    # 1. Update latest git pointer
    db.put_item(f"AGENT#{payload.agent_id}", "POLICY#latest_git", policy_record)
    
    # 2. Store specific commit version
    db.put_item(f"AGENT#{payload.agent_id}", f"POLICY#{payload.commit_sha}", policy_record)
    
    # 3. Update runtime active policy (deploys it directly to production)
    runtime_record = dict(policy_record)
    runtime_record["version_tag"] = "runtime"
    db.put_item(f"AGENT#{payload.agent_id}", "POLICY#runtime", runtime_record)

    # Log successful deployment
    write_audit_log(
        agent_id=payload.agent_id,
        event_type="POLICY_DEPLOYMENT",
        severity="INFO",
        message=f"Successfully deployed policy version {policy_json.get('version')} for commit {payload.commit_sha[:8]}.",
        details={"version": policy_json.get("version"), "commit": payload.commit_sha},
        commit_sha=payload.commit_sha
    )
    
    return {"status": "success", "message": "Policy deployed and activated successfully."}

@app.post("/api/agents/{agent_id}/policy/drift-simulate")
def simulate_policy_drift(agent_id: str, payload: DriftSimulateRequest):
    """Simulates an out-of-band policy modification bypassing Git."""
    try:
        # Validate schema & syntax
        policy_json = validate_policy_yaml(payload.policy_yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Policy YAML: {e}")
        
    timestamp = datetime.now(timezone.utc).isoformat()
    runtime_record = {
        "agent_id": agent_id,
        "commit_sha": "OUT-OF-BAND-MANUAL-CHANGE",
        "policy_content": payload.policy_yaml,
        "policy_json": policy_json,
        "timestamp": timestamp,
        "updated_by": "Manual Admin Bypass",
        "version_tag": "runtime"
    }
    
    # Update runtime pointer ONLY, creating drift relative to latest_git
    db.put_item(f"AGENT#{agent_id}", "POLICY#runtime", runtime_record)
    
    # Write Audit Log
    write_audit_log(
        agent_id=agent_id,
        event_type="DRIFT_DETECTED",
        severity="WARNING",
        message=f"Simulated out-of-band manual policy modification bypassing Git CI/CD.",
        details={"warning": "Enforced runtime policy has drifted from latest git version."}
    )
    
    return {"status": "success", "message": "Runtime policy updated. Drift has been successfully simulated."}

@app.post("/api/agents/{agent_id}/policy/drift-revert")
def revert_policy_drift(agent_id: str):
    """Reverts runtime policy back to the Git-approved version to resolve drift."""
    git_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#latest_git")
    if not git_policy:
        raise HTTPException(status_code=400, detail="No Git policy record found to revert to.")
        
    timestamp = datetime.now(timezone.utc).isoformat()
    runtime_record = dict(git_policy)
    runtime_record["version_tag"] = "runtime"
    runtime_record["timestamp"] = timestamp
    runtime_record["updated_by"] = "Drift Reversal (Console)"
    
    db.put_item(f"AGENT#{agent_id}", "POLICY#runtime", runtime_record)
    
    # Write Audit Log
    write_audit_log(
        agent_id=agent_id,
        event_type="POLICY_DEPLOYMENT",
        severity="INFO",
        message="Reverted drifted runtime policy back to Git-approved state.",
        details={"reverted_to_commit": git_policy.get("commit_sha")},
        commit_sha=git_policy.get("commit_sha")
    )
    
    return {"status": "success", "message": "Policy drift resolved. Runtime reverted back to match Git."}

@app.get("/api/agents/{agent_id}/drift")
def check_policy_drift(agent_id: str):
    """Compares the current runtime policy against the Git version and returns drift reports."""
    runtime_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#runtime")
    git_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#latest_git")
    
    if not runtime_policy or not git_policy:
        raise HTTPException(status_code=404, detail="Policies not seeded or found.")
        
    drift_report = detect_drift(git_policy.get("policy_json", {}), runtime_policy.get("policy_json", {}))
    drift_report["runtime_commit"] = runtime_policy.get("commit_sha")
    drift_report["git_commit"] = git_policy.get("commit_sha")
    drift_report["last_checked"] = datetime.utcnow().isoformat()
    
    return drift_report

@app.post("/api/agents/{agent_id}/run")
def run_governed_workload(agent_id: str, request: ExecuteWorkloadRequest):
    """Runs a workload through policy evaluation, pause for HITL, or direct LLM execution."""
    runtime_policy = db.get_item(f"AGENT#{agent_id}", "POLICY#runtime")
    if not runtime_policy:
        raise HTTPException(status_code=404, detail=f"No policy active for agent '{agent_id}'.")
        
    policy_json = runtime_policy.get("policy_json", {})
    
    # 1. Evaluate Governance Checks
    evaluation = evaluate_workload(
        policy=policy_json,
        prompt=request.prompt,
        model=request.model,
        tool=request.tool
    )
    
    # Case A: Workload Blocked
    if not evaluation["allowed"]:
        write_audit_log(
            agent_id=agent_id,
            event_type="WORKLOAD_BLOCKED",
            severity="ERROR",
            message=f"Workload request blocked: {evaluation['reason']}",
            details={
                "prompt": request.prompt,
                "model": request.model,
                "tool": request.tool,
                "reason": evaluation["reason"]
            }
        )
        raise HTTPException(
            status_code=400,
            detail={
                "status": "BLOCKED",
                "reason": evaluation["reason"],
                "details": evaluation["details"]
            }
        )
        
    # Case B: HITL Triggered
    if evaluation.get("hitl_required", False):
        request_id = f"req-{uuid.uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        hitl_item = {
            "request_id": request_id,
            "agent_id": agent_id,
            "status": "PENDING",
            "prompt": request.prompt,
            "requested_model": request.model,
            "requested_tool": request.tool,
            "requested_tool_args": request.tool_args or {},
            "reason": evaluation["reason"],
            "created_at": timestamp,
            "details": evaluation["details"]
        }
        
        # Save request to database
        db.put_item(f"AGENT#{agent_id}", f"HITL#{request_id}", hitl_item)
        
        # Write Audit Log
        write_audit_log(
            agent_id=agent_id,
            event_type="HITL_TRIGGERED",
            severity="WARNING",
            message=f"Workload paused. Human review required: {evaluation['reason']}",
            details={"request_id": request_id, "trigger_reason": evaluation["reason"]}
        )
        
        return {
            "status": "PENDING_HITL",
            "request_id": request_id,
            "reason": evaluation["reason"],
            "message": "AI workload execution is suspended pending human review and approval."
        }
        
    # Case C: Governance Approved, Proceed to LLM
    workflow_result = run_agent_workflow(
        agent_id=agent_id,
        prompt=request.prompt,
        model=request.model,
        tool=request.tool,
        tool_args=request.tool_args
    )
    
    # Write Audit Log
    write_audit_log(
        agent_id=agent_id,
        event_type="WORKLOAD_ALLOWED",
        severity="INFO",
        message=f"Workload execution completed. Model: {request.model}, Tool: {request.tool or 'None'}",
        details={
            "model": request.model,
            "tool": request.tool,
            "tool_result": workflow_result.get("tool_result")
        }
    )
    
    return {
        "status": "ALLOWED",
        "llm_response": workflow_result["llm_response"],
        "tool_result": workflow_result["tool_result"],
        "governed_by_policy": policy_json.get("version")
    }

@app.get("/api/hitl/pending")
def get_pending_hitl():
    """Lists all pending Human-in-the-Loop approvals across all agents."""
    agent_ids = ["customer-support-agent", "loan-processor-agent"]
    results = []
    
    for agent_id in agent_ids:
        items = db.query_items(f"AGENT#{agent_id}", "HITL#")
        for item in items:
            if item.get("status") == "PENDING":
                results.append(item)
                
    # Sort by created_at descending
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results

@app.post("/api/agents/{agent_id}/hitl/{request_id}/decide")
def decide_hitl_request(agent_id: str, request_id: str, payload: HitlDecisionRequest):
    """Approves or rejects a suspended HITL execution request."""
    hitl_item = db.get_item(f"AGENT#{agent_id}", f"HITL#{request_id}")
    if not hitl_item:
        raise HTTPException(status_code=404, detail="HITL request not found.")
        
    if hitl_item.get("status") != "PENDING":
        raise HTTPException(status_code=400, detail="HITL request has already been decided.")
        
    decision = payload.decision.upper()
    if decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Decision must be either APPROVED or REJECTED.")
        
    timestamp = datetime.now(timezone.utc).isoformat()
    hitl_item["status"] = decision
    hitl_item["decided_at"] = timestamp
    hitl_item["decision_by"] = "Governance Console Admin"
    
    # Save decision state
    db.put_item(f"AGENT#{agent_id}", f"HITL#{request_id}", hitl_item)
    
    # Write Audit Log
    write_audit_log(
        agent_id=agent_id,
        event_type="HITL_DECISION",
        severity="INFO",
        message=f"Human-in-the-loop request '{request_id}' decided: {decision}.",
        details={"request_id": request_id, "decision": decision}
    )
    
    if decision == "APPROVED":
        # Resume workload execution
        workflow_result = run_agent_workflow(
            agent_id=agent_id,
            prompt=hitl_item["prompt"],
            model=hitl_item["requested_model"],
            tool=hitl_item["requested_tool"],
            tool_args=hitl_item.get("requested_tool_args")
        )
        
        return {
            "status": "APPROVED",
            "message": "AI workload approved and executed successfully.",
            "llm_response": workflow_result["llm_response"],
            "tool_result": workflow_result["tool_result"]
        }
    else:
        return {
            "status": "REJECTED",
            "message": "AI workload execution was rejected by human operator."
        }

@app.get("/api/audit-logs")
def get_audit_logs(agent_id: Optional[str] = None):
    """Retrieves all governance ledger logs from the database, sorted chronologically."""
    agents = [agent_id] if agent_id else ["customer-support-agent", "loan-processor-agent"]
    logs = []
    
    for aid in agents:
        items = db.query_items(f"AGENT#{aid}", "AUDIT#")
        logs.extend(items)
        
    # Sort chronologically descending
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs
