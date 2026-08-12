# AI Agent Policy-as-Code Governance Framework (PS-10.1)

A production-ready governance control center and enforcement runtime that aligns AI agent behavior with compliance policies. Policies are defined as YAML files alongside agent code, versioned in Git, verified in CI/CD, and deployed to an authoritative runtime engine. The system monitors policy drift and intercepts high-risk tasks for Human-in-the-Loop (HITL) review.

## 🚀 Architecture

The system is designed for serverless deployment on AWS (running entirely on the AWS Free Tier, $0/month) and fallback local execution.

```
       [ Vue 3 Frontend Control Center ]
                      │
                      ▼
         [ AWS API Gateway HTTP API ]
                      │
                      ▼
        [ AWS Lambda Backend (FastAPI) ]
           │                    │
           ▼                    ▼
   [ DynamoDB Table ]   [ OpenRouter Free LLM API ]
    (Single-Table)         (gemma-2-9b-it / llama-3)
```

### Key Technical Components
1. **Git Policy Repository**: Policies are defined inside `agents/` directories beside `agent.py` code.
2. **FastAPI Policy Engine**: Validates incoming AI workloads (model approval, tool scopes, guardrails, sentiment, and HITL) against database configurations.
3. **Dual-Mode Persistence**: Automatically queries AWS DynamoDB in the cloud, and falls back to a thread-safe local file-based database (`database.json`) for local sandbox environments.
4. **Drift Detector**: Scans and compares runtime active policies against Git-approved files, triggering alerts on unauthorized manual DB modifications.
5. **Interactive Vue 3 Dashboard**: Features dashboard KPIs, policy forms, a YAML visual editor, drift controls, HITL queues, and audit log ledgers.

---

## 🛠️ Local Installation & Development

### 1. Prerequisite Checks
Confirm `node` (v18+) and `python` (v3.10+) are installed.

### 2. Backend Setup
1. Clone the repository and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   py -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Create a `.env` file inside `backend/app/` (or set environment variables):
   ```env
   OPENROUTER_API_KEY=your_free_openrouter_api_key_here
   BACKEND_DEPLOY_TOKEN=dev-token-12345
   ```
   *Note: If `OPENROUTER_API_KEY` is not provided, the runner will output a warning and run in local mock mode to ensure tests and runs complete without cost.*
5. Run the FastAPI development server:
   ```bash
   py -m uvicorn backend.app.main:app --reload --port 8000
   ```
   Access API docs at: `http://localhost:8000/docs`

### 3. Frontend Setup
1. Open a new terminal in the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
   Access the dashboard at: `http://localhost:5173`

---

## 🧪 Running Automated Tests

We have implemented a comprehensive test suite covering 27 test cases (schema constraints, drift, blocks, HITL, health, and multi-thread concurrency).

Run tests from the root directory:
```bash
.\venv\Scripts\python.exe -m unittest discover -s backend/tests/ -p "test_*.py"
```

---

## 🔗 CI/CD Pipeline

The GitHub Actions workflow is defined in `.github/workflows/deploy.yml`. On every push to the `main` branch, the pipeline:
1. Installs Python dependencies.
2. Runs `scripts/validate_policy.py` to parse all agent `policy.yaml` files. If any required field is missing (e.g. `approved_models` or `hitl`) or tool scopes are invalid, **the build fails and blocks deployment**.
3. Executes unit tests.
4. Executes `scripts/deploy_policies.py` to push validated policies to the AWS Lambda backend.

---

## ☁️ AWS Cloud Deployment Guide

### Backend (AWS SAM CLI)
Ensure you have the AWS SAM CLI installed and configured with AWS credentials.

1. Navigate to the root directory containing `backend/template.yaml`.
2. Build the SAM package:
   ```bash
   sam build
   ```
3. Deploy to your AWS account (interactive mode):
   ```bash
   sam deploy --guided
   ```
4. Enter the stack name (e.g. `ai-governance-stack`), select your region, and confirm creation.
5. SAM will output the `ApiEndpoint` URL (e.g. `https://xxx.execute-api.us-east-1.amazonaws.com`). Save this!

### Frontend (Static S3 Hosting + CloudFront)
1. Build the Vue production build:
   ```bash
   cd frontend
   # Set the API endpoint URL to your AWS ApiEndpoint
   $env:VITE_API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com"
   npm run build
   ```
2. Create an AWS S3 bucket and enable static website hosting.
3. Upload the contents of `frontend/dist/` to the S3 bucket.
4. (Recommended) Create an AWS CloudFront distribution pointing to the S3 website endpoint to serve it securely over HTTPS ($0/month under free tier).

---

## 📈 Verification Checklist

You can test all governance criteria directly from the **AI Playground** and **Drift Detector** tabs in the Vue web application:

1. **Model Governance (ALLOW / BLOCK)**: Run a query selecting `google/gemma-2-9b-it:free` (passes check) or `openai/gpt-4o` (blocks with model-not-approved error).
2. **Tool Scope Governance (ALLOW / BLOCK)**: For `customer-support-agent`, run a query with `customer_lookup` tool (passes). Select `delete_database` (blocks with tool-disallowed error).
3. **Guardrail Enforcements**: Submit a query containing sensitive data (e.g. `SSN 000-12-3456`). The request is instantly blocked by the PII guardrail.
4. **Human-in-the-Loop Triggers**: Submit a query using the `send_email` tool. The execution suspends, returns a `PENDING_HITL` status, and puts the request in the HITL review queue where it can be approved or rejected.
5. **Drift Detection**: Modify runtime settings out-of-band on the Drift page. A red alert banner immediately flags the mismatch. Clicking **Revert to Git Policy** resolves the drift.
