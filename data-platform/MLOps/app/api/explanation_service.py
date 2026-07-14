from typing import Any

import numpy as np

from .model_service import PredictionService


class ExplanationService:
    """Calcula explicações locais usando o mesmo modelo e preparo da predição."""

    def __init__(self, prediction_service: PredictionService) -> None:
        self.prediction_service = prediction_service

    def explain(
        self, features: dict[str, Any], max_factors: int = 10
    ) -> dict[str, Any]:
        """Calcula contribuições TreeSHAP locais para um único cliente."""
        customer = self.prediction_service.prepare_customer(features)
        model = self.prediction_service.model
        booster = getattr(model, "booster_", None)
        if booster is None:
            raise RuntimeError("O modelo carregado não oferece explicação TreeSHAP.")

        contributions = np.asarray(
            booster.predict(customer, pred_contrib=True), dtype=float
        )
        expected_features = self.prediction_service.expected_features
        if (
            contributions.ndim != 2
            or contributions.shape[1] != len(expected_features) + 1
        ):
            raise RuntimeError("Formato inesperado das contribuições TreeSHAP.")

        feature_contributions = contributions[0, :-1]
        factors = []
        for feature, shap_value in zip(expected_features, feature_contributions):
            value = customer.iloc[0][feature]
            if hasattr(value, "item"):
                value = value.item()
            factors.append(
                {
                    "feature": feature,
                    "value": value,
                    "shap_value": float(shap_value),
                    "direction": (
                        "increases_risk" if shap_value > 0 else "reduces_risk"
                    ),
                }
            )

        factors.sort(key=lambda item: abs(item["shap_value"]), reverse=True)
        return {
            "base_value": float(contributions[0, -1]),
            "output_scale": "raw_score",
            "top_factors": factors[:max_factors],
        }
