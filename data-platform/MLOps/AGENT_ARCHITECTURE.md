# Arquitetura proposta para o agente acelerador de revisão de crédito

## Objetivo

Esta proposta descreve o agente acelerador de revisão de crédito, que utiliza IA para acelerar o processo de revisão humana de solicitações classificadas pela política como `manual_review` e, com isto, reduzir o tempo de espera do cliente e o custo da avaliação.

O agente acelerador de revisão de crédito transforma as informações produzidas pela API de avaliação de risco de crédito em um relatório que ajuda o analista a identificar rapidamente os aspectos relevantes do caso.

## Contexto disponível

Para viabilizar o trabalho do agente acelerador de revisão de crédito, a API passou a produzir os elementos quantitativos necessários para a análise:

- score de risco, classe prevista e versão do modelo;
- recomendação e limites da política de crédito;
- contribuições TreeSHAP locais para os casos em revisão manual;
- posição das features do cliente na população de treinamento;
- estatísticas por classe e referências globais de impacto SHAP.

O arquivo [`config/feature_catalog.json`](config/feature_catalog.json) complementa esses dados com a semântica de negócio das features, suas unidades, fórmulas, regras de interpretação e restrições de governança.

Portanto, o agente acelerador de revisão de crédito não realiza uma nova análise estatística. Sua função é combinar duas fontes já preparadas: a resposta explicativa da API e o catálogo de features.

## Preparação das informações para o agente acelerador de revisão de crédito

A disponibilização de informações para o agente acelerador de revisão de crédito começa no treinamento e continua
na API. As funcionalidades já implementadas formam uma cadeia única:

```text
train.py
   │ treina e versiona o modelo
   ├── lightgbm_abt.pkl
   └── feature_reference.json
          │ baseline estatístico e SHAP global
          ▼
PredictionService + CreditPolicy
          │ score e recomendação
          ▼
ExplanationService
          │ SHAP local + comparação com o baseline
          ▼
Resposta técnica da API
          │ futura mensagem de manual_review
          ▼
Agente acelerador de revisão de crédito + feature_catalog.json
          │ interpretação semântica e governança
          ▼
Relatório para o analista
```

### Informações preparadas no treinamento

O `train.py` gera `feature_reference.json` junto com o artefato do modelo. Esse
arquivo registra distribuições das features e do score, referências por classe e
a distribuição global da magnitude SHAP. Versão e instante de treinamento ligam
as referências ao modelo que as produziu.

Esse processamento foi incorporado ao treinamento para que o agente acelerador de revisão de crédito não precise acessar a ABT, inferir baselines ou calcular estatísticas sobre a população.

### Informações preparadas na API

Quando a política indica `manual_review`, o `ExplanationService` calcula o SHAP
local e usa `feature_reference.json` para situar cada fator em relação ao
treinamento. A resposta passa a informar tanto o efeito local no score quanto o
contexto populacional necessário para interpretá-lo.

Essa resposta enriquecida foi implementada como a entrada quantitativa do futuro
agente acelerador de revisão de crédito. Quando a mensageria for adicionada, ela será publicada sem que o agente acelerador de revisão de crédito
tenha de chamar novamente o modelo ou reconstruir a explicação.

### Informação acrescentada pelo catálogo

O `feature_catalog.json` não participa do treinamento nem da predição. Ele será
consultado pelo agente acelerador de revisão de crédito para acrescentar nomes legíveis, descrições, unidades,
semântica dos valores e regras de governança às evidências recebidas da API.

Assim, cada camada acrescenta somente a informação de sua responsabilidade:

| Camada | Informação disponibilizada ao agente acelerador de revisão de crédito |
|---|---|
| `train.py` | Baseline populacional e referência SHAP global versionados. |
| API | Score, política, SHAP local e comparação do cliente com o baseline. |
| Catálogo | Significado de negócio e autorização de uso de cada feature. |
| Agente acelerador de revisão de crédito | Organização narrativa das evidências permitidas. |

## Visão arquitetural

```text
Cliente
   │
   ▼
API de predição
   │
   ├── resposta síncrona ao cliente
   │
   └── se recommendation = manual_review
            │ publica solicitação de relatório
            ▼
        RabbitMQ
            │ entrega assíncrona
            ▼
      Agente acelerador de revisão de crédito ◄──── feature_catalog.json
            │
            ├── consulta o modelo de linguagem
            │
            ▼
   Repositório de relatórios
            │
            ▼
      Analista humano
```

A comunicação entre a API e o agente acelerador de revisão de crédito é assíncrona e ocorre por uma fila mantida por um *message broker*. Para esta proposta, o broker é o RabbitMQ: ele atende ao fluxo de um produtor e um consumidor principal sem exigir uma plataforma de *event streaming*.

## Componentes

### API de predição

A API permanece como autoridade sobre o resultado técnico. Ela:

- recupera ou recebe as features do cliente;
- calcula o score com o modelo carregado;
- aplica a política de crédito;
- calcula a explicação local quando a recomendação é `manual_review`;
- publica no RabbitMQ uma solicitação de relatório com esse resultado técnico.

A publicação não altera o contrato matemático da predição. A API também não consulta o catálogo e não chama o modelo de linguagem.

### RabbitMQ

O RabbitMQ desacopla o tempo de resposta da predição do tempo necessário para gerar o relatório. Sua responsabilidade é receber a mensagem publicada pela API, mantê-la disponível e entregá-la ao agente acelerador de revisão de crédito.

Se o agente acelerador de revisão de crédito estiver temporariamente indisponível, a API continua realizando predições e a solicitação permanece pendente para processamento posterior.

### Agente acelerador de revisão de crédito

O agente acelerador de revisão de crédito é um processo independente da API e consumidor da fila. Ele:

- recebe o resultado técnico completo do caso em revisão;
- cruza os nomes das features com o catálogo;
- aplica as restrições de governança antes da geração textual;
- seleciona e contextualiza as evidências mais relevantes;
- solicita ao modelo de linguagem a composição do relatório;
- valida e persiste o resultado produzido.

O agente acelerador de revisão de crédito interpreta evidências determinísticas, mas não substitui o modelo, a política nem o analista.

### Catálogo de features

O catálogo pertence ao contexto do agente acelerador de revisão de crédito, não ao serviço de predição. Ele traduz os campos técnicos para conceitos de negócio e informa quais features podem ser usadas no relatório.

Features com `allowed_in_report: false` não são enviadas ao modelo de linguagem como justificativas da avaliação. Elas podem continuar disponíveis em fluxos separados de auditoria de *fairness*.

### Modelo de linguagem

O modelo de linguagem recebe somente as evidências autorizadas e já calculadas. Sua função é organizar essas evidências em linguagem clara, sem inferir causalidade e sem produzir uma nova decisão de crédito.

O provedor do modelo é uma dependência externa ao domínio de predição. Sua indisponibilidade afeta a geração do relatório, mas não impede a API de calcular e devolver o score.

### Repositório de relatórios

Os relatórios precisam ser persistidos para consulta, rastreabilidade e eventual reprocessamento. A proposta reutiliza o PostgreSQL já presente na plataforma, evitando introduzir outro mecanismo de armazenamento.

O repositório mantém a associação entre o caso analisado, o resultado técnico que originou o relatório e o conteúdo produzido pelo agente acelerador de revisão de crédito.

### Interface do analista

O analista humano consulta o relatório persistido por uma interface de revisão. Essa interface pode evoluir a partir do frontend existente, mas permanece um consumidor do relatório: não executa o agente acelerador de revisão de crédito nem acessa diretamente o modelo de linguagem.

## Fluxo da revisão humana

1. A API realiza uma predição e aplica a política de crédito.
2. Quando a recomendação é `manual_review`, o `ExplanationService` acrescenta as evidências locais e as referências populacionais.
3. A API publica no RabbitMQ uma solicitação de relatório contendo esse resultado técnico.
4. A resposta da predição é devolvida sem aguardar a geração narrativa.
5. O agente acelerador de revisão de crédito consome a solicitação e consulta o catálogo de features.
6. O agente acelerador de revisão de crédito remove do contexto narrativo as features não autorizadas.
7. O modelo de linguagem transforma as evidências permitidas em um relatório estruturado.
8. O agente acelerador de revisão de crédito valida e persiste o relatório no PostgreSQL.
9. O relatório fica disponível para o analista responsável pela decisão final.

## Separação de responsabilidades

| Componente | Responsabilidade | Limite |
|---|---|---|
| `PredictionService` | Preparar features e calcular score e classe. | Não aplica política nem produz explicação narrativa. |
| `CreditPolicy` | Converter o score em recomendação de negócio. | Não conhece SHAP, catálogo ou modelo de linguagem. |
| `ExplanationService` | Calcular SHAP local e comparações com o treinamento. | Não interpreta semanticamente nem redige relatório. |
| API | Expor o contrato e publicar a solicitação de relatório. | Não aguarda nem executa o agente acelerador de revisão de crédito. |
| RabbitMQ | Transportar a solicitação de forma assíncrona. | Não interpreta nem persiste o relatório final. |
| Agente acelerador de revisão de crédito | Combinar evidências e catálogo e gerar o relatório. | Não recalcula risco nem altera a recomendação. |
| PostgreSQL | Persistir o relatório e sua rastreabilidade. | Não participa da geração textual. |
| Analista humano | Avaliar o caso e tomar a decisão final. | Não precisa interpretar diretamente valores SHAP brutos. |

## Fronteiras de dados e governança

A mensagem enviada ao agente acelerador de revisão de crédito contém somente os dados necessários para produzir o relatório. O resultado quantitativo da API permanece imutável durante todo o fluxo.

Antes da chamada ao modelo de linguagem, o agente acelerador de revisão de crédito usa o catálogo para separar evidências autorizadas de atributos reservados à auditoria. Isso evita depender apenas de uma instrução textual para impedir o uso de features sensíveis.

O relatório deve deixar explícito que:

- o score é uma medida de ordenação de risco, não uma probabilidade calibrada;
- contribuições SHAP explicam o comportamento do modelo naquele caso, não relações causais;
- o conteúdo é apoio à revisão, e não uma decisão autônoma;
- a decisão final permanece sob responsabilidade humana e da política de crédito.

## Comportamento em falhas

O desacoplamento por mensageria mantém a predição independente da geração do relatório:

- indisponibilidade do agente acelerador de revisão de crédito ou do modelo de linguagem não interrompe a API;
- uma solicitação não confirmada pelo agente acelerador de revisão de crédito pode voltar à fila;
- falhas definitivas ficam identificadas para inspeção e reprocessamento;
- o relatório só é considerado concluído depois de validado e persistido.

Essas garantias pertencem ao fluxo de relatório. Elas não modificam o comportamento atual do modelo nem da política.

## Estado da proposta

Já estão implementados os pré-requisitos determinísticos do agente acelerador de revisão de crédito:

- predição e política de crédito;
- explicação TreeSHAP local;
- referências estatísticas geradas no treinamento;
- catálogo semântico e de governança das 42 features.

Permanecem como proposta arquitetural, ainda não implementada:

- inclusão do RabbitMQ na plataforma;
- publicação das solicitações pela API;
- processo consumidor do agente acelerador de revisão de crédito e integração com o modelo de linguagem;
- persistência e consulta dos relatórios de revisão.
