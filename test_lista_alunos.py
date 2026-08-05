# -*- coding: utf-8 -*-
"""Testa os novos campos da Lista de Alunos (agora em formato de tabela):
e-mail, créditos disponíveis e validade do próximo crédito."""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_lista_alunos.db")

from db import init_db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import credits, students  # noqa: E402

init_db()
HOJE = date(2026, 8, 5)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


aluno_com_credito = cadastrar_usuario(
    "Rafa Tabela", "M", "rafa_tabela@t.com", "1", "tabela1", "21900001111"
)
aluno_sem_credito = cadastrar_usuario(
    "Sem Credito", "F", "semcredito_tabela@t.com", "1", "tabela2", "21900002222"
)

credits.emitir_creditos(aluno_com_credito, "pacote4", None, 3, hoje=HOJE)

relatorio = {r["nome"]: r for r in students.relatorio_alunos()}

approx(relatorio["Rafa Tabela"]["email"], "rafa_tabela@t.com")
approx(relatorio["Rafa Tabela"]["saldo_creditos"], 3, "deveria contar os 3 créditos emitidos")
approx(relatorio["Rafa Tabela"]["proxima_validade"], (HOJE + timedelta(days=30)).isoformat())
approx(relatorio["Rafa Tabela"]["status"], "Ativo")
print("OK — relatorio_alunos traz e-mail, créditos disponíveis e validade corretos pra quem tem crédito.")

approx(relatorio["Sem Credito"]["saldo_creditos"], 0)
approx(relatorio["Sem Credito"]["proxima_validade"], None)
approx(relatorio["Sem Credito"]["status"], "Inativo")
print("OK — aluno sem crédito aparece com saldo 0, validade None e status Inativo.")

print("\nTodos os testes da tabela de Lista de Alunos passaram.")
