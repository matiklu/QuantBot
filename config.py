import os

# Intentamos leer de las Variables de Entorno (Nube)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Si no están en la nube, intentamos leerlas de un archivo local (tu PC)
# (Esto es para que te siga funcionando en tu compu sin romper nada)
if not TELEGRAM_TOKEN:
    try:
        from mis_claves import TELEGRAM_TOKEN_LOCAL, CHAT_ID_LOCAL, GEMINI_API_KEY_LOCAL
        TELEGRAM_TOKEN = TELEGRAM_TOKEN_LOCAL
        CHAT_ID = CHAT_ID_LOCAL
        GEMINI_API_KEY = GEMINI_API_KEY_LOCAL
    except ImportError:
        pass # Si falla, es porque estamos en la nube sin configurar o falta el archivo

# --- CONFIGURACIÓN DEL BOT ---
DAYS_WINDOW = 365
Z_SCORE_THRESHOLD = -2.0

TICKERS = [
    "SPY", "QQQ", "IWM", "DIA",
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD",
    "GGAL", "YPF", "BMA", "PAM", "CEPU", "TGS", "VIST",
    "BTC-USD", "ETH-USD", "SOL-USD",
    "KO", "JNJ", "MCD", "BRK-B",
    "GLD", "SLV", "USO", "NEM"
]