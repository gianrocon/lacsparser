# LACS Parser — Extrator de Exames Salvador

Aplicativo Streamlit que extrai resultados de exames de PDFs do LACS Salvador e gera uma string clínica compacta para copiar e colar.

## Uso

Acesse o app, envie o PDF do laudo e copie a string gerada. Exemplo de saída:

```
Lab 29/10/24 hb=13,3 Leuco=2770 Plq=132mil glic=78 ct=102 HDL=28 LDL=63 TGC=54 cr=1,04 ur=25 tgo=24 tgp=14 ggt=17 fa=217 ...
```

Se o arquivo não corresponder ao formato LACS Salvador, o app exibe **"Nenhum exame reconhecido"**.

## Formatos suportados

| Formato | Identificação | Período |
|---|---|---|
| Padrão (`2402xxx` / `2502xxx`) | `Data do Cadastro:` | até 2024–2025 |
| Novo (`7-NNN-NOME.pdf`) | `Data da coleta :` | 2025–atual |

## Rodar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Deploy no Streamlit Cloud

1. Fork ou conecte este repositório no [Streamlit Cloud](https://streamlit.io/cloud)
2. Defina o arquivo principal como `app.py`
3. Clique em **Deploy** — as dependências são instaladas automaticamente via `requirements.txt`
