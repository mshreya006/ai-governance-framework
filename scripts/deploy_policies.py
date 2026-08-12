import os
import sys
import yaml
import requests
import argparse

# Resolve paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def deploy_policies():
    parser = argparse.ArgumentParser(description="Deploy validated policies to governance runtime.")
    parser.add_argument("--commit-sha", required=True, help="Git commit SHA being deployed")
    args = parser.parse_args()

    # Get config from env
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000").rstrip("/")
    deploy_token = os.getenv("BACKEND_DEPLOY_TOKEN", "dev-token-12345")

    agents_dir = os.path.join(project_root, "agents")
    if not os.path.exists(agents_dir):
        print(f"Error: Agents directory not found at {agents_dir}")
        sys.exit(1)

    print("==============================================")
    print("        AI POLICY CI/CD DEPLOYER              ")
    print("==============================================")
    print(f"Target API Endpoint: {backend_url}")
    print(f"Deploying version: {args.commit_sha[:8]}")
    print("==============================================")

    failed = False
    headers = {
        "X-Deploy-Token": deploy_token,
        "Content-Type": "application/json"
    }

    for agent_folder in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, agent_folder)
        if not os.path.isdir(agent_path):
            continue

        policy_file = os.path.join(agent_path, "policy.yaml")
        if not os.path.exists(policy_file):
            continue

        try:
            with open(policy_file, "r") as f:
                policy_yaml = f.read()
                
            policy_data = yaml.safe_load(policy_yaml)
            agent_id = policy_data.get("agent_id")
            
            print(f"Pushing policy for agent: '{agent_id}'...")
            
            payload = {
                "agent_id": agent_id,
                "commit_sha": args.commit_sha,
                "policy_yaml": policy_yaml
            }
            
            deploy_api = f"{backend_url}/api/policies/deploy"
            response = requests.post(deploy_api, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                print(f"[SUCCESS] Policy deployed successfully for '{agent_id}'.")
            else:
                print(f"[ERROR] Failed to deploy policy for '{agent_id}'. Status Code: {response.status_code}")
                print(f"        Detail: {response.text}")
                failed = True
                
        except Exception as e:
            print(f"[ERROR] Connection failure deploying policy for '{agent_folder}': {e}")
            failed = True
        print("-" * 46)

    if failed:
        print("[DEPLOYMENT FAILED] Policy synchronization failed.")
        sys.exit(1)
    else:
        print("[SUCCESS] All policies deployed and activated successfully.")
        sys.exit(0)

if __name__ == "__main__":
    deploy_policies()
