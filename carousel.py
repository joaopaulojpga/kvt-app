# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT_MUTED, HEAD_STYLES
import newsletters

CORPO_LIMITE_RESUMO = 150
INTERVALO_SEGUNDOS = 8.0

MAPS_IFRAME = (
    '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3705.757594444719!'
    '2d-41.49500088845974!3d-21.750921380002293!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!'
    '1m2!1s0xbdcf00135da605%3A0xa3b1ff43a44b27fe!2sCanoa%20Havaiana%20-%20Kalani%20Vaa%20Team!'
    '5e0!3m2!1spt-BR!2sbr!4v1785809559354!5m2!1spt-BR!2sbr" width="100%" height="420" '
    'style="border:0;" allowfullscreen="" loading="lazy" '
    'referrerpolicy="strict-origin-when-cross-origin"></iframe>'
)


def _classe_estilo(nome_estilo):
    return HEAD_STYLES.get(nome_estilo, "kv-head-destaque")


def _abrir_modal_conteudo(item):
    with ui.dialog() as dialog, ui.card().style("max-width:600px; padding:28px; gap:10px;"):
        ui.label(item["titulo"]).style(f"color:{TEXT_MUTED}; font-size:12px; font-weight:700; text-transform:uppercase;")
        ui.label(item["head_texto"]).classes(_classe_estilo(item["head_estilo"])).style(f"color:{NAVY};")
        ui.label(item["corpo_texto"]).style("color:#333; font-size:14px; line-height:1.6; white-space:pre-wrap;")
        ui.button("Fechar", on_click=dialog.close).props("flat").style(f"color:{TEAL_DARK}; align-self:flex-end;")
    dialog.open()


def _abrir_modal_mapa():
    with ui.dialog() as dialog, ui.card().style("max-width:640px; padding:16px; gap:10px;"):
        ui.label("Onde treinamos").style(f"color:{NAVY}; font-weight:800; font-size:16px;")
        ui.html(MAPS_IFRAME).style("width:100%;")
        ui.button("Fechar", on_click=dialog.close).props("flat").style(f"color:{TEAL_DARK}; align-self:flex-end;")
    dialog.open()


def _rolar_ate_cadastro():
    ui.run_javascript(
        "document.getElementById('cadastro-section')?.scrollIntoView({behavior:'smooth'});"
    )


def render_carousel():
    itens = newsletters.listar_ativas()
    if not itens:
        return  # nenhuma newsletter ativa cadastrada ainda — carrossel simplesmente não aparece

    estado = {"idx": 0}
    palco = ui.column().style("width:100%; position:relative; gap:8px;")

    def desenhar():
        palco.clear()
        item = itens[estado["idx"]]
        with palco:
            _desenhar_slide(item)
            with ui.row().style("justify-content:center; gap:14px; align-items:center; width:100%;"):
                ui.button(icon="chevron_left", on_click=anterior).props("round flat dense").style(
                    f"color:{TEAL_DARK};"
                )
                with ui.row().style("gap:6px;"):
                    for i in range(len(itens)):
                        cor = TEAL if i == estado["idx"] else "#C9D3BE"
                        ui.label("\u25CF").style(f"color:{cor}; font-size:11px; cursor:pointer;").on(
                            "click", lambda i=i: ir_para(i)
                        )
                ui.button(icon="chevron_right", on_click=proximo).props("round flat dense").style(
                    f"color:{TEAL_DARK};"
                )

    def proximo():
        estado["idx"] = (estado["idx"] + 1) % len(itens)
        desenhar()

    def anterior():
        estado["idx"] = (estado["idx"] - 1) % len(itens)
        desenhar()

    def ir_para(i):
        estado["idx"] = i
        desenhar()

    if len(itens) > 1:
        ui.timer(INTERVALO_SEGUNDOS, proximo)
    desenhar()


def _desenhar_slide(item):
    bg_img = item.get("imagem_url")
    posicao = item.get("imagem_posicao") or "center"
    if bg_img:
        fundo = (
            f"background:linear-gradient(180deg, rgba(11,19,7,0.15), rgba(11,19,7,0.80)), "
            f"url('{bg_img}'); background-size:cover; background-position:{posicao};"
        )
    else:
        fundo = f"background:{NAVY};"

    with ui.column().style(
        f"{fundo} border-radius:16px; padding:28px 32px; min-height:280px; "
        "justify-content:flex-end; gap:8px; width:100%;"
    ):
        ui.label(item["titulo"]).style(
            "color:#CFE3B8; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;"
        )
        ui.label(item["head_texto"]).classes(_classe_estilo(item["head_estilo"])).style("color:white;")

        corpo = item.get("corpo_texto") or ""
        truncado = len(corpo) > CORPO_LIMITE_RESUMO
        resumo = corpo[:CORPO_LIMITE_RESUMO].rstrip() + "\u2026" if truncado else corpo
        if resumo:
            ui.label(resumo).style("color:#E7EEDD; font-size:13.5px; max-width:640px; line-height:1.4;")
        if truncado:
            ui.label("Ler mais").style(
                "color:white; font-size:12.5px; font-weight:700; text-decoration:underline; cursor:pointer; width:fit-content;"
            ).on("click", lambda i=item: _abrir_modal_conteudo(i))

        cta = item.get("botao_cta")
        label = item.get("botao_label") or "Saiba mais"

        def acionar(i=item, c=cta):
            if c == "abrir_modal":
                _abrir_modal_conteudo(i)
            elif c == "rolar_cadastro":
                _rolar_ate_cadastro()
            elif c == "abrir_mapa":
                _abrir_modal_mapa()

        ui.button(label, on_click=acionar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content; margin-top:6px;"
        )
