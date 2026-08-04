# -*- coding: utf-8 -*-
"""Newsletters exibidas no carrossel (página pública e Home do usuário logado)."""
from db import db, insert_returning_id

CTAS = {
    "abrir_modal": "Abrir card em tela cheia",
    "rolar_cadastro": "Rolar até o cadastro",
    "abrir_mapa": "Abrir mapa (localização)",
    "abrir_link": "Abrir link externo (Instagram, WhatsApp etc.)",
}


def listar_ativas():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM newsletters WHERE status = 'ativo' ORDER BY ordem, id"
        ).fetchall()
    return [dict(r) for r in rows]


def listar_todas():
    with db() as conn:
        rows = conn.execute("SELECT * FROM newsletters ORDER BY ordem, id").fetchall()
    return [dict(r) for r in rows]


def obter(newsletter_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM newsletters WHERE id = ?", (newsletter_id,)).fetchone()
    return dict(row) if row else None


def criar(titulo, head_texto, head_estilo, corpo_texto, imagem_url, imagem_posicao,
          botao_label, botao_cta, status="ativo", ordem=0, link_url=None):
    with db() as conn:
        return insert_returning_id(
            conn,
            "INSERT INTO newsletters (titulo, head_texto, head_estilo, corpo_texto, imagem_url, "
            "imagem_posicao, botao_label, botao_cta, status, ordem, link_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (titulo, head_texto, head_estilo, corpo_texto, imagem_url, imagem_posicao,
             botao_label, botao_cta, status, ordem, link_url),
        )


def atualizar(newsletter_id, **campos):
    campos_validos = {
        "titulo", "head_texto", "head_estilo", "corpo_texto", "imagem_url",
        "imagem_posicao", "botao_label", "botao_cta", "status", "ordem", "link_url",
    }
    sets, valores = [], []
    for k, v in campos.items():
        if k in campos_validos:
            sets.append(f"{k} = ?")
            valores.append(v)
    if not sets:
        return
    valores.append(newsletter_id)
    with db() as conn:
        conn.execute(f"UPDATE newsletters SET {', '.join(sets)} WHERE id = ?", valores)


SLIDES_INICIAIS = [
    dict(
        titulo="Bem-vindo à Kalani", head_texto="Mais do que remar.", head_estilo="Título grande",
        corpo_texto="Viva a experiência da canoa havaiana.",
        imagem_url=None, imagem_posicao="center",
        botao_label="Quero conhecer", botao_cta="rolar_cadastro", link_url=None,
    ),
    dict(
        titulo="Primeira remada", head_texto="Você não precisa saber remar", head_estilo="Destaque",
        corpo_texto=(
            "Equipamentos inclusos.\n"
            "Instrutores acompanham toda a aula.\n"
            "Café comunitário após a remada."
        ),
        imagem_url=None, imagem_posicao="center",
        botao_label="Ver orientações", botao_cta="abrir_modal", link_url=None,
    ),
    dict(
        titulo="Benefícios", head_texto="Corpo, saúde e natureza", head_estilo="Destaque",
        corpo_texto="Corpo. Saúde. Natureza. Amizades. Bem-estar.",
        imagem_url=None, imagem_posicao="center",
        botao_label="Quero experimentar", botao_cta="rolar_cadastro", link_url=None,
    ),
    dict(
        titulo="Como funciona", head_texto="Do cadastro à remada", head_estilo="Chamada",
        corpo_texto="Cadastro \u2192 Compra de créditos \u2192 Reserva \u2192 Remada.",
        imagem_url=None, imagem_posicao="center",
        botao_label="Começar agora", botao_cta="rolar_cadastro", link_url=None,
    ),
    dict(
        titulo="Nossa localização", head_texto="Lagoa de Cima", head_estilo="Título grande",
        corpo_texto="Paisagem incrível. Ambiente seguro.",
        imagem_url=None, imagem_posicao="center",
        botao_label="Como chegar", botao_cta="abrir_mapa", link_url=None,
    ),
    dict(
        titulo="Faça parte da comunidade", head_texto="Instagram, WhatsApp, eventos e treinos",
        head_estilo="Chamada",
        corpo_texto="Acompanhe o dia a dia do clube e não perca nenhuma remada.",
        imagem_url=None, imagem_posicao="center",
        botao_label="Seguir a Kalani", botao_cta="abrir_link",
        link_url="https://www.instagram.com/kalani_vaa/",
    ),
]


def seed_newsletters_iniciais():
    """
    Popula os 6 slides padrão na primeira vez que a tabela newsletters
    estiver vazia — seguro de chamar em todo boot do app (não duplica,
    e não sobrescreve nada se o gestor já tiver criado/editado algo).
    """
    if listar_todas():
        return 0
    for ordem, slide in enumerate(SLIDES_INICIAIS):
        criar(ordem=ordem, **slide)
    return len(SLIDES_INICIAIS)
