# -*- coding: utf-8 -*-
"""
Fluxo de aprovação de expansão de vaga (acima de 12, até 18).

O instrutor responsável pela turma aprova ou recusa cada solicitação
pendente e, ao aprovar, indica quem é o 2º instrutor. Só neste momento
o crédito do aluno é consumido.
"""
from datetime import date
from db import db
import credits


class ExpansaoError(Exception):
    pass


def listar_pendentes(instrutor_id=None):
    """Lista solicitações de expansão pendentes (opcionalmente filtradas por instrutor responsável)."""
    query = (
        "SELECT r.id AS reservation_id, r.class_id, u.nome AS aluno_nome, "
        "       c.data, c.horario, c.instrutor_resp_id "
        "FROM reservations r "
        "JOIN classes c ON c.id = r.class_id "
        "JOIN users u ON u.id = r.user_id "
        "WHERE r.status = 'pendente_aprovacao'"
    )
    params = ()
    if instrutor_id is not None:
        query += " AND c.instrutor_resp_id = ?"
        params = (instrutor_id,)
    query += " ORDER BY c.data, c.horario"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def aprovar_expansao(reservation_id, instrutor2_id, hoje=None):
    """
    Aprova a vaga extra: consome o crédito do aluno e registra o 2º
    instrutor na turma (se ainda não estava definido).
    """
    with db() as conn:
        res = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
        if res is None or res["status"] != "pendente_aprovacao":
            raise ExpansaoError("Solicitação não encontrada ou já processada.")

        credit_id = credits.consumir_um_credito(res["user_id"], hoje=hoje)
        if credit_id is None:
            raise ExpansaoError("Aluno não tem mais créditos disponíveis para confirmar a vaga.")

        conn.execute(
            "UPDATE reservations SET status = 'confirmada', credit_id = ? WHERE id = ?",
            (credit_id, reservation_id),
        )
        conn.execute(
            "UPDATE classes SET instrutor2_id = COALESCE(instrutor2_id, ?) WHERE id = ?",
            (instrutor2_id, res["class_id"]),
        )


def recusar_expansao(reservation_id):
    with db() as conn:
        res = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
        if res is None or res["status"] != "pendente_aprovacao":
            raise ExpansaoError("Solicitação não encontrada ou já processada.")
        conn.execute("UPDATE reservations SET status = 'cancelada' WHERE id = ?", (reservation_id,))
        # nenhum crédito foi consumido ainda para vaga pendente, então não há o que devolver
