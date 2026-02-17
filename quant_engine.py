import pandas as pd
import yfinance as yf
import numpy as np
from config import DAYS_WINDOW, Z_SCORE_THRESHOLD

# Umbrales
Z_SCORE_SELL = abs(Z_SCORE_THRESHOLD)

def obtener_datos(ticker):
    try:
        # Descarga optimizada
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty: return None
        return df
    except: return None

# --- FUNCIONES MATEMÁTICAS MANUALES (Sin pandas_ta) ---
def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calcular_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, hist

def calcular_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=period).mean()

# --- ANÁLISIS ---
def analizar_mercado_general():
    try:
        spy = obtener_datos("SPY")
        vix = obtener_datos("^VIX")
        if spy is None or vix is None: return "Neutral", 1.0

        spy_precio = spy['Close'].iloc[-1]
        spy_sma200 = spy['Close'].rolling(window=200).mean().iloc[-1]
        tendencia = "Alcista 🐂" if spy_precio > spy_sma200 else "Bajista 🐻"
        
        nivel_vix = vix['Close'].iloc[-1]
        estado = f"Mercado {tendencia} (VIX: {nivel_vix:.2f})"
        factor_riesgo = 0.5 if nivel_vix > 25 else 1.0
        return estado, factor_riesgo
    except: return "Datos Macro No Disp.", 1.0

def obtener_fundamentales(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "Sector": info.get('sector', 'Desconocido'),
            "P/E Ratio": info.get('trailingPE', 0),
            "PEG Ratio": info.get('pegRatio', 0),
            "Deuda/Patrimonio": info.get('debtToEquity', 0),
            "Margen Neto": info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
        }
    except: return None

def calcular_score_tecnico(metricas, tipo_senal):
    score = 0
    z = abs(metricas['z_score'])
    
    # 1. Z-Score
    if z > 2.0: score += 20
    if z > 2.5: score += 10
    if z > 3.0: score += 10

    # 2. RSI
    rsi = metricas['rsi']
    if tipo_senal == "COMPRA":
        if rsi < 30: score += 30
        elif rsi < 40: score += 15
    elif tipo_senal == "VENTA":
        if rsi > 70: score += 30
        elif rsi > 60: score += 15

    # 3. Volumen
    vol = metricas['vol_factor']
    if vol > 1.5: score += 10
    if vol > 2.0: score += 10

    # 4. Tendencia MACD
    macd_hist = metricas['macd_hist']
    if tipo_senal == "COMPRA" and macd_hist > metricas['macd_hist_prev']: score += 10
    if tipo_senal == "VENTA" and macd_hist < metricas['macd_hist_prev']: score += 10

    return score

def detectar_oportunidad(df):
    if df is None or len(df) < 200: return None, {}, 0

    # CÁLCULOS MANUALES
    # 1. SMA 200
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # 2. Z-Score
    rolling_mean = df['Close'].rolling(window=DAYS_WINDOW).mean()
    rolling_std = df['Close'].rolling(window=DAYS_WINDOW).std()
    df['Z_Score'] = (df['Close'] - rolling_mean) / rolling_std
    
    # 3. RSI Manual
    df['RSI'] = calcular_rsi(df['Close'])
    
    # 4. MACD Manual
    _, df['MACD_Hist'] = calcular_macd(df['Close'])
    
    # 5. ATR Manual
    df['ATR'] = calcular_atr(df)
    
    # 6. Volumen
    df['Vol_Media'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Factor'] = df['Volume'] / df['Vol_Media'] 

    # Datos actuales
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

    # Lógica de Señal (Incluyendo Rebote Agresivo)
    if z < Z_SCORE_THRESHOLD and precio > sma:
        senal = "COMPRA" # Buy the Dip
    elif z < -2.5: 
        senal = "COMPRA" # Rebote técnico (Cuchillo cayendo)
    elif z > Z_SCORE_SELL:
        senal = "VENTA"

    score = calcular_score_tecnico(metricas, senal) if senal else 0

    return senal, metricas, score
