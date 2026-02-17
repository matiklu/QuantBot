import time
import requests
import json
import os
from datetime import datetime
from config import TICKERS, TELEGRAM_TOKEN, CHAT_ID
import quant_engine
import ai_analyst

# Archivo para no repetir alertas
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
    try: 
        requests.post(url, json=payload)
        return True
    except Exception as e: 
        print(f"⚠️ Error Telegram: {e}")
        return False

def ejecutar_bot():
    print("\n" + "="*60)
    print(f"🚀 QUANT-BOT FINAL | {datetime.now().strftime('%H:%M')}")
    
    # 1. ANÁLISIS MACRO (Lo guardamos en una variable para el mensaje)
    print("🌍 Analizando Contexto Macro...", end=" ")
    texto_macro = ""
    try:
        estado_mercado, factor_riesgo = quant_engine.analizar_mercado_general()
        print(f"[{estado_mercado}]")
        texto_macro = f"🌍 *Contexto:* {estado_mercado}\n"
    except:
        print("[Datos Macro No Disp.]")
        texto_macro = "🌍 *Contexto:* Datos no disponibles\n"

    print("="*60 + "\n")

    memoria = cargar_memoria()
    hoy = datetime.now().strftime("%Y-%m-%d")
    alertas = 0
    
    for ticker in TICKERS:
        # 2. DATOS
        df = quant_engine.obtener_datos(ticker)
        if df is None:
            print(f"❌ {ticker}: Sin datos")
            continue
            
        # 3. MOTOR
        tipo_senal, metricas, score = quant_engine.detectar_oportunidad(df)
        z = metricas.get('z_score', 0)
        
        # Log consola
        if tipo_senal:
            print(f"🎯 {ticker:<8} | Z: {z:>5.2f} | Score: {score} | {tipo_senal}")
        else:
            print(f"💤 {ticker:<8} | Z: {z:>5.2f} | Neutral")
            continue
            
        # 4. FILTRO
        if score < 50:
            print(f"   ⚠️ Señal descartada (Score bajo).")
            continue

        # 5. MEMORIA
        clave = f"{ticker}_{hoy}_{tipo_senal}"
        if clave in memoria:
            print(f"   └── 💤 Ya alertado hoy.")
            continue

        # 6. FUNDAMENTALES + IA
        print(f"   └── 📊 Bajando Fundamentales...")
        fundamentales = quant_engine.obtener_fundamentales(ticker)
        
        print(f"   └── 🧠 IA Analizando...")
        analisis_ia = ai_analyst.analizar_riesgo_fundamental(ticker, z, tipo_senal, fundamentales)
        
        # 7. GESTIÓN DE RIESGO (STOP LOSS / TAKE PROFIT)
        atr = metricas['atr']
        precio = metricas['precio']
        
        if tipo_senal == "COMPRA":
            # Long: Stop abajo, Target arriba
            stop = precio - (2 * atr)
            target = precio + (3 * atr)
            icono = "🟢"
        elif tipo_senal == "VENTA":
            # Short: Stop arriba, Target abajo
            stop = precio + (2 * atr)
            target = precio - (3 * atr)
            icono = "🔴"
        
        plan_trade = f"🛑 Stop: ${stop:.2f}\n🎯 Target: ${target:.2f}"

        # 8. MENSAJE FINAL
        barras = "▓" * (int(score) // 10) + "░" * ((100 - int(score)) // 10)
        
        # Info Fundamental Resumida
        info_extra = "N/A"
        if fundamentales:
            peg = fundamentales.get('PEG Ratio', 0)
            str_peg = f"{peg:.2f}" if peg and peg > 0 else "N/A"
            info_extra = f"P/E: {fundamentales['P/E Ratio']:.1f} | PEG: {str_peg} | Deuda: {fundamentales['Deuda/Patrimonio']:.2f}"

        msg = f"{icono} *ALERTA: {ticker}*\n"
        msg += f"{texto_macro}" # <--- ACÁ AGREGAMOS EL CONTEXTO MACRO
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🏆 *Score:* {score}/100\n`{barras}`\n"
        msg += f"📊 *Datos:*\n`{info_extra}`\n"
        msg += f"💰 *Precio:* ${precio:.2f} (Z: {z:.2f}σ)\n"
        msg += f"🛡️ *Plan Sugerido:*\n{plan_trade}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🧠 *IA Hedge Fund:*\n{analisis_ia}"
        
        if enviar_telegram(msg):
            memoria[clave] = True
            guardar_memoria(memoria)
            alertas += 1
            print("   └── ✅ Enviado.")
        
        time.sleep(2)
        
    print(f"\n✅ Finalizado. Alertas: {alertas}")

if __name__ == "__main__":
    ejecutar_bot()
