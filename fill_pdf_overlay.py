"""
fill_pdf_overlay.py
Preenche o receituário SMS A4 via PyMuPDF (overlay direto no PDF original).

O PDF base não contém linhas de preenchimento — o texto é inserido diretamente
nas coordenadas calibradas. Duas funções públicas exportáveis:

    gerar_receita_paisagem(conteudo, caminho_out, vias=1|2)
    gerar_exames(caminho_out)

Antes de chamar, defina os globals NOME e DATA neste módulo:

    import fill_pdf_overlay as rec
    rec.NOME = "João da Silva"
    rec.DATA = "04/06/2026"

────────────────────────────────────────────────────────────────────────────────
EXEMPLOS DE USO (para integração por outra aplicação)
────────────────────────────────────────────────────────────────────────────────

# ── Receita simples (2 medicamentos, 2 vias) ─────────────────────────────────
#
#   import fill_pdf_overlay as rec
#   rec.NOME = "Maria da Silva Santos"
#   rec.DATA = "15/06/2026"
#   rec.gerar_receita_paisagem(
#       conteudo=[
#           "Losartano 50mg -------------------- contínuo",
#           "Uso: 01 cp, via oral, de 12/12 horas.",
#           "",
#           "Hidroclorotiazida 25mg -----------contínuo",
#           "Uso: 01 cp, via oral, de manhã.",
#       ],
#       caminho_out="receita.pdf",
#       vias=2,
#   )

# ── Receita longa (8 medicamentos, 1 via) ────────────────────────────────────
#
#   par = [
#       "Losartano 50mg -------------------- contínuo",
#       "Uso: 01 cp, via oral, de 12/12 horas.",
#       "",
#       "Hidroclorotiazida 25mg -----------contínuo",
#       "Uso: 01 cp, via oral, de manhã.",
#       "",
#   ]
#   rec.gerar_receita_paisagem(par * 4, "receita_8itens_1via.pdf", vias=1)

# ── Solicitação de exames — lista completa (A4 retrato) ──────────────────────
#
#   rec.EXAMES = [
#       "HEMOGRAMA", "GLICEMIA JEJUM", "HbA1c",
#       "CREATININA", "URÉIA", "TGO", "TGP",
#       "COLESTEROL TOTAIS E FRAÇÕES", "TRIGLICÉRIDES",
#   ]
#   rec.gerar_exames("exames.pdf")   # cabeçalho: "SOLICITO (CID Z10):"

# ── Solicitação de exames — lista curta / 3 itens (A4 retrato) ───────────────
#
#   rec.EXAMES = ["HEMOGRAMA", "GLICEMIA JEJUM", "CREATININA"]
#   rec.gerar_exames("exames_3itens.pdf")   # cabeçalho: "SOLICITO (CID Z10):"

────────────────────────────────────────────────────────────────────────────────
REGRAS DE CONTEUDO
────────────────────────────────────────────────────────────────────────────────

  Receita  → lista de strings; linha vazia ("") cria espaço entre medicamentos.
             Cada medicamento ocupa normalmente 2 linhas: nome + posologia.
             Saída: sempre A4 paisagem (842×595 pt), 1 ou 2 vias lado a lado.

  Exames   → lista de strings, uma por exame.
             O cabeçalho "SOLICITO:" é inserido automaticamente.
             A lista é dividida em 2 colunas automaticamente.
             Saída: A4 retrato.

────────────────────────────────────────────────────────────────────────────────
"""

import fitz  # PyMuPDF
from pathlib import Path

PDF_BASE = Path(__file__).parent / "Receituario_SMS_A4_v3.pdf"

# ─── DADOS (alterar para cada paciente) ───────────────────────────────────────
NOME = "Maria da Silva Santos"   # exemplo de teste
DATA = "15/06/2026"              # formato dd/mm/yyyy

# ─── MODO: escolha 'receita' ou 'exames' ──────────────────────────────────────
MODO = "receita"
VIAS = 2          # receita: 1 = uma via (outra metade em branco) | 2 = duas vias

# ─── EXEMPLO: receita ─────────────────────────────────────────────────────────
CONTEUDO_RECEITA = [
    "Losartano 50mg -------------------- contínuo",
    "Uso: 01 cp, via oral, de 12/12 horas.",
    "",
    "Hidroclorotiazida 25mg -----------contínuo",
    "Uso: 01 cp, via oral, de manhã.",
]

# ─── EXEMPLO: solicitação de exames ───────────────────────────────────────────
EXAMES = [
    "HEMOGRAMA",
    "TGO",
    "TGP",
    "GGT",
    "PSA",
    "SOROL SÍFILIS",
    "VDRL",
    "Ácido Úrico",
    "AGHBS",
    "SUMÁRIO DE URINA",
    "Na+",
    "K+",
    "URÉIA",
    "CREATININA",
    "ANTI-HBC TOTAL",
    "ANTI-HBs",
    "ANTI-HVC",
    "ANTI-HVA IGG",
    "CMV IgM/IgG",
    "ANTI-HTLV 1/2",
    "BILIRRUBINAS TOTAIS E FRAÇÕES",
    "PROTEÍNAS TOTAIS E FRAÇÕES",
    "COLESTEROL TOTAIS E FRAÇÕES",
    "TRIGLICÉRIDES",
    "TOXOPLASMOSE IgM/IgG",
    "T3",
    "T4 LIVRE",
    "TSH",
    "FERRITINA",
    "P. DE FEZES",
    "GLICEMIA JEJUM",
    "HbA1c",
    "VITAMINA B 12",
    "MAGNÉSIO",
    "VITAMINA",
    "Anti-Chagas",
]

# ─── CONFIGURAÇÕES VISUAIS ────────────────────────────────────────────────────
FONT             = "helv"
FONT_SIZE        = round(10 * 1.3) - 1    # 12pt  — nome e data
FONT_SIZE_CONTEUDO = FONT_SIZE - 1        # 11pt  — conteúdo (receita / exames)
COLOR            = (0, 0, 0)

# ─── COORDENADAS — não alterar ────────────────────────────────────────────────
# Extraídas do PDF original (ArialMT 10pt, A4 595×842pt)
#   NOME:  x0=171.4  |  baseline y=178.0
#   DATA:  x0= 97.6  |  baseline y=196.5  (string única dd/mm/yyyy)
DX, DY = 2, -3                      # ajuste fino de posicionamento

X_NOME        = 171.4 + DX          # 173.4
BASELINE_NOME = 181.0 + DY          # 178.0

X_DATA        = 97.6 + DX           # 99.6
BASELINE_DATA = 199.5 + DY          # 196.5

X_CONTEUDO   = 62.7 + 10                        # 72.7  (10pt à direita da margem)
Y_CONTEUDO   = 198.8 + 20 + 15                 # 233.8 (35pt abaixo da linha DATA)
LINE_SPACING = round(FONT_SIZE_CONTEUDO * 1.4)  # 15pt para 11pt

# Colunas: margem esq=62.7, margem dir=62.7 → largura útil=469.6pt
X_COL1 = X_CONTEUDO
X_COL2 = X_CONTEUDO + 469.6 / 2    # ~307.5

# ─── FUNÇÕES ──────────────────────────────────────────────────────────────────
def txt(page, x, y, text):
    """Insere texto na posição (x, baseline y)."""
    page.insert_text((x, y), text, fontname=FONT, fontsize=FONT_SIZE, color=COLOR)

def inserir_receita(page, linhas):
    """Insere prescrição em coluna única."""
    for i, linha in enumerate(linhas):
        if linha:
            page.insert_text((X_CONTEUDO, Y_CONTEUDO + i * LINE_SPACING),
                             linha, fontname=FONT, fontsize=FONT_SIZE_CONTEUDO, color=COLOR)

def inserir_exames(page, exames):
    """Insere 'SOLICITO:' e lista de exames em 2 colunas."""
    page.insert_text((X_CONTEUDO, Y_CONTEUDO), "SOLICITO (CID Z10):",
                     fontname=FONT, fontsize=FONT_SIZE_CONTEUDO, color=COLOR)

    # Lista começa 30pt abaixo do "SOLICITO:"
    y_lista = Y_CONTEUDO + 30

    meio = len(exames) // 2 + len(exames) % 2  # arredonda para cima

    for i, item in enumerate(exames[:meio]):
        page.insert_text((X_COL1, y_lista + i * LINE_SPACING),
                         item, fontname=FONT, fontsize=FONT_SIZE_CONTEUDO, color=COLOR)

    for i, item in enumerate(exames[meio:]):
        page.insert_text((X_COL2, y_lista + i * LINE_SPACING),
                         item, fontname=FONT, fontsize=FONT_SIZE_CONTEUDO, color=COLOR)

# ─── GERAR PDF ────────────────────────────────────────────────────────────────
def gerar_pagina_receita(conteudo):
    """Monta a receita numa página A4 retrato em memória e retorna o doc fitz."""
    doc  = fitz.open(str(PDF_BASE))
    page = doc[0]
    txt(page, X_NOME, BASELINE_NOME, NOME)
    txt(page, X_DATA, BASELINE_DATA, DATA)
    inserir_receita(page, conteudo)
    return doc

def gerar_receita_paisagem(conteudo, caminho_out, vias=2):
    """
    Gera A4 paisagem com 1 ou 2 vias da receita.
    A4 portrait: 595×842 pt  →  landscape: 842×595 pt
    Cada via ocupa metade da largura (421 pt), escala ≈ 0.707.

    vias=1 → receita na metade esquerda, metade direita em branco.
    vias=2 → receita nas duas metades.
    """
    src = gerar_pagina_receita(conteudo)

    A4_L_W = 841.92
    A4_L_H = 595.32
    metade  = A4_L_W / 2

    out_doc  = fitz.open()
    page_out = out_doc.new_page(width=A4_L_W, height=A4_L_H)

    page_out.show_pdf_page(fitz.Rect(0, 0, metade, A4_L_H), src, 0)
    if vias == 2:
        page_out.show_pdf_page(fitz.Rect(metade, 0, A4_L_W, A4_L_H), src, 0)

    out_doc.save(caminho_out)
    print(f"Gerado [receita {vias} via(s) paisagem]: {caminho_out}")

def gerar_exames(caminho_out):
    """Gera solicitação de exames em A4 retrato."""
    doc  = fitz.open(str(PDF_BASE))
    page = doc[0]
    txt(page, X_NOME, BASELINE_NOME, NOME)
    txt(page, X_DATA, BASELINE_DATA, DATA)
    inserir_exames(page, EXAMES)
    doc.save(caminho_out)
    print(f"Gerado [exames A4 retrato]: {caminho_out}")

if __name__ == "__main__":
    OUT = r'C:\Users\gian\Desktop\Receituario_preenchido_PDF.pdf'

    if MODO == "receita":
        gerar_receita_paisagem(CONTEUDO_RECEITA, OUT, vias=VIAS)
    elif MODO == "exames":
        gerar_exames(OUT)
