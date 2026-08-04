# -*- coding: utf-8 -*-
"""
Integração com o Mercado Pago (Checkout Pro).

Fluxo: criamos uma "preferência" de pagamento e redirecionamos o
comprador para a página hospedada pelo Mercado Pago (ele escolhe Pix ou
cartão por lá — mais simples e mais seguro do que reimplementar
tokenização de cartão na mão). A confirmação de pagamento chega via
webhook (`processar_webhook`), que é a fonte confiável — o redirecionamento
de volta ao app é só uma conveniência de UX, nunca usado sozinho para
liberar o crédito.
"""
import os
import json
import urllib.request
import urllib.error

from db import db, insert_returning_id
import credits
import mailer as email_mod

MP_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
MP_API_BASE = "https://api.mercadopago.com"
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")


class PagamentoError(Exception):
    pass


def _request(method, path, payload=None):
    if not MP_ACCESS_TOKEN:
        raise PagamentoError("Mercado Pago não configurado (variável MERCADOPAGO_ACCESS_TOKEN ausente).")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        MP_API_BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="replace")
        raise PagamentoError(f"Mercado Pago recusou a requisição ({e.code}): {detalhe}") from e
    except urllib.error.URLError as e:
        raise PagamentoError(f"Não foi possível conectar ao Mercado Pago: {e}") from e


def criar_preferencia(purchase_id, titulo, valor_centavos, email_comprador):
    if not APP_BASE_URL:
        raise PagamentoError(
            "Variável APP_BASE_URL não configurada — necessária para o Mercado Pago "
            "saber para onde redirecionar e avisar sobre o pagamento."
        )
    payload = {
        "items": [{
            "title": titulo,
            "quantity": 1,
            "unit_price": round(valor_centavos / 100, 2),
            "currency_id": "BRL",
        }],
        "payer": {"email": email_comprador},
        "external_reference": str(purchase_id),
        "back_urls": {
            "success": f"{APP_BASE_URL}/comprar",
            "failure": f"{APP_BASE_URL}/comprar",
            "pending": f"{APP_BASE_URL}/comprar",
        },
        "auto_return": "approved",
        "notification_url": f"{APP_BASE_URL}/webhook/mercadopago",
    }
    resp = _request("POST", "/checkout/preferences", payload)
    if "init_point" not in resp:
        raise PagamentoError(f"Resposta inesperada do Mercado Pago ao criar preferência: {resp}")
    return resp["init_point"]


def consultar_pagamento(payment_id):
    return _request("GET", f"/v1/payments/{payment_id}")


def criar_compra_pendente(user_id, plano_key, valor_centavos):
    with db() as conn:
        purchase_id = insert_returning_id(
            conn,
            "INSERT INTO purchases (user_id, plano, valor_centavos, forma_pagamento, status) "
            "VALUES (?, ?, ?, 'mercadopago', 'pendente')",
            (user_id, plano_key, valor_centavos),
        )
    return purchase_id


def processar_webhook(body: dict, query: dict):
    """
    Chamado pela rota /webhook/mercadopago. Aceita tanto o formato de
    query string (?type=payment&data.id=123) quanto o corpo JSON que o
    Mercado Pago manda hoje ({"type": "payment", "data": {"id": "123"}}).
    Idempotente: se a compra já estiver 'pago', não credita de novo.
    """
    tipo = query.get("type") or body.get("type")
    payment_id = query.get("data.id") or (body.get("data") or {}).get("id")
    if tipo != "payment" or not payment_id:
        return  # notificação de outro tipo (ex: merchant_order) — ignora

    pagamento = consultar_pagamento(payment_id)
    if pagamento.get("status") != "approved":
        return

    purchase_id = pagamento.get("external_reference")
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
