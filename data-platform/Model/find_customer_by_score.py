"""Busca exaustivamente na ABT um cliente com score dentro de uma faixa."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

from predict import get_database_connection


MODEL_DIR = Path(__file__).resolve().parent
PREDICT_SCRIPT = MODEL_DIR / "predict.py"
RISK_SCORE_PATTERN = re.compile(r"Risk Score\s*:\s*([0-9]+(?:\.[0-9]+)?)")


def load_customer_ids() -> list[int]:
    """Retorna todos os identificadores existentes na ABT em ordem crescente."""
    connection = get_database_connection(silent=True)
    try:
        customers = pd.read_sql_query(
            "SELECT sk_id_curr FROM application_abt ORDER BY sk_id_curr",
            connection,
        )
    finally:
        connection.close()

    return customers["sk_id_curr"].astype(int).tolist()


def run_prediction(customer_id: int) -> tuple[float, str]:
    """Executa predict.py para um cliente e extrai o score de sua saída."""
    result = subprocess.run(
        [sys.executable, str(PREDICT_SCRIPT), "--sk-id", str(customer_id)],
        cwd=MODEL_DIR.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(
            f"A predição do cliente {customer_id} falhou com código "
            f"{result.returncode}:\n{output}"
        )

    match = RISK_SCORE_PATTERN.search(output)
    if not match:
        raise RuntimeError(
            f"Não foi possível extrair o score do cliente {customer_id}:\n{output}"
        )

    return float(match.group(1)), output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Encontra na ABT o primeiro cliente com score na faixa informada."
    )
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--max-score", type=float, default=0.6)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0 <= args.min_score < args.max_score <= 1:
        raise ValueError("A faixa deve respeitar 0 <= min-score < max-score <= 1.")

    customer_ids = load_customer_ids()
    print(
        f"[BUSCA] Testando {len(customer_ids):,} clientes na faixa "
        f"{args.min_score} <= score < {args.max_score}."
    )

    for position, customer_id in enumerate(customer_ids, start=1):
        score, output = run_prediction(customer_id)
        print(
            f"[BUSCA] {position:,}/{len(customer_ids):,} — "
            f"cliente {customer_id}: score={score:.4f}"
        )
        if args.min_score <= score < args.max_score:
            print("\n[ENCONTRADO]")
            print(output, end="" if output.endswith("\n") else "\n")
            return 0

    print("[BUSCA] Nenhum cliente encontrado na faixa informada.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
