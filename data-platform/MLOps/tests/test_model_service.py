import unittest
from pathlib import Path

from MLOps.app.api.model_service import ModelInputError, PredictionService
from MLOps.tests.sample_features import build_features_from_artifact


DATA_PLATFORM_DIR = Path(__file__).resolve().parents[2]


class PredictionServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = PredictionService(
            DATA_PLATFORM_DIR / "Model" / "artifacts" / "lightgbm_abt.pkl"
        )
        cls.service.load()
        cls.features = build_features_from_artifact(cls.service.artifact)

    def test_prediction_is_valid(self) -> None:
        score, predicted_class = self.service.predict(self.features)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)
        self.assertIn(predicted_class, {0, 1})

    def test_missing_features_are_rejected(self) -> None:
        with self.assertRaises(ModelInputError):
            self.service.predict({"age": 35})


if __name__ == "__main__":
    unittest.main()
