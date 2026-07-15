# Interface Streamlit

O frontend localizado em `app/frontend` é um simulador para o analista de crédito. Ele consome exclusivamente a API FastAPI e nunca acessa diretamente o modelo ou o arquivo Pickle.

## Responsabilidade

O Streamlit apresenta as jornadas de demonstração e explica o resultado da API. Inferência, acesso à ABT e política de crédito permanecem nos serviços da API.

```text
Analista
   │
   ▼
Streamlit ── HTTP ──→ FastAPI ──→ modelo, política e explicação
```

## Recursos implementados

- URL da API configurável na barra lateral;
- botão **Verificar conexão**, que consulta `/health`;
- campos agrupados por contexto;
- opções controladas para categóricas;
- seleção binária para flags;
- limites e passos para valores numéricos;
- exibição da requisição e da resposta JSON;
- aviso de que o score não é uma probabilidade calibrada.

## Jornadas

### Preencher todos os dados

Renderiza as features descritas em `field_config.py`. O formulário envia todas as entradas para `POST /predict/features`.

### Buscar cliente e editar

Recupera as features com `GET /customers/{customer_id}/features`, mantém o cliente no `session_state`, preenche um formulário editável e permite reavaliar o caso. As alterações simuladas não modificam a ABT.

### Consultar cliente do banco

Envia o identificador para `POST /predict/customer/{customer_id}`. A API recupera as features da ABT e calcula o resultado sem edição manual.

## Apresentação do resultado

Em todas as jornadas, o frontend apresenta:

- origem das features;
- `risk_score`;
- classe prevista;
- threshold do modelo;
- recomendação e justificativa da política;
- limites e versão da política;
- barra de posição na escala de risco;
- explicação local quando a recomendação é `manual_review`;
- JSONs enviado e recebido.

O frontend é apenas um consumidor do contrato HTTP. Alterações no modelo ou na política não devem ser implementadas na camada de apresentação.

## Configuração

| Variável | Finalidade | Padrão no Compose |
|---|---|---|
| `CREDIT_API_URL` | URL da API consumida pelo frontend | `http://credit-api:8000` |

## Execução

Com a API disponível:

```bash
cd data-platform
MLOps/.venv/bin/python -m pip install -r MLOps/app/frontend/requirements.txt
CREDIT_API_URL=http://localhost:8000 \
  MLOps/.venv/bin/python -m streamlit run MLOps/app/frontend/app.py
```

A interface estará disponível em http://localhost:8501.

## Evolução proposta

A futura interface de revisão poderá evoluir a partir do frontend atual para consultar os relatórios produzidos pelo agente acelerador de revisão de crédito. Ela continuará sendo consumidora dos relatórios e não executará diretamente o agente ou o modelo de linguagem.

Consulte a [arquitetura proposta do agente acelerador de revisão de crédito](AGENT_ARCHITECTURE.md).

## Documentos relacionados

- [Visão geral do MLOps](README.md)
- [API de risco de crédito](API.md)
- [Desenvolvimento, execução e testes](DEVELOPMENT.md)
