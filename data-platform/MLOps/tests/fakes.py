"""Fakes reutilizáveis para os testes da API.

Regra do projeto: NUNCA usar monkeypatch/mock ou qualquer interceptação de código.
Aqui só existem implementações reais alternativas (fakes) que respeitam a mesma
interface dos componentes de produção e são injetadas por composição.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from MLOps.app.api.feature_service import CustomerNotFoundError
from MLOps.app.api.model_service import ModelInputError


class FakeModel:
    """Modelo com a mesma interface mínima usada pelo ``PredictionService``.

    Devolve uma probabilidade determinística para a classe positiva e guarda o
    ``DataFrame`` recebido, permitindo verificar o alinhamento de colunas e a
    restauração de categóricas feitos pelo serviço antes do ``predict_proba``.
    """

    def __init__(self, positive_proba: float = 0.6) -> None:
        self.positive_proba = positive_proba
        self.received: Any = None
        self.booster_ = self

    def predict_proba(self, features: Any) -> np.ndarray:
        self.received = features
        p = self.positive_proba
        return np.array([[1.0 - p, p]])

    def predict(self, features: Any, pred_contrib: bool = False) -> np.ndarray:
        self.received = features
        if not pred_contrib:
            raise ValueError("FakeModel suporta apenas pred_contrib=True neste método.")
        # Uma contribuição por feature e o valor-base na última coluna.
        return np.array([[0.25, -0.10, -0.40]])


class FakePredictionService:
    """Fake do ``PredictionService`` para exercitar a camada HTTP (``main.py``).

    Reproduz apenas o contrato consumido pelos endpoints: estado de carga,
    features esperadas, threshold e o resultado da predição.
    """

    def __init__(
        self,
        loaded: bool = True,
        features: list[str] | None = None,
        threshold: float = 0.5,
        score: float = 0.55,
        predicted_class: int = 1,
        missing: list[str] | None = None,
    ) -> None:
        self._loaded = loaded
        self._features = features or ["ext_source_1", "occupation_type"]
        self._threshold = threshold
        self._score = score
        self._class = predicted_class
        self._missing = missing
        self.model_path = "/fake/model.pkl"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def expected_features(self) -> list[str]:
        return list(self._features)

    @property
    def decision_threshold(self) -> float:
        return self._threshold

    def predict(self, features: dict[str, Any]) -> tuple[float, int]:
        if self._missing is not None:
            raise ModelInputError(self._missing)
        return self._score, self._class

class FakeFeatureService:
    """Fake do ``CustomerFeatureService`` para os endpoints por cliente.

    Configurável para devolver features, sinalizar cliente inexistente
    (``CustomerNotFoundError``) ou simular falha de banco (erro injetado).
    """

    def __init__(
        self,
        features: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._features = features
        self._error = error

    def build(self, customer_id: int) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        if self._features is None:
            raise CustomerNotFoundError(
                f"Cliente {customer_id} não encontrado em application_abt."
            )
        return dict(self._features)


class FakeExplanationService:
    """Fake do serviço de explicação injetado nos testes HTTP."""

    def __init__(self, explanation: dict[str, Any] | None = None) -> None:
        self.explanation = explanation or {
            "base_value": -0.4,
            "output_scale": "raw_score",
            "top_factors": [],
        }

    def explain(self, features: dict[str, Any]) -> dict[str, Any]:
        return dict(self.explanation)


class RetryFakeService:
    """Serviço de carga com sequência roteirizada, para exercitar o retry.

    ``load`` falha ``failures_before_success`` vezes e então marca ``is_loaded``,
    permitindo cobrir os dois ramos de ``_load_model_with_retry`` (erro + sucesso)
    sem interceptar código.
    """

    def __init__(self, failures_before_success: int = 1) -> None:
        self._remaining_failures = failures_before_success
        self._loaded = False
        self.model_path = "/fake/model.pkl"
        self.load_calls = 0

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        self.load_calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise RuntimeError("falha simulada de carga do artefato")
        self._loaded = True
