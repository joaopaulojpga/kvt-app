# -*- coding: utf-8 -*-
"""
Teste de regressão para um bug real que passou despercebido: um arquivo
foi renomeado de email.py para mailer.py (porque `email` conflita com a
biblioteca padrão do Python), mas um dos imports não foi atualizado.
Como o Python tem um pacote `email` de verdade na biblioteca padrão,
`import email as email_mod` não dava erro nenhum na hora de importar —
só quebraria (AttributeError) no exato momento em que a função fosse
chamada, dentro de um botão que os testes anteriores não clicavam.

Este teste garante que todo lugar que importa "mailer as email_mod"
realmente pegou o módulo certo (com as funções de verdade), não o
pacote `email` da biblioteca padrão do Python.
"""
import os
import sys
import types
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_imports.db")

if "nicegui" not in sys.modules:
    fake_ui = types.ModuleType("ui")
    fake_ui.__getattr__ = lambda name: (lambda *a, **k: None)  # não cobre tudo, só o suficiente pra importar
    fake_nicegui = types.ModuleType("nicegui")
    fake_nicegui.ui = types.SimpleNamespace(**{
        n: (lambda *a, **k: None) for n in
        ["label", "button", "row", "column", "input", "select", "image", "upload",
         "expansion", "separator", "notify", "dialog", "card", "html", "date",
         "checkbox", "radio", "number", "textarea", "tabs", "tab", "tab_panels",
         "tab_panel", "download", "run_javascript", "icon", "space", "echart"]
    })
    fake_nicegui.app = types.SimpleNamespace(storage=types.SimpleNamespace(user={}))
    fake_nicegui.events = types.SimpleNamespace(UploadEventArguments=object)
    sys.modules["nicegui"] = fake_nicegui

import mailer
import agenda_page
import payments

FUNCOES_ESPERADAS = ["enviar_confirmacao_compra", "enviar_notificacao_expansao"]

for nome_modulo, modulo in [("agenda_page", agenda_page), ("payments", payments)]:
    referencia = getattr(modulo, "email_mod", None)
    assert referencia is not None, f"{nome_modulo} deveria ter um email_mod importado"
    assert referencia is mailer, (
        f"{nome_modulo}.email_mod não é o módulo mailer de verdade — "
        f"provavelmente importou o pacote 'email' da biblioteca padrão por engano"
    )
    for fn in FUNCOES_ESPERADAS:
        assert hasattr(referencia, fn), f"{nome_modulo}.email_mod não tem a função {fn}"

print("OK — agenda_page e payments importam o módulo mailer de verdade (não o pacote 'email' padrão do Python).")
print("\nTodos os testes de sanidade de imports passaram.")
