from typing import Any, Literal

from pydantic import BaseModel, Field


class FeaturePredictionRequest(BaseModel):
    features: dict[str, Any] = Field(
        description="Features com os mesmos nomes usados no treinamento."
    )


class CustomerFeaturesResponse(BaseModel):
    customer_id: int
    features: dict[str, Any] = Field(
        description="Features recuperadas do banco para preenchimento do formulário."
    )


class CreditPolicyResult(BaseModel):
    recommendation: Literal["approve", "manual_review", "reject"]
    reason: str
    policy_version: str
    approve_max_score: float
    manual_review_max_score: float


class ShapFactor(BaseModel):
    feature: str
    value: Any
    shap_value: float
    direction: Literal["increases_risk", "reduces_risk"]


class LocalExplanation(BaseModel):
    base_value: float
    output_scale: Literal["raw_score"]
    top_factors: list[ShapFactor]


class PredictionResponse(BaseModel):
    source: Literal["provided_features", "database"]
    customer_id: int | None = None
    risk_score: float = Field(ge=0, le=1)
    predicted_class: int = Field(ge=0, le=1)
    model_decision_threshold: float = Field(ge=0, le=1)
    policy: CreditPolicyResult
    explanation: LocalExplanation | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_loaded: bool
    model_path: str
