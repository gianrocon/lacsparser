# Parser de PDF de Exames - Salvador

Este projeto contém um script Python simples para extrair os dados do paciente e os resultados de exames de arquivos PDF do laboratório central do município de Salvador.

## Como usar

1. Crie e ative uma virtualenv Python:

```powershell
cd c:\Users\gian\Desktop\exames
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```powershell
pip install -r requirements.txt
```

3. Execute o parser em um PDF:

```powershell
python parse_salvador_pdf.py "exames-lacs\arquivo.pdf"
```

4. O script irá gerar um arquivo JSON no mesmo diretório do PDF com o mesmo nome base, por exemplo `arquivo.json`.

## Opções

- `-o` / `--output`: caminho opcional para o arquivo JSON de saída.

```powershell
python parse_salvador_pdf.py "exames-lacs\arquivo.pdf" -o "saida\resultado.json"
```

## Estrutura do JSON de saída

O JSON contém:

- `arquivo`: nome do arquivo PDF processado
- `paciente`: informações extraídas do cabeçalho
- `exames`: lista de pares `nome_exame` / `resultado`

## Observações

- O script usa `pdfplumber` para extrair texto do PDF.
- Se o PDF não contiver texto pesquisável, pode ser necessário um passo adicional com OCR.
- Ajustes nas expressões regulares podem ser necessários para diferentes formatos de relatório.
