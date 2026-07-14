import types
import unittest

from MLOps.app.api.main import _load_model_with_retry
from MLOps.tests.fakes import RetryFakeService


class LoadModelWithRetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_retries_until_model_loads(self) -> None:
        # ``app`` real e leve (não é mock): só precisa de ``state.model_load_error``.
        app = types.SimpleNamespace(
            state=types.SimpleNamespace(model_load_error=None)
        )
        service = RetryFakeService(failures_before_success=1)

        await _load_model_with_retry(app, service, retry_seconds=0.01)

        # Falhou uma vez (ramo de erro) e carregou na segunda (ramo de sucesso).
        self.assertTrue(service.is_loaded)
        self.assertEqual(service.load_calls, 2)
        self.assertIsNone(app.state.model_load_error)


if __name__ == "__main__":
    unittest.main()
