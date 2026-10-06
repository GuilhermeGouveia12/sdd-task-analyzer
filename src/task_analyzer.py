"""task_analyzer.py

Módulo de análise de tarefas e produtividade — TaskAnalyzer.

Implementa a função pública `analyze_tasks`, responsável por calcular
métricas de desempenho (tempo médio de conclusão, taxa de atraso e
indicadores por prioridade) a partir de um conjunto de tarefas, em
conformidade com o contrato de negócio definido em
``specs/task_analyzer_spec.md`` (Especificação SDD — TaskAnalyzer,
Fase 1) e as regras de governança descritas em ``CONTEXT_RULES.md``.

Este módulo não realiza nenhuma persistência de dados: opera
inteiramente em memória, recebendo estruturas de dados e retornando
estruturas de dados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Exceções customizadas
# ---------------------------------------------------------------------


class TaskValidationError(Exception):
    """Exceção base para qualquer violação do contrato de negócio do
    TaskAnalyzer.

    Serve como classe-mãe para as exceções específicas
    (:class:`EmptyTaskListError`, :class:`InvalidTaskDataError` e
    :class:`InvalidPriorityError`), permitindo tanto o tratamento
    granular de cada cenário de aceite quanto a captura genérica de
    qualquer erro de validação com ``except TaskValidationError``.
    """


class EmptyTaskListError(TaskValidationError):
    """Disparada quando a lista de tarefas de entrada está vazia.

    Corresponde ao Cenário 3 (Borda — lista de tarefas vazia) da
    especificação SDD.
    """


class InvalidTaskDataError(TaskValidationError):
    """Disparada para dados de tarefa inconsistentes.

    Cobre, entre outros casos, campos obrigatórios ausentes, formatos
    de data inválidos, status fora do conjunto permitido, IDs
    duplicados e ``data_conclusao`` anterior à referência de início da
    tarefa. Corresponde ao Cenário 2 (Exceção/Erro — entradas
    inválidas) da especificação SDD.
    """


class InvalidPriorityError(TaskValidationError):
    """Disparada quando o campo ``prioridade`` de uma tarefa não
    pertence ao conjunto permitido (``baixa``, ``media``, ``alta``).

    Corresponde ao Cenário 5 (Erro — prioridade inválida) da
    especificação SDD. É sempre disparada antes de qualquer cálculo de
    métricas.
    """


# ---------------------------------------------------------------------
# Modelos internos
# ---------------------------------------------------------------------


class Priority(str, Enum):
    """Valores de prioridade permitidos para uma tarefa."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class Status(str, Enum):
    """Valores de status permitidos para uma tarefa."""

    CONCLUIDA = "concluida"
    PENDENTE = "pendente"
    CANCELADA = "cancelada"


@dataclass(frozen=True)
class Task:
    """Representação interna e validada de uma tarefa.

    Attributes:
        id_tarefa: Identificador único da tarefa (> 0, único no conjunto).
        titulo: Nome/descrição curta da tarefa (1 a 200 caracteres).
        prioridade: Prioridade da tarefa (baixa, media ou alta).
        data_criacao: Data/hora de criação da tarefa (UTC).
        prazo: Data/hora limite para conclusão da tarefa (UTC).
        status: Status atual da tarefa (concluida, pendente ou cancelada).
        data_inicio: Data/hora de início da execução (UTC), opcional.
        data_conclusao: Data/hora de conclusão (UTC), opcional —
            presente apenas quando ``status == Status.CONCLUIDA``.
    """

    id_tarefa: int
    titulo: str
    prioridade: Priority
    data_criacao: datetime
    prazo: datetime
    status: Status
    data_inicio: datetime | None = None
    data_conclusao: datetime | None = None


# ---------------------------------------------------------------------
# Parsing e validação de entrada
# ---------------------------------------------------------------------


def _parse_datetime(value: Any, field_name: str, id_tarefa: Any) -> datetime:
    """Converte um valor de entrada em ``datetime``, validando o formato.

    Args:
        value: Valor recebido (``datetime`` ou string ISO 8601).
        field_name: Nome do campo, usado para compor mensagens de erro.
        id_tarefa: Identificador da tarefa, usado para compor mensagens
            de erro.

    Returns:
        Um objeto ``datetime`` correspondente ao valor informado.

    Raises:
        InvalidTaskDataError: Se o valor não puder ser interpretado
            como data.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise InvalidTaskDataError(
                f"Tarefa {id_tarefa}: campo '{field_name}' possui data em "
                f"formato inválido: {value!r}. Utilize datetime ou string "
                "ISO 8601."
            ) from exc
    raise InvalidTaskDataError(
        f"Tarefa {id_tarefa}: campo '{field_name}' deve ser datetime ou "
        f"string ISO 8601, recebido {type(value).__name__}."
    )


def _parse_task(raw: dict[str, Any]) -> Task:
    """Valida e converte um dicionário bruto de entrada em um objeto ``Task``.

    Args:
        raw: Dicionário com os campos da tarefa, conforme o contrato de
            entrada (Seção 1.3.1 da especificação SDD).

    Returns:
        Uma instância validada de ``Task``.

    Raises:
        InvalidTaskDataError: Se algum campo obrigatório estiver
            ausente ou inválido, ou se as datas forem inconsistentes
            entre si.
        InvalidPriorityError: Se ``prioridade`` não pertencer ao
            conjunto permitido (``baixa``, ``media``, ``alta``).
    """
    id_tarefa = raw.get("id_tarefa")
    if not isinstance(id_tarefa, int) or id_tarefa <= 0:
        raise InvalidTaskDataError(
            f"Campo 'id_tarefa' inválido: {id_tarefa!r}. Deve ser um "
            "inteiro maior que zero."
        )

    titulo = raw.get("titulo")
    if not isinstance(titulo, str) or not titulo.strip():
        raise InvalidTaskDataError(
            f"Tarefa {id_tarefa}: campo 'titulo' é obrigatório e não pode "
            "ser vazio."
        )
    titulo = titulo.strip()
    if len(titulo) > 200:
        raise InvalidTaskDataError(
            f"Tarefa {id_tarefa}: campo 'titulo' excede 200 caracteres."
        )

    # Prioridade inválida é verificada antes de qualquer outro cálculo,
    # conforme o Cenário 5 da especificação SDD.
    prioridade_raw = str(raw.get("prioridade", "")).strip().lower()
    try:
        prioridade = Priority(prioridade_raw)
    except ValueError as exc:
        raise InvalidPriorityError(
            f"Tarefa {id_tarefa}: prioridade inválida "
            f"{raw.get('prioridade')!r}. Valores permitidos: "
            f"{[p.value for p in Priority]}."
        ) from exc

    status_raw = str(raw.get("status", "")).strip().lower()
    try:
        status = Status(status_raw)
    except ValueError as exc:
        raise InvalidTaskDataError(
            f"Tarefa {id_tarefa}: status inválido {raw.get('status')!r}. "
            f"Valores permitidos: {[s.value for s in Status]}."
        ) from exc

    if raw.get("data_criacao") is None:
        raise InvalidTaskDataError(
            f"Tarefa {id_tarefa}: campo 'data_criacao' é obrigatório."
        )
    data_criacao = _parse_datetime(raw["data_criacao"], "data_criacao", id_tarefa)

    if raw.get("prazo") is None:
        raise InvalidTaskDataError(f"Tarefa {id_tarefa}: campo 'prazo' é obrigatório.")
    prazo = _parse_datetime(raw["prazo"], "prazo", id_tarefa)

    data_inicio = None
    if raw.get("data_inicio") is not None:
        data_inicio = _parse_datetime(raw["data_inicio"], "data_inicio", id_tarefa)

    data_conclusao = None
    if raw.get("data_conclusao") is not None:
        data_conclusao = _parse_datetime(
            raw["data_conclusao"], "data_conclusao", id_tarefa
        )

    # Regra de negócio (Seção 1.3.3): data_conclusao anterior a
    # data_inicio é inválida. Quando data_inicio está ausente, usa-se
    # data_criacao como referência (mesma regra aplicada ao cálculo do
    # tempo de conclusão).
    referencia_inicio = data_inicio if data_inicio is not None else data_criacao
    referencia_nome = "data_inicio" if data_inicio is not None else "data_criacao"
    if data_conclusao is not None and data_conclusao < referencia_inicio:
        raise InvalidTaskDataError(
            f"Tarefa {id_tarefa}: 'data_conclusao' ({data_conclusao}) é "
            f"anterior a '{referencia_nome}' ({referencia_inicio})."
        )

    return Task(
        id_tarefa=id_tarefa,
        titulo=titulo,
        prioridade=prioridade,
        data_criacao=data_criacao,
        prazo=prazo,
        status=status,
        data_inicio=data_inicio,
        data_conclusao=data_conclusao,
    )


# ---------------------------------------------------------------------
# Cálculo de métricas
# ---------------------------------------------------------------------


def _tempo_conclusao_horas(task: Task) -> float:
    """Calcula o tempo de conclusão de uma tarefa concluída, em horas.

    Usa ``data_inicio`` como referência de início quando disponível;
    caso contrário, usa ``data_criacao`` (Seção 1.3.3).

    Args:
        task: Tarefa concluída (``status == Status.CONCLUIDA``).

    Returns:
        O tempo de conclusão em horas, como ``float``.
    """
    inicio = task.data_inicio or task.data_criacao
    delta = task.data_conclusao - inicio  # type: ignore[operator]
    return delta.total_seconds() / 3600


def _esta_em_atraso(task: Task, agora: datetime) -> bool:
    """Determina se uma tarefa está em atraso.

    Uma tarefa concluída está em atraso se foi concluída após o prazo.
    Uma tarefa pendente está em atraso se o momento de referência já
    passou do prazo. Tarefas canceladas nunca chegam a esta função (são
    filtradas antes, em ``analyze_tasks``).

    Args:
        task: Tarefa a ser avaliada.
        agora: Data/hora de referência para tarefas pendentes.

    Returns:
        ``True`` se a tarefa estiver em atraso, ``False`` caso contrário.
    """
    if task.status is Status.CONCLUIDA:
        return task.data_conclusao is not None and task.data_conclusao > task.prazo
    if task.status is Status.PENDENTE:
        return agora > task.prazo
    return False


def _calcular_bloco_metricas(tasks: list[Task], agora: datetime) -> dict[str, Any]:
    """Calcula quantidade, tempo médio e taxa de atraso para um subconjunto.

    Função auxiliar usada tanto para o bloco geral quanto para cada
    bloco de prioridade (Seção 1.3.2 / 1.3.3). Nunca lança exceção por
    divisão por zero:

    - Quando não há tarefas no subconjunto, ``tempo_medio_conclusao`` e
      ``taxa_atraso_percentual`` retornam ``None`` (ausentes/nulos).
    - Quando há tarefas mas nenhuma concluída, ``tempo_medio_conclusao``
      retorna ``None``, enquanto ``quantidade_tarefas`` e
      ``taxa_atraso_percentual`` continuam calculados normalmente
      (Cenário 4 da especificação SDD).

    Args:
        tasks: Lista de tarefas elegíveis (já sem as canceladas).
        agora: Data/hora de referência para cálculo de atraso.

    Returns:
        Um dicionário com ``quantidade_tarefas``, ``tempo_medio_conclusao``
        e ``taxa_atraso_percentual``.
    """
    quantidade = len(tasks)
    if quantidade == 0:
        return {
            "quantidade_tarefas": 0,
            "tempo_medio_conclusao": None,
            "taxa_atraso_percentual": None,
        }

    concluidas = [t for t in tasks if t.status is Status.CONCLUIDA]
    if concluidas:
        tempo_medio: float | None = round(
            sum(_tempo_conclusao_horas(t) for t in concluidas) / len(concluidas), 2
        )
    else:
        tempo_medio = None

    em_atraso = sum(1 for t in tasks if _esta_em_atraso(t, agora))
    taxa_atraso = round((em_atraso / quantidade) * 100, 2)

    return {
        "quantidade_tarefas": quantidade,
        "tempo_medio_conclusao": tempo_medio,
        "taxa_atraso_percentual": taxa_atraso,
    }


# ---------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------


def analyze_tasks(
    tasks_raw: list[dict[str, Any]], *, agora: datetime | None = None
) -> dict[str, Any]:
    """Analisa um conjunto de tarefas e calcula métricas de produtividade.

    Função pública de entrada do módulo TaskAnalyzer. Valida cada
    tarefa de entrada, calcula o tempo médio de conclusão e a taxa de
    atraso (geral e por prioridade), e retorna um relatório agregado,
    em conformidade com o contrato definido em
    ``specs/task_analyzer_spec.md`` (Seção 1.3.2).

    Args:
        tasks_raw: Lista de dicionários, cada um representando uma
            tarefa conforme o contrato de entrada (``id_tarefa``,
            ``titulo``, ``prioridade``, ``data_criacao``,
            ``data_inicio``, ``data_conclusao``, ``prazo``, ``status``).
        agora: Data/hora de referência usada para avaliar o atraso de
            tarefas pendentes. Quando omitido, usa o instante atual em
            UTC. Exposto principalmente para viabilizar testes
            automatizados determinísticos.

    Returns:
        Um dicionário com as chaves:
            - ``tempo_medio_conclusao_geral`` (float | None)
            - ``taxa_atraso_percentual_geral`` (float | None)
            - ``quantidade_tarefas_total`` (int)
            - ``indicadores_por_prioridade`` (dict[str, dict]) — uma
              chave por prioridade (``baixa``, ``media``, ``alta``),
              cada uma com ``quantidade_tarefas``,
              ``tempo_medio_conclusao`` e ``taxa_atraso_percentual``.

    Raises:
        EmptyTaskListError: Se a lista de entrada estiver vazia
            (Cenário 3).
        InvalidPriorityError: Se alguma tarefa tiver prioridade fora do
            conjunto permitido (Cenário 5).
        InvalidTaskDataError: Se algum campo obrigatório estiver
            ausente, algum enum (status) for inválido, houver IDs
            duplicados, ou as datas forem inconsistentes entre si
            (Cenário 2).
    """
    if not tasks_raw:
        raise EmptyTaskListError(
            "A lista de tarefas de entrada está vazia. Não há dados "
            "suficientes para gerar a análise."
        )

    agora = agora or datetime.now(timezone.utc)

    logger.info("Iniciando análise de %d tarefa(s) recebida(s).", len(tasks_raw))

    tasks = [_parse_task(raw) for raw in tasks_raw]

    ids_vistos: set[int] = set()
    duplicados: set[int] = set()
    for task in tasks:
        if task.id_tarefa in ids_vistos:
            duplicados.add(task.id_tarefa)
        ids_vistos.add(task.id_tarefa)
    if duplicados:
        raise InvalidTaskDataError(
            f"IDs de tarefa duplicados encontrados: {sorted(duplicados)}. "
            "'id_tarefa' deve ser único no conjunto de entrada."
        )

    # Tarefas canceladas são ignoradas em todos os cálculos, mas não
    # geram erro — apenas são excluídas do conjunto elegível.
    elegiveis = [t for t in tasks if t.status is not Status.CANCELADA]

    geral = _calcular_bloco_metricas(elegiveis, agora)

    indicadores_por_prioridade: dict[str, Any] = {}
    for prioridade in Priority:
        tarefas_prioridade = [t for t in elegiveis if t.prioridade is prioridade]
        indicadores_por_prioridade[prioridade.value] = _calcular_bloco_metricas(
            tarefas_prioridade, agora
        )

    resultado = {
        "tempo_medio_conclusao_geral": geral["tempo_medio_conclusao"],
        "taxa_atraso_percentual_geral": geral["taxa_atraso_percentual"],
        "quantidade_tarefas_total": len(elegiveis),
        "indicadores_por_prioridade": indicadores_por_prioridade,
    }

    logger.info(
        "Análise concluída: %d tarefa(s) elegível(eis) de %d recebida(s).",
        resultado["quantidade_tarefas_total"],
        len(tasks_raw),
    )

    return resultado
