# -*- coding: utf-8 -*-
"""Testa os 3 itens do Pacote 2: próximas remadas, desfazer reserva, remover aluno."""
import os
import sys
import tempfile
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_pacote2.db")

import types
if "nicegui" not in sys.modules:
    _fake = types.ModuleType("nicegui")
    class _F:
        def __getattr__(self, name):
            def _f(*a, **k): return self
            return _f
        def __call__(self, *a, **k): return self
    _fake.ui = _F()
    _fake.app = _F()
    _fake.events = _F()
    sys.modules["nicegui"] = _fake

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import classes as turmas_mod, reservations, credits  # noqa: E402
from agenda_page import _proximas_turmas, _turmas_do_mes  # noqa: E402

init_db()
HOJE = date(2026, 8, 4)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


instrutor = cadastrar_usuario("Zeca", "M", "zeca_p2@t.com", "1", "p2i1", "219")
instrutor_id = instrutor  # cadastrar_usuario retorna o id
with db() as conn:
    conn.execute("UPDATE users SET role='instrutor' WHERE id=?", (instrutor_id,))

# ---- 1) Próximas remadas: pega a mais próxima + as 5 seguintes, cruzando meses ----
datas = [HOJE, HOJE + timedelta(days=3), HOJE + timedelta(days=10),
         HOJE + timedelta(days=20), HOJE + timedelta(days=35), HOJE + timedelta(days=40),
         HOJE + timedelta(days=50)]  # 7 turmas — a 7ª não deve entrar no limite de 6
for i, d in enumerate(datas):
    turmas_mod.criar_turma(d.isoformat(), f"{6+i:02d}:00", "treino", instrutor_resp_id=instrutor_id)

proximas = _proximas_turmas(HOJE, limite=6)
approx(len(proximas), 6, "deveria trazer só as 6 mais próximas")
approx(proximas[0]["data"], HOJE.isoformat(), "a primeira deveria ser a mais próxima (hoje)")
approx(proximas[-1]["data"], datas[5].isoformat(), "a 6ª deveria ser a 6ª turma mais próxima, cruzando meses")
print("OK — _proximas_turmas traz a mais próxima + as 5 seguintes, mesmo cruzando meses.")

# turma sem instrutor não deve aparecer nem em 'próximas' nem em 'por mês'
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, status) VALUES (?, ?, 'treino', 'agendada')",
        (HOJE.isoformat(), "05:00"),
    )
proximas2 = _proximas_turmas(HOJE, limite=10)
assert all(t["instrutor_nome"] for t in proximas2), "toda turma sem instrutor deveria ficar fora"
mes_atual = _turmas_do_mes(HOJE.year, HOJE.month)
assert all(t["instrutor_nome"] for t in mes_atual), "toda turma sem instrutor deveria ficar fora também na visão por mês"
print("OK — turmas sem instrutor responsável não aparecem em nenhum dos dois modos.")

# ---- 2) Desfazer reserva (>=12h antes libera, <12h bloqueia) ----
turma_alvo_id = None
with db() as conn:
    turma_alvo_id = conn.execute(
        "SELECT id FROM classes WHERE data=? AND horario='06:00'", (HOJE.isoformat(),)
    ).fetchone()["id"]

aluna = cadastrar_usuario("Bia", "F", "bia_p2@t.com", "1", "p2a1", "21900001111")
credits.emitir_creditos(aluna, "avulsa", None, 1, hoje=HOJE)
reservations.reservar(aluna, turma_alvo_id, hoje=HOJE)
approx(credits.saldo_disponivel(aluna), 0, "crédito deveria estar consumido após reservar")

with db() as conn:
    res_id = conn.execute(
        "SELECT id FROM reservations WHERE user_id=? AND class_id=?", (aluna, turma_alvo_id)
    ).fetchone()["id"]

agora_tarde = datetime(HOJE.year, HOJE.month, HOJE.day, 2, 0)  # 4h antes da aula das 06:00
try:
    reservations.cancelar_reserva(res_id, agora=agora_tarde)
    raise AssertionError("deveria ter bloqueado, faltam menos de 12h")
except reservations.ReservaError:
    print("OK — desfazer reserva bloqueado a menos de 12h do início.")

agora_cedo = datetime(HOJE.year, HOJE.month, HOJE.day - 1, 10, 0)  # 20h antes
reservations.cancelar_reserva(res_id, agora=agora_cedo)
approx(credits.saldo_disponivel(aluna), 1, "crédito deveria voltar após desfazer >=12h antes")
print("OK — desfazer reserva com 12h+ de antecedência devolve o crédito sem travar o banco.")

# ---- 3) Instrutor remove aluno da turma (crédito devolvido sem consumir) ----
aluno2 = cadastrar_usuario("Caio", "M", "caio_p2@t.com", "1", "p2a2", "21900002222")
credits.emitir_creditos(aluno2, "avulsa", None, 1, hoje=HOJE)
reservations.reservar(aluno2, turma_alvo_id, hoje=HOJE)
approx(credits.saldo_disponivel(aluno2), 0)

with db() as conn:
    res_id2 = conn.execute(
        "SELECT id FROM reservations WHERE user_id=? AND class_id=?", (aluno2, turma_alvo_id)
    ).fetchone()["id"]

reservations.remover_aluno(res_id2)
approx(credits.saldo_disponivel(aluno2), 1, "crédito deveria voltar quando o instrutor remove o aluno")
participantes = reservations.listar_participantes(turma_alvo_id)
assert not any(p["user_id"] == aluno2 for p in participantes), "aluno removido não deveria mais aparecer na lista"
print("OK — instrutor remove aluno da turma e o crédito volta sem consumir, mesmo fora da janela de 12h.")

try:
    reservations.remover_aluno(res_id2)
    raise AssertionError("deveria ter levantado ReservaError")
except reservations.ReservaError:
    print("OK — remover uma reserva já cancelada é bloqueado.")

print("\nTodos os testes do Pacote 2 passaram.")
