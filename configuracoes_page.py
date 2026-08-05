# -*- coding: utf-8 -*-
from nicegui import ui, events
import base64
import io
from datetime import date
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, BORDER, DANGER, HEAD_STYLES, reais
from ui_helpers import page_title, badge
import auth
import students
import newsletters
import reports
import classes as turmas_mod
from classes import TurmaError
from newsletters import CTAS

IMG_MAX_PX = (1200, 600)


def render_alunos(user):
    page_title("Lista de Alunos")
    _secao_lista_alunos()


def render_relatorios(user):
    page_title("Relatórios")
    _secao_relatorio()


def render_newsletter(user):
    page_title("Newsletter")
    _secao_newsletter()


def render_escala(user):
    page_title("Escala")
    _secao_escala()


def _secao_lista_alunos():
    container = ui.column().style("width:100%; gap:0;")

    def recarregar():
        container.clear()
        alunos = students.relatorio_alunos()
        with container:
            if not alunos:
                ui.label("Nenhum aluno cadastrado ainda.").style(f"color:{TEXT_MUTED};")
                return
            _tabela_alunos(alunos, recarregar)

    recarregar()


def _tabela_alunos(linhas, on_done):
    headers = ["Nome", "E-mail", "Celular", "Nascimento", "Aulas", "Créditos", "Última remada", "Validade", ""]
    larguras = ["160px", "190px", "130px", "100px", "60px", "80px", "120px", "100px", "170px"]
    min_total = "1110px"
    with ui.column().classes("canoa-card").style("width:100%; gap:0; overflow-x:auto;"):
        with ui.row().style(
            f"border-bottom:2px solid {BORDER}; padding-bottom:8px; gap:0; width:100%; min-width:{min_total};"
        ):
            for h, w in zip(headers, larguras):
                ui.label(h).style(f"width:{w}; flex-shrink:0; color:{TEXT_MUTED}; font-weight:700; font-size:11.5px;")

        for l in linhas:
            with ui.row().style(
                f"padding:7px 0; gap:0; width:100%; min-width:{min_total}; align-items:center; "
                "border-bottom:1px solid #EEF1F3;"
            ):
                ui.label(l["nome"]).style(f"width:{larguras[0]}; flex-shrink:0; color:{TEXT}; font-weight:700; font-size:12.5px;")
                ui.label(l["email"]).style(f"width:{larguras[1]}; flex-shrink:0; color:{TEXT}; font-size:12px;")
                ui.label(l["celular"]).style(f"width:{larguras[2]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(l["data_nascimento"] or "\u2014").style(f"width:{larguras[3]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(str(l["aulas_reservadas"])).style(f"width:{larguras[4]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(str(l["saldo_creditos"])).style(
                    f"width:{larguras[5]}; flex-shrink:0; color:{TEAL_DARK}; font-weight:700; font-size:12.5px;"
                )
                ui.label(l["ultima_aula"] or "\u2014").style(f"width:{larguras[6]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(l["proxima_validade"] or "\u2014").style(f"width:{larguras[7]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")

                with ui.row().style(f"width:{larguras[8]}; flex-shrink:0; gap:6px;"):
                    def promover(uid=l["id"], nome=l["nome"]):
                        students.promover_para_instrutor(uid)
                        ui.notify(f"{nome} agora é instrutor.", type="positive")
                        on_done()

                    ui.button("Promover", on_click=promover).props("outline dense").style(
                        f"color:{TEAL_DARK}; font-weight:700; font-size:10.5px;"
                    )

                    def abrir_edicao(a=l):
                        _abrir_modal_editar_aluno(a, on_done)

                    ui.button("Editar", on_click=abrir_edicao).props("flat dense").style(
                        f"color:{TEXT_MUTED}; font-weight:700; font-size:10.5px;"
                    )


def _abrir_modal_editar_aluno(aluno, on_done):
    dados = auth.get_usuario(aluno["id"])
    with ui.dialog() as dialog, ui.card().style("width:min(480px, 92vw); padding:22px; gap:10px;"):
        ui.label(f"Editar cadastro \u2014 {dados['nome']}").style(f"color:{NAVY}; font-weight:800; font-size:15px;")
        nome = ui.input("Nome completo *", value=dados["nome"]).classes("w-full")
        sexo = ui.select(["Feminino", "Masculino", "Outro"],
                          value=dados["sexo"] if dados["sexo"] in ["Feminino", "Masculino", "Outro"] else "Feminino",
                          label="Sexo *").classes("w-full")
        cpf = ui.input("CPF *", value=dados["cpf"]).classes("w-full")
        celular = ui.input("Celular / WhatsApp *", value=dados["celular"]).classes("w-full")
        nascimento = ui.input("Data de nascimento (AAAA-MM-DD)", value=dados["data_nascimento"] or "").classes("w-full")
        instagram = ui.input("Instagram (opcional)", value=dados["instagram"] or "").classes("w-full")
        with ui.row().style("gap:10px; width:100%;"):
            cep = ui.input("CEP", value=dados.get("cep") or "").style("flex:1;")
            numero = ui.input("Número", value=dados.get("endereco_numero") or "").style("flex:1;")
        erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

        def salvar():
            if not all([nome.value, sexo.value, cpf.value, celular.value]):
                erro.set_text("Preencha todos os campos obrigatórios (*).")
                return
            auth.atualizar_perfil(
                aluno["id"], nome=nome.value, sexo=sexo.value, cpf=cpf.value,
                celular=celular.value, instagram=instagram.value or None,
                data_nascimento=nascimento.value or None,
                cep=cep.value or None, endereco_numero=numero.value or None,
            )
            ui.notify("Cadastro atualizado.", type="positive")
            dialog.close()
            on_done()

        with ui.row().style("gap:10px; margin-top:4px;"):
            ui.button("Salvar", on_click=salvar).props("unelevated").style(
                f"background:{TEAL}; color:white; font-weight:700;"
            )
            ui.button("Fechar", on_click=dialog.close).props("flat").style(f"color:{TEXT_MUTED};")
    dialog.open()


def _secao_relatorio():
    _secao_relatorio_aulas()


def _secao_newsletter():
    lista_container = ui.column().style("width:100%; gap:10px;")
    form_container = ui.column().style("width:100%;")

    def recarregar():
        lista_container.clear()
        itens = newsletters.listar_todas()
        with lista_container:
            with ui.row().style("justify-content:space-between; align-items:center; width:100%;"):
                ui.label(f"{len(itens)} newsletter(s) cadastrada(s)").style(f"color:{TEXT_MUTED}; font-size:12.5px;")

                def abrir_criacao():
                    form_container.clear()
                    with form_container:
                        _form_newsletter(None, recarregar)

                ui.button("\u2795 Criar novo", on_click=abrir_criacao).props("unelevated").style(
                    f"background:{TEAL}; color:white; font-weight:700;"
                )

            if not itens:
                ui.label("Nenhuma newsletter cadastrada ainda \u2014 o carrossel fica oculto até a primeira ser criada.").style(
                    f"color:{TEXT_MUTED};"
                )
            for item in itens:
                with ui.row().classes("canoa-card").style(
                    "width:100%; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;"
                ):
                    with ui.column().style("gap:0;"):
                        ui.label(item["titulo"]).style(f"color:{TEXT}; font-weight:700; font-size:14px;")
                        ui.label(f"CTA: {CTAS.get(item['botao_cta'], item['botao_cta'])}").style(
                            f"color:{TEXT_MUTED}; font-size:11.5px;"
                        )
                    with ui.row().style("gap:10px; align-items:center;"):
                        badge("Ativo" if item["status"] == "ativo" else "Inativo",
                              "ok" if item["status"] == "ativo" else "muted")

                        def editar(i=item):
                            form_container.clear()
                            with form_container:
                                _form_newsletter(i, recarregar)

                        ui.button("Editar", on_click=editar).props("flat dense").style(
                            f"color:{TEAL_DARK}; font-weight:700;"
                        )

    recarregar()


def _form_newsletter(item, on_done):
    """item=None -> criação; item preenchido -> edição."""
    editando = item is not None
    imagem_atual = {"data_uri": item["imagem_url"] if editando else None}

    with ui.column().classes("canoa-card").style(f"width:100%; border-color:{TEAL}; gap:10px; max-width:640px;"):
        ui.label("Editar newsletter" if editando else "Nova newsletter").style(
            f"color:{TEAL_DARK}; font-weight:700; font-size:14px;"
        )

        titulo = ui.input("Título do slide *", value=item["titulo"] if editando else "").classes("w-full")
        head_texto = ui.input("Head (texto de destaque) *", value=item["head_texto"] if editando else "").classes("w-full")
        head_estilo = ui.select(list(HEAD_STYLES.keys()),
                                 value=item["head_estilo"] if editando else "Destaque",
                                 label="Estilo do Head").classes("w-full")
        corpo_texto = ui.textarea("Corpo", value=item["corpo_texto"] if editando else "").classes("w-full")
        ui.label("Textos longos aparecem resumidos no carrossel, com botão \"Ler mais\" abrindo o texto completo.").style(
            f"color:{TEXT_MUTED}; font-size:11px; margin-top:-6px;"
        )

        preview = ui.image(imagem_atual["data_uri"] or "").style(
            "width:100%; max-height:160px; object-fit:cover; border-radius:8px; "
            f"background:{BORDER}; display:{'block' if imagem_atual['data_uri'] else 'none'};"
        )

        async def ao_enviar_imagem(e: events.UploadEventArguments):
            try:
                from PIL import Image
                dados_arquivo = await e.file.read()
                img = Image.open(io.BytesIO(dados_arquivo)).convert("RGB")
                img.thumbnail(IMG_MAX_PX)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=82, optimize=True)
                data_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
                imagem_atual["data_uri"] = data_uri
                preview.set_source(data_uri)
                preview.style("display:block;")
                ui.notify("Imagem carregada.", type="positive")
            except Exception as ex:
                ui.notify(f"Não foi possível usar essa imagem: {ex}", type="negative")

        ui.upload(on_upload=ao_enviar_imagem, auto_upload=True, max_file_size=8_000_000).props(
            'accept=".jpg,.jpeg,.png" label="Imagem de fundo"'
        ).classes("w-full")
        imagem_posicao = ui.select(["center", "top", "bottom", "left", "right"],
                                    value=item["imagem_posicao"] if editando else "center",
                                    label="Posicionamento da imagem").classes("w-full")

        botao_label = ui.input("Texto do botão", value=item["botao_label"] if editando else "Saiba mais").classes("w-full")
        botao_cta = ui.select(CTAS, value=item["botao_cta"] if editando else "abrir_modal",
                               label="Ação do botão (CTA)").classes("w-full")
        link_url = ui.input("URL de destino (Instagram, WhatsApp etc.)",
                             value=(item.get("link_url") or "") if editando else "").classes("w-full")
        link_url.visible = botao_cta.value == "abrir_link"
        botao_cta.on_value_change(lambda e: setattr(link_url, "visible", e.value == "abrir_link"))
        status = ui.select(["ativo", "inativo"], value=item["status"] if editando else "ativo",
                            label="Status").classes("w-full")
        erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

        def salvar():
            if not titulo.value or not head_texto.value:
                erro.set_text("Título e Head são obrigatórios.")
                return
            if botao_cta.value == "abrir_link" and not link_url.value:
                erro.set_text("Informe a URL de destino para o CTA de link externo.")
                return
            campos = dict(
                titulo=titulo.value, head_texto=head_texto.value, head_estilo=head_estilo.value,
                corpo_texto=corpo_texto.value or "", imagem_url=imagem_atual["data_uri"],
                imagem_posicao=imagem_posicao.value, botao_label=botao_label.value or "Saiba mais",
                botao_cta=botao_cta.value, status=status.value,
                link_url=link_url.value if botao_cta.value == "abrir_link" else None,
            )
            if editando:
                newsletters.atualizar(item["id"], **campos)
                ui.notify("Newsletter atualizada.", type="positive")
            else:
                newsletters.criar(**campos)
                ui.notify("Newsletter criada.", type="positive")
            on_done()

        ui.button("Salvar", on_click=salvar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
        )


def _opcoes_mes():
    """Lista de (rótulo, ano, mês): 12 meses anteriores até 3 meses à frente do atual."""
    hoje = date.today()
    opcoes = []
    idx_atual = 0
    y, m = hoje.year, hoje.month
    # volta 12 meses a partir do atual
    for _ in range(12):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    for i in range(16):
        rotulo = f"{reports.MESES_PT[m].capitalize()}/{y}"
        opcoes.append((rotulo, y, m))
        if y == hoje.year and m == hoje.month:
            idx_atual = len(opcoes) - 1
        m += 1
        if m == 13:
            m = 1
            y += 1
    return opcoes, idx_atual


def _secao_relatorio_aulas():
    ui.label("Aulas do Mês").style(f"color:{TEXT}; font-weight:700; font-size:15px;")

    opcoes, idx_atual = _opcoes_mes()
    rotulos = [o[0] for o in opcoes]
    resultado_container = ui.column().style("width:100%; gap:10px;")

    def montar(rotulo_escolhido):
        ano, mes = next((o[1], o[2]) for o in opcoes if o[0] == rotulo_escolhido)
        linhas = reports.relatorio_aulas_mes(ano, mes)
        resumo = reports.resumo_por_instrutor(linhas)
        resultado_container.clear()
        with resultado_container:
            if not linhas:
                ui.label("Nenhuma aula registrada neste mês.").style(f"color:{TEXT_MUTED};")
            else:
                _tabela_aulas(linhas)
                ui.label("Resumo por instrutor").style(f"color:{TEXT}; font-weight:700; font-size:13.5px; margin-top:6px;")
                _tabela_resumo(resumo)

            def exportar():
                try:
                    from reports_pdf import gerar_pdf_relatorio
                    nome_mes = reports.MESES_PT[mes]
                    pdf_bytes = gerar_pdf_relatorio(ano, mes, nome_mes, linhas, resumo)
                    ui.download(pdf_bytes, f"{reports.nome_arquivo_pdf(ano, mes)}.pdf")
                except Exception as e:
                    ui.notify(f"Não foi possível gerar o PDF: {e}", type="negative")

            ui.button("\U0001F4C4 Exportar como PDF", on_click=exportar).props("outline").style(
                f"color:{TEAL_DARK}; font-weight:700; margin-top:8px;"
            )

    seletor = ui.select(rotulos, value=rotulos[idx_atual], label="Mês").style("max-width:220px;")
    seletor.on_value_change(lambda e: montar(e.value))
    montar(rotulos[idx_atual])


def _tabela_aulas(linhas):
    with ui.column().classes("canoa-card").style("width:100%; gap:0; overflow-x:auto;"):
        headers = ["Instrutor", "Dia/Hora", "Vagas", "Presentes", "Faltosos", "Status", "Repasse"]
        larguras = ["170px", "140px", "80px", "100px", "100px", "140px", "110px"]
        min_total = "840px"
        with ui.row().style(f"border-bottom:2px solid {BORDER}; padding-bottom:8px; gap:0; width:100%; min-width:{min_total};"):
            for h, w in zip(headers, larguras):
                ui.label(h).style(f"width:{w}; flex-shrink:0; color:{TEXT_MUTED}; font-weight:700; font-size:11.5px;")
        for l in linhas:
            with ui.row().style(f"padding:7px 0; gap:0; width:100%; min-width:{min_total}; border-bottom:1px solid #EEF1F3;"):
                ui.label(l["instrutor"]).style(f"width:{larguras[0]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(f"{l['data']} {l['horario']}").style(f"width:{larguras[1]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(str(l["vagas_ocupadas"])).style(f"width:{larguras[2]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(str(l["presentes"])).style(f"width:{larguras[3]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(str(l["faltosos"])).style(f"width:{larguras[4]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                kind = "ok" if l["status"] == "Confirmada" else ("muted" if "Suspensa" in l["status"] else "warn")
                with ui.row().style(f"width:{larguras[5]}; flex-shrink:0;"):
                    badge(l["status"], kind)
                ui.label(reais(l["repasse_centavos"])).style(f"width:{larguras[6]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")


def _tabela_resumo(resumo):
    larguras = ["220px", "170px", "170px", "170px"]
    min_total = "730px"
    with ui.column().classes("canoa-card").style(f"width:100%; gap:0; background:#EAF6F4; border-color:{TEAL}; overflow-x:auto;"):
        headers = ["Instrutor", "Alunos atendidos", "Aulas ministradas", "Total do repasse"]
        with ui.row().style(f"border-bottom:2px solid {TEAL}; padding-bottom:8px; gap:0; width:100%; min-width:{min_total};"):
            for h, w in zip(headers, larguras):
                ui.label(h).style(f"width:{w}; flex-shrink:0; color:{TEAL_DARK}; font-weight:700; font-size:11.5px;")
        for r in resumo:
            with ui.row().style(f"padding:7px 0; gap:0; width:100%; min-width:{min_total};"):
                ui.label(r["instrutor"]).style(f"width:{larguras[0]}; flex-shrink:0; color:{TEXT}; font-weight:700; font-size:12.5px;")
                ui.label(str(r["alunos"])).style(f"width:{larguras[1]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(str(r["aulas"])).style(f"width:{larguras[2]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(reais(r["total_centavos"])).style(f"width:{larguras[3]}; flex-shrink:0; color:{TEXT}; font-weight:700; font-size:12.5px;")



def _secao_escala():
    ui.label("Escala de Instrutores").style(f"color:{TEXT}; font-weight:700; font-size:15px;")
    ui.label(
        "Turmas criadas pela grade padrão do sistema nascem sem instrutor definido — "
        "atribua aqui quem vai responder por cada uma. Turmas já baixadas/suspensas não podem mais ser alteradas."
    ).style(f"color:{TEXT_MUTED}; font-size:12px;")

    opcoes, idx_atual = _opcoes_mes()
    rotulos = [o[0] for o in opcoes]
    tabela_container = ui.column().style("width:100%; gap:8px;")

    def montar(rotulo_escolhido):
        ano, mes = next((o[1], o[2]) for o in opcoes if o[0] == rotulo_escolhido)
        tabela_container.clear()
        with tabela_container:
            def gerar_grade():
                n = turmas_mod.gerar_grade_padrao(ano, mes)
                if n:
                    ui.notify(f"{n} turma(s) da grade padrão criada(s).", type="positive")
                else:
                    ui.notify("A grade padrão deste mês já estava completa.", type="info")
                montar(rotulo_escolhido)

            ui.button("\U0001F504 Gerar grade padrão deste mês", on_click=gerar_grade).props("outline").style(
                f"color:{TEAL_DARK}; font-weight:700;"
            )

            turmas = turmas_mod.listar_turmas_mes_admin(ano, mes)
            if not turmas:
                ui.label("Nenhuma turma neste mês ainda.").style(f"color:{TEXT_MUTED};")
                return

            def exportar(ano=ano, mes=mes, turmas=turmas):
                try:
                    from reports_pdf import gerar_pdf_escala
                    nome_mes = reports.MESES_PT[mes]
                    pdf_bytes = gerar_pdf_escala(ano, mes, nome_mes, turmas)
                    ui.download(pdf_bytes, f"escala-{reports.nome_arquivo_pdf(ano, mes)}.pdf")
                except Exception as e:
                    ui.notify(f"Não foi possível gerar o PDF: {e}", type="negative")

            ui.button("\U0001F4C4 Exportar escala em PDF", on_click=exportar).props("outline").style(
                f"color:{TEAL_DARK}; font-weight:700; margin-bottom:8px;"
            )

            _tabela_escala(turmas, lambda: montar(rotulo_escolhido))

    seletor = ui.select(rotulos, value=rotulos[idx_atual], label="Mês").style("max-width:220px;")
    seletor.on_value_change(lambda e: montar(e.value))
    montar(rotulos[idx_atual])


def _tabela_escala(turmas, on_done):
    instrutores = turmas_mod.listar_instrutores()
    nomes_instrutores = [i["nome"] for i in instrutores]
    ids_por_nome = {i["nome"]: i["id"] for i in instrutores}
    SEM_INSTRUTOR = "(sem instrutor)"
    pendentes = []  # (class_id, select) das linhas editáveis, pra alimentar o "Salvar tudo"

    def salvar_tudo():
        selecionadas = [(cid, sel) for cid, sel in pendentes if sel.value]
        if not selecionadas:
            ui.notify("Nenhuma linha com instrutor selecionado para salvar.", type="warning")
            return
        erros = 0
        for class_id, sel in selecionadas:
            try:
                turmas_mod.atribuir_instrutor_escala(class_id, ids_por_nome[sel.value])
            except TurmaError:
                erros += 1
        if erros:
            ui.notify(f"{len(selecionadas) - erros} linha(s) salva(s), {erros} com erro.", type="warning")
        else:
            ui.notify(f"{len(selecionadas)} linha(s) salva(s) com sucesso.", type="positive")
        on_done()

    if any(t["status"] == "agendada" for t in turmas):
        ui.button("\U0001F4BE Salvar tudo", on_click=salvar_tudo).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; margin-bottom:8px;"
        )

    with ui.column().classes("canoa-card").style("width:100%; gap:0; overflow-x:auto;"):
        headers = ["Data", "Horário", "Tipo", "Instrutor responsável", ""]
        larguras = ["100px", "90px", "90px", "260px", "110px"]
        min_total = "650px"
        with ui.row().style(f"border-bottom:2px solid {BORDER}; padding-bottom:8px; gap:0; width:100%; min-width:{min_total};"):
            for h, w in zip(headers, larguras):
                ui.label(h).style(f"width:{w}; flex-shrink:0; color:{TEXT_MUTED}; font-weight:700; font-size:11.5px;")

        for t in turmas:
            bloqueada = t["status"] != "agendada"
            with ui.row().style(
                f"padding:7px 0; gap:0; width:100%; min-width:{min_total}; align-items:center; border-bottom:1px solid #EEF1F3;"
            ):
                ui.label(str(t["data"])).style(f"width:{larguras[0]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(t["horario"]).style(f"width:{larguras[1]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")
                ui.label(t["tipo"].capitalize()).style(f"width:{larguras[2]}; flex-shrink:0; color:{TEXT}; font-size:12.5px;")

                with ui.row().style(f"width:{larguras[3]}; flex-shrink:0;"):
                    if bloqueada:
                        ui.label(t["instrutor_nome"] or SEM_INSTRUTOR).style(f"color:{TEXT_MUTED}; font-size:12.5px;")
                    else:
                        valor_atual = t["instrutor_nome"] if t["instrutor_nome"] in nomes_instrutores else None
                        sel = ui.select(nomes_instrutores, value=valor_atual).style("width:220px;")
                        pendentes.append((t["id"], sel))

                with ui.row().style(f"width:{larguras[4]}; flex-shrink:0;"):
                    if bloqueada:
                        badge(STATUS_ESCALA.get(t["status"], t["status"]), "muted")
                    else:
                        def salvar(class_id=t["id"], sel=sel):
                            if not sel.value:
                                ui.notify("Escolha um instrutor antes de salvar.", type="warning")
                                return
                            try:
                                turmas_mod.atribuir_instrutor_escala(class_id, ids_por_nome[sel.value])
                                ui.notify("Instrutor atribuído.", type="positive")
                                on_done()
                            except TurmaError as e:
                                ui.notify(str(e), type="negative")

                        ui.button("Salvar", on_click=salvar).props("flat dense").style(
                            f"color:{TEAL_DARK}; font-weight:700; font-size:12px;"
                        )


STATUS_ESCALA = {
    "confirmada": "Confirmada",
    "suspensa_clima": "Suspensa (Clima)",
    "suspensa_quorum": "Suspensa (Quórum)",
}
