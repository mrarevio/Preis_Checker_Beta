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
    
    # Rest der main()-Funktion...
    # (Behalte den vorhandenen Code bei)

if __name__ == "__main__":
    main()
