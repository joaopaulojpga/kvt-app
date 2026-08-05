# -*- coding: utf-8 -*-
"""
Integração com o Asaas — checkout transparente (Pix com QR code + cartão
via formulário próprio, ambos dentro da nossa página, sem redirecionar
nem abrir nova aba).

Fluxo: criamos a cobrança direto na API (`/v3/payments`) e mostramos o
QR code do Pix (ou processamos o cartão) na hora. A confirmação de
pagamento definitiva chega via webhook (`processar_webhook`), que é a
fonte confiável — mesmo a resposta de sucesso da cobrança com cartão
não credita nada sozinha, só o webhook credita de fato.

Autenticação do Asaas: header `access_token` (não usa `Authorization:
Bearer`, diferente da maioria das APIs REST — atenção ao integrar).
"""
import re
import os
import json
import urllib.request
import urllib.error
from datetime import date

from db import db, insert_returning_id
import credits
import mailer as email_mod

ASAAS_API_KEY = os.environ.get("ASAAS_API_KEY")
ASAAS_ENV = os.environ.get("ASAAS_ENV", "sandbox")  # "sandbox" ou "production"
ASAAS_API_BASE = (
    "https://api.asaas.com/v3" if ASAAS_ENV == "production" else "https://api-sandbox.asaas.com/v3"
)
# Token opcional enviado pelo Asaas no header 'asaas-access-token' de cada
# webhook — configurado ao criar o webhook no painel do Asaas. Se não for
# definido, pulamos a validação (não recomendado em produção).
ASAAS_WEBHOOK_TOKEN = os.environ.get("ASAAS_WEBHOOK_TOKEN")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")

# Eventos de webhook que consideramos "pago" — Pix cai direto em
# PAYMENT_RECEIVED; cartão de crédito é aprovado em PAYMENT_CONFIRMED
# (o dinheiro em si é liquidado depois, mas a compra já está garantida).
EVENTOS_PAGO = {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"}


class PagamentoError(Exception):
    pass


def _somente_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def _limpar_telefone(texto):
    """
    Limpa o telefone para o formato que o Asaas espera (DDD + número,
    sem código do país). Se sobrar o "55" do Brasil na frente (ex:
    alguém salvou "+55 21 98765-4321"), removemos — do contrário o
    Asaas recusa por excesso de dígitos.
    """
    digitos = _somente_digitos(texto)
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    return digitos


def _buscar_endereco_via_cep(cep):
    """
    Consulta o ViaCEP (serviço público, sem autenticação) para preencher
    logradouro/bairro/cidade a partir do CEP. O Asaas exige endereço
    completo (não só o CEP) para liberar cobrança com cartão de crédito
    — pedimos ao aluno só o CEP + número em 'Meu Cadastro' e completamos
    o resto aqui, pra não forçar todo mundo a digitar endereço na mão.
    """
    cep_limpo = _somente_digitos(cep)
    if len(cep_limpo) != 8:
        return None
    try:
        req = urllib.request.Request(
            f"https://viacep.com.br/ws/{cep_limpo}/json/",
            headers={"User-Agent": "KalaniVaaTeam/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return None
    if dados.get("erro"):
        return None
    return dados


def _request(method, path, payload=None):
    if not ASAAS_API_KEY:
        raise PagamentoError("Asaas não configurado (variável ASAAS_API_KEY ausente).")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        ASAAS_API_BASE + path,
        data=data,
        method=method,
        headers={
            "access_token": ASAAS_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "KalaniVaaTeam/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="replace")
        raise PagamentoError(f"Asaas recusou a requisição ({e.code}): {detalhe}") from e
    except urllib.error.URLError as e:
        raise PagamentoError(f"Não foi possível conectar ao Asaas: {e}") from e


def obter_ou_criar_cliente(dados_comprador):
    """
    Retorna o ID do cliente no Asaas (cus_...), criando-o na primeira vez
    e reaproveitando (guardado em users.asaas_customer_id) nas próximas
    compras — evita criar um cliente duplicado a cada compra.
    """
    if dados_comprador.get("asaas_customer_id"):
        return dados_comprador["asaas_customer_id"]

    payload = {
        "name": dados_comprador["nome"],
        "cpfCnpj": _somente_digitos(dados_comprador.get("cpf")),
        "email": dados_comprador["email"],
        "phone": _limpar_telefone(dados_comprador.get("celular")),
        "externalReference": str(dados_comprador["id"]),
    }
    resp = _request("POST", "/customers", payload)
    if "id" not in resp:
        raise PagamentoError(f"Resposta inesperada do Asaas ao criar cliente: {resp}")
    with db() as conn:
        conn.execute("UPDATE users SET asaas_customer_id = ? WHERE id = ?", (resp["id"], dados_comprador["id"]))
    return resp["id"]


def criar_cobranca_pix(purchase_id, valor_centavos, dados_comprador):
    """Cria a cobrança Pix e já retorna o QR code (imagem + copia-e-cola) pra exibir na hora."""
    customer_id = obter_ou_criar_cliente(dados_comprador)
    payload = {
        "customer": customer_id,
        "billingType": "PIX",
        "value": round(valor_centavos / 100, 2),
        "dueDate": date.today().isoformat(),
        "externalReference": str(purchase_id),
    }
    resp = _request("POST", "/payments", payload)
    payment_id = resp.get("id")
    if not payment_id:
        raise PagamentoError(f"Resposta inesperada do Asaas ao criar cobrança Pix: {resp}")

    qr = _request("GET", f"/payments/{payment_id}/pixQrCode")
    if not qr.get("encodedImage") or not qr.get("payload"):
        raise PagamentoError(f"Resposta inesperada do Asaas ao gerar o QR code: {qr}")
    return {
        "payment_id": payment_id,
        "qr_image_base64": qr["encodedImage"],
        "copia_cola": qr["payload"],
        "expiracao": qr.get("expirationDate"),
    }


def criar_cobranca_cartao(purchase_id, valor_centavos, dados_comprador, cartao):
    """
    Cobra o cartão direto (checkout transparente): os dados passam pelo
    nosso servidor só de repasse — via HTTPS, sem nunca serem salvos —
    e vão direto pra API do Asaas, que é quem processa e guarda de
    verdade (é PCI-DSS certificado). `cartao` é um dict com holderName,
    number, expiryMonth, expiryYear, ccv (vindos do formulário).

    Exige CEP + número já preenchidos em "Meu Cadastro" (antifraude de
    cartão) — a tela de compra só oferece essa opção quando o aluno já
    tem esses dados.
    """
    cep = dados_comprador.get("cep")
    numero = dados_comprador.get("endereco_numero")
    if not (cep and numero):
        raise PagamentoError("Complete CEP e número em \u201cMeu Cadastro\u201d antes de pagar com cartão.")
    endereco = _buscar_endereco_via_cep(cep)
    if not endereco:
        raise PagamentoError("Não foi possível validar o CEP cadastrado. Confira em \u201cMeu Cadastro\u201d.")

    customer_id = obter_ou_criar_cliente(dados_comprador)
    payload = {
        "customer": customer_id,
        "billingType": "CREDIT_CARD",
        "value": round(valor_centavos / 100, 2),
        "dueDate": date.today().isoformat(),
        "externalReference": str(purchase_id),
        "creditCard": {
            "holderName": cartao["holderName"],
            "number": cartao["number"],
            "expiryMonth": cartao["expiryMonth"],
            "expiryYear": cartao["expiryYear"],
            "ccv": cartao["ccv"],
        },
        "creditCardHolderInfo": {
            "name": dados_comprador["nome"],
            "email": dados_comprador["email"],
            "cpfCnpj": _somente_digitos(dados_comprador.get("cpf")),
            "postalCode": _somente_digitos(cep),
            "addressNumber": numero,
            "phone": _limpar_telefone(dados_comprador.get("celular")),
        },
    }
    return _request("POST", "/payments", payload)


def consultar_status_compra(purchase_id):
    with db() as conn:
        row = conn.execute("SELECT status FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    return row["status"] if row else None


def consultar_pagamento(payment_id):
    return _request("GET", f"/payments/{payment_id}")


def criar_compra_pendente(user_id, plano_key, valor_centavos):
    with db() as conn:
        purchase_id = insert_returning_id(
            conn,
            "INSERT INTO purchases (user_id, plano, valor_centavos, forma_pagamento, status) "
            "VALUES (?, ?, ?, 'asaas', 'pendente')",
            (user_id, plano_key, valor_centavos),
        )
    return purchase_id


def processar_webhook(body: dict, headers: dict):
    """
    Chamado pela rota /webhook/asaas. Valida o header 'asaas-access-token'
    (se ASAAS_WEBHOOK_TOKEN estiver configurado) e credita a compra quando
    o evento indica pagamento confirmado. Idempotente: se a compra já
    estiver 'pago', não credita de novo.
    """
    if ASAAS_WEBHOOK_TOKEN:
        recebido = headers.get("asaas-access-token") or headers.get("Asaas-Access-Token")
        if recebido != ASAAS_WEBHOOK_TOKEN:
            print("[webhook asaas] token inválido — ignorando notificação")
            return

    evento = body.get("event")
    if evento not in EVENTOS_PAGO:
        return  # outros eventos (criado, vencido, estornado etc.) não interessam aqui

    payment_id = (body.get("payment") or {}).get("id")
    if not payment_id:
        return

    pagamento = consultar_pagamento(payment_id)
    purchase_id = pagamento.get("externalReference")
    if not purchase_id:
        return

    with db() as conn:
        compra = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
        if compra is None or compra["status"] == "pago":
            return  # já processado (ou não encontrado) — evita creditar duas vezes
        conn.execute(
            "UPDATE purchases SET status = 'pago', payment_ref = ? WHERE id = ?",
            (str(payment_id), purchase_id),
        )

    from comprar_page import PLANOS  # import local para evitar ciclo de import
    plano = PLANOS[compra["plano"]]
    credits.emitir_creditos(compra["user_id"], compra["plano"], purchase_id, plano["creditos"])

    with db() as conn:
        usuario = conn.execute("SELECT * FROM users WHERE id = ?", (compra["user_id"],)).fetchone()
    if usuario:
        email_mod.enviar_confirmacao_compra(usuario["email"], usuario["nome"], plano["nome"], plano["creditos"])
        import whatsapp
        whatsapp.notificar_compra(usuario["nome"], usuario["celular"], plano["nome"], plano["creditos"])
