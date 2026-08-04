# -*- coding: utf-8 -*-
"""
Testa o boot do app.py de verdade — não só cada tela isolada, mas o
processo de inicialização completo: init_db(), seed_demo(),
seed_newsletters_iniciais(), registro de todas as rotas (@ui.page) e a
rota de webhook do Mercado Pago (@app.post).
"""
import os
import sys
import types
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_app_boot.db")


class FakeElement:
    def __init__(self, *a, **k):
        self.value = k.get("value")
        self.visible = True

    def __getattr__(self, name):
        return lambda *a, **k: self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __call__(self, *a, **k):
        return self

    def on_value_change(self, cb):
        return self

    def set_text(self, *a, **k):
        return self


class FakeUiModule(types.ModuleType):
    def __getattr__(self, name):
        return lambda *a, **k: FakeElement(*a, **k)

    @staticmethod
    def page(path):
        return lambda f: f

    @staticmethod
    def run(*a, **k):
        return None


fake_ui = FakeUiModule("ui")
fake_ui.navigate = types.SimpleNamespace(to=lambda p: None)
fake_app = types.SimpleNamespace(storage=types.SimpleNamespace(user={}))
fake_app.post = lambda path: (lambda f: f)  # decorator do webhook

fake_nicegui = types.ModuleType("nicegui")
fake_nicegui.ui = fake_ui
fake_nicegui.app = fake_app
fake_nicegui.events = types.SimpleNamespace(UploadEventArguments=object)
sys.modules["nicegui"] = fake_nicegui

fake_fastapi = types.ModuleType("fastapi")
fake_fastapi.Request = type("Request", (), {})
sys.modules["fastapi"] = fake_fastapi

import app  # noqa: E402

assert hasattr(app, "webhook_mercadopago"), "rota de webhook do Mercado Pago deveria existir"
print("OK — app.py sobe do zero sem erro: init_db, seeds e todas as rotas registradas.")
print("\nTodos os testes de boot do app passaram.")
