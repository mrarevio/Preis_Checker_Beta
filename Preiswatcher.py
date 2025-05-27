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

# --- Globale Variablen (müssen VOR der main()-Funktion definiert werden) ---
USER_AGENT = UserAgent()
REQUEST_DELAY = (5, 15)
DATA_FILE = "gpu_prices.json"

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

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def scrape_price(url):
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': USER_AGENT.random,
        'Accept-Language': 'de-DE,de;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        time.sleep(random.uniform(*REQUEST_DELAY))
        response = scraper.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find('span', {'class': 'gh_price'})
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            return float(price_text.replace('.', '').replace(',', '.'))
    except Exception as e:
        st.error(f"Fehler beim Scraping: {str(e)}")
    return None

def main():
    st.title("🚀 GPU-Preis Tracker Pro")
    selected_category = st.selectbox("Kategorie wählen", list(PRODUCTS.keys()))

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
