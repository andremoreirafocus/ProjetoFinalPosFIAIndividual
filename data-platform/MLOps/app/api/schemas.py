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


class BinaryRates(BaseModel):
    overall: float
    target_0: float
    target_1: float


class NumericComparison(BaseModel):
    training_percentile_low: float = Field(ge=0, le=100)
    training_percentile_high: float = Field(ge=0, le=100)
    population_mean: float
    population_median: float
    population_p25: float
    population_p75: float
    target_0_median: float
    target_1_median: float
    binary_rates: BinaryRates | None = None


class CategoricalComparison(BaseModel):
    category_count: int = Field(ge=0)
    category_frequency: float = Field(ge=0, le=1)
    category_default_rate: float | None = Field(default=None, ge=0, le=1)
    population_default_rate: float = Field(ge=0, le=1)


class ShapComparison(BaseModel):
    global_mean_abs_shap: float = Field(ge=0)
    local_abs_shap: float = Field(ge=0)
    abs_shap_percentile_low: int = Field(ge=0, le=100)
    abs_shap_percentile_high: int = Field(ge=0, le=100)


class FeatureComparison(BaseModel):
    feature_type: Literal["numeric", "categorical"]
    shap: ShapComparison
    numeric: NumericComparison | None = None
    categorical: CategoricalComparison | None = None


class ShapFactor(BaseModel):
    feature: str
    value: Any
    shap_value: float
    direction: Literal["increases_risk", "reduces_risk"]
    comparison: FeatureComparison


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
