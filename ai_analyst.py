import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from config import GEMINI_API_KEY

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"⚠️ Error Gemini: {e}")

def conseguir_modelo_valido():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return m.name
        return "models/gemini-1.5-flash"
    except: return "gemini-pro"

MODELO_ACTUAL = conseguir_modelo_valido()

def obtener_noticias_rss(ticker):
    try:
        url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        
        # TRUCO: Intentamos sacar también la descripción, no solo el título
        noticias = []
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            description = item.find('description').text if item.find('description') is not None else ""
            if title:
                # Limpiamos un poco el texto HTML si viene sucio
                full_text = f"TITULAR: {title}\nRESUMEN: {description[:200]}..." 
                noticias.append(full_text)
        return noticias[:5]
    except: return []

def analizar_riesgo_fundamental(ticker, z_score, tipo_senal, fundamentales):
    """
    Ahora recibe 'fundamentales' (Diccionario con P/E, Deuda, etc.)
    """
    noticias = obtener_noticias_rss(ticker)
    txt_noticias = "\n---\n".join(noticias) if noticias else "Sin noticias recientes."
    
    # Formateamos los datos financieros para que la IA los entienda fácil
    # Formateamos los datos financieros
    if fundamentales:
        # Lógica para PEG: Si es 0 o None, mostramos "N/A"
        peg = fundamentales.get('PEG Ratio', 0)
        str_peg = f"{peg:.2f}" if peg and peg > 0 else "N/A (Dato Yahoo faltante)"

        txt_fundamentales = f"""
        - Sector: {fundamentales['Sector']}
        - Valuación (P/E): {fundamentales['P/E Ratio']:.2f} (Ideal < 20)
        - Crecimiento (PEG): {str_peg}
        - Salud (Deuda/Patrimonio): {fundamentales['Deuda/Patrimonio']:.2f} (Ideal < 100)
        - Rentabilidad (Margen Neto): {fundamentales['Margen Neto']:.1f}%
        """
    else:
        txt_fundamentales = "Datos fundamentales no disponibles."

    # --- PROMPT CONTEXTUAL PROFUNDO ---
    prompt = f"""
    Actúa como un Inversor Value Senior (Warren Buffett / Benjamin Graham).
    
    OBJETIVO: Validar una señal técnica de {tipo_senal} en {ticker} (Z-Score: {z_score:.2f}).
    
    1. ANÁLISIS FINANCIERO (Hoja Clínica):
    {txt_fundamentales}
    
    2. CONTEXTO NARRATIVO (Noticias):
    {txt_noticias}
    
    TU MISIÓN:
    Cruza los datos duros con las noticias. 
    - Si la señal es COMPRA: ¿La empresa es sólida (buenos márgenes/baja deuda) y la caída es injustificada? -> OPORTUNIDAD REAL.
    - Si la empresa tiene deuda alta y márgenes negativos, y la noticia es mala -> TRAMPA DE VALOR (NO COMPRAR).
    
    Responde ESTRICTAMENTE:
    🎯 VEREDICTO: (FUERTE / ESPECULATIVA / PELIGROSA / DESCARTAR)
    ⚖️ CONVICCIÓN: (0-10)
    🧠 RAZONAMIENTO: (Explica tu lógica cruzando Fundamental + Noticias)
    ⚠️ RIESGO: (¿Qué dice el balance que podría salir mal?)
    """

    try:
        model = genai.GenerativeModel(MODELO_ACTUAL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:

        return f"Error IA: {e}"
