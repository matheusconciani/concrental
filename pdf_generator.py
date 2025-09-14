
from fpdf import FPDF
from datetime import datetime
import pandas as pd

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'ConcRental - Contrato de Locação de Equipamentos', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def create_contract_pdf(data):
    """Gera um arquivo PDF de contrato com base nos dados fornecidos."""
    
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    
    effective_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "CONTRATO DE LOCAÇÃO DE BENS MÓVEIS", 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "PARTES CONTRATANTES", 0, 1)
    pdf.set_font('Arial', '', 12)
    
    pdf.multi_cell(effective_width, 5, f"LOCADORA: ConcRental, doravante denominada simplesmente LOCADORA.")
    pdf.multi_cell(effective_width, 5, f"LOCATÁRIO(A): {data['full_name']}, portador(a) do telefone {data['phone_number']}, residente no endereço {data['address']}, doravante denominado(a) simplesmente LOCATÁRIO(A).")
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "CLÁUSULA PRIMEIRA - DO OBJETO DA LOCAÇÃO", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(effective_width, 5, "O presente contrato tem como objeto a locação do(s) seguinte(s) equipamento(s):")
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"- Equipamento: {data['name']} (S/N: {data['serial_number']})", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "CLÁUSULA SEGUNDA - DO PRAZO", 0, 1)
    pdf.set_font('Arial', '', 12)
    start_date_str = pd.to_datetime(data['start_date']).strftime('%d/%m/%Y')
    end_date_str = pd.to_datetime(data['end_date']).strftime('%d/%m/%Y')
    pdf.multi_cell(effective_width, 5, f"A locação do equipamento terá início em {start_date_str} e término em {end_date_str}.")
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "CLÁUSULA TERCEIRA - DO VALOR E FORMA DE PAGAMENTO", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(effective_width, 5, f"O valor total da locação é de R$ {data['valor']:.2f}. O status atual do pagamento é: {data['payment_status']}.")
    pdf.ln(20)

    pdf.cell(0, 10, "__________________________________________________", 0, 1, 'C')
    pdf.cell(0, 5, "LOCADORA", 0, 1, 'C')
    pdf.ln(20)
    pdf.cell(0, 10, "__________________________________________________", 0, 1, 'C')
    pdf.cell(0, 5, f"{data['full_name']}", 0, 1, 'C')
    pdf.cell(0, 5, "LOCATÁRIO(A)", 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font('Arial', 'I', 10)
    today_str = datetime.now().strftime("%d de %B de %Y")
    pdf.cell(0, 10, f"Gerado em {today_str}", 0, 1, 'C')

    # A saída com dest='S' é um bytearray, que convertemos para bytes.
    return bytes(pdf.output(dest='S'))
