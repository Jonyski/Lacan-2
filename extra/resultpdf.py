from pathlib import Path
from typing import Any, Dict

from fpdf import FPDF


class ClinicalPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Relatório Clínico da IA", border=False, align="R")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")


def check_space(pdf, height_needed):
    """
    Verifica se há espaço suficiente na página. Se não, cria nova página.
    """
    # Altura da página - Margem Inferior - Posição Atual
    if pdf.get_y() + height_needed > (pdf.h - 20):
        pdf.add_page()


def create_clinical_pdf(data: Dict[str, Any], original_filename: str, output_dir: Path):
    """
    Gera um PDF formatado com os dados da análise clínica.
    """
    pdf = ClinicalPDF()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # TÍTULO E METADADOS
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Análise: {original_filename}", ln=True, align="L")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0,
        10,
        "Este documento foi gerado automaticamente e requer revisão humana.",
        ln=True,
    )
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(10)

    # Dados extraídos
    risk = data.get("risk_assessment", {})
    risk_level = risk.get("level", "N/A").upper()

    # AVALIAÇÃO DE RISCO
    check_space(pdf, 30)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(40, 10, "Nível de Risco:", align="L")

    # Lógica de Cor: Vermelho para Alto/Médio, Verde para Baixo
    if risk_level == "ALTO":
        pdf.set_text_color(214, 56, 77)  # Vermelho
    elif risk_level == "MÉDIO":
        pdf.set_text_color(209, 205, 100)  # Amarelo
    else:
        pdf.set_text_color(85, 194, 118)  # Verde

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, risk_level, ln=True)

    # Volta para preto
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)

    if risk.get("signals"):
        signals_str = ", ".join(risk.get("signals"))
        pdf.multi_cell(0, 7, f"Sinais identificados: {signals_str}")
    pdf.ln(5)

    # ANÁLISE DISCURSIVA
    check_space(pdf, 20)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Análise Discursiva", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    analysis_text = data.get("analysis", "Nenhuma análise disponível.")
    pdf.multi_cell(0, 7, analysis_text)
    pdf.ln(5)

    # MAPA ESTRUTURAL
    check_space(pdf, 30)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Mapa Estrutural", ln=True)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 11)

    # Temas
    themes = ", ".join(data.get("themes", []))
    pdf.multi_cell(0, 7, "Temas Centrais: ", ln=True)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(pdf.epw, 7, themes)
    pdf.ln(2)

    # Significantes
    pdf.set_font("Helvetica", "", 11)
    signifiers = ", ".join(data.get("signifiers", []))
    pdf.multi_cell(0, 7, "Significantes: ", ln=True)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(pdf.epw, 7, signifiers)
    pdf.ln(2)

    # HIPÓTESES
    check_space(pdf, 20)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Hipóteses Clínicas")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 11)
    hypotheses = data.get("hypotheses", [])
    for h in hypotheses:
        pdf.multi_cell(180, 7, f"- {h}", align="L")
        pdf.ln(1)

    pdf.ln(2)

    # PERGUNTAS SUGERIDAS
    check_space(pdf, 20)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Perguntas sugeridas")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 11)
    questions = data.get("questions", [])
    for q in questions:
        pdf.multi_cell(180, 7, f"- {q}", align="L")
        pdf.ln(1)

    pdf.ln(5)

    # LAUDO CLÍNICO (SE NECESSÁRIO)
    report_data = data.get("clinical_report", {})

    if report_data.get("required"):
        check_space(pdf, 30)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(
            0,
            8,
            " LAUDO CLÍNICO DE ENCAMINHAMENTO / OBSERVAÇÃO",
            ln=True,
        )
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 11)
        summary_text = report_data.get("summary", "Sem resumo detalhado fornecido.")
        pdf.multi_cell(0, 7, summary_text)

    # SALVAMENTO
    # Garante que o diretório existe
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = original_filename.rsplit(".", 1)[0] + "_report.pdf"
    file_path = output_dir / safe_name

    pdf.output(str(file_path))
    return file_path
