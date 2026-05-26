# Projeto exames — LACS PDF extractor

## Ambiente Python

Usar sempre `.venv\Scripts\python.exe` (nunca `python` — o Windows intercepta com stub da Store).

Rodar testes: `.venv\Scripts\pytest.exe test_formato_string.py -q`

## Nomes de arquivo acentuados (ex: JOSÉ)

Arquivos com acentos no nome causam `OSError: Invalid argument` se passados diretamente no Windows.
Resolver via `glob.glob()` — o helper `_glob_one()` já existe em `test_formato_string.py`.

## Saída Unicode

Scripts que imprimem texto extraído de PDFs (µ, γ, etc.) exigem:
```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```
Adicionar no topo de qualquer script diagnóstico avulso.
