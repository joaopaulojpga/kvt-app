# -*- coding: utf-8 -*-
import json
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER, reais
from ui_helpers import page_title
from db import get_param
import auth
import payments
from payments import PagamentoError

PLANOS = {
    "avulsa": {"nome": "Remada avulsa", "creditos": 1, "param": "preco_avulsa_centavos"},
    "pacote4": {"nome": "Pacote 4 remadas", "creditos": 4, "param": "preco_pacote4_centavos"},
    "pacote6": {"nome": "Pacote 6 remadas", "creditos": 6, "param": "preco_pacote6_centavos"},
}


def render(user):
    page_title("Comprar Remadas")
    dados_user = auth.get_usuario(user["id"])
    tem_endereco = bool(dados_user.get("cep") and dados_user.get("endereco_numero"))

    ui.label(
        "Escolha um pacote e pague por Pix ou cartão, sem sair desta página. "
        "Suas remadas aparecem em \"Minhas Remadas\" assim que o pagamento for aprovado."
    ).style(f"color:{TEXT_MUTED}; font-size:12.5px; max-width:560px;")

    if not tem_endereco:
        ui.label(
            "Quer pagar com cartão de crédito? Preencha CEP e número em "
            "\"Meu Cadastro\" — por enquanto, só Pix está disponível pra você."
        ).style(f"color:{TEAL_DARK}; font-size:11.5px; max-width:560px;")

    with ui.row().style("gap:16px; width:100%; flex-wrap:wrap;"):
        for key, plano in PLANOS.items():
            preco = get_param(plano["param"], 0, int)
            destaque = key == "pacote6"
            with ui.column().classes("canoa-card").style(
                f"flex:1; min-width:220px; gap:6px; "
                f"{'border:2px solid ' + TEAL + ';' if destaque else ''}"
            ):
                if destaque:
                    ui.label("Melhor custo").style(
                        "background:#EAF7EE; color:#3FA35A; border-radius:999px; "
                        "padding:2px 10px; font-size:11px; font-weight:700; width:fit-content;"
                    )
                ui.label(plano["nome"]).style(f"color:{TEXT}; font-weight:700; font-size:14px;")
                ui.label(reais(preco)).style(f"color:{NAVY}; font-size:22px; font-weight:800;")
                if plano["creditos"] > 1:
                    ui.label(f"{plano['creditos']} remadas \u2022 {reais(preco // plano['creditos'])}/remada").style(
                        f"color:{TEXT_MUTED}; font-size:11.5px;"
                    )
                else:
                    ui.label("1 remada").style(f"color:{TEXT_MUTED}; font-size:11.5px;")
                ui.button(
                    "Comprar", on_click=lambda k=key: _abrir_modal_pagamento(user, dados_user, k, tem_endereco)
                ).props("unelevated" if destaque else "outline").style(
                    (f"background:{TEAL}; color:white;" if destaque else f"color:{TEAL_DARK};")
                    + " font-weight:700; width:100%; margin-top:4px;"
                )


def _abrir_modal_pagamento(user, dados_user, plano_key, tem_endereco):
    plano = PLANOS[plano_key]
    preco = get_param(plano["param"], 0, int)
    purchase_id = payments.criar_compra_pendente(user["id"], plano_key, preco)

    with ui.dialog().props("persistent") as dialog, ui.card().style(
        "width:min(440px, 92vw); padding:24px; gap:14px;"
    ):
        corpo = ui.column().style("width:100%; gap:14px;")
        timers = []

        def _parar_timers():
            for t in timers:
                t.cancel()
            timers.clear()

        def fechar():
            _parar_timers()
            dialog.close()

        def mostrar_selecao():
            _parar_timers()
            corpo.clear()
            with corpo:
                ui.label(f"{plano['nome']} \u2014 {reais(preco)}").style(
                    f"color:{NAVY}; font-weight:800; font-size:16px;"
                )
                ui.label("Como você quer pagar?").style(f"color:{TEXT_MUTED}; font-size:13px;")
                with ui.row().style("gap:10px; width:100%;"):
                    ui.button("Pix", on_click=mostrar_pix).props("unelevated").style(
                        f"flex:1; background:{TEAL}; color:white; font-weight:700;"
                    )
                    btn_cartao = ui.button("Cartão de crédito", on_click=mostrar_cartao).props("outline").style(
                        f"flex:1; color:{TEAL_DARK}; font-weight:700;"
                    )
                    if not tem_endereco:
                        btn_cartao.set_enabled(False)
                        btn_cartao.tooltip("Preencha CEP e número em \u201cMeu Cadastro\u201d pra habilitar")
                ui.button("Cancelar", on_click=fechar).props("flat").style(
                    f"color:{TEXT_MUTED}; align-self:center;"
                )

        def _mostrar_sucesso():
            _parar_timers()
            corpo.clear()
            with corpo:
                ui.label("\U0001F389 Pagamento confirmado!").style(
                    f"color:{TEAL_DARK}; font-weight:800; font-size:17px; align-self:center;"
                )
                ui.label("Suas remadas já estão disponíveis em \u201cMinhas Remadas\u201d.").style(
                    f"color:{TEXT_MUTED}; align-self:center; text-align:center;"
                )
                ui.button("Fechar", on_click=lambda: (dialog.close(), ui.navigate.reload())).props(
                    "unelevated"
                ).style(f"background:{TEAL}; color:white; font-weight:700; align-self:center;")

        def _acompanhar_pagamento(status_label, segundos_max, ao_expirar):
            """Fica de olho no status da compra (webhook credita em background) e comemora
            assim que o pagamento cai, sem precisar o aluno recarregar a página."""
            estado = {"restante": segundos_max}

            def tick():
                estado["restante"] -= 1
                if payments.consultar_status_compra(purchase_id) == "pago":
                    _mostrar_sucesso()
                    return
                if estado["restante"] <= 0:
                    _parar_timers()
                    ao_expirar()
                    return
                if status_label is not None:
                    m, s = divmod(max(0, estado["restante"]), 60)
                    status_label.set_text(f"Aguardando confirmação \u2022 expira em {m:02d}:{s:02d}")

            timers.append(ui.timer(1.0, tick))

        def mostrar_pix():
            _parar_timers()
            corpo.clear()
            with corpo:
                ui.label("Gerando o Pix\u2026").style(f"color:{TEXT_MUTED}; align-self:center;")
            try:
                pix = payments.criar_cobranca_pix(purchase_id, preco, dados_user)
            except PagamentoError as e:
                corpo.clear()
                with corpo:
                    ui.label(f"Não foi possível gerar o Pix: {e}").style(f"color:{DANGER};")
                    ui.button("Voltar", on_click=mostrar_selecao).props("flat").style(f"color:{TEXT_MUTED};")
                return

            corpo.clear()
            with corpo:
                ui.label("Escaneie o QR code ou copie o código Pix").style(
                    f"color:{NAVY}; font-weight:700; align-self:center; text-align:center;"
                )
                ui.image(f"data:image/png;base64,{pix['qr_image_base64']}").style(
                    "width:220px; height:220px; align-self:center;"
                )
                copia = pix["copia_cola"]
                with ui.row().style("width:100%; gap:8px; align-items:center;"):
                    ui.input(value=copia).props("readonly dense").style("flex:1; font-size:10.5px;")

                    def copiar():
                        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(copia)})")
                        ui.notify("Código copiado!", type="positive")

                    ui.button(icon="content_copy", on_click=copiar).props("flat dense")

                status_label = ui.label("").style(f"color:{TEAL_DARK}; font-weight:700; font-size:12.5px; align-self:center;")

                def ao_expirar():
                    status_label.set_text("O código expirou. Feche e gere um novo.")

                _acompanhar_pagamento(status_label, 300, ao_expirar)
                ui.button("Voltar", on_click=mostrar_selecao).props("flat").style(
                    f"color:{TEXT_MUTED}; align-self:center; font-size:12px;"
                )

        def mostrar_cartao():
            _parar_timers()
            corpo.clear()
            with corpo:
                ui.label(f"{plano['nome']} \u2014 {reais(preco)}").style(f"color:{NAVY}; font-weight:800;")
                holder = ui.input("Nome impresso no cartão *").classes("w-full")
                numero_cartao = ui.input("Número do cartão *").classes("w-full")
                with ui.row().style("gap:8px; width:100%;"):
                    mes = ui.input("Mês (MM) *").style("flex:1;")
                    ano = ui.input("Ano (AAAA) *").style("flex:1;")
                    cvv = ui.input("CVV *", password=True).style("flex:1;")
                erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

                def pagar():
                    if not all([holder.value, numero_cartao.value, mes.value, ano.value, cvv.value]):
                        erro.set_text("Preencha todos os campos do cartão.")
                        return
                    erro.set_text("")
                    try:
                        payments.criar_cobranca_cartao(purchase_id, preco, dados_user, {
                            "holderName": holder.value,
                            "number": numero_cartao.value.replace(" ", ""),
                            "expiryMonth": mes.value,
                            "expiryYear": ano.value,
                            "ccv": cvv.value,
                        })
                    except PagamentoError as e:
                        erro.set_text(str(e))
                        return

                    corpo.clear()
                    with corpo:
                        ui.label("Cartão aprovado \u2014 confirmando o pagamento\u2026").style(
                            f"color:{TEXT_MUTED}; align-self:center; text-align:center;"
                        )
                        status_label = ui.label("").style(
                            f"color:{TEAL_DARK}; font-weight:700; font-size:12.5px; align-self:center;"
                        )

                        def ao_expirar():
                            status_label.set_text(
                                "Ainda processando \u2014 confira \u201cMinhas Remadas\u201d em instantes."
                            )

                        _acompanhar_pagamento(status_label, 60, ao_expirar)

                ui.button("Pagar", on_click=pagar).props("unelevated").classes("w-full").style(
                    f"background:{TEAL}; color:white; font-weight:700;"
                )
                ui.button("Voltar", on_click=mostrar_selecao).props("flat").style(
                    f"color:{TEXT_MUTED}; align-self:center; font-size:12px;"
                )

        mostrar_selecao()
    dialog.open()
