# -*- coding: utf-8 -*-
"""Testa a seção 'Minhas Próximas Turmas' da Home do instrutor: só turmas
onde é o instrutor RESPONSÁVEL (não conta como extra), no máximo 4, e a
contagem de alunos já reservados por turma."""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_minhas_turmas.db")

import types
if "nicegui" not in sys.modules:
    _fake = types.ModuleType("nicegui")
    class _F:
        def __getattr__(self, name):
            def _f(*a, **k): return self
            return _f
        def __call__(self, *a, **k): return self
    _fake.ui = _F(); _fake.app = _F(); _fake.events = _F()
    sys.modules["nicegui"] = _fake

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import classes as turmas_mod, reservations, credits  # noqa: E402

init_db()
HOJE = date(2026, 8, 5)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


instrutor = cadastrar_usuario("Marcos Reis", "M", "marcos_home@t.com", "1", "home1", "21900001111")
outro_instrutor = cadastrar_usuario("Ana Lima", "F", "ana_home@t.com", "1", "home2", "21900002222")
with db() as conn:
    conn.execute("UPDATE users SET role='instrutor' WHERE id IN (?, ?)", (instrutor, outro_instrutor))

# 6 turmas onde é o responsável (só as 4 mais próximas devem aparecer)
for i in range(6):
    turmas_mod.criar_turma(
        (HOJE + timedelta(days=i + 1)).isoformat(), "06:00", "treino", instrutor_resp_id=instrutor
    )
# 1 turma como instrutor EXTRA (não deve contar como "responsável")
turmas_mod.criar_turma(HOJE.isoformat(), "18:00", "treino", instrutor_resp_id=outro_instrutor)
with db() as conn:
    extra_id = conn.execute(
        "SELECT id FROM classes WHERE instrutor_resp_id=? AND horario='18:00'", (outro_instrutor,)
    ).fetchone()["id"]
    conn.execute("UPDATE classes SET instrutor2_id=? WHERE id=?", (instrutor, extra_id))
# 1 turma passada como responsável (não deve aparecer)
turmas_mod.criar_turma((HOJE - timedelta(days=1)).isoformat(), "06:00", "treino", instrutor_resp_id=instrutor)

# reserva 2 alunos numa das turmas futuras, pra testar a contagem
with db() as conn:
    primeira_turma_id = conn.execute(
        "SELECT id FROM classes WHERE instrutor_resp_id=? AND data=? ", (instrutor, (HOJE + timedelta(days=1)).isoformat())
    ).fetchone()["id"]
for i in range(2):
    aluno = cadastrar_usuario(f"Aluno{i}", "F", f"aluno_home{i}@t.com", "1", f"home_al{i}", "21900003333")
    credits.emitir_creditos(aluno, "avulsa", None, 1, hoje=HOJE)
    reservations.reservar(aluno, primeira_turma_id, hoje=HOJE)

# reproduz a query usada em creditos_page._minhas_proximas_turmas
with db() as conn:
    rows = conn.execute(
        "SELECT c.*, "
        "  (SELECT COUNT(*) FROM reservations r WHERE r.class_id = c.id "
        "     AND r.status IN ('confirmada','presente','faltou')) AS confirmados "
        "FROM classes c "
        "WHERE c.instrutor_resp_id = ? AND c.data >= ? AND c.status = 'agendada' "
        "ORDER BY c.data, c.horario LIMIT 4",
        (instrutor, HOJE.isoformat()),
    ).fetchall()

approx(len(rows), 4, "deveria trazer no máximo 4 turmas")
approx(str(rows[0]["data"]), (HOJE + timedelta(days=1)).isoformat(), "a primeira deveria ser a mais próxima")
approx(rows[0]["confirmados"], 2, "deveria contar os 2 alunos reservados")
assert all(r["data"] != HOJE.isoformat() or r["horario"] != "18:00" for r in rows), \
    "turma onde é só instrutor EXTRA não deveria aparecer aqui"
assert all(date.fromisoformat(str(r["data"])) >= HOJE for r in rows), "turma passada não deveria aparecer"
print("OK — Minhas Próximas Turmas: até 4 turmas, só como responsável, com a contagem de reservas correta.")

print("\nTodos os testes de Minhas Próximas Turmas passaram.")
