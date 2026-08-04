# -*- coding: utf-8 -*-
"""Relatório mensal de aulas (Configurações > Relatórios)."""
import calendar
from datetime import date
from db import db

MESES_PT = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

STATUS_LABEL = {
    "confirmada": "Confirmada",
    "suspensa_clima": "Suspensa (Clima)",
    "suspensa_quorum": "Suspensa (Quórum)",
    "agendada": "Aguardando baixa",
    "cancelada": "Cancelada",
}


def nome_arquivo_pdf(ano, mes):
    return f"{MESES_PT[mes]}-{str(ano)[-2:]}"


def relatorio_aulas_mes(ano, mes):
    """
    Uma linha por aula+instrutor (uma turma com 2 instrutores gera 2
    linhas, uma para cada repasse) — isso é o que permite a tabela-resumo
    seguinte somar corretamente por instrutor. Aulas suspensas/sem baixa
    aparecem com repasse zero, atribuídas ao instrutor responsável.
    """
    primeiro = date(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ultimo = date(ano, mes, ultimo_dia)

    with db() as conn:
        classes_mes = conn.execute(
            "SELECT c.*, u.nome AS instrutor_nome FROM classes c "
            "JOIN users u ON u.id = c.instrutor_resp_id "
            "WHERE c.data BETWEEN ? AND ? AND c.status != 'cancelada' "
            "ORDER BY c.data, c.horario",
            (primeiro.isoformat(), ultimo.isoformat()),
        ).fetchall()

        linhas = []
        for c in classes_mes:
            ocupadas = conn.execute(
                "SELECT COUNT(*) AS n FROM reservations WHERE class_id = ? "
                "AND status IN ('confirmada','presente','faltou')", (c["id"],)
            ).fetchone()["n"]
            presentes = conn.execute(
                "SELECT COUNT(*) AS n FROM reservations WHERE class_id = ? AND status = 'presente'", (c["id"],)
            ).fetchone()["n"]
            faltosos = conn.execute(
                "SELECT COUNT(*) AS n FROM reservations WHERE class_id = ? AND status = 'faltou'", (c["id"],)
            ).fetchone()["n"]
            payouts_turma = conn.execute(
                "SELECT p.*, u.nome AS instrutor_nome FROM payouts p "
                "JOIN users u ON u.id = p.instrutor_id WHERE p.class_id = ?", (c["id"],)
            ).fetchall()

            base = {
                "data": c["data"], "horario": c["horario"],
                "vagas_ocupadas": ocupadas, "presentes": presentes, "faltosos": faltosos,
                "status": STATUS_LABEL.get(c["status"], c["status"]),
            }
            if payouts_turma:
                for p in payouts_turma:
                    linhas.append({**base, "instrutor": p["instrutor_nome"], "repasse_centavos": p["valor_centavos"]})
            else:
                linhas.append({**base, "instrutor": c["instrutor_nome"], "repasse_centavos": 0})
    return linhas


def resumo_por_instrutor(linhas):
    resumo = {}
    for l in linhas:
        r = resumo.setdefault(l["instrutor"], {"instrutor": l["instrutor"], "alunos": 0, "aulas": 0, "total_centavos": 0})
        r["alunos"] += l["presentes"]
        r["aulas"] += 1
        r["total_centavos"] += l["repasse_centavos"]
    return sorted(resumo.values(), key=lambda r: r["instrutor"])
