# -*- coding: utf-8 -*-
"""Testa a lógica da landing page: captura de prospect (WhatsApp da
newsletter) na tabela prospects, e o conteúdo estático de horários."""
import os
import sys
import tempfile
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_landing.db")

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
import landing_page  # noqa: E402

init_db()


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


# ---- cadastro já aceita CEP/número opcionalmente (pedido no formulário da página de login) ----
uid = cadastrar_usuario(
    "Teste CEP", "F", "teste_cep@t.com", "1", "cepnum1", "21999990000",
    cep="28035-000", endereco_numero="42",
)
with db() as conn:
    row = conn.execute("SELECT cep, endereco_numero FROM users WHERE id = ?", (uid,)).fetchone()
approx(row["cep"], "28035-000")
approx(row["endereco_numero"], "42")
print("OK — cadastrar_usuario salva CEP e número quando informados.")

uid2 = cadastrar_usuario("Teste Sem CEP", "M", "teste_sem_cep@t.com", "1", "cepnum2", "21999990001")
with db() as conn:
    row2 = conn.execute("SELECT cep, endereco_numero FROM users WHERE id = ?", (uid2,)).fetchone()
approx(row2["cep"], None)
approx(row2["endereco_numero"], None)
print("OK — cadastro continua funcionando normalmente sem CEP/número (campos opcionais).")


# ---- captura de prospect: reproduz a lógica de validação + insert de _newsletter() ----
def _capturar(celular_digitado):
    digitos = re.sub(r"\D", "", celular_digitado or "")
    if len(digitos) < 10:
        return False
    with db() as conn:
        conn.execute(
            "INSERT INTO prospects (celular, origem) VALUES (?, 'landing_newsletter')",
            (digitos,),
        )
    return True


assert not _capturar("123"), "número curto demais não deveria ser aceito"
with db() as conn:
    approx(conn.execute("SELECT COUNT(*) AS n FROM prospects").fetchone()["n"], 0)
print("OK — número de WhatsApp inválido (curto demais) não é salvo.")

assert _capturar("(21) 99999-1234")
with db() as conn:
    row = conn.execute("SELECT * FROM prospects").fetchone()
approx(row["celular"], "21999991234", "deveria salvar só os dígitos")
approx(row["origem"], "landing_newsletter")
print("OK — WhatsApp válido é salvo em prospects, só com os dígitos.")

_capturar("21988882222")
with db() as conn:
    approx(conn.execute("SELECT COUNT(*) AS n FROM prospects").fetchone()["n"], 2)
print("OK — múltiplas inscrições acumulam na tabela, sem apagar as anteriores.")

# ---- conteúdo estático: 6 horários, 3 depoimentos, 3 passos ----
approx(len(landing_page.HORARIOS_SEMANA), 6, "grade da landing deveria ter as 6 turmas semanais")
approx(len(landing_page.PASSOS), 3, "como funciona deveria ter 3 passos")
assert len(landing_page.DEPOIMENTOS) <= landing_page.DEPOIMENTOS_MAX_PAGINAS * landing_page.DEPOIMENTOS_POR_PAGINA, \
    "não pode passar do limite de 3 páginas x 3 depoimentos (9 no total)"
print("OK — conteúdo estático (horários/passos/depoimentos) dentro do combinado.")

# ---- APP_URL sempre aponta pro subdomínio do app, nunca pro domínio raiz ----
assert "app." in landing_page.APP_URL or "onrender" in landing_page.APP_URL, \
    f"CTAs da landing deveriam apontar pro app, não pro domínio raiz: {landing_page.APP_URL}"
print(f"OK — CTAs da landing apontam para {landing_page.APP_URL} (subdomínio do app).")

print("\nTodos os testes da landing page passaram.")
