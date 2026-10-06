# Especificação SDD — TaskAnalyzer

**Bootcamp III — Desafio de Entrega Inicial (Fase 1) | Spec-Driven Development & AI Harness**

> Transposição fiel da especificação entregue na Fase 1 (Google Docs / PDF) para o repositório, servindo de contrato executável para a geração de código via IA na Fase 2.

## 1. Visão Geral e Contrato de Negócio (SDD)

### 1.1 Identificação

| Campo | Valor |
|---|---|
| Nome completo | Guilherme Gouveia Dalla Mutta |
| Curso | Superior de Tecnologia em Análise e Desenvolvimento de Sistema |
| Turma | Turma A |
| E-mail institucional | guilherme.gouveia@sempreceub.com |
| Data de elaboração | 13/09/2026 |
| Versão da especificação | 1.0 |

### 1.2 Propósito do Módulo TaskAnalyzer

O TaskAnalyzer é um módulo de análise de tarefas e produtividade que recebe um conjunto de tarefas de um time ou indivíduo e calcula métricas objetivas de desempenho de execução. O objetivo de negócio é dar visibilidade quantitativa sobre como as tarefas estão sendo cumpridas, permitindo que gestores e equipes identifiquem gargalos, priorizem melhor o trabalho e monitorem a evolução da produtividade ao longo do tempo.

Escopo funcional desta primeira versão:

- Cálculo do tempo médio de conclusão das tarefas, geral e segmentado por prioridade;
- Cálculo da taxa de atraso das tarefas (percentual de tarefas concluídas ou pendentes após o prazo), geral e por prioridade;
- Geração de indicadores agregados por prioridade (baixa, média, alta), incluindo quantidade de tarefas, tempo médio e taxa de atraso individuais.

Este documento é o contrato executável (fonte da verdade) que orienta a geração de código assistida por IA na Fase 2 e a construção do pipeline de CI/CD, containerização e revisão ética na Fase 3.

### 1.3 Contrato Executável de Interface

#### 1.3.1 Entradas (`tasks_raw: list[dict]`)

| Campo | Tipo | Obrigatório | Descrição / Restrições |
|---|---|---|---|
| `id_tarefa` | int | Sim | Identificador único da tarefa (> 0 e único no conjunto de entrada). |
| `titulo` | str | Sim | Nome/descrição curta (1 a 200 caracteres, não vazio após trim). |
| `prioridade` | enum(str) | Sim | Valores: `"baixa"`, `"media"`, `"alta"` (case-insensitive, normalizado internamente). |
| `data_criacao` | datetime | Sim | Data/hora de criação, UTC, ISO 8601. |
| `data_inicio` | datetime | Não | Data/hora de início da execução, UTC. Ausente = tarefa ainda não iniciada. |
| `data_conclusao` | datetime | Não | Data/hora de conclusão, UTC. Presente apenas se `status = "concluida"`. |
| `prazo` | datetime | Sim | Data/hora limite (deadline), UTC. |
| `status` | enum(str) | Sim | Valores: `"concluida"`, `"pendente"`, `"cancelada"`. |

#### 1.3.2 Saídas (`dict`)

| Campo | Tipo | Descrição |
|---|---|---|
| `tempo_medio_conclusao_geral` | float \| None | Tempo médio de conclusão (horas), apenas tarefas `"concluida"`, 2 casas decimais. `None` quando não há tarefas concluídas. |
| `taxa_atraso_percentual_geral` | float \| None | Percentual (0–100) de tarefas em atraso sobre o total elegível, 2 casas decimais. `None` quando não há tarefas elegíveis. |
| `quantidade_tarefas_total` | int | Quantidade total de tarefas analisadas, excluindo as canceladas. |
| `indicadores_por_prioridade` | dict[str, dict] | Uma chave por prioridade (`"baixa"`, `"media"`, `"alta"`), cada uma com `quantidade_tarefas`, `tempo_medio_conclusao` e `taxa_atraso_percentual`. |

#### 1.3.3 Regras de Negócio e Restrições

- Somente tarefas `"concluida"` entram no cálculo do tempo médio de conclusão.
- Tempo de conclusão = `data_conclusao − data_inicio`, em horas. Se `data_inicio` ausente, usar `data_criacao` como referência.
- Uma tarefa está em atraso quando: (a) concluída e `data_conclusao > prazo`; ou (b) pendente e a data/hora atual `> prazo`.
- Tarefas `"cancelada"` são ignoradas em todos os cálculos, sem gerar erro.
- `indicadores_por_prioridade` sempre contempla as três categorias, mesmo com `quantidade_tarefas = 0` — nesse caso as demais métricas são `None` (ausentes/nulas), nunca erro de divisão por zero.
- Todas as datas em UTC; `data_conclusao` anterior a `data_inicio` é inválida e deve ser rejeitada.
- Percentuais e tempos arredondados a 2 casas decimais.

## 2. Especificação de Cenários de Aceite e Test Harness

### 2.1 Cenários de Aceite (Dado–Quando–Então)

**Cenário 1 — Sucesso (métricas corretas).** Dado um conjunto de tarefas válidas com diferentes prioridades, prazos e status (concluídas e pendentes), quando o analisador for executado, então deve retornar corretamente o tempo médio de conclusão, a taxa de atraso e a quantidade de tarefas, geral e por prioridade.

**Cenário 2 — Exceção/Erro (entradas inválidas).** Dado um conjunto contendo ao menos um registro com data de conclusão anterior à data de início, quando o analisador for executado, então deve disparar `InvalidTaskDataError`, com mensagem clara, sem interromper o processo de forma não controlada.

**Cenário 3 — Borda: lista de tarefas vazia.** Dado que a lista de entrada está vazia, quando o analisador for executado, então deve disparar `EmptyTaskListError`, informando explicitamente a ausência de dados.

**Cenário 4 — Borda: nenhuma tarefa concluída.** Dado um conjunto em que nenhuma tarefa está `"concluida"`, quando o analisador calcular o tempo médio, então deve retornar o indicador correspondente como `None`, sem lançar exceção, mantendo quantidade e taxa de atraso normalmente calculadas.

**Cenário 5 — Erro: prioridade inválida.** Dado uma tarefa cuja `prioridade` não pertence ao conjunto permitido, quando o analisador for executado, então deve disparar `InvalidPriorityError` antes de iniciar qualquer cálculo de métricas.

### 2.2 Planejamento do Test Harness

| Cenário | Função de teste (pytest) | Fixture | Resultado esperado |
|---|---|---|---|
| 1 — Sucesso | `test_analisar_tarefas_retorna_metricas_corretas` | `tarefas_validas_mistas` | Dict de métricas com valores numéricos consistentes |
| 2 — Entradas inválidas | `test_analisar_tarefas_data_invalida_lanca_excecao` | `tarefa_data_invalida` | `pytest.raises(InvalidTaskDataError)` |
| 3 — Lista vazia | `test_analisar_tarefas_lista_vazia_lanca_excecao` | `lista_vazia` | `pytest.raises(EmptyTaskListError)` |
| 4 — Sem conclusões | `test_tempo_medio_sem_tarefas_concluidas_retorna_none` | `tarefas_todas_pendentes` | `tempo_medio_conclusao_geral is None`, sem exceção |
| 5 — Prioridade inválida | `test_prioridade_invalida_lanca_excecao` | `tarefa_prioridade_invalida` | `pytest.raises(InvalidPriorityError)` |

Diretrizes gerais: testes independentes entre si, uso de fixtures, cobertura do caminho feliz e dos casos de erro/borda, cobertura mínima de 90% de `task_analyzer.py`. A execução completa da suíte é pré-condição obrigatória para a homologação do código gerado por IA.

## 3. Exceções Customizadas

- `TaskValidationError` — classe base de todas as exceções de validação do módulo.
- `EmptyTaskListError(TaskValidationError)` — lista de entrada vazia (Cenário 3).
- `InvalidTaskDataError(TaskValidationError)` — dados inconsistentes: datas, campos obrigatórios, status inválido, IDs duplicados (Cenário 2).
- `InvalidPriorityError(TaskValidationError)` — prioridade fora do enum permitido (Cenário 5).
