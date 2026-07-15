# Arquitetura proposta para monitoramento do modelo em produção

## Objetivo

Esta proposta define como identificar mudanças no comportamento dos dados e perda de performance do modelo após o deploy. O foco é acompanhar se novas solicitações continuam semelhantes à população de treinamento e, quando os desfechos reais estiverem disponíveis, verificar se o modelo mantém sua capacidade de ordenar o risco de crédito.

O monitoramento produz evidências e alertas para investigação. Ele não altera a política, não promove automaticamente um novo modelo e não substitui a validação necessária antes de um novo deploy.

## Escopo

API, PostgreSQL, Airflow e containers também precisam de monitoramento operacional de disponibilidade, latência, erros e recursos, como qualquer aplicação em produção. Para isso, propõe-se uma stack de observabilidade com Prometheus, Grafana e Alertmanager.

O monitoramento operacional é tratado no nível necessário para identificar falhas dos componentes. O foco principal permanece no risco específico de Machine Learning: mudanças nos dados, drift do score e degradação do modelo ao longo do tempo.

## Possíveis falhas operacionais

| Componente | Falha relevante |
|---|---|
| API e modelo | Indisponibilidade, aumento de latência ou falha no carregamento do artefato. |
| PostgreSQL | Indisponibilidade ou falha de conexão que impeça predição e persistência. |
| Airflow | Falha ou atraso nas DAGs de dados, treinamento e monitoramento. |
| Containers | Reinícios, indisponibilidade ou esgotamento de recursos. |
| Monitoramento | Ausência de métricas ou atraso no processamento dos lotes, detectados por regras específicas de monitoramento e alertas. |

Esses componentes enviam telemetria ao Prometheus. O Grafana permite acompanhar sua saúde e o Alertmanager encaminha as falhas detectadas para investigação operacional.

## Limitações e formação dos lotes

A base Home Credit utilizada no projeto é transversal e não contém datas absolutas de originação adequadas para reconstruir safras reais. Portanto, não seria correto simular monitoramento temporal sobre essa base como se ela representasse a operação histórica.

Em produção, cada nova aplicação deve registrar o instante da predição, a versão do modelo e da política e um identificador de lote. Os lotes passam a ser comparados com os baselines do treinamento e, posteriormente, com seus próprios desfechos de pagamento.

## Dois momentos do monitoramento

### Antes da chegada do desfecho

Logo após o processamento de um lote já é possível monitorar:

- qualidade e validade das features;
- distribuição das principais features;
- distribuição do `risk_score`;
- proporção de `approve`, `manual_review` e `reject`;
- PSI das features e do score contra o treinamento.

O PSI (*Population Stability Index*) mede quanto uma distribuição mudou em relação ao baseline. Ele permite detectar drift sem conhecer o target, mas não informa sozinho se o modelo perdeu performance ou qual foi a causa da mudança.

### Depois da maturação do desfecho

A inadimplência pode ocorrer durante o contrato, por isso um cliente que ainda não apresentou atraso não deve ser tratado imediatamente como adimplente. Cada operação permanece em um dos seguintes estados:

```text
pending       → janela de observação ainda aberta
default       → critério de inadimplência já observado
non_default   → janela encerrada sem inadimplência
```

Um default pode ser reconhecido assim que o critério for atingido. Um non-default só pode ser confirmado ao final de uma janela de observação definida pelo negócio e coerente com o target usado no treinamento. Contratos `pending` não entram como negativos nas métricas oficiais.

Somente com lotes maduros são recalculados:

- ROC AUC e Gini;
- KS;
- Average Precision;
- Brier e comportamento da calibração;
- inadimplência observada por faixa de score;
- performance e taxas de decisão por subgrupo para auditoria de fairness.

Quando apenas operações concedidas produzem desfecho observável, essas métricas representam a população aprovada. Essa limitação deve acompanhar sua interpretação.

## Baselines disponíveis e artefato proposto

O treinamento já produz os artefatos necessários para iniciar as comparações:

- `metrics.json`, com as métricas do holdout;
- `feature_reference.json`, com distribuições das features e do score;
- artefato do modelo, com features, categorias, threshold e versão da configuração.

Esses artefatos ainda não constituem monitoramento contínuo, mas fornecem as referências versionadas que serão consumidas pelo processo proposto.

Parte das informações necessárias ao monitoramento já existe em `feature_reference.json`, incluindo percentis das features numéricas, frequências das categorias e distribuição do score. Entretanto, esse artefato foi estruturado para apoiar a explicação individual produzida pela API.

O artefato proposto `monitoring_reference.json`, ainda não implementado, terá outra finalidade: registrar faixas fixas e proporções esperadas para o cálculo de PSI, referências de calibração e inadimplência por faixa de score e resultados por subgrupo para auditoria de fairness. Ele e `feature_reference.json` serão gerados na mesma execução e vinculados à mesma versão do modelo. A redundância parcial é intencional para preservar contratos e responsabilidades independentes.

Para gerar `monitoring_reference.json`, a etapa de treinamento executada pela DAG deverá ser estendida para calcular ou invocar esses cálculos sobre os dados de referência. A futura DAG de monitoramento utilizará o artefato para comparar os novos lotes sem recalcular o baseline.

## Arquitetura proposta

```text
API, PostgreSQL, Airflow e containers
              │ telemetria operacional
              ▼
          Prometheus ─────────→ Grafana
              │
              └───────────────→ Alertmanager ───→ Investigação operacional

Novas aplicações e predições
              │
              ▼
       Lotes de produção
              │
              ├────────────── Baselines do treinamento
              │              metrics.json + monitoring_reference.json (proposto)
              │                         │
              ▼                         ▼
            Airflow — pipeline de monitoramento
              │
              ├── qualidade e PSI das features e do score
              ├── distribuição das recomendações
              └── performance após maturação do target
              │
              ├── resultados ────────→ PostgreSQL ───────→ Grafana
              │
              └── métricas ──────────→ Prometheus
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
                          Grafana                     Alertmanager
                                                            │
                                                            ▼
                                                 Investigação e ação controlada
```

Uma DAG específica no Airflow executa o monitoramento por lote, carrega o baseline correspondente à versão do modelo, calcula as métricas disponíveis para o estágio de maturação e persiste os resultados no PostgreSQL.

O Prometheus recebe as métricas usadas pela stack de observabilidade. O Grafana apresenta sua evolução e também pode consultar os resultados analíticos persistidos no PostgreSQL. O Alertmanager encaminha as violações avaliadas a partir das métricas do Prometheus.

## Critérios de alerta

Os limites devem ser configurados e versionados conforme o baseline, o tamanho dos lotes e a tolerância do negócio. Os alertas principais são:

- aumento relevante do PSI das features ou do score;
- surgimento de categorias ou padrões de ausência inesperados;
- mudança acentuada na distribuição das recomendações;
- queda confirmada de AUC, KS ou Average Precision em lotes maduros;
- degradação da calibração;
- aumento de disparidade entre subgrupos.

Um alerta não prova sozinho que o modelo deve ser substituído. Ele abre uma investigação sobre origem dos dados, transformações, mudança de população, política vigente e comportamento observado.

## Resposta à degradação

```text
Alerta
  ↓
Validar dados e cálculo da métrica
  ↓
Identificar origem: dados, população, política ou modelo
  ↓
Confirmar impacto em mais de um indicador ou lote
  ↓
Reavaliar ou retreinar o modelo, quando necessário
  ↓
Validar e aprovar novo artefato antes do deploy
```

Drift sem perda de performance pode exigir apenas acompanhamento. Uma queda confirmada pode iniciar um retreinamento controlado, mas o novo candidato deve repetir avaliação, aprovação e versionamento. Não há promoção automática para produção.

## Responsabilidades

| Componente | Responsabilidade |
|---|---|
| API e pipeline de dados | Registrar predições, versões, lotes e informações necessárias ao monitoramento. |
| Airflow | Orquestrar os cálculos por lote e respeitar a maturação do target. |
| PostgreSQL | Persistir resultados, versões e rastreabilidade das avaliações. |
| Prometheus | Manter as séries da stack de observabilidade. |
| Grafana | Apresentar a evolução das métricas operacionais e do modelo. |
| Alertmanager | Encaminhar alertas quando os critérios versionados forem violados. |
| Responsável de ML ou negócio | Investigar o contexto e decidir a resposta adequada. |

## Estado da proposta

Já estão implementados:

- métricas de avaliação persistidas pelo treinamento;
- distribuições de referência das features e do score;
- validação do contrato de entrada pela API;
- endpoint de prontidão e retry de carregamento do modelo;
- avaliação offline de performance, calibração e fairness.

Permanecem como proposta:

- geração do artefato proposto `monitoring_reference.json` pela etapa de treinamento;
- persistência estruturada das predições e identificação dos lotes;
- definição da janela e ingestão dos desfechos reais;
- DAG de monitoramento;
- persistência dos resultados por lote;
- stack Prometheus, Grafana e Alertmanager;
- critérios versionados de alerta e processo controlado de resposta.
