import pandas as pd
import pandas_ta as ta
import yfinance as yf
import numpy as np
from config import DAYS_WINDOW, Z_SCORE_THRESHOLD

Z_SCORE_SELL = abs(Z_SCORE_THRESHOLD)

def obtener_datos(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty: return None
        return df
    except: return None

def analizar_mercado_general():
    try:
        spy = obtener_datos("SPY")
        vix = obtener_datos("^VIX")
        if spy is None or vix is None: return "Neutral", 1.0

        spy_precio = spy['Close'].iloc[-1]
        spy_sma200 = ta.sma(spy['Close'], length=200).iloc[-1]
        tendencia = "Alcista 🐂" if spy_precio > spy_sma200 else "Bajista 🐻"
        
        nivel_vix = vix['Close'].iloc[-1]
        estado = f"Mercado {tendencia} (VIX: {nivel_vix:.2f})"
        factor_riesgo = 0.5 if nivel_vix > 25 else 1.0
        return estado, factor_riesgo
    except: return "Datos Macro No Disp.", 1.0

# --- NUEVO: RADIOGRAFÍA FUNDAMENTAL ---
def obtener_fundamentales(ticker):
    """Extrae datos clave del balance y estado de resultados."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extracción segura (si el dato no está, pone 'N/A')
        datos = {
            "Sector": info.get('sector', 'Desconocido'),
            "P/E Ratio": info.get('trailingPE', 0),
            "Forward P/E": info.get('forwardPE', 0),
            "PEG Ratio": info.get('pegRatio', 0), # Crecimiento vs Precio
            "Price/Book": info.get('priceToBook', 0),
            "Deuda/Patrimonio": info.get('debtToEquity', 0),
            "Margen Neto": info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
            "Beta": info.get('beta', 1.0)
        }
        return datos
    except Exception as e:
        print(f"⚠️ Error fundamentales {ticker}: {e}")
        return None

def calcular_score_tecnico(metricas, tipo_senal):
    score = 0
    z = abs(metricas['z_score'])
    
    # Z-Score
    if z > 2.0: score += 20
    if z > 2.5: score += 10
    if z > 3.0: score += 10

    # RSI
    rsi = metricas['rsi']
    if tipo_senal == "COMPRA":
        if rsi < 30: score += 30
        elif rsi < 40: score += 15
    elif tipo_senal == "VENTA":
        if rsi > 70: score += 30
        elif rsi > 60: score += 15

    # Volumen
    vol = metricas['vol_factor']
    if vol > 1.5: score += 10
    if vol > 2.0: score += 10

    # Tendencia MACD
    macd_hist = metricas['macd_hist']
    if tipo_senal == "COMPRA" and macd_hist > metricas['macd_hist_prev']: score += 10
    if tipo_senal == "VENTA" and macd_hist < metricas['macd_hist_prev']: score += 10

    return score

def detectar_oportunidad(df):
    if df is None or len(df) < 200: return None, {}, 0

    df['SMA_200'] = ta.sma(df['Close'], length=200)
    
    rolling_mean = df['Close'].rolling(window=DAYS_WINDOW).mean()
    rolling_std = df['Close'].rolling(window=DAYS_WINDOW).std()
    df['Z_Score'] = (df['Close'] - rolling_mean) / rolling_std
    
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df['MACD_Hist'] = macd['MACDh_12_26_9']
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    df['Vol_Media'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Factor'] = df['Volume'] / df['Vol_Media'] 

    ultimo = df.iloc[-1]
    penultimo = df.iloc[-2]

    metricas = {
        "precio": ultimo['Close'],
        "z_score": ultimo['Z_Score'],
        "rsi": ultimo['RSI'],
        "vol_factor": ultimo['Vol_Factor'],
        "atr": ultimo['ATR'],
        "macd_hist": ultimo['MACD_Hist'],
        "macd_hist_prev": penultimo['MACD_Hist'],
        "tendencia": "Alcista 🐂" if ultimo['Close'] > ultimo['SMA_200'] else "Bajista 🐻"
    }

    senal = None
    z = metricas['z_score']
    precio = metricas['precio']
    sma = ultimo['SMA_200']

    if z < Z_SCORE_THRESHOLD and precio > sma:
        senal = "COMPRA"
    elif z > Z_SCORE_SELL:
        senal = "VENTA"

    score = calcular_score_tecnico(metricas, senal) if senal else 0

    return senal, metricas, score