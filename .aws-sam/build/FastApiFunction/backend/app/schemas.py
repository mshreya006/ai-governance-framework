from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class ToolSchema(BaseModel):
    name: str = Field(..., description="Name of the tool")
    description: Optional[str] = Field(None, description="Description of the tool")
    scopes: List[str] = Field(..., description="List of scopes, e.g. read, write")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Scopes list cannot be empty")
        valid_scopes = {"read", "write"}
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope '{scope}'. Allowed scopes are: 'read', 'write'")
        return v

class GuardrailSchema(BaseModel):
    name: str = Field(..., description="Name of the guardrail")
    type: str = Field(..., description="Type of the guardrail, e.g. pii_redaction, content_filter")
    enabled: bool = Field(True, description="Whether the guardrail is active")

class HitlRuleSchema(BaseModel):
    condition: str = Field(..., description="Condition rule, e.g. tool_use == 'send_email'")
    reason: str = Field(..., description="Reason HITL is triggered if condition matches")

class HitlSchema(BaseModel):
    enabled: bool = Field(True, description="Whether HITL check is enabled")
    threshold: Optional[float] = Field(None, description="Sensitivity threshold for HITL trigger (0.0 to 1.0)")
    rules: List[HitlRuleSchema] = Field(default_factory=list, description="Specific rules triggering HITL")

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v

class DataRetentionSchema(BaseModel):
    audit_logs_days: int = Field(..., description="Number of days to retain logs")
    pii_masking: bool = Field(True, description="Whether to mask PII in retained logs")

    @field_validator("audit_logs_days")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Audit logs retention days must be greater than 0")
        return v

class PolicySchema(BaseModel):
    agent_id: str = Field(..., description="Unique alphanumeric identifier of the agent")
    version: str = Field(..., description="Semantic version string, e.g., 1.0.0")
    description: Optional[str] = Field(None, description="Detailed agent policy description")
    approved_models: List[str] = Field(..., description="Approved models list")
    allowed_tools: List[ToolSchema] = Field(default_factory=list, description="Permitted tools and scopes")
    guardrails: List[GuardrailSchema] = Field(default_factory=list, description="Active guardrails")
    hitl: HitlSchema = Field(..., description="Human-in-the-loop triggers")
    data_retention: DataRetentionSchema = Field(..., description="Data retention rules")
    regulatory_frameworks: List[str] = Field(default_factory=list, description="Regulatory compliance tags")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Agent ID must be alphanumeric and can only include '-' or '_'")
        return v

    @field_validator("approved_models")
    @classmethod
    def validate_approved_models(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Approved models list cannot be empty")
        for m in v:
            if not m.strip():
                raise ValueError("Model names cannot be empty strings")
        return v
