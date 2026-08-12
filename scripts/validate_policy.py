import os
import sys
import yaml

# Add the project root directory to the python path so we can import backend schemas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.schemas import PolicySchema
from pydantic import ValidationError

def validate_policies():
    agents_dir = os.path.join(project_root, "agents")
    if not os.path.exists(agents_dir):
        print(f"Error: Agents directory not found at {agents_dir}")
        sys.exit(1)

    print("==============================================")
    print("        AI POLICY-AS-CODE VALIDATOR           ")
    print("==============================================")

    failed = False
    validated_count = 0

    for agent_folder in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, agent_folder)
        if not os.path.isdir(agent_path):
            continue

        policy_file = os.path.join(agent_path, "policy.yaml")
        if not os.path.exists(policy_file):
            print(f"[WARNING] Skipping agent folder '{agent_folder}': No policy.yaml found.")
            continue

        print(f"Validating policy for agent: {agent_folder} ({policy_file})")
        
        try:
            with open(policy_file, "r") as f:
                policy_data = yaml.safe_load(f)
            
            # This triggers Pydantic schema validation
            PolicySchema(**policy_data)
            print(f"[PASS] Policy for '{policy_folder_to_id(agent_folder)}' is structurally complete and valid.")
            validated_count += 1
            
        except yaml.YAMLError as ye:
            print(f"[FAIL] Invalid YAML syntax in '{policy_file}':")
            print(f"       {ye}")
            failed = True
        except ValidationError as ve:
            print(f"[FAIL] Policy validation failed for '{policy_file}':")
            for error in ve.errors():
                loc = " -> ".join(str(x) for x in error.get("loc", []))
                msg = error.get("msg")
                print(f"       Field [{loc}]: {msg}")
            failed = True
        except Exception as e:
            print(f"[FAIL] Unexpected error reading policy '{policy_file}': {e}")
            failed = True
        print("-" * 46)

    if failed:
        print("[DEPLOYMENT BLOCKED] One or more policies failed validation check.")
        sys.exit(1)
    else:
        print(f"[SUCCESS] All {validated_count} policy files successfully validated. Ready for deployment!")
        sys.exit(0)

def policy_folder_to_id(folder_name: str) -> str:
    # Basic mapping helper
    if folder_name == "customer-support":
        return "customer-support-agent"
    elif folder_name == "loan-processor":
        return "loan-processor-agent"
    return f"{folder_name}-agent"

if __name__ == "__main__":
    validate_policies()
