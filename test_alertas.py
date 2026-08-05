# -*- coding: utf-8 -*-
"""Testa os 7 alertas (aluno, instrutor, gestor) descritos no roteiro."""
import os
import sys
import tempfile
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_alertas.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import classes as turmas_mod, reservations, credits, alerts  # noqa: E402

init_db()
HOJE = date(2026, 8, 5)
AGORA = datetime(2026, 8, 5, 12, 0)  # meio-dia


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


# ============ ALUNO ============
aluno = cadastrar_usuario("Duda Alerta", "F", "duda_alerta@t.com", "1", "alerta1", "21900001111")

# sem nada ainda: zero alertas
approx(alerts.alertas_aluno(aluno, AGORA), [])
print("OK — aluno sem créditos vencendo nem remada próxima: zero alertas.")

# crédito vencendo em 3 dias -> alerta
credits.emitir_creditos(aluno, "avulsa", None, 1, hoje=HOJE)
with db() as conn:
    conn.execute(
        "UPDATE credits SET validade = ? WHERE user_id = ?",
        ((HOJE + timedelta(days=3)).isoformat(), aluno),
    )
a = alerts.alertas_aluno(aluno, AGORA)
approx(len(a), 1)
assert "vencendo" in a[0]["mensagem"]
approx(a[0]["rota"], "/creditos")
print("OK — alerta de crédito vencendo em até 7 dias.")

# reserva pra daqui a 6h -> alerta de lembrete de véspera
instrutor = cadastrar_usuario("Zeca Alerta", "M", "zeca_alerta@t.com", "1", "alerta2", "21900002222")
with db() as conn:
    conn.execute("UPDATE users SET role='instrutor' WHERE id=?", (instrutor,))
turmas_mod.criar_turma(HOJE.isoformat(), "18:00", "treino", instrutor_resp_id=instrutor)  # daqui a 6h
with db() as conn:
    turma_id = conn.execute("SELECT id FROM classes WHERE horario='18:00'").fetchone()["id"]
credits.emitir_creditos(aluno, "avulsa", None, 1, hoje=HOJE)
reservations.reservar(aluno, turma_id, hoje=HOJE)

a = alerts.alertas_aluno(aluno, AGORA)
lembrete = [x for x in a if "responsável" not in x["mensagem"] and "18:00" in x["mensagem"]]
assert lembrete, "deveria ter um lembrete pra remada em 6h"
assert "12 horas" in lembrete[0]["mensagem"], f"6h restantes deveria cair na janela de 12h: {lembrete[0]}"
print("OK — lembrete de remada na véspera (janela certa: <=12h).")

# ============ INSTRUTOR ============
# turma como responsável daqui a 1h -> janela de 2h
turmas_mod.criar_turma(HOJE.isoformat(), "13:00", "treino", instrutor_resp_id=instrutor)
ai = alerts.alertas_instrutor(instrutor, AGORA)
lembrete_i = [x for x in ai if "13:00" in x["mensagem"]]
assert lembrete_i, "deveria lembrar da turma das 13:00 (daqui a 1h)"
assert "2 horas" in lembrete_i[0]["mensagem"]
approx(lembrete_i[0]["rota"], "/agenda")
print("OK — instrutor: lembrete de remada como responsável (janela de 2h).")

# turma que já passou há 3h (10:00, agora é 12:00... vamos usar uma turma das 08:00, 4h atrás) -> dar baixa
turmas_mod.criar_turma(HOJE.isoformat(), "08:00", "treino", instrutor_resp_id=instrutor)
ai2 = alerts.alertas_instrutor(instrutor, AGORA)
baixa = [x for x in ai2 if "dar baixa" in x["mensagem"]]
assert baixa, "deveria alertar sobre turma pendente de baixa"
approx(baixa[0]["rota"], "/presenca")
print("OK — instrutor: alerta de turma disponível para dar baixa (2h+ após o início).")

# nova atribuição na escala (agora) -> alerta de nova turma
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', NULL, 'agendada')",
        ((HOJE + timedelta(days=10)).isoformat(), "06:00"),
    )
with db() as conn:
    turma_escala_id = conn.execute(
        "SELECT id FROM classes WHERE data = ?", ((HOJE + timedelta(days=10)).isoformat(),)
    ).fetchone()["id"]
turmas_mod.atribuir_instrutor_escala(turma_escala_id, instrutor)
ai3 = alerts.alertas_instrutor(instrutor, AGORA)
nova = [x for x in ai3 if "escalado" in x["mensagem"]]
assert nova, "deveria alertar sobre a nova atribuição na escala"
approx(nova[0]["rota"], "/configuracoes")
print("OK — instrutor: alerta de nova turma atribuída na escala.")

# ============ GESTOR ============
# a turma de +10 dias já tem instrutor (acabamos de atribuir); cria outra sem instrutor em 5 dias
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', NULL, 'agendada')",
        ((HOJE + timedelta(days=5)).isoformat(), "07:00"),
    )
ag = alerts.alertas_gestor(AGORA)
approx(len(ag), 1)
assert "sem instrutor" in ag[0]["mensagem"]
approx(ag[0]["urgencia"], "danger")
print("OK — gestor: alerta de aula em até 7 dias sem instrutor responsável.")

# turma sem instrutor mas em 20 dias (fora da janela de 7 dias) -> não conta
with db() as conn:
    conn.execute("DELETE FROM classes WHERE instrutor_resp_id IS NULL")
with db() as conn:
    conn.execute(
        "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) VALUES (?, ?, 'treino', NULL, 'agendada')",
        ((HOJE + timedelta(days=20)).isoformat(), "07:00"),
    )
approx(alerts.alertas_gestor(AGORA), [], "turma sem instrutor fora da janela de 7 dias não deveria alertar")
print("OK — gestor: turma sem instrutor fora da janela de 7 dias não gera alerta.")

# ============ dispatcher ============
user_aluno = {"id": aluno, "role": "aluno"}
user_instrutor = {"id": instrutor, "role": "instrutor"}
user_gestor = {"id": 999, "role": "gestor"}
approx(alerts.alertas_para(user_aluno, AGORA), alerts.alertas_aluno(aluno, AGORA))
approx(alerts.alertas_para(user_instrutor, AGORA), alerts.alertas_instrutor(instrutor, AGORA))
approx(alerts.alertas_para(user_gestor, AGORA), alerts.alertas_gestor(AGORA))
print("OK — alertas_para despacha corretamente por perfil.")

print("\nTodos os testes de alertas passaram.")
