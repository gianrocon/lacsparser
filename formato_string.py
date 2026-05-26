"""
Extrai resultados de exames de um PDF do LACS (Salvador) e retorna
uma única string compacta no formato clínico.

Uso:
    python formato_string.py <caminho_pdf>

Saída esperada (Carlos Victor):
    Lab 29/10/24 hb=13,3 Leuco=2770 Plq=132mil glic=78 ...
"""

import re
import sys
from pathlib import Path

import pdfplumber


# ─── Extração de texto ────────────────────────────────────────────────────────

def extract_text(pdf_path: Path) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n".join(pages)


# ─── Helpers ──────────────────────────────────────────────────────────────────

FLAGS = re.IGNORECASE | re.DOTALL


def get(text: str, pattern: str, group: int = 1) -> str | None:
    m = re.search(pattern, text, FLAGS)
    return m.group(group).strip() if m else None


def fmt_date(val: str | None) -> str | None:
    """'29/10/2024' → '29/10/24'"""
    if val and re.match(r"\d{2}/\d{2}/\d{4}", val):
        return val[:6] + val[8:]
    return val


def fmt_plq(val: str | None) -> str | None:
    """'132.000' → '132mil'"""
    if not val:
        return None
    num = int(val.replace(".", "").replace(",", ""))
    return f"{num // 1000}mil"


def fmt_num(val: str | None) -> str | None:
    """Remove zeros decimais desnecessários: '2,00' → '2', '259,0' → '259'"""
    if not val:
        return None
    if re.match(r"^\d+[,\.][0]+$", val):
        return val.split(",")[0].split(".")[0]
    return val


def fmt_sor(val: str | None) -> str | None:
    """Normaliza resultado sorológico qualitativo."""
    if not val:
        return None
    v = val.strip()
    if re.match(r"n[aã]o\s+reagente", v, re.I):
        return "Não_Reagente"
    if re.match(r"reagente", v, re.I):
        return "Reagente"
    return v.replace(" ", "_")


def qualitativo_de_secao(text: str, section_re: str) -> str | None:
    """Captura resultado qualitativo dentro de uma seção sorológica (formato padrão)."""
    pat = (
        section_re
        + r".{0,900}?"
        + r"(?:Qualitativo|RESULTADO|Resultado)\s+((?:N[AÃ]O\s+)?Reagente)"
    )
    return fmt_sor(get(text, pat))


def urina_dipstick(val: str | None) -> str:
    """Converte resultado dipstick para notação compacta."""
    if not val:
        return "?"
    if re.match(r"negativo|ausente|n[aã]o\s+encontrado|\-", val, re.I):
        return "-"
    if re.match(r"positivo|presente|\+", val, re.I):
        return "+"
    return val


def dipstick_concat(label: str, raw: str) -> str:
    """'proteínas' + 'Ausente' → 'proteínas-'  |  'hemoglobina' + 'Traços' → 'hemoglobina=Traços'"""
    s = urina_dipstick(raw)
    return f"{label}{s}" if s in ("-", "+") else f"{label}={s}"


def extract_parasito(text: str) -> str | None:
    """Extrai resultado do Parasitológico (formato padrão)."""
    blocos = re.split(r"(?=PARASITOL[OÓ]GICO)", text, flags=FLAGS)
    blocos = [b for b in blocos if re.match(r"PARASITOL[OÓ]GICO", b, re.I)]
    if not blocos:
        return None

    achados: list[str] = []
    tem_negativo = False

    for bloco in blocos:
        m = re.search(
            r"RESULTADO\s+(.+?)(?=\nAssinado|\nCRF|\nEste laudo|\nFarmac|\Z)",
            bloco, FLAGS
        )
        if not m:
            continue
        raw = m.group(1).strip()

        if re.search(r"N[AÃ]O FORAM", raw, re.I):
            tem_negativo = True
            continue

        for linha in raw.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            if re.match(r"^\d{2}/\d{2}/\d{4}|^CRF|^Este|^As amostras|^NOTA", linha, re.I):
                continue
            if linha.isupper():
                linha = linha.capitalize()
            achados.append(linha)

    if not achados:
        return "Negativo" if tem_negativo else None

    seen: set[str] = set()
    unicos: list[str] = []
    for a in achados:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            unicos.append(a)

    return ", ".join(unicos)


def _extract_parasito_7xxx(text: str) -> str | None:
    """Extrai resultado do Parasitológico (formato 7-xxx)."""
    blocos = re.split(r"(?=PARASITOL[OÓ]GICO)", text, flags=FLAGS)
    blocos = [b for b in blocos if re.match(r"PARASITOL[OÓ]GICO", b, re.I)]
    if not blocos:
        return None
    for bloco in blocos:
        if re.search(r"N[aã]o foram visualizados", bloco):
            return "Negativo"
    return None


# ─── Montagem da string de saída ──────────────────────────────────────────────

def _assemble(f: dict) -> str:
    """Monta a string clínica a partir de um dict de campos extraídos."""
    def add(parts: list, label: str, val) -> None:
        if val is not None:
            parts.append(f"{label}={val}")

    urina_parts = []
    if f.get("prot_raw") is not None:
        urina_parts.append(dipstick_concat("proteínas", f["prot_raw"]))
    if f.get("hemo_raw") is not None:
        urina_parts.append(dipstick_concat("hemoglobina", f["hemo_raw"]))
    if f.get("hem_urina") is not None:
        urina_parts.append(f"Hemácias={f['hem_urina']}")
    urina_str = f"({' '.join(urina_parts)})" if urina_parts else None

    parts = [f"Lab {f['data']}"]
    add(parts, "hb",             f.get("hb"))
    add(parts, "Leuco",          f.get("leuco"))
    add(parts, "Plq",            f.get("plq"))
    add(parts, "glic",           f.get("glic"))
    add(parts, "ct",             f.get("ct"))
    add(parts, "HDL",            f.get("hdl"))
    add(parts, "LDL",            f.get("ldl"))
    add(parts, "TGC",            f.get("tgc"))
    add(parts, "cr",             f.get("cr"))
    add(parts, "ur",             f.get("ur"))
    add(parts, "tgo",            f.get("tgo"))
    add(parts, "tgp",            f.get("tgp"))
    add(parts, "ggt",            f.get("ggt"))
    add(parts, "pt",             f.get("pt"))
    add(parts, "alb",            f.get("alb"))
    add(parts, "glob",           f.get("glob"))
    add(parts, "bt",             f.get("bt"))
    add(parts, "bd",             f.get("bd"))
    add(parts, "bi",             f.get("bi"))
    add(parts, "fa",             f.get("fa"))
    add(parts, "Na",             f.get("na"))
    add(parts, "K",              f.get("k"))
    add(parts, "Mg",             f.get("mg_val"))
    add(parts, "TSH",            f.get("tsh"))
    add(parts, "T4L",            f.get("t4l"))
    add(parts, "T4",             f.get("t4"))
    add(parts, "T3",             f.get("t3"))
    add(parts, "Aghbs",          f.get("aghbs"))
    add(parts, "Antihbc",        f.get("antihbc"))
    add(parts, "Antihbs",        f.get("antihbs"))
    add(parts, "HCV",            f.get("hcv"))
    add(parts, "Antitrepo",      f.get("antitrepo"))
    add(parts, "VDRL",           f.get("vdrl"))
    add(parts, "VitD",           f.get("vitd"))
    add(parts, "HTLV",           f.get("htlv"))
    add(parts, "HVAIGG",         f.get("hvaigg"))
    add(parts, "B12",            f.get("b12"))
    add(parts, "HerpesIGG",      f.get("herpes_igg"))
    if urina_str:
        parts.append(f"Urina={urina_str}")
    add(parts, "Parasitológico", f.get("parasito"))

    return " ".join(parts)


# ─── Extrator — formato padrão (2402xxx / 2502xxx) ───────────────────────────

def _extract_standard(text: str) -> dict:
    data = fmt_date(get(text, r"Data do Cadastro:\s*(\d{2}/\d{2}/\d{4})"))

    hb    = get(text, r"hemoglobina\s+(\d+[,\.]\d+)\s+g/dL")
    leuco = get(text, r"leucócitos\s+\d+\s*%\s*(\d+)\s*/mm3")
    plq   = fmt_plq(get(text, r"PLAQUETAS\s+([\d.]+)/mm3"))

    glic = get(text, r"GLICEMIA.{0,300}?RESULTADO\s+(\d+)\s+mg/dL")
    ct   = get(text, r"COLESTEROL TOTAL.{0,300}?[Rr]esultado\s+(\d+)\s+mg/dL")
    hdl  = get(text, r"COLESTEROL\s*[-–]\s*HDL.{0,300}?RESULTADO\s+(\d+)\s+mg/dL")
    ldl  = get(text, r"COLESTEROL\s*[-–]\s*LDL.{0,300}?RESULTADO\s+(\d+)\s+mg/dL")
    tgc  = get(text, r"TRIGLICERIDES.{0,300}?RESULTADO\s+(\d+)\s+mg/dL")

    cr  = get(text, r"CREATININA.{0,300}?[Rr]esultado\s+(\d+[,\.]\d+)\s+mg/")
    ur  = get(text, r"\bUREIA\b.{0,300}?RESULTADO\s+(\d+)\s+mg/dL")
    tgo = get(text, r"TGO\s*/\s*AST.{0,300}?RESULTADO\s+(\d+)\s+U/L")
    tgp = get(text, r"TGP\s*/\s*ALT.{0,300}?RESULTADO\s+(\d+)\s+U/L")
    ggt = get(text, r"GAMA.GLUTAMIL.{0,400}?RESULTADO\s+(\d+)\s+U/L")
    fa  = get(text, r"FOSFATASE ALCALINA.{0,400}?RESULTADO\s+(\d+)\s+U/L")

    pt   = get(text, r"PROTEINA TOTAL\s+(\d+[,\.]\d+)\s+g/dL")
    alb  = get(text, r"ALBUMINA\s+(\d+[,\.]\d+)\s+g/dL")
    glob = get(text, r"GLOBULINA\s+(\d+[,\.]\d+)\s+g/dL")
    bt   = get(text, r"BILIRRUBINA TOTAL\s+(\d+[,\.]\d+)\s+mg/dL")
    bd   = get(text, r"BILIRRUBINA DIRETA\s+(\d+[,\.]\d+)\s+mg/dL")
    bi   = get(text, r"BILIRRUBINA INDIRETA\s+(\d+[,\.]\d+)\s+mg/dL")

    na     = get(text, r"SÓDIO.{0,300}?RESULTADO\s+(\d+)\s+mEq/L")
    k      = get(text, r"POTÁSSIO.{0,300}?RESULTADO\s+(\d+[,\.]\d+)\s+mmol/L")
    mg_val = fmt_num(get(text, r"MAGNESIO.{0,300}?RESULTADO\s+(\d+[,\.]\d+)\s+mg/dL"))

    tsh = get(text, r"TSH.{0,500}?[Rr]esultado\s+(\d+[,\.]\d+)\s+[uµ]UI/mL")
    t4l = get(text, r"T4 LIVRE.{0,300}?[Rr]esultado\s+(\d+[,\.]\d+)\s+ng/")
    t4  = get(text, r"DOSAGEM DE T4.{0,300}?[Rr]esultado\s+(\d+[,\.]\d+)\s+[uµ]g/dL")
    t3  = get(text, r"DOSAGEM DE T3.{0,300}?[Rr]esultado\s+(\d+[,\.]\d+)\s+ng/mL")

    vitd = get(text, r"(?:HIDROXI VITAMINA D3|CALCIDIOL).{0,400}?RESULTADO\s+([\d,]+)\s+ng/mL")
    b12  = fmt_num(get(text, r"VITAMINA B12\s+([\d,]+)\s+pg/mL"))

    aghbs   = qualitativo_de_secao(text, r"HEPATITE HBS-AG")
    antihbc = qualitativo_de_secao(text, r"HEPATITE ANTI HBC TOTAL")

    antihbs_raw = get(text, r"HEPATITE ANTI HBS.{0,600}?LEITURA\s+(>?\d+)\s+mUI")
    if antihbs_raw:
        antihbs = antihbs_raw if antihbs_raw.startswith(">") else f">{antihbs_raw}"
    else:
        antihbs = qualitativo_de_secao(text, r"HEPATITE ANTI HBS")

    hcv       = qualitativo_de_secao(text, r"HEPATITE C")
    antitrepo = qualitativo_de_secao(text, r"ANTICORPO ANTI TREPONEMA")

    vdrl = get(text, r"VDRL.{0,600}?TITULA[CÇ][AÃ]O\s+([\d/]+)")
    if not vdrl:
        vdrl = qualitativo_de_secao(text, r"VDRL")

    htlv      = qualitativo_de_secao(text, r"HTLV")
    hvaigg    = qualitativo_de_secao(text, r"HEPATITE A ANTICORPOS IGG")
    herpes_igg = fmt_sor(get(text, r"HERPES\s*-\s*IGG\s+II\s+((?:N[AÃ]O\s+)?Reagente)"))

    prot_raw  = get(text, r"URINA.{0,2000}?Proteínas\s+(Negativo|Ausente|Positivo|Traços|\+|\-)")
    hemo_raw  = get(text, r"URINA.{0,2000}?Hemoglobina\s+(Negativo|Ausente|Positivo|Traços|\+|\-)")
    hem_urina = get(text, r"URINA.{0,2000}?Hemácias\s+(\d+)\s+/mL")

    parasito = extract_parasito(text)

    return dict(
        data=data, hb=hb, leuco=leuco, plq=plq,
        glic=glic, ct=ct, hdl=hdl, ldl=ldl, tgc=tgc,
        cr=cr, ur=ur, tgo=tgo, tgp=tgp, ggt=ggt, fa=fa,
        pt=pt, alb=alb, glob=glob, bt=bt, bd=bd, bi=bi,
        na=na, k=k, mg_val=mg_val,
        tsh=tsh, t4l=t4l, t4=t4, t3=t3,
        vitd=vitd, b12=b12,
        aghbs=aghbs, antihbc=antihbc, antihbs=antihbs,
        hcv=hcv, antitrepo=antitrepo, vdrl=vdrl,
        htlv=htlv, hvaigg=hvaigg, herpes_igg=herpes_igg,
        prot_raw=prot_raw, hemo_raw=hemo_raw, hem_urina=hem_urina,
        parasito=parasito,
    )


# ─── Extrator — formato 7-xxx (2025-atual) ────────────────────────────────────

def _extract_7xxx(text: str) -> dict:
    def sor(section_re: str) -> str | None:
        pat = section_re + r".{0,900}?Resultado:\s*((?:N[AÃ]O\s+)?REAGENTE)"
        return fmt_sor(get(text, pat))

    # Primeira data de coleta no documento
    data = fmt_date(get(text, r"Data da coleta\s*:\s*(\d{2}/\d{2}/\d{4})"))

    # Hemograma — valores separados por pontos, contagem usa '.' como milhar
    hb        = get(text, r"Hemoglobina\.+:\s*(\d+[,\.]\d+)\s+g/dL")
    leuco_raw = get(text, r"Leucócitos\.+:\s*([\d.]+)\s+/mm")
    leuco     = leuco_raw.replace(".", "") if leuco_raw else None
    plq_raw   = get(text, r"Plaquetas\.+:\s*([\d.]+)\s+mil/mm")
    plq       = fmt_plq(plq_raw) if plq_raw else None

    # Bioquímica
    glic = get(text, r"GLICOSE.{0,300}?Resultado:\s*(\d+)\s+mg/dL")
    ct   = fmt_num(get(text, r"COLESTEROL TOTAL\s*:\s*([\d,]+)\s+mg/dL"))
    hdl  = fmt_num(get(text, r"COLESTEROL HDL\s*:\s*([\d,]+)\s+mg/dL"))
    ldl  = fmt_num(get(text, r"COLESTEROL LDL\s*:\s*([\d,]+)\s+mg/dL"))
    tgc  = fmt_num(get(text, r"TRIGLICÉRIDES\s*:\s*([\d,]+)\s+mg/d[Ll]"))
    cr   = get(text, r"CREATININA.{0,300}?Resultado:\s*(\d+[,\.]\d+)\s+mg/dL")
    ur   = get(text, r"\bUREIA\b.{0,300}?Resultado:\s*(\d+)\s+mg/dL")
    tgo  = get(text, r"TGO/AST.{0,300}?Resultado:\s*(\d+)\s+U/L")
    tgp  = get(text, r"TGP/ALT.{0,300}?Resultado:\s*(\d+)\s+U/L")
    ggt  = get(text, r"GAMA GLUTAMIL.{0,300}?Resultado:\s*(\d+)\s+U/L")
    fa   = get(text, r"FOSFATASE ALCALINA.{0,400}?Resultado:\s*(\d+)\s+U/L")

    # Proteínas totais e frações
    pt   = get(text, r"Proteínas totais:\s*(\d+[,\.]\d+)\s+g/dL")
    alb  = get(text, r"PROTEÍNAS TOTAIS.{0,300}?Albumina\s*:\s*(\d+[,\.]\d+)\s+g/dL")
    glob = get(text, r"PROTEÍNAS TOTAIS.{0,300}?Globulina\s*:\s*(\d+[,\.]\d+)\s+g/dL")

    # Bilirrubinas
    bt = get(text, r"Bilirrubina total\s*:\s*(\d+[,\.]\d+)\s+mg/dL")
    bd = get(text, r"Bilirrubina direta\s*:\s*(\d+[,\.]\d+)\s+mg/dL")
    bi = get(text, r"Bilirrubina indireta:\s*(\d+[,\.]\d+)\s+mg/dL")

    # Eletrólitos
    na     = get(text, r"SÓDIO.{0,300}?Resultado:\s*(\d+)\s+mEq")
    k      = get(text, r"POTÁSSIO.{0,300}?Resultado:\s*(\d+[,\.]\d+)\s+mmol")
    mg_val = fmt_num(get(text, r"MAGNESIO.{0,300}?Resultado:\s*(\d+[,\.]\d+)\s+mg/dL"))

    # Tireoide
    tsh = get(text, r"TSH.{0,300}?Resultado:\s*(\d+[,\.]\d+)\s+[µμu]UI/mL")
    t4l = get(text, r"T4 LIVRE.{0,300}?Resultado:\s*(\d+[,\.]\d+)\s+ng/")
    t4  = None
    t3  = None

    # Vitaminas
    vitd = get(text, r"VITAMINA D.{0,300}?Resultado:\s*([\d,]+)\s+ng/mL")
    b12  = fmt_num(get(text, r"VITAMINA B12.{0,300}?Resultado:\s*([\d,]+)\s+pg/mL"))

    # Sorologias
    aghbs   = sor(r"HEPATITE B - HBSAg")
    antihbc = sor(r"HEPATITE B - ANTI HBC TOTAL")

    # Anti-HBs: titar pelo Índice quando reagente
    antihbs_idx = get(text, r"HEPATITE B - ANTI HBS.{0,400}?[IÍ]ndice:\s*([\d,]+)\s+mUI")
    antihbs_res = sor(r"HEPATITE B - ANTI HBS")
    if antihbs_idx and antihbs_res == "Reagente":
        antihbs = antihbs_idx
    else:
        antihbs = antihbs_res

    hcv       = sor(r"HEPATITE C - ANTI HCV")
    antitrepo = sor(r"SOROLOGIA PARA S[IÍ]FILIS")

    # VDRL: captura titulação se reagente, senão qualitativo
    vdrl = get(text, r"VDRL.{0,300}?Resultado:\s*REAGENTE\s+([\d/]+)")
    if not vdrl:
        vdrl = fmt_sor(get(text, r"VDRL.{0,300}?Resultado:\s*((?:N[AÃ]O\s+)?REAGENTE)"))

    htlv   = sor(r"HTLV I/II")
    hvaigg = sor(r"HEPATITE A - ANTI-HVA IgG")

    # Herpes IgG — formato inline com pontos no 7-xxx
    herpes_igg = fmt_sor(get(text, r"HERPES.{0,50}IgG\.+:\s*((?:N[AÃ]O\s+)?Reagente)"))

    # Urina — labels com pontos no dipstick; hemácias na linha seguinte
    prot_raw  = get(text, r"Proteínas\.{5,}:\s*(Ausente|Negativo|Positivo|Presente|Traços?|Tra[çc]o|\+)")
    hemo_raw  = get(text, r"Hemoglobina\.{5,}:\s*(Ausente|Negativo|Positivo|Presente|Traços?|Tra[çc]o|\+)")
    hem_urina = get(text, r"Hemácias\.{5,}:[^\n]+\n\s*(\d+)\s+/mL")

    parasito = _extract_parasito_7xxx(text)

    return dict(
        data=data, hb=hb, leuco=leuco, plq=plq,
        glic=glic, ct=ct, hdl=hdl, ldl=ldl, tgc=tgc,
        cr=cr, ur=ur, tgo=tgo, tgp=tgp, ggt=ggt, fa=fa,
        pt=pt, alb=alb, glob=glob, bt=bt, bd=bd, bi=bi,
        na=na, k=k, mg_val=mg_val,
        tsh=tsh, t4l=t4l, t4=t4, t3=t3,
        vitd=vitd, b12=b12,
        aghbs=aghbs, antihbc=antihbc, antihbs=antihbs,
        hcv=hcv, antitrepo=antitrepo, vdrl=vdrl,
        htlv=htlv, hvaigg=hvaigg, herpes_igg=herpes_igg,
        prot_raw=prot_raw, hemo_raw=hemo_raw, hem_urina=hem_urina,
        parasito=parasito,
    )


# ─── Ponto de entrada público ─────────────────────────────────────────────────

def build_string(pdf_path: Path) -> str:
    text = extract_text(pdf_path)
    if re.search(r"Data da coleta\s*:", text):
        fields = _extract_7xxx(text)
    else:
        fields = _extract_standard(text)
    return _assemble(fields)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python formato_string.py <caminho_pdf>", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Arquivo não encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(build_string(pdf_path))


if __name__ == "__main__":
    main()
