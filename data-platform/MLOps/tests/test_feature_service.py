import unittest

import numpy as np

from MLOps.app.api.feature_service import (
    CustomerFeatureService,
    CustomerNotFoundError,
)
from MLOps.tests.fixtures import sqlite_abt_engine


class CustomerFeatureServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CustomerFeatureService(sqlite_abt_engine())

    def test_build_returns_features_without_identifier_and_target(self) -> None:
        features = self.service.build(100002)

        # Identificador e alvo não podem vazar como variáveis explicativas.
        self.assertNotIn("sk_id_curr", features)
        self.assertNotIn("target", features)
        self.assertEqual(features["ext_source_1"], 0.5)
        self.assertEqual(features["occupation_type"], "Laborers")
        # setdefault não sobrescreve valor presente...
        self.assertEqual(features["inst_late_payment_rate"], 0.3)
        # ...e insere o padrão quando a coluna não existe na ABT.
        self.assertEqual(features["has_installments_history"], 0)

    def test_missing_customer_raises_not_found(self) -> None:
        with self.assertRaises(CustomerNotFoundError):
            self.service.build(999999)

    def test_python_value_unwraps_numpy_scalars(self) -> None:
        result = CustomerFeatureService._python_value(np.int64(5))
        self.assertEqual(result, 5)
        self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main()
