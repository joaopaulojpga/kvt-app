# -*- coding: utf-8 -*-
"""
Criação e edição de turmas.

Separado de reservations.py porque lida com a "oferta" da turma
(vagas, instrutores designados) — não com o ato de reservar em si.
"""
from db import db


class TurmaError(Exception):
    pass


def listar_instrutores():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, nome FROM users WHERE role = 'instrutor' AND ativo = 1 ORDER BY nome"
        ).fetchall()
    return [dict(r) for r in rows]


def criar_turma(data, horario, tipo, instrutor_resp_id, instrutor2_id=None, vagas_base=12, vagas_max=18):
    if not instrutor_resp_id:
        raise TurmaError("Instrutor responsável é obrigatório.")
    if instrutor2_id == instrutor_resp_id:
        instrutor2_id = None
    with db() as conn:
        conn.execute(
            "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, instrutor2_id, "
            "vagas_base, vagas_max, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'agendada')",
            (data, horario, tipo, instrutor_resp_id, instrutor2_id, vagas_base,
             max(vagas_max, vagas_base)),
        )


def atualizar_vagas_turma(class_id, novas_vagas, instrutor2_id=None):
    """
    Edita a quantidade de vagas ofertadas numa turma futura (para mais
    ou para menos). Se `novas_vagas` for maior que 13, exige que um 2º
    instrutor já esteja indicado (a UI só chama esta função depois de
    coletar essa informação do instrutor responsável).
    """
    with db() as conn:
        turma = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if turma is None:
            raise TurmaError("Turma não encontrada.")
        if turma["status"] != "agendada":
            raise TurmaError("Só é possível editar turmas ainda não confirmadas/baixadas.")

        confirmados = conn.execute(
            "SELECT COUNT(*) AS n FROM reservations WHERE class_id = ? "
            "AND status IN ('confirmada','presente','faltou')",
            (class_id,),
        ).fetchone()["n"]
        if novas_vagas < confirmados:
            raise TurmaError(
                f"Não é possível reduzir para {novas_vagas} vagas: já há {confirmados} reservas confirmadas."
            )

        if novas_vagas > 13 and not instrutor2_id and not turma["instrutor2_id"]:
            raise TurmaError("Para mais de 13 vagas, indique também o instrutor extra.")

        vagas_max_final = max(novas_vagas, 18)
        conn.execute(
            "UPDATE classes SET vagas_base = ?, vagas_max = ?, "
            "instrutor2_id = COALESCE(?, instrutor2_id) WHERE id = ?",
            (novas_vagas, vagas_max_final, instrutor2_id, class_id),
        )
