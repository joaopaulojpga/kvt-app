# -*- coding: utf-8 -*-
"""Testa a geração da grade padrão e a atribuição de instrutor pela Escala."""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_escala.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import classes as turmas_mod  # noqa: E402
from classes import TurmaError  # noqa: E402
import attendance  # noqa: E402

init_db()


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


def espera_erro(func, *a, **k):
    try:
        func(*a, **k)
        raise AssertionError("deveria ter levantado TurmaError")
    except TurmaError:
        pass


# agosto/2026: confirma manualmente quantas ocorrências de cada dia existem
# (calendário de agosto/2026: começa numa sábado)
criadas = turmas_mod.gerar_grade_padrao(2026, 8)
assert criadas > 0, "deveria ter criado pelo menos uma turma"
print(f"OK — gerou {criadas} turmas da grade padrão para agosto/2026.")

# idempotência: rodar de novo não duplica
criadas2 = turmas_mod.gerar_grade_padrao(2026, 8)
approx(criadas2, 0, "rodar de novo não deveria criar turmas duplicadas")
print("OK — gerar a grade padrão de novo não duplica turmas.")

# todas nascem sem instrutor
turmas = turmas_mod.listar_turmas_mes_admin(2026, 8)
approx(all(t["instrutor_resp_id"] is None for t in turmas), True, "todas deveriam nascer sem instrutor")
approx(all(t["instrutor_nome"] is None for t in turmas), True)
print("OK — turmas da grade padrão nascem sem instrutor responsável definido.")

# ---- atribuir instrutor via Escala ----
joao = cadastrar_usuario("João", "M", "joaoesc@t.com", "1", "esc1", "219", role="instrutor")
alvo = turmas[0]
turmas_mod.atribuir_instrutor_escala(alvo["id"], joao)
turmas_depois = turmas_mod.listar_turmas_mes_admin(2026, 8)
alvo_depois = next(t for t in turmas_depois if t["id"] == alvo["id"])
approx(alvo_depois["instrutor_resp_id"], joao)
approx(alvo_depois["instrutor_nome"], "João")
print("OK — Escala consegue atribuir um instrutor a uma turma sem instrutor.")

# ---- turma já baixada não pode mais ser alterada pela Escala ----
attendance.dar_baixa(alvo["id"], "suspensa_clima", {}, hoje=date(2026, 8, 1))
espera_erro(turmas_mod.atribuir_instrutor_escala, alvo["id"], joao)
print("OK — Escala bloqueia alteração de turma já baixada/suspensa.")

# ---- criar_turma (lado instrutor) continua exigindo instrutor obrigatório ----
espera_erro(turmas_mod.criar_turma, "2026-08-15", "06:00", "treino", None)
print("OK — criação manual pelo instrutor continua exigindo instrutor responsável.")

print("\nTodos os testes de Escala/grade padrão passaram.")

# ---- turma sem instrutor não aparece na Agenda (alunos/instrutores) ----
import sys, types
if "nicegui" not in sys.modules:
    _fake_st = types.ModuleType("nicegui")
    _fake_st.ui = types.SimpleNamespace(**{k: (lambda *a, **k: None) for k in
        ["label", "button", "row", "column", "expansion", "input", "select", "date_input"]})
    sys.modules["nicegui"] = _fake_st
from agenda_page import _turmas_do_mes

# a turma "alvo" já foi baixada (suspensa) no teste anterior, então cria outra sem instrutor
turmas_sem_instrutor = [t for t in turmas_mod.listar_turmas_mes_admin(2026, 8)
                         if t["instrutor_resp_id"] is None and t["status"] == "agendada"]
assert len(turmas_sem_instrutor) > 0, "deveria sobrar pelo menos uma turma sem instrutor pros próximos testes"

agenda_do_mes = _turmas_do_mes(date(2026, 8, 1))
ids_na_agenda = {t["id"] for t in agenda_do_mes}
for t in turmas_sem_instrutor:
    assert t["id"] not in ids_na_agenda, "turma sem instrutor não deveria aparecer na Agenda"
print("OK — turmas sem instrutor ficam de fora da Agenda até serem atribuídas na Escala.")

print("\nTodos os testes de Escala/grade padrão (rodada 2) passaram.")
