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
from payments import PagamentoError  # noqa: E402
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

# ---- obter_ou_criar_cliente: cria na 1ª vez, reaproveita se já tiver id ----
_payload_capturado = {}


def _stub_request_cliente(method, path, payload=None):
    _payload_capturado["method"], _payload_capturado["path"], _payload_capturado["payload"] = method, path, payload
    return {"id": "cus_fake123"}


payments._request = _stub_request_cliente
dados_sem_asaas_id = {
    "id": aluno, "nome": "Fernanda Reis", "cpf": "111.222.333-44", "email": "f@t.com",
    "celular": "+55 (21) 90000-9999",
}
cid = payments.obter_ou_criar_cliente(dados_sem_asaas_id)
approx(cid, "cus_fake123")
approx(_payload_capturado["payload"]["cpfCnpj"], "11122233344", "CPF deveria vir só com dígitos")
approx(_payload_capturado["payload"]["phone"], "21900009999", "telefone deveria remover o +55 do país")
with db() as conn:
    salvo = conn.execute("SELECT asaas_customer_id FROM users WHERE id = ?", (aluno,)).fetchone()
approx(salvo["asaas_customer_id"], "cus_fake123", "id do cliente deveria ficar salvo pra reaproveitar depois")
print("OK — obter_ou_criar_cliente cria o cliente, limpa CPF/telefone (removendo +55) e salva o id.")

dados_com_asaas_id = dict(dados_sem_asaas_id, asaas_customer_id="cus_ja_existia")
_payload_capturado.clear()
cid2 = payments.obter_ou_criar_cliente(dados_com_asaas_id)
approx(cid2, "cus_ja_existia")
approx(_payload_capturado, {}, "não deveria chamar a API se o cliente já existe")
print("OK — obter_ou_criar_cliente reaproveita o id já salvo, sem chamar a API de novo.")

# ---- criar_cobranca_pix: cria a cobrança e busca o QR code ----
def _stub_request_pix(method, path, payload=None):
    if path == "/payments":
        return {"id": "pay_pix_1"}
    if path == "/payments/pay_pix_1/pixQrCode":
        return {"encodedImage": "BASE64FAKE", "payload": "00020126...copiaecola...6304ABCD", "expirationDate": "2026-08-05 12:00:00"}
    raise AssertionError(f"chamada inesperada: {path}")


payments._request = _stub_request_pix
pix = payments.criar_cobranca_pix(purchase_id, 10500, dados_com_asaas_id)
approx(pix["payment_id"], "pay_pix_1")
approx(pix["qr_image_base64"], "BASE64FAKE")
approx(pix["copia_cola"], "00020126...copiaecola...6304ABCD")
print("OK — criar_cobranca_pix cria a cobrança e retorna a imagem + copia-e-cola do QR code.")

# ---- criar_cobranca_cartao: sem CEP/número -> bloqueia com mensagem clara ----
try:
    payments.criar_cobranca_cartao(purchase_id, 10500, dados_com_asaas_id, {
        "holderName": "F R", "number": "4111111111111111", "expiryMonth": "12", "expiryYear": "2030", "ccv": "123",
    })
    raise AssertionError("deveria ter bloqueado por falta de CEP/número")
except PagamentoError as e:
    assert "Meu Cadastro" in str(e)
    print(f"OK — cartão sem CEP/número é bloqueado com mensagem clara: {e}")

# ---- criar_cobranca_cartao: com CEP/número + ViaCEP OK -> cobra normalmente ----
payments._buscar_endereco_via_cep = lambda cep: {
    "logradouro": "Rua das Palmeiras", "bairro": "Centro", "localidade": "Campos dos Goytacazes", "ibge": "3301009",
}
dados_com_endereco = dict(dados_com_asaas_id, cep="28035-000", endereco_numero="123")


def _stub_request_cartao(method, path, payload=None):
    _payload_capturado["payload"] = payload
    return {"id": "pay_card_1", "status": "CONFIRMED"}


payments._request = _stub_request_cartao
resp = payments.criar_cobranca_cartao(purchase_id, 10500, dados_com_endereco, {
    "holderName": "Fernanda Reis", "number": "4111111111111111", "expiryMonth": "12", "expiryYear": "2030", "ccv": "123",
})
approx(resp["status"], "CONFIRMED")
pl = _payload_capturado["payload"]
approx(pl["creditCardHolderInfo"]["postalCode"], "28035000")
approx(pl["creditCardHolderInfo"]["addressNumber"], "123")
approx(pl["creditCard"]["number"], "4111111111111111")
print("OK — criar_cobranca_cartao com CEP/número preenchido cobra normalmente, incluindo endereço.")

# ---- criar_cobranca_cartao: CEP/número presentes mas ViaCEP falha -> bloqueia (não deixa passar sem validar) ----
payments._buscar_endereco_via_cep = lambda cep: None
try:
    payments.criar_cobranca_cartao(purchase_id, 10500, dados_com_endereco, {
        "holderName": "F R", "number": "4111111111111111", "expiryMonth": "12", "expiryYear": "2030", "ccv": "123",
    })
    raise AssertionError("deveria ter bloqueado por CEP inválido")
except PagamentoError as e:
    print(f"OK — falha do ViaCEP ao cobrar cartão é tratada com mensagem clara: {e}")

print("\nTodos os testes de pagamento (Asaas) passaram.")
