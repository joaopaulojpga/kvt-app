# -*- coding: utf-8 -*-
"""
Bot de Scripts (Fase 2) — responde mensagens que o próprio usuário manda
pelo WhatsApp. Menu numerado, determinístico, sem IA: mais barato, mais
previsível, e cobre os 8 scripts combinados. IA entra numa fase futura,
só pra perguntas que não encaixem aqui.

`processar_mensagem_recebida` é uma função pura (telefone + texto → texto
de resposta) — fácil de testar sem precisar simular um payload real da
Meta. Quem efetivamente decide ENVIAR a resposta é `processar_webhook_recebido`,
chamado pela rota /webhook/whatsapp em app.py.
"""
import re
from datetime import date, timedelta

from db import db, get_param
import credits
import whatsapp
from comprar_page import PLANOS

LOCAL_CLUBE = "Lagoa de Cima"
JANELA_CREDITOS_VENCENDO_DIAS = 7

MENU = (
    "Oi! Eu sou o assistente da Kalani Vaa Team \U0001F3D4\uFE0F\n\n"
    "Digite o número da opção que você quer saber:\n\n"
    "1\uFE0F\u20E3 Meus créditos disponíveis\n"
    "2\uFE0F\u20E3 Créditos vencendo\n"
    "3\uFE0F\u20E3 Turmas da semana\n"
    "4\uFE0F\u20E3 Valores dos pacotes\n"
    "5\uFE0F\u20E3 Como usar o app\n"
    "6\uFE0F\u20E3 Nossa localização\n"
    "7\uFE0F\u20E3 Primeira vez? Comece aqui\n"
    "8\uFE0F\u20E3 Como marcar minha remada\n"
)

_SEM_CADASTRO = (
    "Não encontrei seu cadastro por esse número. Cadastre-se pelo app "
    "pra eu conseguir te ajudar com isso!"
)


def _buscar_usuario_por_telefone(telefone):
    """
    Compara pelos últimos 9 dígitos (o número da linha em si, sem DDI/DDD
    que variam de formato) em vez de tentar casar strings formatadas
    diferente no banco — mais simples e portável entre SQLite/Postgres
    do que fazer isso via SQL.
    """
    digitos_msg = re.sub(r"\D", "", telefone or "")[-9:]
    if not digitos_msg:
        return None
    with db() as conn:
        usuarios = conn.execute("SELECT * FROM users").fetchall()
    for row in usuarios:
        digitos_cad = re.sub(r"\D", "", row["celular"] or "")
        if digitos_cad and digitos_cad.endswith(digitos_msg):
            return dict(row)
    return None


def _resposta_creditos(user):
    if not user:
        return _SEM_CADASTRO
    saldo = credits.saldo_disponivel(user["id"])
    return f"Você tem {saldo} remada(s) disponível(is). \U0001F6F6"


def _resposta_creditos_vencendo(user):
    if not user:
        return _SEM_CADASTRO
    hoje = date.today()
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, MIN(validade) AS proxima FROM credits "
            "WHERE user_id = ? AND status = 'disponivel' AND validade BETWEEN ? AND ?",
            (user["id"], hoje.isoformat(), (hoje + timedelta(days=JANELA_CREDITOS_VENCENDO_DIAS)).isoformat()),
        ).fetchone()
    if row["n"] == 0:
        return "Nenhum crédito seu vence nos próximos 7 dias. \U0001F44D"
    plural = "s" if row["n"] > 1 else ""
    return f"Atenção: você tem {row['n']} remada{plural} vencendo até {row['proxima']}!"


def _resposta_pacotes():
    linhas = ["\U0001F4B0 *Nossos pacotes:*", ""]
    for plano in PLANOS.values():
        preco = get_param(plano["param"], 0, int)
        linhas.append(f"\u2022 {plano['nome']}: R$ {preco / 100:.2f}".replace(".", ","))
    if whatsapp.APP_BASE_URL:
        linhas += ["", f"Compre pelo app: {whatsapp.APP_BASE_URL}/comprar"]
    return "\n".join(linhas)


def _resposta_como_usar():
    link = whatsapp.APP_BASE_URL or "(link do app)"
    return (
        "\U0001F4F1 *Como usar o app*\n\n"
        f"1. Cadastre-se ou entre em {link}\n"
        "2. Compre um pacote de remadas\n"
        "3. Vá em Agenda de Turmas e reserve sua vaga\n"
        "4. Chegue 15 minutos antes da aula\n\n"
        "Qualquer dúvida, é só chamar por aqui!"
    )


LINK_MAPS = "https://maps.app.goo.gl/CC4e7c2cqZFMWrNn8"


def _resposta_localizacao():
    return (
        f"\U0001F4CD Estamos na Toca do Tatu, em {LOCAL_CLUBE} (Morangaba).\n"
        "Acesso via Tapera ou Usina Sta Cruz.\n"
        f"Clique para acessar nossa localização: {LINK_MAPS}\n\n"
        "Qualquer dúvida de como chegar, chama a gente!"
    )


def _resposta_primeira_visita():
    return (
        "\U0001F33A *Primeira vez remando com a gente?*\n\n"
        "Não precisa saber remar! Nossos instrutores acompanham toda a aula.\n"
        "Leve roupa que possa molhar, protetor solar, água e uma toalha \u2014 "
        "o remo e o colete a gente empresta.\n\n"
        "\u2615 Depois da remada, rola um café comunitário lá na Lagoa pra gente socializar "
        "\u2014 sinta-se à vontade pra levar algo pra compartilhar!\n\n"
        "Chegue 15 minutos antes pra gente te receber com calma."
    )


def _resposta_como_marcar():
    return (
        "\U0001F6F6 *Como marcar sua remada*\n\n"
        "Turmas da grade padrão: reserve direto pelo app, na Agenda de Turmas.\n"
        "Quer um horário exclusivo (fora da grade)? Chama a gente por aqui que a gente organiza."
    )


_ROTEADOR = {
    "1": lambda user: _resposta_creditos(user),
    "2": lambda user: _resposta_creditos_vencendo(user),
    "3": lambda user: whatsapp.gerar_texto_lista_semana(incluir_alunos=False),
    "4": lambda user: _resposta_pacotes(),
    "5": lambda user: _resposta_como_usar(),
    "6": lambda user: _resposta_localizacao(),
    "7": lambda user: _resposta_primeira_visita(),
    "8": lambda user: _resposta_como_marcar(),
}


def processar_mensagem_recebida(telefone, texto):
    """Função pura: telefone + texto recebido \u2192 texto de resposta."""
    opcao = (texto or "").strip()
    if opcao not in _ROTEADOR:
        return MENU
    user = _buscar_usuario_por_telefone(telefone)
    return _ROTEADOR[opcao](user)


def processar_webhook_recebido(body):
    """Extrai a(s) mensagem(ns) do payload da Meta e responde cada uma."""
    try:
        mensagens = body["entry"][0]["changes"][0]["value"].get("messages")
    except (KeyError, IndexError, TypeError):
        return  # outros tipos de evento no mesmo webhook (status de entrega etc.) — ignora
    if not mensagens:
        return
    for msg in mensagens:
        telefone = msg.get("from")
        texto = (msg.get("text") or {}).get("body", "")
        resposta = processar_mensagem_recebida(telefone, texto)
        whatsapp.responder_mensagem(telefone, resposta)
