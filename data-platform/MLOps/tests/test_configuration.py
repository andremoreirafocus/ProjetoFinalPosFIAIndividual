import json
import pickle
import unittest
from pathlib import Path


DATA_PLATFORM_DIR = Path(__file__).resolve().parents[2]


class ModelContractTest(unittest.TestCase):
    """Protege o contrato entre a configuração do modelo e o artefato treinado.

    Se a lista de features declarada em ``config_model.json`` divergir da lista
    persistida no artefato (por edição da configuração sem retreino, ou vice-versa),
    a API alinharia as colunas de forma incorreta na inferência. Este teste falha
    cedo diante dessa divergência.
    """

    def test_model_features_match_persisted_artifact(self) -> None:
        config = json.loads(
            (DATA_PLATFORM_DIR / "Model/config_model.json").read_text(
                encoding="utf-8"
            )
        )
        with (
            DATA_PLATFORM_DIR / "Model/artifacts/lightgbm_abt.pkl"
        ).open("rb") as file:
            artifact = pickle.load(file)

        # A chave atual do artefato é ``features``; ``input_features`` é a histórica.
        artifact_features = artifact.get("input_features", artifact.get("features"))
        self.assertEqual(
            config["variables"]["input_features"],
            artifact_features,
        )


if __name__ == "__main__":
    unittest.main()
