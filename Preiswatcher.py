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

# --- Streamlit Konfiguration ---
st.set_page_config(
    page_title="🚀 GPU-Preis Tracker Pro",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Design-Einstellungen ---
st.markdown("""
    <style>
        .main {background-color: #f0f2f6;}
        .stAlert {border-left: 4px solid #FF4B4B;}
        .stProgress > div > div > div {background-color: #FF4B4B;}
        .price-card {
            background: white;
            border-radius: 10px;
            padding: 15px;
            margin: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# --- Globale Variablen ---
USER_AGENT = UserAgent()
REQUEST_DELAY = (5, 15)  # Längere Wartezeiten für Geizhals
DATA_FILE = "gpu_prices.json"

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

# --- Datenhandling ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# --- Verbesserte Scraping-Funktion ---
def scrape_price(url):
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': USER_AGENT.random,
        'Accept-Language': 'de-DE,de;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        # Zufällige Wartezeit
        time.sleep(random.uniform(*REQUEST_DELAY))
        
        response = scraper.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find('span', {'class': 'gh_price'})
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = float(price_text.replace('.', '').replace(',', '.'))
            return price
    except Exception as e:
        st.error(f"Fehler beim Scraping: {str(e)}")
    return None

# --- Haupt-UI ---
def main():
    st.title("🚀 GPU-Preis Tracker Pro")
    st.markdown("""
        Tracke die Preise von Grafikkarten in Echtzeit von Geizhals.at
        """)
    
    selected_category = st.selectbox("Kategorie wählen", list(PRODUCTS.keys()))
    
    if st.button("🔄 Preise aktualisieren", type="primary"):
        progress_bar = st.progress(0)
        price_data = load_data()
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for i, (product, url) in enumerate(PRODUCTS[selected_category].items()):
            progress_bar.progress((i + 1) / len(PRODUCTS[selected_category]))
            
            price = scrape_price(url)
            if price:
                if product not in price_data:
                    price_data[product] = []
                price_data[product].append({
                    "date": current_date,
                    "price": price,
                    "url": url
                })
                st.success(f"{product}: {price:.2f}€")
            else:
                st.warning(f"{product}: Preis nicht verfügbar")
        
        save_data(price_data)
        st.balloons()
    
    # Preisverlauf anzeigen
    st.subheader("📈 Historische Preisdaten")
    price_data = load_data()
    
    if price_data:
        df = pd.DataFrame([
            {"Produkt": product, "Datum": entry["date"], "Preis": entry["price"]}
            for product, entries in price_data.items()
            for entry in entries
        ])
        
        if not df.empty:
            st.line_chart(
                df,
                x="Datum",
                y="Preis",
                color="Produkt",
                height=500
            )
            
            st.dataframe(
                df.sort_values("Datum", ascending=False),
                column_config={
                    "Preis": st.column_config.NumberColumn(format="%.2f €")
                },
                use_container_width=True
            )
    else:
        st.info("Keine Daten verfügbar. Klicke auf 'Preise aktualisieren'.")

if __name__ == "__main__":
    main()
