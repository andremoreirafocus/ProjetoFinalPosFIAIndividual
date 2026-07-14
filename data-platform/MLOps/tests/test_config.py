import unittest

from MLOps.app.api.config import Settings


class SettingsValidateTest(unittest.TestCase):
    def _settings(self, **overrides) -> Settings:
        base = dict(
            model_load_retry_seconds=5.0,
            approve_max_score=0.50,
            manual_review_max_score=0.60,
        )
        base.update(overrides)
        return Settings(**base)

    def test_valid_settings_pass(self) -> None:
        # Não deve levantar exceção.
        self._settings().validate()

    def test_non_positive_retry_is_rejected(self) -> None:
        for retry in (0.0, -1.0):
            with self.subTest(retry=retry):
                with self.assertRaises(ValueError):
                    self._settings(model_load_retry_seconds=retry).validate()

    def test_invalid_thresholds_are_rejected(self) -> None:
        invalid = [
            {"approve_max_score": 0.70, "manual_review_max_score": 0.60},  # approve >= review
            {"approve_max_score": 0.50, "manual_review_max_score": 1.10},  # review > 1
            {"approve_max_score": -0.10, "manual_review_max_score": 0.60},  # approve < 0
        ]
        for overrides in invalid:
            with self.subTest(**overrides):
                with self.assertRaises(ValueError):
                    self._settings(**overrides).validate()


if __name__ == "__main__":
    unittest.main()
