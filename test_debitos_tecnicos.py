# -*- coding: utf-8 -*-
"""Testa a migração de coluna nova e as regras de gestão/relatório de alunos."""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_debitos.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario, atualizar_perfil, get_usuario  # noqa: E402
import students  # noqa: E402
import credits  # noqa: E402
import reservations  # noqa: E402

init_db()
# roda a migração DUAS vezes de propósito — simula um redeploy num banco
# que já tem a coluna, pra garantir que não quebra (idempotência)
init_db()
HOJE = date(2026, 8, 4)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


# ---- Migração: coluna nova existe e aceita valor ----
aluno1 = cadastrar_usuario("Beatriz Alves", "F", "bea@t.com", "123", "d1", "21988887777")
atualizar_perfil(aluno1, data_nascimento="1995-04-12")
dados = get_usuario(aluno1)
approx(dados["data_nascimento"], "1995-04-12")
print("OK — coluna data_nascimento migrada e editável.")

# ---- Promoção a instrutor ----
aluno2 = cadastrar_usuario("Carlos Dias", "M", "carlos@t.com", "123", "d2", "21977776666")
approx(get_usuario(aluno2)["role"], "aluno")
students.promover_para_instrutor(aluno2)
approx(get_usuario(aluno2)["role"], "instrutor")
print("OK — promoção de aluno a instrutor funciona.")

# ---- Relatório de alunos: status ativo/inativo por crédito, aulas presentes, última aula ----
aluno3 = cadastrar_usuario("Diana Reis", "F", "diana@t.com", "123", "d3", "21966665555")
instrutor = cadastrar_usuario("Zeca", "M", "zeca@t.com", "123", "d4", "21955554444", role="instrutor")

with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        (HOJE.isoformat(), "06:00", instrutor),
    )
    turma_id = conn.execute("SELECT id FROM classes WHERE data=?", (HOJE.isoformat(),)).fetchone()["id"]

# sem crédito e sem presença ainda -> inativo, 0 aulas
relatorio = {r["nome"]: r for r in students.relatorio_alunos()}
approx(relatorio["Diana Reis"]["status"], "Inativo")
approx(relatorio["Diana Reis"]["aulas_reservadas"], 0)
approx(relatorio["Diana Reis"]["ultima_aula"], None)

# compra crédito, reserva e é marcada como presente
credits.emitir_creditos(aluno3, "avulsa", None, 1, hoje=HOJE)
reservations.reservar(aluno3, turma_id, hoje=HOJE)
with db() as conn:
    res_id = conn.execute(
        "SELECT id FROM reservations WHERE user_id=? AND class_id=?", (aluno3, turma_id)
    ).fetchone()["id"]
    conn.execute("UPDATE reservations SET status='presente' WHERE id=?", (res_id,))

relatorio = {r["nome"]: r for r in students.relatorio_alunos()}
approx(relatorio["Diana Reis"]["aulas_reservadas"], 1)
approx(relatorio["Diana Reis"]["ultima_aula"], HOJE.isoformat())
# crédito já foi consumido no check-in -> saldo zerado -> Inativo de novo
approx(relatorio["Diana Reis"]["status"], "Inativo")
print("OK — relatório de alunos calcula status, aulas presentes e última aula corretamente.")

print("\nTodos os testes dos débitos técnicos passaram.")
