# -*- coding: utf-8 -*-
"""
Exportação do relatório mensal de aulas em PDF.

Isolado neste módulo porque depende da biblioteca fpdf2, que não foi
possível testar de ponta a ponta no ambiente de desenvolvimento (sem
acesso à internet para instalar). O botão de exportar no
Configurações > Relatórios está com tratamento de erro para não
derrubar a tela caso algo aqui precise de ajuste fino em produção.
"""
from theme import reais
from reports import STATUS_LABEL


def gerar_pdf_relatorio(ano, mes, nome_mes, linhas, resumo):
    from fpdf import FPDF

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Relatorio de aulas - {nome_mes}/{ano}", ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Kalani Vaa Team", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # ---- Tabela 1: uma linha por aula/instrutor ----
    pdf.set_font("Helvetica", "B", 10)
    headers = ["Instrutor", "Data", "Horario", "Vagas", "Presentes", "Faltosos", "Status", "Repasse"]
    larguras = [45, 25, 20, 18, 22, 20, 45, 25]

    def cabecalho():
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 235, 225)
        for w, h in zip(larguras, headers):
            pdf.cell(w, 8, h, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)

    cabecalho()
    for l in linhas:
        valores = [
            l["instrutor"], l["data"], l["horario"], str(l["vagas_ocupadas"]),
            str(l["presentes"]), str(l["faltosos"]), l["status"], reais(l["repasse_centavos"]),
        ]
        if pdf.get_y() > 190:  # quebra de página manual antes de estourar o rodapé
            pdf.add_page()
            cabecalho()
        for w, v in zip(larguras, valores):
            pdf.cell(w, 7, _limpar(v), border=1)
        pdf.ln()

    pdf.ln(8)

    # ---- Tabela 2: resumo por instrutor ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Resumo por instrutor (valor a pagar no mes)", ln=1)
    pdf.ln(1)

    headers2 = ["Instrutor", "Alunos atendidos", "Aulas ministradas", "Total do repasse"]
    larguras2 = [70, 45, 45, 45]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 235, 225)
    for w, h in zip(larguras2, headers2):
        pdf.cell(w, 8, h, border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for r in resumo:
        valores2 = [r["instrutor"], str(r["alunos"]), str(r["aulas"]), reais(r["total_centavos"])]
        for w, v in zip(larguras2, valores2):
            pdf.cell(w, 7, _limpar(v), border=1)
        pdf.ln()

    saida = pdf.output()
    if isinstance(saida, (bytes, bytearray)):
        return bytes(saida)
    return saida.encode("latin-1")  # versões mais antigas do fpdf devolvem str


def _limpar(texto):
    """Garante compatibilidade com a codificação latin-1 usada pelas fontes padrão do PDF."""
    return str(texto).encode("latin-1", errors="replace").decode("latin-1")
