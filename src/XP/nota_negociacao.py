# ==========================================================
# PDF XP -> Excel IRPF Completo
# Autor: ChatGPT
# Entrada : Nota de negociação XP em PDF
# Saída   : IRPF_XP.xlsx
# ==========================================================

import pdfplumber
import pandas as pd
import re
from datetime import datetime

ARQUIVO_PDF = "2025-12-16.pdf"
ARQUIVO_XLSX = "IRPF_XP.xlsx"


# ==========================================================
# UTIL
# ==========================================================

# ----------------------------------------------------------
# Converte string com número no formato brasileiro para float
# ----------------------------------------------------------
def br_to_float(txt: str) ->  float:
    '''
    :param txt: string com número no formato brasileiro (ex: "1.234,56")
    :return: float correspondente (ex: 1234.56)

    Converte uma string com número no formato brasileiro para float. 
    Remove pontos como separadores de milhar e substitui a vírgula por ponto decimal. 
    Se a conversão falhar, retorna 0.0.
        Exemplo:
        >>> br_to_float("1.234,56")
        1234.56
        >>> br_to_float("100,00")
        100.0
        >>> br_to_float("0,99")
        0.99
        >>> br_to_float("abc")
        0.0
    '''
    txt = str(txt).strip()
    txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except:
        return 0.0

# ----------------------------------------------------------
# Extrai data de referência do texto da nota
# ----------------------------------------------------------
def extrair_data(texto: str) -> datetime.date:
    '''
    :param texto: Texto da nota de negociação
    :return: Data de referência ou None se não encontrada

    Extrai a data de referência do texto da nota.
    '''
    m = re.search(r"Data de Referência:\s*(\d{2}/\d{2}/\d{4})", texto)
    if m:
        return datetime.strptime(m.group(1), "%d/%m/%Y").date()
    return None


# ==========================================================
# EXTRAI OPERAÇÕES
# ==========================================================
def extrair_operacoes(pdf_file: str) -> pd.DataFrame:
    '''
    :param pdf_file: Caminho para o arquivo PDF da nota de negociação
    :return: DataFrame com as operações extraídas

    Extrai as operações de compra e venda do PDF da nota de negociação.
    Procura por linhas que começam com "1-BOVESPA" e extrai os seguintes campos:
        - Tipo (Compra/Venda)
        - Mercado
        - Ativo
        - Ticker
        - Quantidade
        - Preço
        - Valor Total
    Também extrai a data de referência da nota para cada operação.
    Retorna um DataFrame com todas as operações encontradas.
    Exemplo de linha a ser extraída:
    1-BOVESPA C VISTA PETROBRAS PETR4 PN 900 30,82 27.738,00 C
    Onde:
    - "C" indica compra (ou "V" para venda)
    - "VISTA" é o mercado
    - "PETROBRAS PETR4 PN" é o ativo
    - "900" é a quantidade
    - "30,82" é o preço
    - "27.738,00" é o valor total
    O ticker é identificado como a parte do ativo que corresponde ao formato de ticker (ex: "PETR4"). 
    A função retorna um DataFrame com colunas: Data, Tipo, Mercado, Ativo, Ticker, Quantidade, Preço, Total. 
    '''
    registros = []

    with pdfplumber.open(pdf_file) as pdf:

        for pagina in pdf.pages:

            texto = pagina.extract_text()
            if not texto:
                continue

            data_ref = extrair_data(texto)

            linhas = texto.split("\n")

            for linha in linhas:

                if linha.startswith("1-BOVESPA"):
                    linha = re.sub(r"\s+", " ", linha)
                    partes = linha.split()

                    # exemplo:
                    # 1-BOVESPA C VISTA PETROBRAS PETR4 PN 900 30,82 27.738,00 C

                    cv = partes[1]
                    mercado = partes[2]

                    valor_total = partes[-2]
                    preco = partes[-3]
                    quantidade = partes[-4]

                    ativo = " ".join(partes[3:-4])

                    ticker = None
                    for p in partes:
                        if re.match(r"[A-Z]{4}\d{1,2}F?$", p):
                            ticker = p
                            break

                    registros.append({
                        "Data": data_ref,
                        "Tipo": "Compra" if cv == "C" else "Venda",
                        "Mercado": mercado,
                        "Ativo": ativo,
                        "Ticker": ticker,
                        "Quantidade": br_to_float(quantidade),
                        "Preço": br_to_float(preco),
                        "Total": br_to_float(valor_total),
                    })

    return pd.DataFrame(registros)


# ==========================================================
# PREÇO MÉDIO
# ==========================================================
def calcular_preco_medio(df: pd.DataFrame) -> pd.DataFrame:
    '''
    :param df: DataFrame com as operações extraídas
    :return: DataFrame com as operações e colunas adicionais de preço médio, lucro e saldo
    Calcula o preço médio, lucro e saldo de quantidade para cada operação.
    Para cada operação, atualiza a carteira de acordo com o tipo (compra ou venda).
    Para compras, aumenta a quantidade e o custo total.
    Para vendas, calcula o lucro com base no preço médio e reduz a quantidade e o custo total.
    Retorna um DataFrame com as colunas originais mais:
        - Preço Médio: custo total dividido pela quantidade atualizada
        - Lucro: lucro da operação (0 para compras, valor positivo ou negativo para vendas)
        - Saldo Qtde: quantidade restante do ativo após a operação
    '''
    carteira = {}
    linhas = []

    for _, row in df.sort_values("Data").iterrows():

        ticker = row["Ticker"]
        qtd = row["Quantidade"]
        total = row["Total"]

        if ticker not in carteira:
            carteira[ticker] = {
                "qtd": 0,
                "custo": 0
            }

        pos = carteira[ticker]

        if row["Tipo"] == "Compra":
            pos["qtd"] += qtd
            pos["custo"] += total
            pm = pos["custo"] / pos["qtd"]
            lucro = 0
        else:
            pm = pos["custo"] / pos["qtd"] if pos["qtd"] else 0
            custo_saida = pm * qtd
            lucro = total - custo_saida
            pos["qtd"] -= qtd
            pos["custo"] -= custo_saida

        linhas.append({
            **row,
            "Preço Médio": round(pm, 4),
            "Lucro": round(lucro, 2),
            "Saldo Qtde": pos["qtd"]
        })

    return pd.DataFrame(linhas)


# ==========================================================
# RESUMO MENSAL IRPF
# ==========================================================
def resumo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    '''
    :param df: DataFrame com operações e preços médios
    :return: DataFrame com resumo mensal para IRPF

    Calcula o resumo mensal para fins de IRPF.
    Para cada mês, soma o total de vendas e o lucro.
    Aplica a isenção de IR para vendas até 20k por mês.
    Calcula o IR devido (15% sobre o lucro, se não isento).
    '''
    vendas = df[df["Tipo"] == "Venda"].copy()

    vendas["Mes"] = pd.to_datetime(vendas["Data"]).dt.to_period("M")

    resumo = vendas.groupby("Mes").agg({
        "Total": "sum",
        "Lucro": "sum"
    }).reset_index()

    resumo["Isenção Swing até 20k"] = resumo["Total"] <= 20000

    resumo["IR Devido (15%)"] = resumo.apply(
        lambda x: 0 if x["Isenção Swing até 20k"] else max(x["Lucro"], 0) * 0.15,
        axis=1
    )

    return resumo


# ==========================================================
# EXECUÇÃO
# ==========================================================
if __name__ == "__main__":
    df = extrair_operacoes(ARQUIVO_PDF)
    df2 = calcular_preco_medio(df)
    resumo = resumo_mensal(df2)

    with pd.ExcelWriter(ARQUIVO_XLSX, engine="openpyxl") as writer:
        df2.to_excel(writer, sheet_name="Operacoes", index=False)
        resumo.to_excel(writer, sheet_name="IRPF_Mensal", index=False)
        carteira = df2.groupby("Ticker").tail(1)[
            ["Ticker", "Saldo Qtde", "Preço Médio"]
        ]
        carteira.to_excel(writer, sheet_name="Carteira Final", index=False)

    print("Arquivo gerado:", ARQUIVO_XLSX)