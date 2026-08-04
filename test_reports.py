# -*- coding: utf-8 -*-
"""Testa reports.py: relatório de aulas do mês e resumo por instrutor."""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_reports.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import credits, reservations, attendance, reports  # noqa: E402

init_db()
HOJE = date(2026, 8, 4)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


joao = cadastrar_usuario("João", "M", "joao9@t.com", "1", "r1", "219", role="instrutor")
ana = cadastrar_usuario("Ana", "F", "ana9@t.com", "1", "r2", "219", role="instrutor")

# turma 1: 13 remadores (12 com joao + 1 com ana), confirmada, 1 falta
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        (HOJE.isoformat(), "06:00", joao),
    )
    turma1 = conn.execute("SELECT id FROM classes WHERE horario='06:00'").fetchone()["id"]

alunos = []
for i in range(13):
    uid = cadastrar_usuario(f"Rem{i}", "F", f"rem{i}rep@t.com", "1", f"repcpf{i}", "219")
    credits.emitir_creditos(uid, "avulsa", None, 1, hoje=HOJE)
    reservations.reservar(uid, turma1, hoje=HOJE)
    alunos.append(uid)

with db() as conn:
    pendente = conn.execute(
        "SELECT id FROM reservations WHERE class_id=? AND status='pendente_aprovacao'", (turma1,)
    ).fetchone()
import expansion
expansion.aprovar_expansao(pendente["id"], ana, hoje=HOJE)

with db() as conn:
    confirmadas = conn.execute(
        "SELECT id FROM reservations WHERE class_id=? AND status='confirmada'", (turma1,)
    ).fetchall()
presencas = {r["id"]: "presente" for r in confirmadas}
presencas[confirmadas[0]["id"]] = "faltou"
attendance.dar_baixa(turma1, "confirmada", presencas, hoje=HOJE)

# turma 2: suspensa por clima (sem baixa "confirmada")
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        (HOJE.isoformat(), "08:00", joao),
    )
    turma2 = conn.execute("SELECT id FROM classes WHERE horario='08:00'").fetchone()["id"]
attendance.dar_baixa(turma2, "suspensa_clima", {}, hoje=HOJE)

linhas = reports.relatorio_aulas_mes(HOJE.year, HOJE.month)
approx(len(linhas), 3, "turma1 vira 2 linhas (2 instrutores) + turma2 vira 1 linha = 3")

linhas_turma1 = [l for l in linhas if l["horario"] == "06:00"]
approx(len(linhas_turma1), 2)
joao_linha = next(l for l in linhas_turma1 if l["instrutor"] == "João")
ana_linha = next(l for l in linhas_turma1 if l["instrutor"] == "Ana")
approx(joao_linha["repasse_centavos"], 7500, "instrutor 1 (12 remadores) = R$75")
approx(ana_linha["repasse_centavos"], 3000, "instrutor 2 (1 remador) = 25+5*1 = R$30")
approx(joao_linha["vagas_ocupadas"], 13, "vagas ocupadas é o total da turma, igual nas duas linhas")
approx(joao_linha["status"], "Confirmada")
print("OK — turma com 2 instrutores vira 2 linhas com o repasse correto de cada um.")

linha_turma2 = next(l for l in linhas if l["horario"] == "08:00")
approx(linha_turma2["status"], "Suspensa (Clima)")
approx(linha_turma2["repasse_centavos"], 0, "turma suspensa não gera repasse")
approx(linha_turma2["instrutor"], "João", "sem baixa confirmada, usa o instrutor responsável")
print("OK — turma suspensa aparece no relatório com repasse zero.")

# ---- resumo por instrutor ----
resumo = {r["instrutor"]: r for r in reports.resumo_por_instrutor(linhas)}
approx(resumo["João"]["aulas"], 2, "João aparece nas 2 aulas (06h e a suspensa das 08h)")
approx(resumo["João"]["total_centavos"], 7500, "só a aula confirmada gerou repasse pra ele")
approx(resumo["Ana"]["aulas"], 1)
approx(resumo["Ana"]["total_centavos"], 3000)
approx(resumo["João"]["alunos"], 12, "12 presentes na aula confirmada (13 - 1 falta)")
print("OK — resumo por instrutor soma corretamente aulas, alunos e repasses.")

# ---- nome do arquivo PDF ----
from reports import nome_arquivo_pdf
approx(nome_arquivo_pdf(2026, 8), "agosto-26")
print("OK — nome do arquivo PDF no formato 'mês-ano'.")

print("\nTodos os testes do relatório de aulas passaram.")
