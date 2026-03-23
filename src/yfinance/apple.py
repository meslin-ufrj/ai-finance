import yfinance as yf
import matplotlib.pyplot as plt

# Cria objeto do ativo
acao = yf.Ticker("AAPL")

# Baixa dados históricos
dados = acao.history(period="1mo")  # últimos 30 dias

print(dados)

dados["Close"].plot(title="Preço de fechamento - AAPL")
plt.show()
plt.savefig("grafico.png")