import os
from dotenv import load_dotenv

# Load env variables from a .env file if it exists (useful for local dev)
load_dotenv()

# Check if we are running in AWS Lambda
IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ
IS_LOCAL = not IS_LAMBDA

# AWS DynamoDB config
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "ai_governance_data")

# API Keys and Auth Tokens
# OpenRouter API Key for real LLM connection
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Deployment Token to authenticate push deployments from CI/CD
BACKEND_DEPLOY_TOKEN = os.getenv("BACKEND_DEPLOY_TOKEN", "dev-token-12345")

# Local fallback database file
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "database.json")
