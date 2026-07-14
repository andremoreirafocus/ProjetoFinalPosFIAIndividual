import unittest

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from MLOps.app.api.credit_policy import CreditPolicy
from MLOps.app.api.main import app
from MLOps.tests.fakes import FakeFeatureService, FakePredictionService


def _db_error() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("conexão indisponível"))


class ApiEndpointsTest(unittest.TestCase):
    """Exercita a camada HTTP injetando fakes em ``app.state``.

    O ``TestClient`` é usado sem ``with`` de propósito: assim o ``lifespan`` não
    roda e nenhum serviço real (engine de banco, tarefa de carga) é criado. Os
    endpoints leem os serviços de ``app.state`` a cada requisição, então basta
    popular esse estado — o mecanismo oficial de estado do FastAPI, não um patch.
    """

    def _client(
        self,
        prediction_service: FakePredictionService | None = None,
        feature_service: FakeFeatureService | None = None,
    ) -> TestClient:
        client = TestClient(app)
        app.state.prediction_service = prediction_service or FakePredictionService()
        app.state.feature_service = feature_service or FakeFeatureService(
            features={"ext_source_1": 0.5, "occupation_type": "Laborers"}
        )
        app.state.credit_policy = CreditPolicy(0.50, 0.60, "test-v1")
        app.state.model_load_error = None
        return client

    # --- /health ---------------------------------------------------------
    def test_health_ok_when_model_loaded(self) -> None:
        client = self._client(FakePredictionService(loaded=True))
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model_loaded"], True)

    def test_health_unavailable_when_model_not_loaded(self) -> None:
        client = self._client(FakePredictionService(loaded=False))
        app.state.model_load_error = "Modelo não encontrado"
        response = client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["detail"]["model_loaded"])

    # --- /model/features -------------------------------------------------
    def test_model_features_lists_expected_features(self) -> None:
        client = self._client(
            FakePredictionService(features=["ext_source_1", "age"])
        )
        response = client.get("/model/features")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["ext_source_1", "age"])

    # --- /customers/{id}/features ---------------------------------------
    def test_customer_features_returns_row(self) -> None:
        client = self._client(
            feature_service=FakeFeatureService(features={"ext_source_1": 0.5})
        )
        response = client.get("/customers/100002/features")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["customer_id"], 100002)
        self.assertEqual(body["features"], {"ext_source_1": 0.5})

    def test_customer_features_not_found(self) -> None:
        client = self._client(feature_service=FakeFeatureService(features=None))
        response = client.get("/customers/999/features")
        self.assertEqual(response.status_code, 404)

    def test_customer_features_database_error(self) -> None:
        client = self._client(
            feature_service=FakeFeatureService(error=_db_error())
        )
        response = client.get("/customers/100002/features")
        self.assertEqual(response.status_code, 503)

    # --- /predict/features ----------------------------------------------
    def test_predict_from_features_contract(self) -> None:
        client = self._client(
            FakePredictionService(score=0.55, predicted_class=1, threshold=0.5)
        )
        response = client.post(
            "/predict/features", json={"features": {"ext_source_1": 0.5}}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "provided_features")
        self.assertIsNone(body["customer_id"])
        self.assertEqual(body["risk_score"], 0.55)
        self.assertEqual(body["predicted_class"], 1)
        self.assertEqual(body["model_decision_threshold"], 0.5)
        # 0.55 cai na faixa [0.50, 0.60) -> revisão manual.
        self.assertEqual(body["policy"]["recommendation"], "manual_review")
        self.assertEqual(body["policy"]["policy_version"], "test-v1")
        self.assertIsNotNone(body["explanation"])
        self.assertEqual(body["explanation"]["output_scale"], "raw_score")

    def test_predict_from_features_missing_returns_422(self) -> None:
        client = self._client(
            FakePredictionService(missing=["occupation_type", "age"])
        )
        response = client.post(
            "/predict/features", json={"features": {"ext_source_1": 0.5}}
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["missing_features"],
            ["occupation_type", "age"],
        )

    def test_predict_from_features_model_unavailable_returns_503(self) -> None:
        client = self._client(FakePredictionService(loaded=False))
        response = client.post(
            "/predict/features", json={"features": {"ext_source_1": 0.5}}
        )
        self.assertEqual(response.status_code, 503)

    # --- /predict/customer/{id} -----------------------------------------
    def test_predict_from_database_uses_customer_source(self) -> None:
        client = self._client(
            FakePredictionService(score=0.20, predicted_class=0),
            feature_service=FakeFeatureService(features={"ext_source_1": 0.5}),
        )
        response = client.post("/predict/customer/100002")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "database")
        self.assertEqual(body["customer_id"], 100002)
        # 0.20 < 0.50 -> aprovação.
        self.assertEqual(body["policy"]["recommendation"], "approve")
        self.assertIsNone(body["explanation"])

    def test_predict_from_database_not_found_returns_404(self) -> None:
        client = self._client(feature_service=FakeFeatureService(features=None))
        response = client.post("/predict/customer/999")
        self.assertEqual(response.status_code, 404)

    def test_predict_from_database_error_returns_503(self) -> None:
        client = self._client(
            feature_service=FakeFeatureService(error=_db_error())
        )
        response = client.post("/predict/customer/100002")
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
