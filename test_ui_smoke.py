# -*- coding: utf-8 -*-
"""
Como este ambiente não tem acesso à internet para instalar o NiceGUI de
verdade, simulamos a biblioteca (elementos encadeáveis, context managers,
app.storage.user) e chamamos render() de cada tela com dados de exemplo.
Não substitui abrir o app de verdade no navegador, mas pega erros de
código (imports errados, nomes de função trocados, exceptions) antes disso.
"""
import os
import sys
import types
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_ui_nicegui.db")


# ---------- Dublê (mock) do NiceGUI ----------
class FakeElement:
    def __init__(self, *args, **kwargs):
        self.value = kwargs.get("value")
        self.visible = True
        self._on_value_change_cb = None

    def __getattr__(self, name):
        # qualquer método encadeável (.classes(), .style(), .props() etc.)
        # devolve o próprio elemento, como no NiceGUI de verdade.
        def _chain(*a, **k):
            return self
        return _chain

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __call__(self, *a, **k):
        return self

    def on_value_change(self, cb):
        self._on_value_change_cb = cb
        return self

    def set_text(self, *_a, **_k):
        return self


class FakeUiModule(types.ModuleType):
    def __getattr__(self, name):
        return lambda *a, **k: FakeElement(*a, **k)

    @staticmethod
    def page(path):
        return lambda f: f

    @staticmethod
    def notify(*a, **k):
        return None

    @staticmethod
    def add_head_html(*a, **k):
        return None

    @staticmethod
    def run(*a, **k):
        return None


fake_ui = FakeUiModule("ui")
fake_app = types.SimpleNamespace(storage=types.SimpleNamespace(user={}))
fake_navigate = types.SimpleNamespace(to=lambda path: None)
fake_ui.navigate = fake_navigate

fake_nicegui = types.ModuleType("nicegui")
fake_nicegui.ui = fake_ui
fake_nicegui.app = fake_app
fake_nicegui.events = types.SimpleNamespace(UploadEventArguments=object)
sys.modules["nicegui"] = fake_nicegui

from db import init_db, db as dbctx  # noqa: E402
from seed import seed_demo  # noqa: E402

init_db()
seed_demo()

with dbctx() as conn:
    instrutor = conn.execute("SELECT id, nome, role FROM users WHERE role='instrutor' LIMIT 1").fetchone()
    gestor = conn.execute("SELECT id, nome, role FROM users WHERE role='gestor' LIMIT 1").fetchone()

user_instrutor = {"id": instrutor["id"], "nome": instrutor["nome"], "role": "instrutor"}
user_gestor = {"id": gestor["id"], "nome": gestor["nome"], "role": "gestor"}

erros = []


def testar(nome_modulo, func_nome, *args):
    try:
        mod = __import__(nome_modulo)
        getattr(mod, func_nome)(*args)
        print(f"OK   {nome_modulo}.{func_nome}(...)")
    except Exception as e:
        erros.append((nome_modulo, e))
        print(f"FALHOU {nome_modulo}.{func_nome}(...) -> {type(e).__name__}: {e}")


testar("home_page", "render")
testar("creditos_page", "render", user_instrutor)
testar("comprar_page", "render", user_instrutor)
testar("agenda_page", "render", user_instrutor)
testar("perfil_page", "render", user_instrutor)
testar("presenca_page", "render", user_instrutor)
testar("dashboard_page", "render", user_gestor)
testar("configuracoes_page", "render", user_gestor)

# layout.shell também precisa funcionar (é usado por toda página autenticada)
try:
    from layout import shell
    with shell("/creditos", user_instrutor):
        pass
    print("OK   layout.shell(...)")
except Exception as e:
    erros.append(("layout", e))
    print(f"FALHOU layout.shell(...) -> {type(e).__name__}: {e}")

print()
if erros:
    print(f"{len(erros)} tela(s)/módulo(s) com erro:")
    for nome, e in erros:
        print(f" - {nome}: {e}")
    sys.exit(1)
else:
    print("Todas as 7 telas + layout carregaram sem erro com os dados de exemplo.")
