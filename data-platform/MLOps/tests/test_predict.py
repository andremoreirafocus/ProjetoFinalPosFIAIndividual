import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from Model.predict import load_artifact, predict_score
from MLOps.tests.sample_features import build_features_from_artifact


DATA_PLATFORM_DIR = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = DATA_PLATFORM_DIR / "Model" / "artifacts" / "lightgbm_abt.pkl"
ARTIFACT_READY = (
    ARTIFACT_PATH.is_file() and importlib.util.find_spec("lightgbm") is not None
)


@unittest.skipUnless(
    ARTIFACT_READY,
    "Teste de integração: requer o artefato lightgbm_abt.pkl e o LightGBM instalado.",
)
class PredictScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = load_artifact(
            DATA_PLATFORM_DIR / "Model" / "artifacts" / "lightgbm_abt.pkl"
        )

    def test_predicts_single_row(self) -> None:
        features = build_features_from_artifact(self.artifact)
        row = pd.DataFrame([features])
        result = predict_score(row, self.artifact)

        self.assertGreaterEqual(result["risk_score"], 0)
        self.assertLessEqual(result["risk_score"], 1)
        self.assertIn(result["predicted_class"], {0, 1})
        self.assertEqual(result["decision_threshold"], 0.5)


if __name__ == "__main__":
    unittest.main()
