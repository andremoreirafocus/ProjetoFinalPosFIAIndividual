# Desenvolvimento, execução e testes

Este documento reúne instruções de empacotamento, execução local e validação dos componentes MLOps.

## Estrutura

```text
MLOps/
├── app/
│   ├── api/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── feature_service.py
│   │   ├── model_service.py
│   │   ├── explanation_service.py
│   │   ├── credit_policy.py
│   │   └── requirements.txt
│   └── frontend/
│       ├── app.py
│       ├── field_config.py
│       └── requirements.txt
├── config/
│   └── feature_catalog.json
├── tests/
├── API.md
├── FRONTEND.md
├── DEVELOPMENT.md
├── AGENT_ARCHITECTURE.md
├── MONITORING_ARCHITECTURE.md
├── Dockerfile.api
├── Dockerfile.frontend
├── test-requirements.txt
└── README.md
```

## Inicialização com Docker

Na pasta `data-platform`:

```bash
docker compose up -d --build postgres credit-api credit-frontend
```

Para acompanhar os serviços:

```bash
docker compose logs -f credit-api credit-frontend
```

| Serviço | URL |
|---|---|
| Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Streamlit | http://localhost:8501 |

## Empacotamento

### API

`Dockerfile.api` instala as dependências da API, copia o código de `MLOps` e inicia Uvicorn na porta 8000.

O artefato não é embutido na imagem. O diretório `./Model/artifacts` é montado como somente leitura em `/app/Model/artifacts`. Um novo treinamento atualiza os arquivos no volume sem exigir novo build ou reinício da API: o modelo e suas referências são recarregados automaticamente quando formam um par compatível.

### Frontend

`Dockerfile.frontend` instala Streamlit e Requests, copia a aplicação e inicia o servidor na porta 8501. A comunicação interna utiliza `http://credit-api:8000`.

Como o código das aplicações é copiado durante o build, alterações em arquivos Python exigem reconstrução da imagem correspondente.

## Execução local

Com PostgreSQL e artefato disponíveis, crie o ambiente e inicie a API:

```bash
cd data-platform
python3 -m venv MLOps/.venv
MLOps/.venv/bin/python -m pip install -r MLOps/app/api/requirements.txt
MLOps/.venv/bin/python -m uvicorn MLOps.app.api.main:app --reload
```

Em outro terminal, inicie o frontend:

```bash
cd data-platform
MLOps/.venv/bin/python -m pip install -r MLOps/app/frontend/requirements.txt
CREDIT_API_URL=http://localhost:8000 \
  MLOps/.venv/bin/python -m streamlit run MLOps/app/frontend/app.py
```

## Testes

```bash
cd data-platform
python3 -m venv MLOps/.venv
MLOps/.venv/bin/python -m pip install -r MLOps/test-requirements.txt
MLOps/.venv/bin/python -m pip install -r MLOps/app/frontend/requirements.txt
MLOps/.venv/bin/python -m unittest discover -s MLOps/tests -v
```

`test-requirements.txt` inclui as dependências da API. A instalação dos requisitos do frontend permite executar `test_frontend.py`.

## Cobertura existente

| Arquivo | Responsabilidade validada |
|---|---|
| `test_credit_policy.py` | Faixas de aprovação, revisão e rejeição; limites inválidos e score fora de `[0, 1]`. |
| `test_config.py` | Limiares da política e intervalo de retry. |
| `test_model_service.py` | Carga do artefato, predição, categóricas e features ausentes. |
| `test_feature_service.py` | Recuperação da ABT, cliente inexistente e normalização de tipos. |
| `test_explanation_service.py` | SHAP local, referências e validação de versão. |
| `test_api_endpoints.py` | Contratos e erros HTTP via `TestClient`. |
| `test_model_loading.py` | Carga do modelo em segundo plano com ramos de falha e sucesso. |
| `test_frontend.py` | Inicialização da aplicação Streamlit. |
| `test_predict.py` | Inferência pelo script local e contrato do resultado. |
| `test_configuration.py` | Coerência entre configuração e artefato. |

Os testes da API utilizam fakes e fixtures injetados por composição. A suíte principal roda offline, sem PostgreSQL, LightGBM ou artefato treinado.

Os testes de integração `test_predict.py` e `test_configuration.py` são pulados automaticamente quando o artefato ou LightGBM não estão disponíveis. `test_frontend.py` é pulado quando o Streamlit não está instalado.

## Documentos relacionados

- [Visão geral do MLOps](README.md)
- [API de risco de crédito](API.md)
- [Interface Streamlit](FRONTEND.md)
- [Modelo](../Model/README.md)
- [Plataforma](../README.md)
