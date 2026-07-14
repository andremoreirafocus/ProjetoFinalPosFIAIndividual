import unittest
from pathlib import Path

from MLOps.app.api.explanation_service import ExplanationService
from MLOps.app.api.model_service import PredictionService
from MLOps.tests.fakes import FakeModel
from MLOps.tests.fixtures import build_artifact


class ExplanationServiceTest(unittest.TestCase):
    def _service(self) -> ExplanationService:
        prediction_service = PredictionService(Path("/loaded/in/memory.pkl"))
        prediction_service.artifact = build_artifact(
            model=FakeModel(), include_input_features=True
        )
        return ExplanationService(prediction_service)

    def test_returns_ranked_local_shap_contributions(self) -> None:
        explanation = self._service().explain(
            {"ext_source_1": 0.5, "occupation_type": "Managers"}
        )

        self.assertEqual(explanation["base_value"], -0.4)
        self.assertEqual(explanation["output_scale"], "raw_score")
        self.assertEqual(
            [factor["feature"] for factor in explanation["top_factors"]],
            ["ext_source_1", "occupation_type"],
        )
        self.assertEqual(
            explanation["top_factors"][0]["direction"], "increases_risk"
        )
        self.assertEqual(
            explanation["top_factors"][1]["direction"], "reduces_risk"
        )


if __name__ == "__main__":
    unittest.main()
