# -*- coding: utf-8 -*-
"""
Criação e edição de turmas.

Separado de reservations.py porque lida com a "oferta" da turma
(vagas, instrutores designados) — não com o ato de reservar em si.
"""
import calendar
from datetime import date
from db import db

# Grade fixa do clube: (dia da semana 0=segunda..6=domingo, horário, tipo)
GRADE_PADRAO = [
    (1, "06:00", "treino"),   # terça
    (3, "06:00", "treino"),   # quinta
    (5, "06:00", "treino"),   # sábado
    (5, "08:00", "treino"),   # sábado
    (6, "07:00", "passeio"),  # domingo
    (6, "09:00", "treino"),   # domingo
]


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


def atualizar_turma(class_id, data, horario, tipo, instrutor_resp_id, instrutor2_id=None):
    """
    Edita data/horário/tipo/instrutor(es) responsável(is) de uma turma
    que ainda não foi confirmada/baixada nem suspensa/cancelada.
    """
    if not instrutor_resp_id:
        raise TurmaError("Instrutor responsável é obrigatório.")
    if instrutor2_id == instrutor_resp_id:
        instrutor2_id = None
    with db() as conn:
        turma = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if turma is None:
            raise TurmaError("Turma não encontrada.")
        if turma["status"] != "agendada":
            raise TurmaError("Só é possível editar turmas ainda não confirmadas/baixadas.")
        conn.execute(
            "UPDATE classes SET data = ?, horario = ?, tipo = ?, instrutor_resp_id = ?, "
            "instrutor2_id = ? WHERE id = ?",
            (data, horario, tipo, instrutor_resp_id, instrutor2_id, class_id),
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


def gerar_grade_padrao(ano, mes):
    """
    Cria as turmas da grade fixa do clube para o mês informado, SEM
    instrutor definido (isso é papel da tela Escala, depois). Pula
    qualquer combinação de data+horário que já exista, então pode ser
    chamada quantas vezes quiser sem duplicar turmas.
    """
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    criadas = 0
    with db() as conn:
        for dia in range(1, ultimo_dia + 1):
            data_atual = date(ano, mes, dia)
            for weekday, horario, tipo in GRADE_PADRAO:
                if data_atual.weekday() != weekday:
                    continue
                existe = conn.execute(
                    "SELECT id FROM classes WHERE data = ? AND horario = ?",
                    (data_atual.isoformat(), horario),
                ).fetchone()
                if existe:
                    continue
                conn.execute(
                    "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, "
                    "vagas_base, vagas_max, status) VALUES (?, ?, ?, NULL, 12, 18, 'agendada')",
                    (data_atual.isoformat(), horario, tipo),
                )
                criadas += 1
    return criadas


def listar_turmas_mes_admin(ano, mes):
    """Todas as turmas do mês (com ou sem instrutor definido) — usado na Escala."""
    primeiro = date(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ultimo = date(ano, mes, ultimo_dia)
    with db() as conn:
        rows = conn.execute(
            "SELECT c.*, u.nome AS instrutor_nome FROM classes c "
            "LEFT JOIN users u ON u.id = c.instrutor_resp_id "
            "WHERE c.data BETWEEN ? AND ? AND c.status != 'cancelada' "
            "ORDER BY c.data, c.horario",
            (primeiro.isoformat(), ultimo.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def atribuir_instrutor_escala(class_id, instrutor_id):
    """
    Define/troca o instrutor responsável pela tela Escala. Só permitido
    enquanto a turma ainda não foi confirmada/suspensa (status='agendada')
    — depois disso, o histórico de repasse já pode ter sido gerado.
    """
    with db() as conn:
        turma = conn.execute("SELECT status FROM classes WHERE id = ?", (class_id,)).fetchone()
        if turma is None:
            raise TurmaError("Turma não encontrada.")
        if turma["status"] != "agendada":
            raise TurmaError("Esta turma já foi baixada/suspensa e não pode mais ser alterada pela Escala.")
        conn.execute("UPDATE classes SET instrutor_resp_id = ? WHERE id = ?", (instrutor_id, class_id))
