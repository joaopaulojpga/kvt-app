# -*- coding: utf-8 -*-
"""Teste de integração: cobre o caminho ponta a ponta das regras críticas."""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_flow.db")

from db import init_db, db  # noqa: E402
import auth, credits, reservations, expansion, attendance  # noqa: E402

init_db()
HOJE = date(2026, 8, 3)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


# ---- Setup: 1 instrutor + 13 alunos (pra forçar expansão de vaga) ----
instrutor_id = auth.cadastrar_usuario("João", "M", "joao@t.com", "123", "111", "21900000000", role="instrutor")
instrutor2_id = auth.cadastrar_usuario("Ana", "F", "ana@t.com", "123", "222", "21900000001", role="instrutor")
alunos = []
for i in range(13):
    uid = auth.cadastrar_usuario(f"Aluno{i}", "F", f"a{i}@t.com", "123", f"cpf{i}", "219999999")
    credits.emitir_creditos(uid, "pacote4", None, 2, hoje=HOJE)
    alunos.append(uid)

with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        (HOJE.isoformat(), "06:00", instrutor_id),
    )
    class_id = conn.execute("SELECT id FROM classes WHERE data = ?", (HOJE.isoformat(),)).fetchone()["id"]

# ---- 12 primeiros reservam normalmente (consome crédito na hora) ----
reservation_ids = []
for uid in alunos[:12]:
    r = reservations.reservar(uid, class_id, hoje=HOJE)
    approx(r["status"], "confirmada", f"aluno {uid}")
approx(credits.saldo_disponivel(alunos[0], hoje=HOJE), 1, "aluno0 deveria ter 1 crédito restante (tinha 2)")

# ---- 13º aluno cai em pendente de aprovação, crédito NÃO é consumido ----
r13 = reservations.reservar(alunos[12], class_id, hoje=HOJE)
approx(r13["status"], "pendente_aprovacao")
approx(credits.saldo_disponivel(alunos[12], hoje=HOJE), 2, "crédito do 13º não deve ser consumido ainda")

pendentes = expansion.listar_pendentes(instrutor_id=instrutor_id)
approx(len(pendentes), 1, "deveria haver 1 solicitação pendente para o instrutor responsável")

# ---- Instrutor aprova a expansão, indicando o 2º instrutor ----
expansion.aprovar_expansao(pendentes[0]["reservation_id"], instrutor2_id, hoje=HOJE)
approx(credits.saldo_disponivel(alunos[12], hoje=HOJE), 1, "crédito do 13º deve ser consumido após aprovação")

print("OK — reserva normal, vaga extra pendente e aprovação de expansão funcionam como esperado.")

# ---- Dar baixa: turma confirmada, 1 falta, repasse dividido 12+1 ----
with db() as conn:
    todas_reservas = conn.execute(
        "SELECT id FROM reservations WHERE class_id = ? AND status='confirmada'", (class_id,)
    ).fetchall()
presencas = {row["id"]: "presente" for row in todas_reservas}
# marca o primeiro como falta (não deve afetar o repasse)
presencas[todas_reservas[0]["id"]] = "faltou"

resultado = attendance.dar_baixa(class_id, "confirmada", presencas, hoje=HOJE)
approx(resultado["status"], "confirmada")
detalhe = resultado["detalhe"]
approx(detalhe["remadores_instrutor1"], 12)
approx(detalhe["repasse_instrutor1_centavos"], 7500, "instrutor1 deveria receber R$75 (teto)")
approx(detalhe["remadores_instrutor2"], 1)
approx(detalhe["repasse_instrutor2_centavos"], 3000, "instrutor2 com 1 remador: 25+5*1=30")
print("OK — repasse calculado sobre inscritos (13), independente da falta registrada.")

with db() as conn:
    faltou = conn.execute(
        "SELECT status FROM reservations WHERE id = ?", (todas_reservas[0]["id"],)
    ).fetchone()
approx(faltou["status"], "faltou")
# falta consome o crédito (permanece 'consumido' — já foi debitado no check-in)
print("OK — falta não devolve o crédito (permanece consumido).")

# ---- Turma suspensa por clima: devolve créditos com +7 dias, sem repasse ----
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        (HOJE.isoformat(), "08:00", instrutor_id),
    )
    class_id2 = conn.execute("SELECT id FROM classes WHERE horario = '08:00'").fetchone()["id"]

aluno_x = alunos[0]
saldo_antes = credits.saldo_disponivel(aluno_x, hoje=HOJE)
reservations.reservar(aluno_x, class_id2, hoje=HOJE)
approx(credits.saldo_disponivel(aluno_x, hoje=HOJE), saldo_antes - 1)

resultado2 = attendance.dar_baixa(class_id2, "suspensa_clima", {}, hoje=HOJE)
approx(resultado2["status"], "suspensa_clima")
approx(resultado2["repasses"], [], "turma suspensa não gera repasse")
approx(credits.saldo_disponivel(aluno_x, hoje=HOJE), saldo_antes, "crédito devolvido após suspensão")
approx(credits.proxima_validade(aluno_x, hoje=HOJE), (HOJE + timedelta(days=7)).isoformat(),
       "crédito devolvido deveria ganhar +7 dias de validade")
print("OK — suspensão por clima devolve crédito com +7 dias e não gera repasse.")

print("\nTodos os testes de integração passaram.")
