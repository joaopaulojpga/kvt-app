# -*- coding: utf-8 -*-
"""Testa a integração de pagamento com o Asaas: criação de compra, webhook
(idempotência, filtro de eventos, validação de token) — sem chamadas de
rede de verdade (payments.consultar_pagamento é substituída por um stub)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_pagamento_asaas.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import payments  # noqa: E402
import credits  # noqa: E402

init_db()


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


aluno = cadastrar_usuario("Fernanda Reis", "F", "fernanda_pay@t.com", "1", "payasaas1", "21900009999")

# ---- criar_compra_pendente ----
purchase_id = payments.criar_compra_pendente(aluno, "pacote4", 10500)
with db() as conn:
    compra = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
approx(compra["forma_pagamento"], "asaas", "forma_pagamento deveria ser 'asaas'")
approx(compra["status"], "pendente")
print("OK — criar_compra_pendente grava forma_pagamento='asaas' e status pendente.")

# ---- stub de consultar_pagamento (sem rede) ----
_original_consultar = payments.consultar_pagamento


def _stub_consultar(payment_id):
    return {"id": payment_id, "externalReference": str(purchase_id), "status": "RECEIVED"}


payments.consultar_pagamento = _stub_consultar

# ---- evento que não é de pagamento confirmado: não credita ----
payments.processar_webhook({"event": "PAYMENT_CREATED", "payment": {"id": "pay_1"}}, {})
approx(credits.saldo_disponivel(aluno), 0, "PAYMENT_CREATED não deveria creditar nada")
print("OK — eventos fora de EVENTOS_PAGO são ignorados (nenhum crédito emitido).")

# ---- token de webhook inválido (quando configurado): não credita ----
payments.ASAAS_WEBHOOK_TOKEN = "segredo-forte-de-teste-1234567890"
payments.processar_webhook(
    {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
    {"asaas-access-token": "token-errado"},
)
approx(credits.saldo_disponivel(aluno), 0, "token inválido não deveria creditar nada")
print("OK — webhook com asaas-access-token inválido é rejeitado.")

# ---- evento válido com token correto: credita ----
payments.processar_webhook(
    {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
    {"asaas-access-token": "segredo-forte-de-teste-1234567890"},
)
approx(credits.saldo_disponivel(aluno), 4, "deveria creditar as 4 remadas do pacote4")
with db() as conn:
    compra = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
approx(compra["status"], "pago")
approx(compra["payment_ref"], "pay_1")
print("OK — PAYMENT_RECEIVED com token válido credita as remadas e marca a compra como paga.")

# ---- idempotência: mesmo evento de novo não credita duas vezes ----
payments.processar_webhook(
    {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
    {"asaas-access-token": "segredo-forte-de-teste-1234567890"},
)
approx(credits.saldo_disponivel(aluno), 4, "reprocessar o mesmo evento não deveria creditar de novo")
print("OK — reenvio do mesmo evento (idempotência) não duplica o crédito.")

payments.consultar_pagamento = _original_consultar
payments.ASAAS_WEBHOOK_TOKEN = None

# ---- criar_checkout: sem CEP/número -> só Pix, sem campos de endereço ----
payments.APP_BASE_URL = "https://kvt-app.onrender.com"
_payload_capturado = {}


def _stub_request(method, path, payload=None):
    _payload_capturado["method"], _payload_capturado["path"], _payload_capturado["payload"] = method, path, payload
    return {"link": "https://checkout.asaas.com/fake-link"}


payments._request = _stub_request

dados_sem_endereco = {"nome": "Fernanda Reis", "cpf": "111.222.333-44", "email": "f@t.com", "celular": "(21) 90000-9999"}
link = payments.criar_checkout(purchase_id, "Pacote 4 remadas", 10500, dados_sem_endereco)
approx(link, "https://checkout.asaas.com/fake-link")
approx(_payload_capturado["payload"]["billingTypes"], ["PIX"], "sem CEP/número deveria oferecer só Pix")
assert "postalCode" not in _payload_capturado["payload"]["customerData"], "não deveria mandar endereço sem CEP"
approx(_payload_capturado["payload"]["customerData"]["cpfCnpj"], "11122233344", "CPF deveria vir só com dígitos")
approx(_payload_capturado["payload"]["customerData"]["phone"], "21900009999", "telefone deveria vir só com dígitos")
print("OK — criar_checkout sem CEP/número oferece só Pix e limpa CPF/telefone corretamente.")

# ---- criar_checkout: com CEP/número + ViaCEP OK -> Pix + Cartão, endereço preenchido ----
payments._buscar_endereco_via_cep = lambda cep: {
    "logradouro": "Rua das Palmeiras", "bairro": "Centro", "localidade": "Campos dos Goytacazes", "ibge": "3301009",
}
dados_com_endereco = dict(dados_sem_endereco, cep="28035-000", endereco_numero="123")
payments.criar_checkout(purchase_id, "Pacote 4 remadas", 10500, dados_com_endereco)
pl = _payload_capturado["payload"]
approx(pl["billingTypes"], ["PIX", "CREDIT_CARD"], "com CEP/número deveria liberar cartão também")
approx(pl["customerData"]["postalCode"], "28035000")
approx(pl["customerData"]["addressNumber"], "123")
approx(pl["customerData"]["address"], "Rua das Palmeiras")
approx(pl["customerData"]["province"], "Centro")
approx(pl["customerData"]["city"], 3301009)
print("OK — criar_checkout com CEP/número libera Pix + Cartão e preenche endereço via ViaCEP.")

# ---- criar_checkout: CEP/número presentes mas ViaCEP falha -> cai pra só Pix (não quebra) ----
payments._buscar_endereco_via_cep = lambda cep: None
payments.criar_checkout(purchase_id, "Pacote 4 remadas", 10500, dados_com_endereco)
approx(_payload_capturado["payload"]["billingTypes"], ["PIX"], "se o ViaCEP falhar, deveria cair pra só Pix")
print("OK — falha no ViaCEP não trava a compra, só remove a opção de cartão.")

print("\nTodos os testes de pagamento (Asaas) passaram.")
