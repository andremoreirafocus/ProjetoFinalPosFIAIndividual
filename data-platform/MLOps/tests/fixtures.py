"""Fixtures de dados para os testes da API (sem banco nem artefato treinado)."""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, text

from MLOps.tests.fakes import FakeModel


def build_artifact(
    model: Any | None = None,
    features: list[str] | None = None,
    categorical_features: list[str] | None = None,
    categories: dict[str, list[str]] | None = None,
    threshold: float = 0.5,
    include_input_features: bool = False,
) -> dict[str, Any]:
    """Monta um dicionário-artefato coerente com o contrato do ``PredictionService``.

    Por padrão usa ``features`` (chave atual); ``include_input_features`` adiciona a
    chave histórica ``input_features`` quando se quer testar a normalização.
    """
    artifact: dict[str, Any] = {
        "model": model if model is not None else FakeModel(),
        "features": features if features is not None else ["ext_source_1", "occupation_type"],
        "categorical_features": (
            categorical_features
            if categorical_features is not None
            else ["occupation_type"]
        ),
        "categories": (
            categories
            if categories is not None
            else {"occupation_type": ["Laborers", "Managers"]}
        ),
        "decision_threshold": threshold,
        "metrics": {"roc_auc": 0.75},
    }
    if include_input_features:
        artifact["input_features"] = artifact["features"]
    return artifact


def write_artifact_pickle(directory: Path, artifact: dict[str, Any]) -> Path:
    """Persiste um artefato-fixture em ``.pkl`` real para exercitar ``load()``."""
    path = directory / "artifact.pkl"
    with path.open("wb") as file:
        pickle.dump(artifact, file)
    return path


def sqlite_abt_engine() -> Engine:
    """Engine SQLite em memória com ``application_abt`` semeada.

    A linha 100002 traz ``inst_late_payment_rate`` presente (exercita o ramo em
    que ``setdefault`` não sobrescreve) e omite ``has_installments_history`` da
    tabela (exercita o ramo em que ``setdefault`` insere o valor padrão).
    """
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE application_abt ("
                "sk_id_curr INTEGER, target INTEGER, ext_source_1 REAL, "
                "occupation_type TEXT, inst_late_payment_rate REAL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO application_abt VALUES "
                "(100002, 1, 0.5, 'Laborers', 0.3)"
            )
        )
    return engine
