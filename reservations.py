# -*- coding: utf-8 -*-
"""
Reservas, check-in, cancelamento e o fluxo de expansão de vaga.

Regras aplicadas (confirmadas na especificação):
- Até `vagas_base` (12): check-in consome o crédito na hora.
- Acima de `vagas_base` e até `vagas_max` (18): a reserva fica
  'pendente_aprovacao' e o crédito NÃO é consumido até o instrutor
  responsável aprovar a expansão e indicar o 2º instrutor.
- Cancelamento até `horas_limite_cancelamento` (12h) antes do início
  não consome/devolve o crédito.
"""
from datetime import datetime, timedelta, date
import calendar
from db import db, get_param
import credits


class ReservaError(Exception):
    pass


def _contagem_confirmados(conn, class_id):
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM reservations WHERE class_id = ? AND status IN ('confirmada','presente','faltou')",
        (class_id,),
    ).fetchone()
    return row["n"]


def reservar(user_id, class_id, hoje=None):
    """
    Faz a reserva de um aluno numa turma. Retorna um dicionário com
    {'status': 'confirmada'} ou {'status': 'pendente_aprovacao'}.
    """
    with db() as conn:
        turma = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if turma is None:
            raise ReservaError("Turma não encontrada.")
        if turma["status"] in ("cancelada", "suspensa_clima", "suspensa_quorum"):
            raise ReservaError("Esta turma não está disponível para reserva.")

        # Vagas são por turma (editável pelo instrutor) — cai para o padrão global
        # (12/18) só se por algum motivo a turma não tiver esses campos preenchidos.
        vagas_base = turma["vagas_base"] or get_param("vagas_base", 12, int)
        vagas_max = turma["vagas_max"] or get_param("vagas_max", 18, int)

        ja_reservado = conn.execute(
            "SELECT id FROM reservations WHERE class_id = ? AND user_id = ? AND status != 'cancelada'",
            (class_id, user_id),
        ).fetchone()
        if ja_reservado:
            raise ReservaError("Você já tem uma reserva nesta turma.")

        confirmados = _contagem_confirmados(conn, class_id)

        if confirmados < vagas_base:
            # Fluxo normal: consome crédito na hora
            credit_id = credits.consumir_um_credito(user_id, hoje=hoje)
            if credit_id is None:
                raise ReservaError("Sem remadas disponíveis. Compre um pacote para reservar.")
            conn.execute(
                "INSERT INTO reservations (class_id, user_id, credit_id, status, is_vaga_extra) "
                "VALUES (?, ?, ?, 'confirmada', 0)",
                (class_id, user_id, credit_id),
            )
            return {"status": "confirmada"}

        elif confirmados < vagas_max:
            # Vaga extra: fica pendente de aprovação do instrutor responsável.
            # O crédito só é consumido quando a expansão for aprovada.
            conn.execute(
                "INSERT INTO reservations (class_id, user_id, credit_id, status, is_vaga_extra) "
                "VALUES (?, ?, NULL, 'pendente_aprovacao', 1)",
                (class_id, user_id),
            )
            return {"status": "pendente_aprovacao"}

        else:
            raise ReservaError("Turma lotada (limite máximo de vagas atingido).")


def cancelar_reserva(reservation_id, agora=None):
    """
    Cancela a reserva do próprio aluno. Se dentro do prazo (>= horas
    limite antes do início), o crédito não é consumido/é devolvido
    sem extensão de validade (a validade original é mantida).
    """
    agora = agora or datetime.now()
    horas_limite = get_param("horas_limite_cancelamento", 12, int)

    with db() as conn:
        res = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
        if res is None:
            raise ReservaError("Reserva não encontrada.")
        turma = conn.execute("SELECT * FROM classes WHERE id = ?", (res["class_id"],)).fetchone()
        inicio = datetime.fromisoformat(f"{turma['data']} {turma['horario']}")
        if inicio - agora < timedelta(hours=horas_limite):
            raise ReservaError(
                f"Cancelamento não permitido a menos de {horas_limite}h do início da aula."
            )
        conn.execute("UPDATE reservations SET status = 'cancelada' WHERE id = ?", (reservation_id,))
        if res["credit_id"] is not None:
            # devolve o crédito com a validade original (não é suspensão/cancelamento do instrutor)
            credits.devolver_credito(res["credit_id"], motivo_extensao=False)


def listar_participantes(class_id):
    with db() as conn:
        rows = conn.execute(
            "SELECT r.id, r.user_id, r.status, r.is_vaga_extra, u.nome "
            "FROM reservations r JOIN users u ON u.id = r.user_id "
            "WHERE r.class_id = ? AND r.status != 'cancelada' ORDER BY r.criado_em",
            (class_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def proxima_reserva(user_id, hoje=None):
    """Próxima remada confirmada do aluno (para o card de destaque da Home)."""
    hoje = hoje or date.today()
    with db() as conn:
        row = conn.execute(
            "SELECT r.id, c.data, c.horario, c.tipo FROM reservations r "
            "JOIN classes c ON c.id = r.class_id "
            "WHERE r.user_id = ? AND r.status = 'confirmada' AND c.data >= ? "
            "ORDER BY c.data ASC, c.horario ASC LIMIT 1",
            (user_id, hoje.isoformat()),
        ).fetchone()
    return dict(row) if row else None


def contagem_remadas_mes(user_id, ano=None, mes=None):
    """Quantas remadas o aluno realmente compareceu neste mês (indicador de frequência na Home)."""
    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or hoje.month
    primeiro = date(ano, mes, 1)
    ultimo = date(ano, mes, calendar.monthrange(ano, mes)[1])
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM reservations r JOIN classes c ON c.id = r.class_id "
            "WHERE r.user_id = ? AND r.status = 'presente' AND c.data BETWEEN ? AND ?",
            (user_id, primeiro.isoformat(), ultimo.isoformat()),
        ).fetchone()
    return row["n"]
