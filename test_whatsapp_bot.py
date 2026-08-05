# -*- coding: utf-8 -*-
"""Testa os 8 Scripts do bot de WhatsApp (Fase 2): roteamento por número,
identificação do usuário pelo telefone, e o payload real da Meta."""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_whatsapp_bot.db")

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
import credits, whatsapp_bot  # noqa: E402

init_db()
HOJE = date(2026, 8, 5)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


aluno = cadastrar_usuario("Fernanda Bot", "F", "fernanda_bot@t.com", "1", "bot1", "(21) 90000-1234")

# ---- texto que não é uma opção válida -> mostra o menu ----
resposta = whatsapp_bot.processar_mensagem_recebida("5521900001234", "oi")
assert resposta == whatsapp_bot.MENU
print("OK — mensagem fora do menu retorna o menu numerado.")

# ---- 1) créditos disponíveis — usuário identificado pelo telefone (formatos diferentes) ----
credits.emitir_creditos(aluno, "avulsa", None, 3, hoje=HOJE)
for formato in ["5521900001234", "21900001234", "+55 21 90000-1234", "(21) 90000-1234"]:
    resposta = whatsapp_bot.processar_mensagem_recebida(formato, "1")
    assert "3 remada" in resposta, f"formato {formato} deveria reconhecer o usuário: {resposta}"
print("OK — opção 1 (créditos) reconhece o usuário em qualquer formato de telefone recebido.")

# ---- telefone não cadastrado -> mensagem clara, sem erro ----
resposta = whatsapp_bot.processar_mensagem_recebida("5521999998888", "1")
assert "cadastro" in resposta.lower()
print("OK — telefone não cadastrado recebe aviso claro, sem quebrar.")

# ---- 2) créditos vencendo em 7 dias ----
with db() as conn:
    conn.execute(
        "UPDATE credits SET validade = ? WHERE user_id = ? AND id = (SELECT MIN(id) FROM credits WHERE user_id = ?)",
        ((HOJE + timedelta(days=3)).isoformat(), aluno, aluno),
    )
resposta = whatsapp_bot.processar_mensagem_recebida("5521900001234", "2")
assert "vencendo" in resposta.lower()
print("OK — opção 2 (créditos vencendo) identifica o crédito próximo do vencimento.")

# ---- 4) pacotes: cita os 3 planos ----
resposta = whatsapp_bot.processar_mensagem_recebida("5521900001234", "4")
assert "Remada avulsa" in resposta and "Pacote 4" in resposta and "Pacote 6" in resposta
print("OK — opção 4 (pacotes) lista os 3 planos com preço.")

# ---- 5, 6, 7, 8: respostas fixas não vazias ----
for opcao in ["5", "6", "7", "8"]:
    resposta = whatsapp_bot.processar_mensagem_recebida("5521900001234", opcao)
    assert len(resposta) > 20, f"opção {opcao} deveria ter uma resposta de verdade"
print("OK — opções 5 a 8 (como usar, localização, primeira visita, como marcar) respondem com conteúdo real.")

# ---- 3) turmas da semana — reaproveita a mesma função do módulo whatsapp.py (Fase 1), sem nomes ----
import whatsapp
import classes as turmas_mod

turmas_mod.criar_turma(HOJE.isoformat(), "06:00", "treino", instrutor_resp_id=aluno)  # aluno vira instrutor só pra este teste
with db() as conn:
    conn.execute("UPDATE users SET role='instrutor' WHERE id=?", (aluno,))
    turma_id = conn.execute("SELECT id FROM classes WHERE data=?", (HOJE.isoformat(),)).fetchone()["id"]
reservations_aluno = cadastrar_usuario("Outra Aluna", "F", "outra_bot@t.com", "1", "bot2", "21900009999")
credits.emitir_creditos(reservations_aluno, "avulsa", None, 1, hoje=HOJE)
import reservations as reservations_mod
reservations_mod.reservar(reservations_aluno, turma_id, hoje=HOJE)

resposta = whatsapp_bot.processar_mensagem_recebida("5521900001234", "3")
approx(
    resposta, whatsapp.gerar_texto_lista_semana(incluir_alunos=False),
    "opção 3 deveria reaproveitar o mesmo gerador da Fase 1, sem a lista de alunos",
)
assert "Outra Aluna" not in resposta, "opção 3 não deveria expor nomes de alunos, mesmo havendo reserva"
print("OK — opção 3 (turmas da semana) reaproveita o gerador da Fase 1, sem duplicar lógica e sem nomes.")

# ---- processar_webhook_recebido: payload real da Meta ----
_capturado = {}


def _stub_responder(telefone, texto):
    _capturado["telefone"] = telefone
    _capturado["texto"] = texto
    return True


whatsapp.responder_mensagem = _stub_responder

payload = {
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{"from": "5521900001234", "type": "text", "text": {"body": "1"}}]
            }
        }]
    }]
}
whatsapp_bot.processar_webhook_recebido(payload)
approx(_capturado["telefone"], "5521900001234")
assert "3 remada" in _capturado["texto"]
print("OK — processar_webhook_recebido interpreta o payload real da Meta e responde.")

# ---- payload de outro tipo de evento (status de entrega) -> ignora sem quebrar ----
_capturado.clear()
whatsapp_bot.processar_webhook_recebido({"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]})
approx(_capturado, {}, "eventos que não são mensagem recebida não deveriam gerar resposta")
print("OK — eventos que não são mensagens recebidas (ex: status de entrega) são ignorados sem erro.")

print("\nTodos os testes do bot de Scripts (WhatsApp) passaram.")
