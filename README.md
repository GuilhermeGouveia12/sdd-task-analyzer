# sdd-task-analyzer

Módulo de análise de tarefas e produtividade (**TaskAnalyzer**), desenvolvido seguindo a abordagem de **Spec-Driven Development (SDD)** com geração de código assistida por IA, no âmbito do Bootcamp III.

![status](https://img.shields.io/badge/tests-7%2F7%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.11%2B-blue)

## Sobre o projeto

Este repositório implementa o sistema **TaskAnalyzer**: recebe um conjunto de tarefas e calcula métricas de produtividade — tempo médio de conclusão, taxa de atraso e indicadores por prioridade (baixa, média, alta).

O projeto é a **Fase 2** de uma entrega cumulativa em 3 etapas:

| Fase | Entrega | Status |
|---|---|---|
| 1 | Especificação SDD, cenários de aceite e CONTEXT_RULES (Google Docs) | ✅ Concluída |
| 2 | Este repositório: código via IA, Test Harness (pytest), versionamento Git/GitHub | 🔵 Atual |
| 3 | CI/CD (GitHub Actions), Docker, relatório de governança e homologação final | ⬜ Próxima |

## Estrutura do repositório

```
sdd-task-analyzer/
├── README.md                  # Este arquivo
├── CONTEXT_RULES.md           # Regras de governança de IA
├── requirements.txt           # Dependências autorizadas (pytest)
├── .gitignore
├── specs/
│   └── task_analyzer_spec.md  # Contrato executável (especificação SDD)
├── tests/
│   └── test_harness.py        # Suíte de testes automatizados (pytest)
└── src/
    └── task_analyzer.py       # Código-fonte (analyze_tasks, TaskValidationError)
```

## Como executar

### 1. Criar e ativar um ambiente virtual (opcional, recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Rodar os testes automatizados

```bash
python -m pytest tests/ -v
```

Resultado esperado: **9 passed** (100% de aprovação), cobrindo os 5 cenários de aceite da especificação (sucesso, erro, lista vazia, sem conclusões, prioridade inválida) e testes complementares de robustez.

### 4. Usar o módulo

```python
from src.task_analyzer import analyze_tasks, TaskValidationError

tarefas = [
    {
        "id_tarefa": 1,
        "titulo": "Configurar ambiente",
        "prioridade": "alta",
        "data_criacao": "2026-09-01T08:00:00+00:00",
        "data_inicio": "2026-09-01T08:00:00+00:00",
        "data_conclusao": "2026-09-01T12:00:00+00:00",
        "prazo": "2026-09-02T08:00:00+00:00",
        "status": "concluida",
    },
    # ...
]

resultado = analyze_tasks(tarefas)
print(resultado)
# {
#   "tempo_medio_conclusao_geral": 4.0,
#   "taxa_atraso_percentual_geral": 0.0,
#   "quantidade_tarefas_total": 1,
#   "indicadores_por_prioridade": {"baixa": {...}, "media": {...}, "alta": {...}},
# }
```

### Exceções customizadas

Todas herdam de `TaskValidationError`, permitindo captura granular ou genérica:

| Exceção | Quando é disparada |
|---|---|
| `EmptyTaskListError` | Lista de tarefas de entrada vazia |
| `InvalidTaskDataError` | Datas inconsistentes, campos obrigatórios ausentes, status inválido, IDs duplicados |
| `InvalidPriorityError` | Prioridade fora do conjunto permitido (`baixa`, `media`, `alta`) |

## Governança de IA

Todo o código deste repositório foi gerado com apoio de assistente de IA, estritamente guiado pelo contrato definido em [`specs/task_analyzer_spec.md`](specs/task_analyzer_spec.md) e pelas regras em [`CONTEXT_RULES.md`](CONTEXT_RULES.md), seguido de revisão crítica e homologação humana antes de cada merge.

## Fluxo de contribuição

- Branches de funcionalidade a partir de `main` (ex.: `feature/task-analyzer-impl`).
- Commits atômicos e descritivos (`feat:`, `test:`, `docs:`, ...).
- Pull Requests obrigatórios, com revisão antes do merge em `main`.
