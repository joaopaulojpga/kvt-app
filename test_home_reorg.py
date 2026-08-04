# -*- coding: utf-8 -*-
"""Testa proxima_reserva() e contagem_remadas_mes() (usadas na Home reorganizada)."""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_home.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import credits, reservations  # noqa: E402

init_db()
HOJE = date(2026, 8, 4)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


aluno = cadastrar_usuario("Bia", "F", "bia_home@t.com", "1", "home1", "219")
instrutor = cadastrar_usuario("Zeca", "M", "zeca_home@t.com", "1", "home2", "219", role="instrutor")

# sem reserva nenhuma ainda
approx(reservations.proxima_reserva(aluno, hoje=HOJE), None)
approx(reservations.contagem_remadas_mes(aluno, HOJE.year, HOJE.month), 0)
print("OK — sem reservas, próxima remada é None e contagem do mês é zero.")

with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        ((HOJE.replace(day=HOJE.day + 3)).isoformat(), "06:00", instrutor),
    )
    turma_futura = conn.execute("SELECT id FROM classes WHERE horario='06:00'").fetchone()["id"]

credits.emitir_creditos(aluno, "avulsa", None, 2, hoje=HOJE)
reservations.reservar(aluno, turma_futura, hoje=HOJE)

prox = reservations.proxima_reserva(aluno, hoje=HOJE)
assert prox is not None, "deveria haver uma próxima remada agora"
approx(prox["horario"], "06:00")
print("OK — próxima remada aparece corretamente após reservar.")

# marca uma remada PASSADA como presente -> conta na frequência do mês
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', ?, 'agendada')",
        (HOJE.isoformat(), "08:00", instrutor),
    )
    turma_passada = conn.execute("SELECT id FROM classes WHERE horario='08:00'").fetchone()["id"]
reservations.reservar(aluno, turma_passada, hoje=HOJE)
with db() as conn:
    res_id = conn.execute(
        "SELECT id FROM reservations WHERE user_id=? AND class_id=?", (aluno, turma_passada)
    ).fetchone()["id"]
    conn.execute("UPDATE reservations SET status='presente' WHERE id=?", (res_id,))

approx(reservations.contagem_remadas_mes(aluno, HOJE.year, HOJE.month), 1)
print("OK — contagem de remadas do mês soma só as presenças confirmadas.")

print("\nTodos os testes da Home reorganizada passaram.")
