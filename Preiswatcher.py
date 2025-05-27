import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import cloudscraper
from fake_useragent import UserAgent
import os

# --- Streamlit Konfiguration ---
st.set_page_config(
    page_title="GPU-Preis Tracker",
    page_icon="💻",
    layout="wide"
)

# --- Anti-Scraping-Einstellungen ---
USER_AGENT = UserAgent()
REQUEST_DELAY = (3, 8)  # Zufällige Wartezeit zwischen 3-8 Sekunden
MAX_RETRIES = 3

# --- Datenverwaltung ---
DATA_DIR = "preis_daten"
os.makedirs(DATA_DIR, exist_ok=True)

# --- Streamlit UI ---
st.title("🛒 GPU-Preis Tracker")
st.markdown("""
    <style>
        .stProgress > div > div > div {background-color: #FF4B4B;}
        .stAlert {border-left: 4px solid #FF4B4B;}
    </style>
""", unsafe_allow_html=True)

# --- Produktliste ---
PRODUKTE = {
    "RTX 5070 Ti": {
        "Gainward RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
        "MSI RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html"
    },
    "RTX 5080": {
        "Palit RTX 5080": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-v1-ne75080019t2-gb2031y-a3487808.html",
        "Zotac RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html"
    }
}

# --- Verbesserte Scraping-Funktion ---
@st.cache_data(show_spinner=False)
def scrape_preis(url, max_retries=MAX_RETRIES):
    scraper = cloudscraper.create_scraper()
    
    for attempt in range(max_retries):
        try:
            # Zufällige Wartezeit
            time.sleep(random.uniform(*REQUEST_DELAY))
            
            # Headers mit zufälligem User-Agent
            headers = {
                'User-Agent': USER_AGENT.random,
                'Accept-Language': 'de-DE,de;q=0.9'
            }
            
            response = scraper.get(url, headers=headers, timeout=15)
            
            if response.status_code == 429:
                wait_time = (2 ** attempt) + random.uniform(1, 3)
                st.warning(f"Rate Limit erreicht! Warte {wait_time:.1f} Sekunden...")
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Preis extrahieren
            preis_element = soup.find('span', class_='price__value')
            if preis_element:
                preis_text = preis_element.get_text(strip=True)
                return float(preis_text.replace('.', '').replace(',', '.'))
            
        except Exception as e:
            st.error(f"Versuch {attempt + 1} fehlgeschlagen: {str(e)}")
            continue
            
    return None

# --- Hauptfunktion ---
def main():
    selected_category = st.selectbox("Kategorie wählen", list(PRODUKTE.keys()))
    
    if st.button("Preise aktualisieren", type="primary"):
        progress_bar = st.progress(0)
        results = []
        
        for i, (produkt, url) in enumerate(PRODUKTE[selected_category].items()):
            progress_bar.progress((i + 1) / len(PRODUKTE[selected_category]))
            preis = scrape_preis(url)
            
            if preis:
                results.append({
                    "Produkt": produkt,
                    "Preis (€)": preis,
                    "Datum": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "URL": url
                })
            else:
                st.warning(f"Konnte Preis für {produkt} nicht abrufen")
        
        if results:
            df = pd.DataFrame(results)
            st.session_state.last_data = df
            st.success("Preise erfolgreich aktualisiert!")
            
            # Daten speichern
            file_path = os.path.join(DATA_DIR, f"{selected_category.replace(' ', '_')}.csv")
            df.to_csv(file_path, index=False)
            
            # Ergebnisse anzeigen
            st.dataframe(
                df,
                column_config={
                    "URL": st.column_config.LinkColumn("Link"),
                    "Preis (€)": st.column_config.NumberColumn(
                        format="%.2f €"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Preisverlauf visualisieren
            if os.path.exists(file_path):
                hist_data = pd.read_csv(file_path)
                st.line_chart(
                    hist_data,
                    x="Datum",
                    y="Preis (€)",
                    color="Produkt"
                )

if __name__ == "__main__":
    main()
