"""test_harness.py

Suíte de testes automatizados (pytest) para o módulo TaskAnalyzer.

Traduz diretamente os cenários de aceite definidos na especificação
SDD da Fase 1 (specs/task_analyzer_spec.md, Seção 2), seguindo o
mapeamento cenário → teste → fixture → resultado esperado da Seção
2.2 (Planejamento do Test Harness).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Garante que `src/` esteja no path, independentemente de onde o
# pytest for executado a partir da raiz do repositório.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from task_analyzer import (  # noqa: E402
    EmptyTaskListError,
    InvalidPriorityError,
    InvalidTaskDataError,
    analyze_tasks,
)

UTC = timezone.utc
AGORA_REF = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def tarefas_validas_mistas() -> list[dict]:
    """Cenário 1: conjunto de tarefas válidas, com diferentes
    prioridades, prazos e status (concluídas e pendentes)."""
    return [
        {
            "id_tarefa": 1,
            "titulo": "Configurar ambiente",
            "prioridade": "alta",
            "data_criacao": datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            "data_inicio": datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            "data_conclusao": datetime(2026, 9, 1, 12, 0, tzinfo=UTC),  # 4h
            "prazo": datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            "status": "concluida",
        },
        {
            "id_tarefa": 2,
            "titulo": "Escrever especificação SDD",
            "prioridade": "alta",
            "data_criacao": datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            "data_inicio": datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            "data_conclusao": datetime(2026, 9, 3, 8, 0, tzinfo=UTC),  # 24h, atrasada
            "prazo": datetime(2026, 9, 2, 20, 0, tzinfo=UTC),
            "status": "concluida",
        },
        {
            "id_tarefa": 3,
            "titulo": "Revisar documentação",
            "prioridade": "media",
            "data_criacao": datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": datetime(2026, 10, 10, 9, 0, tzinfo=UTC),  # ainda no prazo
            "status": "pendente",
        },
        {
            "id_tarefa": 4,
            "titulo": "Planejar sprint",
            "prioridade": "baixa",
            "data_criacao": datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": datetime(2026, 9, 20, 9, 0, tzinfo=UTC),  # já vencido
            "status": "pendente",
        },
        {
            "id_tarefa": 5,
            "titulo": "Ideia descartada",
            "prioridade": "baixa",
            "data_criacao": datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            "status": "cancelada",
        },
    ]


@pytest.fixture
def tarefa_data_invalida() -> list[dict]:
    """Cenário 2: tarefa com data_conclusao anterior à data_inicio."""
    return [
        {
            "id_tarefa": 10,
            "titulo": "Tarefa com datas inconsistentes",
            "prioridade": "media",
            "data_criacao": datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
            "data_inicio": datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            "data_conclusao": datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
            "prazo": datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
            "status": "concluida",
        }
    ]


@pytest.fixture
def lista_vazia() -> list[dict]:
    """Cenário 3 (Borda): nenhuma tarefa informada."""
    return []


@pytest.fixture
def tarefas_todas_pendentes() -> list[dict]:
    """Cenário 4 (Borda): nenhuma tarefa concluída (todas pendentes)."""
    return [
        {
            "id_tarefa": 20,
            "titulo": "Tarefa pendente 1",
            "prioridade": "alta",
            "data_criacao": datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": datetime(2026, 12, 1, 9, 0, tzinfo=UTC),
            "status": "pendente",
        },
        {
            "id_tarefa": 21,
            "titulo": "Tarefa pendente 2",
            "prioridade": "baixa",
            "data_criacao": datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": datetime(2026, 12, 2, 9, 0, tzinfo=UTC),
            "status": "pendente",
        },
    ]


@pytest.fixture
def tarefa_prioridade_invalida() -> list[dict]:
    """Cenário 5: tarefa com valor de prioridade fora do enum permitido."""
    return [
        {
            "id_tarefa": 30,
            "titulo": "Prioridade inválida",
            "prioridade": "urgentissima",
            "data_criacao": datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            "status": "pendente",
        }
    ]


# ---------------------------------------------------------------------
# Cenário 1 — Sucesso (métricas corretas)
# ---------------------------------------------------------------------


def test_analisar_tarefas_retorna_metricas_corretas(tarefas_validas_mistas):
    """O sistema deve retornar corretamente tempo médio, taxa de atraso
    e quantidade de tarefas, geral e por prioridade."""
    resultado = analyze_tasks(tarefas_validas_mistas, agora=AGORA_REF)

    # A tarefa cancelada (id 5) é ignorada: restam 4 tarefas elegíveis.
    assert resultado["quantidade_tarefas_total"] == 4

    # Tempo médio de conclusão geral: (4h + 24h) / 2 = 14h
    assert resultado["tempo_medio_conclusao_geral"] == pytest.approx(14.0)

    # Em atraso: tarefa 2 (concluída após o prazo) e tarefa 4
    # (pendente e vencida) => 2 de 4 = 50%
    assert resultado["taxa_atraso_percentual_geral"] == pytest.approx(50.0)

    indicadores = resultado["indicadores_por_prioridade"]
    assert set(indicadores.keys()) == {"baixa", "media", "alta"}

    # Prioridade alta: 2 tarefas concluídas, tempo médio (4h + 24h) / 2 = 14h,
    # 1 em atraso de 2 = 50%
    assert indicadores["alta"]["quantidade_tarefas"] == 2
    assert indicadores["alta"]["tempo_medio_conclusao"] == pytest.approx(14.0)
    assert indicadores["alta"]["taxa_atraso_percentual"] == pytest.approx(50.0)

    # Prioridade média: 1 tarefa pendente, dentro do prazo, nenhuma concluída
    assert indicadores["media"]["quantidade_tarefas"] == 1
    assert indicadores["media"]["tempo_medio_conclusao"] is None
    assert indicadores["media"]["taxa_atraso_percentual"] == pytest.approx(0.0)

    # Prioridade baixa: 1 tarefa pendente (a cancelada não entra), vencida
    assert indicadores["baixa"]["quantidade_tarefas"] == 1
    assert indicadores["baixa"]["tempo_medio_conclusao"] is None
    assert indicadores["baixa"]["taxa_atraso_percentual"] == pytest.approx(100.0)


# ---------------------------------------------------------------------
# Cenário 2 — Exceção / Erro (entradas inválidas)
# ---------------------------------------------------------------------


def test_analisar_tarefas_data_invalida_lanca_excecao(tarefa_data_invalida):
    """Datas inconsistentes (conclusão antes do início) devem disparar
    InvalidTaskDataError com mensagem clara."""
    with pytest.raises(InvalidTaskDataError, match="anterior a 'data_inicio'"):
        analyze_tasks(tarefa_data_invalida, agora=AGORA_REF)


# ---------------------------------------------------------------------
# Cenário 3 — Borda: lista de tarefas vazia
# ---------------------------------------------------------------------


def test_analisar_tarefas_lista_vazia_lanca_excecao(lista_vazia):
    """Lista de entrada vazia deve disparar EmptyTaskListError de forma
    controlada, informando explicitamente a ausência de dados."""
    with pytest.raises(EmptyTaskListError, match="vazia"):
        analyze_tasks(lista_vazia, agora=AGORA_REF)


# ---------------------------------------------------------------------
# Cenário 4 — Borda: nenhuma tarefa concluída
# ---------------------------------------------------------------------


def test_tempo_medio_sem_tarefas_concluidas_retorna_none(tarefas_todas_pendentes):
    """Quando nenhuma tarefa está concluída, tempo_medio_conclusao_geral
    deve ser None, sem lançar exceção — mantendo quantidade e taxa de
    atraso normalmente calculadas."""
    resultado = analyze_tasks(tarefas_todas_pendentes, agora=AGORA_REF)

    assert resultado["tempo_medio_conclusao_geral"] is None
    assert resultado["quantidade_tarefas_total"] == 2
    # Nenhuma tarefa está vencida em relação a AGORA_REF.
    assert resultado["taxa_atraso_percentual_geral"] == pytest.approx(0.0)


def test_indicadores_por_prioridade_sem_tarefas_retorna_none(tarefas_todas_pendentes):
    """indicadores_por_prioridade deve sempre conter as três categorias;
    uma prioridade sem nenhuma tarefa retorna métricas ausentes/nulas."""
    resultado = analyze_tasks(tarefas_todas_pendentes, agora=AGORA_REF)
    indicadores = resultado["indicadores_por_prioridade"]

    assert set(indicadores.keys()) == {"baixa", "media", "alta"}
    # Nenhuma tarefa de prioridade "media" nesta fixture.
    assert indicadores["media"]["quantidade_tarefas"] == 0
    assert indicadores["media"]["tempo_medio_conclusao"] is None
    assert indicadores["media"]["taxa_atraso_percentual"] is None


# ---------------------------------------------------------------------
# Cenário 5 — Erro: prioridade inválida
# ---------------------------------------------------------------------


def test_prioridade_invalida_lanca_excecao(tarefa_prioridade_invalida):
    """Prioridade fora do conjunto permitido deve disparar
    InvalidPriorityError antes de qualquer cálculo de métricas."""
    with pytest.raises(InvalidPriorityError, match="prioridade inválida"):
        analyze_tasks(tarefa_prioridade_invalida, agora=AGORA_REF)


# ---------------------------------------------------------------------
# Testes complementares (robustez adicional do contrato)
# ---------------------------------------------------------------------


def test_tarefa_concluida_sem_data_inicio_usa_data_criacao():
    """Quando data_inicio está ausente, o tempo de conclusão deve ser
    calculado a partir de data_criacao (Seção 1.3.3)."""
    tarefas = [
        {
            "id_tarefa": 40,
            "titulo": "Sem data de início",
            "prioridade": "media",
            "data_criacao": datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            "data_inicio": None,
            "data_conclusao": datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            "prazo": datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
            "status": "concluida",
        }
    ]
    resultado = analyze_tasks(tarefas, agora=AGORA_REF)
    assert resultado["tempo_medio_conclusao_geral"] == pytest.approx(2.0)


def test_id_tarefa_duplicado_lanca_excecao():
    """id_tarefa deve ser único no conjunto de entrada (Seção 1.3.1)."""
    tarefas = [
        {
            "id_tarefa": 50,
            "titulo": "Primeira",
            "prioridade": "baixa",
            "data_criacao": datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            "prazo": datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
            "status": "pendente",
        },
        {
            "id_tarefa": 50,
            "titulo": "Duplicada",
            "prioridade": "alta",
            "data_criacao": datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            "prazo": datetime(2026, 9, 6, 8, 0, tzinfo=UTC),
            "status": "pendente",
        },
    ]
    with pytest.raises(InvalidTaskDataError, match="duplicados"):
        analyze_tasks(tarefas, agora=AGORA_REF)


def test_cancelada_nao_entra_em_nenhum_calculo():
    """Tarefas canceladas são ignoradas em todos os cálculos, mas não
    geram erro (Seção 1.3.3)."""
    tarefas = [
        {
            "id_tarefa": 60,
            "titulo": "Única tarefa, cancelada",
            "prioridade": "alta",
            "data_criacao": datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            "prazo": datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
            "status": "cancelada",
        }
    ]
    resultado = analyze_tasks(tarefas, agora=AGORA_REF)
    assert resultado["quantidade_tarefas_total"] == 0
    assert resultado["tempo_medio_conclusao_geral"] is None
    assert resultado["taxa_atraso_percentual_geral"] is None
