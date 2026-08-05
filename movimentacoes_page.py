# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER
from ui_helpers import page_title
from db import db
import auth
import credits
import students
from comprar_page import PLANOS
from historico_creditos_page import FORMA_PAGAMENTO_LABEL, _linha_movimentacao

TIPOS_OPERACAO = [
    ("venda_offline", "Venda Offline", "point_of_sale"),
    ("cortesia", "Cortesia", "redeem"),
    ("reposicao", "Reposição", "history"),
    ("reagendamento", "Reagendamento", "event_repeat"),
    ("ajuste_manual", "Ajuste Manual", "tune"),
]
FORMAS_PAGAMENTO = [("pix", "Pix"), ("dinheiro", "Dinheiro"), ("cartao", "Cartão"), ("transferencia", "Transferência")]


def render(user):
    page_title("Movimentações de Créditos")
    ui.label(
        "Lance créditos manualmente para um aluno — venda offline, cortesia, reposição, "
        "reagendamento ou ajuste. Fica tudo registrado no histórico do aluno, com a mesma "
        "lógica usada nas compras online."
    ).style(f"color:{TEXT_MUTED}; font-size:12.5px; max-width:640px;")

    alunos = students.listar_alunos()
    mapa_alunos = {a["nome"]: a["id"] for a in alunos}

    estado = {"aluno_id": None, "tipo": None, "pacote_key": None, "forma_pagamento": None}
    painel_resumo = ui.column().style("width:100%; gap:16px;")

    def atualizar_resumo():
        painel_resumo.clear()
        with painel_resumo:
            if estado["aluno_id"] is not None:
                _resumo_aluno(estado["aluno_id"])
                _historico_aluno(estado["aluno_id"])

    with ui.row().style("gap:24px; width:100%; flex-wrap:wrap; align-items:flex-start; margin-top:8px;"):
        with ui.column().style("flex:1.2; min-width:320px; gap:18px;"):
            _form_nova_movimentacao(user, estado, mapa_alunos, atualizar_resumo)
        with ui.column().style("flex:1; min-width:300px;"):
            painel_resumo


def _card_selecionavel(label, sublinha, selecionado, on_click):
    borda = TEAL if selecionado else "#D8DED2"
    with ui.column().style(
        f"border:2px solid {borda}; border-radius:10px; padding:10px 14px; cursor:pointer; "
        f"gap:2px; min-width:130px; background:{'#EAF6F4' if selecionado else 'white'};"
    ) as card:
        ui.label(label).style(f"color:{TEXT}; font-weight:700; font-size:13px;")
        if sublinha:
            ui.label(sublinha).style(f"color:{TEXT_MUTED}; font-size:11px;")
    card.on("click", on_click)
    return card


def _form_nova_movimentacao(user, estado, mapa_alunos, atualizar_resumo):
    with ui.column().classes("canoa-card").style("width:100%; gap:16px;"):
        ui.label("Nova Movimentação").style(f"color:{NAVY}; font-weight:800; font-size:15px;")

        ui.label("Aluno *").style(f"color:{TEXT}; font-weight:700; font-size:12.5px;")
        select_aluno = ui.select(
            list(mapa_alunos.keys()), with_input=True, label="Pesquisar aluno pelo nome"
        ).classes("w-full")

        def ao_escolher_aluno():
            estado["aluno_id"] = mapa_alunos.get(select_aluno.value)
            atualizar_resumo()

        select_aluno.on_value_change(ao_escolher_aluno)

        ui.label("Tipo da Operação *").style(f"color:{TEXT}; font-weight:700; font-size:12.5px; margin-top:6px;")
        linha_tipos = ui.row().style("gap:10px; flex-wrap:wrap;")
        linha_forma = ui.row().style("gap:10px; flex-wrap:wrap;")

        def redesenhar_tipos():
            linha_tipos.clear()
            with linha_tipos:
                for chave, label, _icone in TIPOS_OPERACAO:
                    _card_selecionavel(
                        label, None, estado["tipo"] == chave,
                        lambda c=chave: (estado.__setitem__("tipo", c), redesenhar_tipos(), redesenhar_forma()),
                    )
            redesenhar_forma()

        def redesenhar_forma():
            linha_forma.clear()
            if estado["tipo"] != "venda_offline":
                estado["forma_pagamento"] = None
                return
            with linha_forma:
                ui.label("Forma de pagamento *").style(f"color:{TEXT}; font-weight:700; font-size:12.5px; width:100%;")
                for chave, label in FORMAS_PAGAMENTO:
                    _card_selecionavel(
                        label, None, estado["forma_pagamento"] == chave,
                        lambda c=chave: (estado.__setitem__("forma_pagamento", c), redesenhar_forma()),
                    )

        redesenhar_tipos()

        ui.label("Pacote *").style(f"color:{TEXT}; font-weight:700; font-size:12.5px; margin-top:6px;")
        linha_pacotes = ui.row().style("gap:10px; flex-wrap:wrap;")

        def redesenhar_pacotes():
            linha_pacotes.clear()
            with linha_pacotes:
                for chave, plano in PLANOS.items():
                    sublinha = f"+{plano['creditos']} crédito" + ("s" if plano["creditos"] > 1 else "")
                    _card_selecionavel(
                        plano["nome"], sublinha, estado["pacote_key"] == chave,
                        lambda c=chave: (estado.__setitem__("pacote_key", c), redesenhar_pacotes()),
                    )

        redesenhar_pacotes()

        observacoes = ui.textarea("Observações (opcional)").classes("w-full").props("rows=2")
        erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

        def cancelar():
            select_aluno.set_value(None)
            estado.update(aluno_id=None, tipo=None, pacote_key=None, forma_pagamento=None)
            observacoes.set_value("")
            redesenhar_tipos()
            redesenhar_pacotes()
            atualizar_resumo()

        def validar_e_confirmar():
            if estado["aluno_id"] is None:
                erro.set_text("Selecione um aluno.")
                return
            if estado["tipo"] is None:
                erro.set_text("Selecione o tipo da operação.")
                return
            if estado["pacote_key"] is None:
                erro.set_text("Selecione o pacote.")
                return
            if estado["tipo"] == "venda_offline" and estado["forma_pagamento"] is None:
                erro.set_text("Selecione a forma de pagamento.")
                return
            erro.set_text("")
            _abrir_confirmacao(user, estado, mapa_alunos, select_aluno, observacoes, atualizar_resumo, cancelar)

        with ui.row().style("gap:10px; margin-top:4px;"):
            ui.button("Cancelar", on_click=cancelar).props("flat").style(f"color:{TEXT_MUTED};")
            ui.button("Lançar Movimentação", on_click=validar_e_confirmar).props("unelevated").style(
                f"background:{TEAL}; color:white; font-weight:700;"
            )


def _abrir_confirmacao(user, estado, mapa_alunos, select_aluno, observacoes, atualizar_resumo, resetar_form):
    plano = PLANOS[estado["pacote_key"]]
    tipo_label = dict((c, l) for c, l, _i in TIPOS_OPERACAO)[estado["tipo"]]
    nome_aluno = select_aluno.value

    with ui.dialog() as dialog, ui.card().style("width:min(400px, 90vw); padding:22px; gap:10px;"):
        ui.label("Confirmar lançamento").style(f"color:{NAVY}; font-weight:800; font-size:16px;")
        ui.label(f"{tipo_label} \u2014 +{plano['creditos']} crédito(s)").style(f"color:{TEXT}; font-size:13.5px;")
        ui.label(f"Aluno: {nome_aluno}").style(f"color:{TEXT}; font-size:13.5px;")
        if estado["forma_pagamento"]:
            ui.label(f"Forma de pagamento: {FORMA_PAGAMENTO_LABEL[estado['forma_pagamento']]}").style(
                f"color:{TEXT_MUTED}; font-size:12.5px;"
            )
        ui.label("Essa movimentação fica registrada no histórico do aluno e não pode ser apagada — "
                  "só corrigida com um novo lançamento.").style(f"color:{TEXT_MUTED}; font-size:11.5px;")

        def confirmar():
            credits.emitir_creditos(
                estado["aluno_id"], estado["pacote_key"], None, plano["creditos"],
                tipo_movimentacao=estado["tipo"], forma_pagamento=estado["forma_pagamento"],
                usuario_responsavel_id=user["id"], observacoes=observacoes.value or None,
            )
            dialog.close()
            ui.notify(
                f"{plano['creditos']} créditos adicionados com sucesso ao aluno {nome_aluno}.",
                type="positive",
            )
            resetar_form()
            select_aluno.set_value(nome_aluno)
            estado["aluno_id"] = mapa_alunos.get(nome_aluno)
            atualizar_resumo()

        with ui.row().style("gap:10px; margin-top:8px; justify-content:flex-end;"):
            ui.button("Voltar", on_click=dialog.close).props("flat").style(f"color:{TEXT_MUTED};")
            ui.button("Confirmar", on_click=confirmar).props("unelevated").style(
                f"background:{TEAL}; color:white; font-weight:700;"
            )
    dialog.open()


def _resumo_aluno(aluno_id):
    dados = auth.get_usuario(aluno_id)
    saldo = credits.saldo_disponivel(aluno_id)
    validade = credits.proxima_validade(aluno_id)

    with db() as conn:
        ultima_compra = conn.execute(
            "SELECT criado_em FROM credit_transactions WHERE user_id = ? AND tipo_operacao = 'entrada' "
            "ORDER BY criado_em DESC LIMIT 1",
            (aluno_id,),
        ).fetchone()
        ultima_remada = conn.execute(
            "SELECT MAX(c.data) AS d FROM reservations r JOIN classes c ON c.id = r.class_id "
            "WHERE r.user_id = ? AND r.status = 'presente'",
            (aluno_id,),
        ).fetchone()

    with ui.column().classes("canoa-card").style("width:100%; gap:10px;"):
        with ui.row().style("align-items:center; gap:12px;"):
            if dados.get("foto_url"):
                ui.image(dados["foto_url"]).style(
                    f"width:48px; height:48px; border-radius:50%; object-fit:cover; border:2px solid {TEAL};"
                )
            else:
                iniciais = "".join([p[0] for p in dados["nome"].split()[:2]]).upper()
                ui.label(iniciais).style(
                    f"background:#E3EEDA; color:{TEAL_DARK}; border-radius:50%; width:48px; height:48px; "
                    "display:flex; align-items:center; justify-content:center; font-weight:700; font-size:15px;"
                )
            with ui.column().style("gap:0;"):
                ui.label(dados["nome"]).style(f"color:{NAVY}; font-weight:800; font-size:15px;")
                ui.label(dados["celular"]).style(f"color:{TEXT_MUTED}; font-size:12px;")
                ui.label(dados["email"]).style(f"color:{TEXT_MUTED}; font-size:12px;")

        ui.separator()
        with ui.row().style("gap:24px; flex-wrap:wrap;"):
            _mini_stat("Saldo atual", f"{saldo} remadas")
            _mini_stat("Validade dos créditos", validade or "\u2014")
            _mini_stat("Última compra/lançamento", str(ultima_compra["criado_em"])[:10] if ultima_compra else "\u2014")
            _mini_stat("Última remada", ultima_remada["d"] or "\u2014")

        with ui.row().style(
            "background:#EAF6F4; border-radius:8px; padding:10px 12px; gap:8px; align-items:center; margin-top:4px;"
        ):
            ui.icon("info").style(f"color:{TEAL_DARK}; font-size:16px;")
            ui.label("Toda movimentação lançada aqui fica registrada no histórico do aluno.").style(
                f"color:{TEAL_DARK}; font-size:11.5px;"
            )


def _mini_stat(label, valor):
    with ui.column().style("gap:0;"):
        ui.label(label).style(f"color:{TEXT_MUTED}; font-size:10.5px;")
        ui.label(str(valor)).style(f"color:{TEXT}; font-weight:700; font-size:13px;")


def _historico_aluno(aluno_id):
    estado_hist = {"expandido": False}
    container = ui.column().classes("canoa-card").style("width:100%; gap:0;")

    def desenhar():
        container.clear()
        limite = None if estado_hist["expandido"] else 5
        movimentacoes = credits.listar_movimentacoes(aluno_id, limite=limite)
        with container:
            ui.label("Últimas movimentações").style(f"color:{NAVY}; font-weight:800; font-size:14px; margin-bottom:4px;")
            if not movimentacoes:
                ui.label("Nenhuma movimentação ainda.").style(f"color:{TEXT_MUTED}; font-size:12.5px;")
                return
            for mov in movimentacoes:
                _linha_movimentacao(mov)

            total = len(credits.listar_movimentacoes(aluno_id))
            if total > 5:
                def alternar():
                    estado_hist["expandido"] = not estado_hist["expandido"]
                    desenhar()

                texto = "Ver menos" if estado_hist["expandido"] else "Ver histórico completo"
                ui.label(texto).style(
                    f"color:{TEAL_DARK}; font-size:12px; font-weight:700; text-decoration:underline; "
                    "cursor:pointer; margin-top:8px;"
                ).on("click", alternar)

    desenhar()
