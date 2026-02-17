import time
import requests
import json
import os
from datetime import datetime
from config import TICKERS, TELEGRAM_TOKEN, CHAT_ID
import quant_engine
import ai_analyst

ARCHIVO_MEMORIA = "historial_alertas.json"

def cargar_memoria():
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r") as f: return json.load(f)
        except: return {}
    return {}

def guardar_memoria(memoria):
    with open(ARCHIVO_MEMORIA, "w") as f: json.dump(memoria, f)

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload); return True
    except: return False

def ejecutar_bot():
    print("\n" + "="*60)
    print(f"🚀 QUANT-BOT VALUE PRO | {datetime.now().strftime('%H:%M')}")
    
    print("🌍 Analizando Contexto Macro...", end=" ")
    try:
        estado_mercado, factor_riesgo = quant_engine.analizar_mercado_general()
        print(f"[{estado_mercado}]")
    except: print("[Datos Macro No Disp.]")
    print("="*60 + "\n")

    memoria = cargar_memoria()
    hoy = datetime.now().strftime("%Y-%m-%d")
    alertas = 0
    
    for ticker in TICKERS:
        df = quant_engine.obtener_datos(ticker)
        if df is None:
            print(f"❌ {ticker}: Sin datos")
            continue
            
        tipo_senal, metricas, score = quant_engine.detectar_oportunidad(df)
        z = metricas.get('z_score', 0)
        
        # Log simplificado
        if tipo_senal:
            print(f"🎯 {ticker:<8} | Z: {z:>5.2f} | Score: {score} | {tipo_senal}")
        else:
            print(f"💤 {ticker:<8} | Z: {z:>5.2f} | Neutral")
            continue
            
        if score < 50:
            print(f"   ⚠️ Señal descartada (Score bajo).")
            continue

        clave = f"{ticker}_{hoy}_{tipo_senal}"
        if clave in memoria:
            print(f"   └── 💤 Ya alertado.")
            continue

        # --- AQUÍ LA MAGIA NUEVA ---
        print(f"   └── 📊 Descargando Balance y Fundamentales...")
        fundamentales = quant_engine.obtener_fundamentales(ticker)
        
        print(f"   └── 🧠 IA Analizando Balance + Noticias...")
        analisis_ia = ai_analyst.analizar_riesgo_fundamental(ticker, z, tipo_senal, fundamentales)
        
        # Gestión de Riesgo
        atr = metricas['atr']
        precio = metricas['precio']
        if tipo_senal == "COMPRA":
            stop = precio - (2 * atr)
            target = precio + (3 * atr)
            plan = f"🛑 Stop: ${stop:.2f}\n🎯 Target: ${target:.2f}"
            icono = "🟢"
        else:
            plan = "⚠️ Evaluar cobertura."
            icono = "🔴"

        # Mensaje Enriquecido
        barras = "▓" * (int(score) // 10) + "░" * ((100 - int(score)) // 10)
        
        # Armamos un mini resumen de fundamentales para el mensaje
        info_extra = "N/A"
        if fundamentales:
            info_extra = f"P/E: {fundamentales['P/E Ratio']:.1f} | Margen: {fundamentales['Margen Neto']:.1f}% | Deuda: {fundamentales['Deuda/Patrimonio']:.2f}"

        msg = f"{icono} *VALUE ALERT: {ticker}*\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🏆 *Calidad:* {score}/100\n`{barras}`\n"
        msg += f"📊 *Fundamentales:*\n`{info_extra}`\n"
        msg += f"💰 *Precio:* ${precio:.2f} (Z: {z:.2f}σ)\n"
        msg += f"🛡️ *Plan:*\n{plan}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🧠 *Análisis Profundo:*\n{analisis_ia}"
        
        if enviar_telegram(msg):
            memoria[clave] = True
            guardar_memoria(memoria)
            alertas += 1
            print("   └── ✅ Enviado.")
        
        time.sleep(2)
        
    print(f"\n✅ Finalizado. Alertas: {alertas}")

if __name__ == "__main__":
    ejecutar_bot()