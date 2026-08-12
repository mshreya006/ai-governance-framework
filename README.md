# AI Agent Policy-as-Code Governance Framework (PS-10.1)

This project is a production-ready governance control center and enforcement runtime designed to align AI agent operations with enterprise compliance policies. Policies are defined as YAML files alongside agent code, versioned in Git, validated automatically in CI/CD pipelines, and deployed to an authoritative runtime engine. The system monitors policy drift and intercepts high-risk tasks for Human-in-the-Loop (HITL) review.

---

## Project Overview and Problem Statement

### PS-10.1: Policy-as-Code for AI Agents
Autonomous AI agents are increasingly deployed in enterprise workflows, performing automated lookups, credit reviews, customer messaging, and transaction approvals. Without authoritative guardrails, these agents run the risk of executing unauthorized commands, utilizing unapproved LLM models, exposing personally identifiable information (PII), or making high-stakes decisions without human oversight.

This framework solves the problem by inserting a centralized, lightweight governance gateway between client applications and large language models (LLMs). The gateway intercepts all requests, parses the active policy rules, evaluates compliance boundaries, logs actions to an immutable ledger, and halts executions for human verification when necessary.

---

## System Architecture

The application is engineered to support both local developer testing and scalable, cost-efficient serverless hosting on AWS.

### 1. Serverless AWS Cloud Stack
* **Frontend Hosting**: AWS S3 Static Website Hosting stores the pre-compiled, optimized Vue 3 Single Page Application (SPA), delivering the dashboard to the user's browser.
* **API Entrypoint**: AWS API Gateway routes public HTTP requests from the browser directly to the Lambda function.
* **Execution Environment**: AWS Lambda executes the FastAPI Python backend, scaling dynamically to zero when inactive to eliminate hosting costs.
* **Database Layer**: AWS DynamoDB stores version logs, pending approvals, and audits in a single-table layout.
* **LLM Integration**: The Lambda function connects to OpenRouter to query live models (like OpenAI GPT-4o or Google Gemini), automatically falling back to a local mockup completion engine if API connections are offline.

### 2. Local Sandbox Environment
* **Database Fallback**: When run locally, the system automatically detects the environment and uses a thread-safe local JSON database (`database.json`) protected by file-locking threads.
* **Mock LLM Fallback**: If no OpenRouter API key is provided, the backend generates simulated text completions, allowing full governance checks without cost.

---

## Directory Structure

```text
ai-governance-framework/
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD workflow
├── agents/                         # Git-tracked agent code and policies
│   ├── customer-support/
│   │   ├── agent.py               # Customer Support Agent class
│   │   └── policy.yaml            # Customer Support YAML policy configuration
│   └── loan-processor/
│       ├── agent.py               # Loan Processor Agent class
│       └── policy.yaml            # Loan Processor YAML policy configuration
├── backend/                        # FastAPI Application
│   ├── app/
│   │   ├── config.py              # Environment configuration loader
│   │   ├── database.py            # Database client (DynamoDB / JSON fallback)
│   │   ├── schemas.py             # Pydantic v2 policy schemas
│   │   ├── policy_engine.py       # Validation, drift, and intercept engines
│   │   ├── agent_runner.py        # LLM connector and mock tool execution
│   │   └── main.py                # FastAPI routes, CORS, and seeding
│   ├── tests/                     # Automated unit test suite (27 tests)
│   │   ├── test_policy.py         # Schema constraint tests
│   │   ├── test_drift.py          # Drift diff algorithm tests
│   │   ├── test_governance.py     # Model and tool block tests
│   │   ├── test_hitl.py           # HITL sentiment and rules tests
│   │   ├── test_api.py            # API endpoint integration tests
│   │   └── test_concurrency.py    # Database thread safety tests
│   └── template.yaml              # AWS SAM IaC template
├── frontend/                      # Vue 3 Vite Control Center
│   ├── src/
│   │   ├── App.vue                # Main layout and tab routing
│   │   ├── style.css              # Custom dark-themed CSS styling
│   │   └── components/            # View components
│   │       ├── DashboardView.vue  # KPI summary cards
│   │       ├── AgentsView.vue     # Agent status panels
│   │       ├── PoliciesView.vue   # Structured policy and YAML editor
│   │       ├── VersionsView.vue   # Deployment history explorer
│   │       ├── DriftView.vue      # Out-of-band drift simulator
│   │       ├── PlaygroundView.vue # Interactive query tester
│   │       ├── ApprovalsView.vue  # HITL manager queue
│   │       └── AuditView.vue      # Immutable ledger browser
├── scripts/                       # Automation scripts
│   ├── validate_policy.py         # CI schema validation script
│   └── deploy_policies.py         # CI database deploy script
├── .gitignore                     # Git tracking exclusions
├── .samignore                     # AWS SAM package exclusions
├── requirements.txt               # Workspace dependencies
└── README.md                      # Main documentation file
```

---

## Local Installation and Development

### 1. Prerequisite Verification
Ensure your system has the following runtimes installed:
* Python (version 3.10 or higher)
* Node.js (version 18 or higher)
* Git

### 2. Backend Setup
1. Clone the project to your local directory.
2. In your terminal, navigate to the project root directory and create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   * Windows PowerShell: `.\venv\Scripts\Activate.ps1`
   * Windows CMD: `.\venv\Scripts\activate.bat`
   * macOS/Linux: `source venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Launch the FastAPI backend:
   ```bash
   python -m uvicorn backend.app.main:app --port 8000
   ```
   Confirm that the server starts on `http://127.0.0.1:8000` and creates the `database.json` file.

### 3. Frontend Setup
1. Open a separate terminal, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   Confirm the interface compiles and opens at `http://localhost:5173`.

---

## Running the Automated Test Suite

A comprehensive test suite containing 27 unit and integration tests verifies the integrity of the schema, policy engine, API routes, database concurrency, and drift detection.

To run the test suite, execute this command from the project root directory:
```bash
python -m unittest discover -s backend/tests/ -p "test_*.py"
```

---

## Important Environment Variables

The backend loads settings dynamically. You can configure these in your terminal environment or inside a `.env` file in the project root:

* `LOCAL_DB_PATH`: Sets the filename for local JSON database file (defaults to `database.json`).
* `OPENROUTER_API_KEY`: The API key used to execute real requests on OpenRouter. If empty, the backend runs in mockup fallback mode.
* `BACKEND_DEPLOY_TOKEN`: The authorization token required by the CI/CD script to publish new policies (defaults to `dev-token-12345`).

---

## AWS Cloud Deployment Guide

### 1. Backend Deployment (AWS SAM)
Ensure you have the AWS CLI and AWS SAM CLI installed, and your credentials configured via `aws configure`.

1. In the project root, build the serverless package:
   ```bash
   sam build -t backend/template.yaml
   ```
2. Deploy the stack:
   ```bash
   sam deploy --template-file .aws-sam/build/template.yaml --stack-name ai-governance-stack --resolve-s3 --capabilities CAPABILITY_IAM --region ap-south-1
   ```
   Note the `ApiEndpoint` URL printed in the Outputs table (e.g., `https://uw3az06df5.execute-api.ap-south-1.amazonaws.com`).

### 2. Frontend Deployment (AWS S3 Static Website)
1. Open [frontend/.env](file:///d:/Shreya/AI_GOVERNANCE_PROJECT/frontend/.env) and set the endpoint to your live API Gateway URL:
   ```env
   VITE_API_URL=https://your-api-id.execute-api.ap-south-1.amazonaws.com
   ```
2. Run the deployment script to compile code and upload assets:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/deploy_frontend.ps1
   ```
   Enter a unique S3 bucket name when prompted. The script will output the live URL.

---

## GitHub Actions CI/CD Integration

The GitHub Actions workflow is defined in `.github/workflows/deploy.yml` and triggers automatically on pushes to the `main` branch:

1. **Schema Check**: Executes `validate_policy.py` to verify that all policy YAMLs adhere strictly to Pydantic rules. If there are missing fields or invalid scopes, the pipeline halts.
2. **Unit Tests**: Executes all 27 unit tests to verify backend logic.
3. **Sync Policies**: Calls the deployment API to register the policies under the Git commit SHA.

To link the pipeline to your live AWS backend, add these Secrets to your GitHub repository settings:
* `BACKEND_API_URL`: Your deployed API Gateway endpoint.
* `BACKEND_DEPLOY_TOKEN`: The deploy token (e.g. `dev-token-12345`).

---

## How to Verify Governance Rules

Open the S3 static website URL in your browser and execute these checks:

### 1. Model Governance
Go to the **AI Playground** tab. Select `anthropic/claude-3-opus (Unapproved)` and click **Run**. The engine will intercept the call, block it, and display a model-blocked validation message. Select `openai/gpt-4o` (Approved) to pass the check.

### 2. Tool Scope Governance
Select `Customer Support Agent` in the playground. Run a prompt with the `customer_lookup` tool (Approved scope). The workload executes. Change the tool to `delete_database` (Disallowed scope) and run. The workload is blocked by the policy engine.

### 3. Guardrail Exclosures
Submit a prompt containing sensitive data (e.g., `"Query applicant details with SSN 000-12-3456"`). The request is instantly blocked by the PII content guardrail.

### 4. Human-in-the-Loop Intercepts
Submit a prompt with the `send_email` tool. The pipeline intercepts the write tool and sets the status to `PENDING_HITL`. Go to the **HITL Reviews** tab to approve or reject the paused workload.

### 5. Drift Detection and Resolution
Go to the **Drift Detector** tab. Select the threshold drift simulator and inject a manual DB modification. The page alerts you of policy drift. Click **Revert to Git Policy** to restore database alignment with your Git repository files.
