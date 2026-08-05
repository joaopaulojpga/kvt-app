# -*- coding: utf-8 -*-
"""
Integração com o Asaas (Checkout Asaas).

Fluxo: criamos um "checkout" (equivalente à antiga preferência do Mercado
Pago) e mostramos o link retornado dentro de um iframe, na própria página
de compra — sem abrir nova aba nem forçar redirecionamento. A confirmação
de pagamento chega via webhook (`processar_webhook`), que é a fonte
confiável — o retorno de callback (successUrl) é só uma conveniência de
UX, nunca usado sozinho para liberar o crédito.

Autenticação do Asaas: header `access_token` (não usa `Authorization:
Bearer`, diferente da maioria das APIs REST — atenção ao integrar).
"""
import re
import os
import json
import urllib.request
import urllib.error

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


def criar_checkout(purchase_id, titulo, valor_centavos, dados_comprador):
    """
    Cria um Checkout Asaas (equivalente à preferência do Mercado Pago) e
    retorna o link hospedado para o pagador concluir Pix ou cartão.
    `dados_comprador` é o dict de auth.get_usuario(...) do comprador.

    Cartão de crédito exige endereço completo (antifraude); Pix não. Se o
    aluno ainda não preencheu CEP + número em "Meu Cadastro", oferecemos
    só Pix — evita travar quem só quer pagar por Pix só por faltar um
    dado que ele nem vai usar.
    """
    if not APP_BASE_URL:
        raise PagamentoError(
            "Variável APP_BASE_URL não configurada — necessária para o Asaas "
            "saber para onde redirecionar e avisar sobre o pagamento."
        )

    billing_types = ["PIX"]
    customer_data = {
        "name": dados_comprador["nome"],
        "cpfCnpj": _somente_digitos(dados_comprador.get("cpf")),
        "email": dados_comprador["email"],
        "phone": _somente_digitos(dados_comprador.get("celular")),
    }

    cep = dados_comprador.get("cep")
    numero = dados_comprador.get("endereco_numero")
    if cep and numero:
        endereco = _buscar_endereco_via_cep(cep)
        if endereco:
            billing_types.append("CREDIT_CARD")
            customer_data.update({
                "postalCode": _somente_digitos(cep),
                "addressNumber": numero,
                "address": endereco.get("logradouro") or endereco.get("bairro") or "Endereço não informado",
                "province": endereco.get("bairro") or endereco.get("localidade") or "Centro",
            })
            if endereco.get("ibge"):
                customer_data["city"] = int(endereco["ibge"])

    payload = {
        "billingTypes": billing_types,
        "chargeTypes": ["DETACHED"],
        "minutesToExpire": 30,
        "externalReference": str(purchase_id),
        "callback": {
            "successUrl": f"{APP_BASE_URL}/comprar",
            "cancelUrl": f"{APP_BASE_URL}/comprar",
            "expiredUrl": f"{APP_BASE_URL}/comprar",
        },
        "items": [{
            "name": titulo,
            "quantity": 1,
            "value": round(valor_centavos / 100, 2),
        }],
        "customerData": customer_data,
    }
    resp = _request("POST", "/checkouts", payload)
    if "link" not in resp:
        raise PagamentoError(f"Resposta inesperada do Asaas ao criar checkout: {resp}")
    return resp["link"]


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
