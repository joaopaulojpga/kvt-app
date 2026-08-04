# -*- coding: utf-8 -*-
"""Testa os 3 ajustes pedidos após o primeiro deploy."""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_ajustes.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario, atualizar_perfil, get_usuario  # noqa: E402
import classes as turmas_mod  # noqa: E402
from classes import TurmaError  # noqa: E402
import reservations  # noqa: E402

init_db()
HOJE = date(2026, 8, 3)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


def espera_erro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        raise AssertionError("deveria ter levantado TurmaError")
    except TurmaError:
        pass


joao = cadastrar_usuario("João", "M", "joao3@t.com", "123", "aaa", "219999", role="instrutor")
ana = cadastrar_usuario("Ana", "F", "ana3@t.com", "123", "bbb", "219998", role="instrutor")

# ---- 1) Criar turma exige instrutor responsável ----
espera_erro(turmas_mod.criar_turma, HOJE.isoformat(), "06:00", "treino", None)
print("OK — criar turma sem instrutor responsável é bloqueado.")

turmas_mod.criar_turma(HOJE.isoformat(), "06:00", "treino", instrutor_resp_id=joao)
with db() as conn:
    turma = conn.execute("SELECT * FROM classes WHERE data=? AND horario='06:00'", (HOJE.isoformat(),)).fetchone()
approx(turma["instrutor_resp_id"], joao)
approx(turma["vagas_base"], 12, "vagas_base padrão deveria ser 12")
print("OK — turma criada com instrutor responsável obrigatório.")

# ---- 2) Editar vagas de uma turma futura (aumentar e diminuir, mesmo sem estar cheia) ----
turmas_mod.atualizar_vagas_turma(turma["id"], 8)  # diminui, sem ninguém reservado ainda
with db() as conn:
    t2 = conn.execute("SELECT * FROM classes WHERE id=?", (turma["id"],)).fetchone()
approx(t2["vagas_base"], 8)
print("OK — vagas podem ser reduzidas mesmo turma vazia.")

# acima de 13 exige instrutor extra
espera_erro(turmas_mod.atualizar_vagas_turma, turma["id"], 15)
print("OK — acima de 13 vagas exige instrutor extra.")

turmas_mod.atualizar_vagas_turma(turma["id"], 15, instrutor2_id=ana)
with db() as conn:
    t3 = conn.execute("SELECT * FROM classes WHERE id=?", (turma["id"],)).fetchone()
approx(t3["vagas_base"], 15)
approx(t3["instrutor2_id"], ana)
print("OK — vagas ampliadas para 15 com instrutor extra definido.")

# não pode reduzir abaixo do nº de confirmados
for i in range(5):
    uid = cadastrar_usuario(f"Rem{i}", "F", f"rem{i}@t.com", "123", f"cpf{i}", "2199", role="aluno")
    from credits import emitir_creditos
    emitir_creditos(uid, "pacote4", None, 2, hoje=HOJE)
    reservations.reservar(uid, turma["id"], hoje=HOJE)

espera_erro(turmas_mod.atualizar_vagas_turma, turma["id"], 3)  # já tem 5 confirmados
print("OK — não permite reduzir vagas abaixo do nº de reservas já confirmadas.")

# ---- 3) E-mail não pode ser alterado via atualizar_perfil ----
email_original = get_usuario(joao)["email"]
atualizar_perfil(joao, nome="João Souza Jr.", email="outroemail@t.com")
depois = get_usuario(joao)
approx(depois["email"], email_original, "e-mail não deveria mudar mesmo tentando passar email=")
approx(depois["nome"], "João Souza Jr.", "nome deveria ter sido atualizado normalmente")
print("OK — e-mail é protegido contra alteração mesmo se passado por engano.")

print("\nTodos os testes dos ajustes passaram.")

# ---- 4.1: instrutor pode alterar a turma (inclusive o instrutor responsável) ----
turma_edit_id = turma["id"]  # reaproveita a turma já criada acima (15 vagas, instrutor2=ana)
turmas_mod.atualizar_turma(turma_edit_id, HOJE.isoformat(), "07:30", "passeio",
                            instrutor_resp_id=ana, instrutor2_id=None)
with db() as conn:
    t_edit = conn.execute("SELECT * FROM classes WHERE id=?", (turma_edit_id,)).fetchone()
approx(t_edit["instrutor_resp_id"], ana, "instrutor responsável deveria ter mudado para Ana")
approx(t_edit["horario"], "07:30")
approx(t_edit["tipo"], "passeio")
print("OK — instrutor responsável e demais campos da turma podem ser editados via atualizar_turma.")

# editar turma exige instrutor responsável
espera_erro(turmas_mod.atualizar_turma, turma_edit_id, HOJE.isoformat(), "07:30", "passeio", None)
print("OK — editar turma sem instrutor responsável é bloqueado.")

print("\nTodos os testes dos ajustes (rodada 2) passaram.")
