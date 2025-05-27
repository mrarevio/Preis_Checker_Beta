import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import cloudscraper
from fake_useragent import UserAgent
import os
import json

# --- Konfiguration ---
USER_AGENT = UserAgent()
REQUEST_DELAY = (10, 25)  # Deutlich längere Wartezeiten (10-25 Sekunden)
MAX_RETRIES = 2           # Weniger Wiederholungsversuche
TIMEOUT = 30              # Längere Timeouts

# --- Produktliste ---
PRODUCTS = {
    "RTX 5070 Ti": {
  "Gainward RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
    "MSI RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html",
    "Palit RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-v186845.html",
    "Gainward Phoenix": "https://geizhals.at/gainward-geforce-rtx-5070-ti-phoenix-v1-5509-ne7507t019t2-gb2031c-a3470768.html",
    "MSI Gaming Trio": "https://geizhals.at/msi-geforce-rtx-5070-ti-16g-gaming-trio-oc-a3445122.html",
    "ASUS ROG Strix": "https://geizhals.at/asus-rog-strix-geforce-rtx-5070-ti-oc-a3382464.html",
    "Palit GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-v1-ne7507t019t2-gb2031y-a3470756.html",
    "Palit GamingPro OC V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-oc-v1-ne7507ts19t2-gb2031y-a3470759.html"
    },
    "RTX 5080": {
    "Palit GeForce RTX 5080 GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-v1-ne75080019t2-gb2031y-a3487808.html",
    "Zotac GeForce RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html",
    "INNO3D GeForce RTX 5080 X3": "https://geizhals.at/inno3d-geforce-rtx-5080-x3-n50803-16d7-176068n-a3382794.html",
    "Gainward GeForce RTX 5080 Phoenix GS V1": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
    "Palit GeForce RTX 5080 GamingPro": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-ne75080019t2-gb2031a-a3382521.html",
    }
}

# --- Verbesserte Scraping-Funktion mit Proxy-Support ---
def scrape_price(url):
    scraper = cloudscraper.create_scraper()
    
    for attempt in range(MAX_RETRIES):
        try:
            # Zufällige Wartezeit + jitter
            delay = random.uniform(*REQUEST_DELAY) * (attempt + 1)
            time.sleep(delay)
            
            headers = {
                'User-Agent': USER_AGENT.random,
                'Accept-Language': 'de-DE,de;q=0.9',
                'Referer': 'https://www.google.com/',
                'DNT': '1'  # Do Not Track Header
            }
            
            # Optional: Proxies hinzufügen (z.B. BrightData/ScraperAPI)
            proxies = None
            # proxies = {
            #     'http': 'http://USERNAME:PASSWORD@proxy-server:port',
            #     'https': 'http://USERNAME:PASSWORD@proxy-server:port'
            # }
            
            response = scraper.get(
                url,
                headers=headers,
                timeout=TIMEOUT,
                proxies=proxies
            )
            
            # Bei Rate-Limiting länger warten
            if response.status_code == 429:
                wait_time = 60 * (attempt + 1)  # 1-2 Minuten warten
                st.warning(f"Rate Limited! Warte {wait_time} Sekunden...")
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            
            # Preis extrahieren mit robustem Parsing
            soup = BeautifulSoup(response.text, 'html.parser')
            price_element = (
                soup.find('span', class_='gh_price') or 
                soup.find('span', class_='price__value') or
                soup.find('strong', id='pricerange-min')
            )
            
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = float(price_text
                    .replace('€', '')
                    .replace('.', '')
                    .replace(',', '.'))
                return price
                
        except Exception as e:
            st.error(f"Versuch {attempt + 1} fehlgeschlagen: {str(e)}")
            continue
            
    return None

# --- Hauptfunktion mit optimierter Logik ---
def main():
    st.title("🛒 GPU-Preis Tracker (Geizhals)")
    
    # Nur 1 Produkt pro Durchlauf prüfen
    selected_product = st.selectbox(
        "Modell auswählen",
        list(PRODUCTS["RTX 5080"].items()),
        format_func=lambda x: x[0]
    )
    
    if st.button("Preis prüfen", type="primary"):
        with st.spinner("Scrape läuft (bitte warten...)"):

            name, url = selected_product
            price = scrape_price(url)
            
            if price:
                st.success(f"✅ {name}: {price:.2f}€")
                # Daten speichern (für Streamlit Cloud angepasst)
                try:
                    data = {"product": name, "price": price, "date": datetime.now().isoformat()}
                    st.session_state.last_price = data
                    st.json(data)  # Debug-Ausgabe
                except Exception as e:
                    st.error(f"Speicherfehler: {str(e)}")
            else:
                st.warning(f"❌ {name}: Preis nicht verfügbar")

if __name__ == "__main__":
    main()
