import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
import time
import smtplib
from email.message import EmailMessage
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ========== KONFIGURATION ==========
TIMEZONE = None
DATA_DIR = "preis_daten"
os.makedirs(DATA_DIR, exist_ok=True)

# ========== DESIGN-EINSTELLUNGEN ==========
primary_color = "#FF4B4B"
secondary_color = "#1F77B4"
bg_color = "#F4F4F4"  # Helle Hintergrundfarbe für bessere Lesbarkeit
text_color = "#333"  # Dunklere Schriftfarbe für besseren Kontrast
font = "Helvetica Neue, sans-serif"

st.set_page_config(
    page_title="GPU Preis-Tracker Pro",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
    <style>
        .main {{
            background-color: {bg_color};
            color: {text_color};
            font-family: {font};
        }}
        .stButton>button {{
            background-color: {primary_color};
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            transition: background-color 0.3s ease;
        }}
        .stButton>button:hover {{
            background-color: #FF6464; /* Hellerer Farbton bei Hover */
        }}
        .stAlert {{
            border-left: 4px solid {primary_color};
        }}
        .stProgress > div > div > div {{
            background-color: {primary_color};
        }}
        h1, h2, h3 {{
            font-family: 'Arial', sans-serif;
            font-weight: bold;
        }}
        .css-1aumxhk {{
            background-color: #FFF; /* Kartenhintergrund */
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
    </style>
""", unsafe_allow_html=True)

# ========== PRODUKTLISTEN ==========
produkte_5070ti = {
    "Gainward RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
    "MSI RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html",
    "Palit RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-v186845.html",
    "Gainward Phoenix": "https://geizhals.at/gainward-geforce-rtx-5070-ti-phoenix-v1-5509-ne7507t019t2-gb2031c-a3470768.html",
    "MSI Gaming Trio": "https://geizhals.at/msi-geforce-rtx-5070-ti-16g-gaming-trio-oc-a3445122.html",
    "ASUS ROG Strix": "https://geizhals.at/asus-rog-strix-geforce-rtx-5070-ti-oc-a3382464.html",
    "Palit GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-v1-ne7507t019t2-gb2031y-a3470756.html",
    "Palit GamingPro OC V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-oc-v1-ne7507ts19t2-gb2031y-a3470759.html"
}

produkte_5080 = {
    "Palit GeForce RTX 5080 GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-v1-ne75080019t2-gb2031y-a3487808.html",
    "Zotac GeForce RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html",
    "INNO3D GeForce RTX 5080 X3": "https://geizhals.at/inno3d-geforce-rtx-5080-x3-n50803-16d7-176068n-a3382794.html",
    "Gainward GeForce RTX 5080 Phoenix GS V1": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
    "Palit GeForce RTX 5080 GamingPro": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-ne75080019t2-gb2031a-a3382521.html",
}

def clean_data(df):
    if 'product' in df.columns:
        df['product'] = pd.to_numeric(df['product'], errors='coerce')

    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Duplikate entfernen
    df = df.drop_duplicates(subset=['product', 'date', 'price'], keep='last')
    
    return df

def robust_scrape(url, max_retries=3):
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            preis_element = (soup.find('strong', id='pricerange-min') or 
                             soup.find('span', class_='price') or
                             soup.find('div', class_='gh_price'))
            
            if preis_element:
                preis_text = preis_element.get_text(strip=True)
                preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                datum = datetime.now(TIMEZONE)
                return preis, datum
        except Exception as e:
            print(f"Fehler bei Versuch {attempt + 1}: {e}")
            time.sleep(2 ** attempt)
    return None, None

def speichere_tagesdaten(daten, dateipfad):
    heute = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    df = pd.DataFrame(daten)
    df = clean_data(df)
    
    vorhanden = pd.read_json(dateipfad) if os.path.exists(dateipfad) else pd.DataFrame()
    vorhanden = clean_data(vorhanden)
    
    aktualisiert = pd.concat([vorhanden, df])
    aktualisiert.to_json(dateipfad, orient='records', indent=2)

def lade_alle_daten(data_dir):
    alle_daten = []
    for datei in os.listdir(data_dir):
        if datei.startswith("preise_") and datei.endswith(".json"):
            try:
                df = pd.read_json(os.path.join(data_dir, datei))
                df = clean_data(df)
                alle_daten.append(df)
            except:
                continue
    return pd.concat(alle_daten, ignore_index=True) if alle_daten else pd.DataFrame()

def show_price_trend(df):
    st.subheader("📈 Preisverlauf")
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        ausgewählte_produkte = st.multiselect(
            "Modelle auswählen",
            options=df['product'].unique(),
            default=df['product'].unique()[:3]
        )

        if ausgewählte_produkte:
            gefiltert = df[df['product'].isin(ausgewählte_produkte)]
            fig = make_subplots(specs=[[{"secondary_y": False}]])

            for produkt in ausgewählte_produkte:
                pdata = gefiltert[gefiltert['product'] == produkt]
                fig.add_trace(go.Scatter(
                    x=pdata['date'],
                    y=pdata['price'],
                    name=produkt,
                    mode='lines+markers',
                    line=dict(width=2),
                    marker=dict(size=8)
                ))

            fig.update_layout(
                title="Preisverlauf der GPUs",
                xaxis_title="Datum",
                yaxis_title="Preis (€)",
                hovermode="x unified",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=text_color)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Bitte wähle mindestens ein Modell aus, um den Preisverlauf anzuzeigen.")

def show_historical_prices(df):
    st.subheader("📜 Historische Preise")
    if not df.empty:
        ausgewähltes_produkt = st.selectbox(
            "Wähle ein Produkt aus",
            options=df['product'].unique()
        )

        historisch_df = df[df['product'] == ausgewähltes_produkt]

        if not historisch_df.empty:
            historisch_df['date'] = pd.to_datetime(historisch_df['date'])
            historisch_df = historisch_df.sort_values('date')
            st.dataframe(historisch_df[['date', 'price']], use_container_width=True)
        else:
            st.info("Keine historischen Daten für das gewählte Produkt verfügbar.")

st.title("💻 GPU Preis-Tracker Pro")

tab1, tab2, tab3, tab4 = st.tabs(["5070 Ti Übersicht", "5080 Übersicht", "⚙️ Einstellungen", "📈 Analyse"])

# === TAB 1: Übersicht 5070 Ti ===
with tab1:
    col1, col2 = st.columns([1, 2])

    st.header("Preisübersicht für 5070 Ti")
    daten_5070ti = []
    for name, url in produkte_5070ti.items():
        preis, datum = robust_scrape(url)
        if preis is not None:
            daten_5070ti.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    speichere_tagesdaten(daten_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))
    df_5070ti = lade_alle_daten(DATA_DIR)
    if not df_5070ti.empty:
        st.dataframe(df_5070ti[['product', 'price', 'date', 'url']], use_container_width=True)

# === TAB 2: Übersicht 5080 ===
with tab2:
    st.header("Preisübersicht für 5080")
    daten_5080 = []
    for name, url in produkte_5080.items():
        preis, datum = robust_scrape(url)
        if preis is not None:
            daten_5080.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    speichere_tagesdaten(daten_5080, os.path.join(DATA_DIR, "preise_5080.json"))
    df_5080 = lade_alle_daten(DATA_DIR)
    if not df_5080.empty:
        st.dataframe(df_5080[['product', 'price', 'date', 'url']], use_container_width=True)

# === TAB 3: Einstellungen ===
with tab3:
    with st.form("einstellungen_formular"):
        alarm_price = st.number_input("Preisalarm setzen (€)", min_value=100, value=700, step=10)
        email = st.text_input("Benachrichtigungs-E-Mail")
        smtp_server = st.text_input("SMTP-Server", "smtp.gmail.com")
        smtp_port = st.number_input("Port", 465)
        smtp_user = st.text_input("Benutzername")
        smtp_pass = st.text_input("Passwort", type="password")

        if st.form_submit_button("💾 Einstellungen speichern"):
            st.session_state.alarm_price = alarm_price
            st.session_state.email = email
            st.session_state.smtp = {
                "server": smtp_server,
                "port": smtp_port,
                "user": smtp_user,
                "password": smtp_pass
            }
            st.success("Einstellungen gespeichert!")

# === TAB 4: Analyse ===
with tab4:
    df_combined = pd.concat([df_5070ti, df_5080], ignore_index=True)
    if not df_combined.empty:
        show_historical_prices(df_combined)  # Historische Preise anzeigen

        st.subheader("📊 Analyse")
        df_combined['date'] = pd.to_datetime(df_combined['date'])
        st.dataframe(df_combined.sort_values('date', ascending=False), use_container_width=True)

        st.subheader("Statistik")
        stats = df_combined.groupby('product')['price'].agg(['min', 'max', 'mean', 'last'])
        st.dataframe(stats.style.format("{:.2f}€"), use_container_width=True)

        fig = px.box(df_combined, x="product", y="price", color="product")
        st.plotly_chart(fig, use_container_width=True)

# === AUTOMATISCHES UPDATE ===
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.min

if (datetime.now() - st.session_state.last_update) > timedelta(hours=24):
    with st.spinner("Tägliches Update läuft..."):
        auto_data_5070ti = []
        for name, url in produkte_5070ti.items():
            preis, datum = robust_scrape(url)
            if preis is not None:
                auto_data_5070ti.append({'product': name, 'price': preis, 'date': datum, 'url': url})
            time.sleep(1)
        speichere_tagesdaten(auto_data_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))
        
        auto_data_5080 = []
        for name, url in produkte_5080.items():
            preis, datum = robust_scrape(url)
            if preis is not None:
                auto_data_5080.append({'product': name, 'price': preis, 'date': datum, 'url': url})
            time.sleep(1)
        speichere_tagesdaten(auto_data_5080, os.path.join(DATA_DIR, "preise_5080.json"))

        st.session_state.last_update = datetime.now()
        st.rerun()
