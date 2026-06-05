# Projeto exames — LACS PDF extractor

## Ambiente Python

Usar sempre `.venv\Scripts\python.exe` (nunca `python` — o Windows intercepta com stub da Store).

Rodar testes: `.venv\Scripts\pytest.exe test_formato_string.py -q`

## Nomes de arquivo acentuados (ex: JOSÉ)

Arquivos com acentos no nome causam `OSError: Invalid argument` se passados diretamente no Windows.
Resolver via `glob.glob()` — o helper `_glob_one()` já existe em `test_formato_string.py`.

## Sentinela de arquivo não reconhecido

`build_string()` retorna `"Lab None"` quando nenhum campo é extraído (data ausente).
`app.py` usa `result.startswith("Lab None")` para detectar esse caso e exibir o aviso.
Se `_assemble()` ou o formato de saída mudar, atualizar essa verificação em `app.py`.

## Saída Unicode

Scripts que imprimem texto extraído de PDFs (µ, γ, etc.) exigem:

```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

Adicionar no topo de qualquer script diagnóstico avulso.

## Estrutura do app Streamlit (app.py)

Três páginas navegadas via `st.session_state.page`:

| Página | Descrição |
| ------ | --------- |
| `home` | 3 botões: Extrair / Solicitar / Receita |
| `extrator` | Upload de PDF de laudo LACS → extrai string de exames |
| `solicitar` | Formulário de solicitação de exames com checkboxes; gera PDF SUS e Particular |
| `receita` | Emite receituário SMS A4 (1 ou 2 vias, paisagem) |
| `solicitar_config` | Configura bookmarklet VIDA para importar dados do paciente |

## Receituário — fill_pdf_overlay.py

- Usa PyMuPDF (`fitz`) para overlay direto no PDF base `Receituario_SMS_A4_v3.pdf`
- PDF base deve estar na mesma pasta do script (`PDF_BASE = Path(__file__).parent / "..."`)
- Funções públicas: `gerar_receita_paisagem(conteudo, caminho_out, vias=1|2)` e `gerar_exames(caminho_out)`
- Globals que devem ser definidos antes de chamar: `NOME`, `DATA`, `EXAMES`
- `app.py` usa wrappers `_gerar_receita_bytes` / `_gerar_exames_particular_bytes` com arquivo temporário para obter bytes (PyMuPDF salva em arquivo, não em buffer direto)
- Cache: `@st.cache_data` em `_cached_receita` e `_cached_exames_particular`

## Receituário — limites de conteúdo

- Máximo 24 linhas de medicação (`_MAX_MEDS_LINES`)
- Máximo 80 caracteres por linha (`_MAX_MEDS_CHARS`)
- Validação em `_validate_meds()` — se houver erros, botões de download ficam desabilitados
- Contador em tempo real exibido abaixo do `text_area` (fica vermelho ao ultrapassar)
- Limpar usa padrão de contador de key (`rec_nome_count`, `rec_meds_count`) — nunca modificar `session_state` de widget já renderizado

## Exames especiais (Carga Viral HIV / CD4+)

- Definidos em `EXAMES_ESPECIAIS` — fora da lista `EXAMES`
- Sempre desmarcados ao entrar na página e ao clicar qualquer botão de preset
- **Incluídos somente no PDF Particular** — nunca no PDF SUS
- Inicializados no bloco `solicitar_initialized` (não usar `value=` nos widgets — ver regra global de Streamlit)

## Dependências adicionais (.venv)

- `pymupdf` — necessário para `fill_pdf_overlay.py`
