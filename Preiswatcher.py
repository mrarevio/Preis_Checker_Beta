# Modernisiertes und benutzerfreundliches Preisalarm-Tool mit Tabs & Design
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

# === KONSTANTEN ===
TIMEZONE = None  # Optional: datetime.now().astimezone().tzinfo
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# === Produktlinks ===
products = {
    "Gainward RTX 5070 Ti (1)": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
    "MSI RTX 5070 Ti (1)": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html",
    "Palit RTX 5070 Ti (1)": "https://geizhals.at/palit-geforce-rtx-5070-ti-v186845.html",
    "Gainward Phoenix RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-phoenix-v1-5509-ne7507t019t2-gb2031c-a3470768.html",
    "MSI Gaming Trio RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-16g-gaming-trio-oc-a3445122.html",
    "ASUS ROG Strix RTX 5070 Ti": "https://geizhals.at/asus-rog-strix-geforce-rtx-5070-ti-oc-a3382464.html",
    "Palit GamingPro RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-v1-ne7507t019t2-gb2031y-a3470756.html",
    "Palit GamingPro OC RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-oc-v1-ne7507ts19t2-gb2031y-a3470759.html"
}

# === Scraper ===
def robust_scrape(url, max_retries=3):
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            price_elm = soup.find('span', class_='gh_price')
            price = float(price_elm.text.replace('€','').replace('.','').replace(',','.').strip()) if price_elm else None
            scraped_date = datetime.now(TIMEZONE)
            return price, scraped_date
        except Exception:
            time.sleep(2 ** attempt)
    return None, None

# === Speichern & Laden ===
def save_daily_data(data):
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    filename = os.path.join(DATA_DIR, f"prices_{today}.json")
    existing = pd.read_json(filename) if os.path.exists(filename) else pd.DataFrame()
    updated = pd.concat([existing, pd.DataFrame(data)])
    updated.to_json(filename, orient='records', indent=2)

def load_all_data():
    all_data = []
    for file in os.listdir(DATA_DIR):
        if file.startswith("prices_") and file.endswith(".json"):
            try:
                df = pd.read_json(os.path.join(DATA_DIR, file))
                all_data.append(df)
            except: continue
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# === Mailversand ===
def send_email(subject, body, to_email, server, port, user, password):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = to_email
        msg.set_content(body)
        with smtplib.SMTP_SSL(server, port) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Fehler beim Senden der Mail: {str(e)}")
        return False

# === Streamlit UI ===
st.set_page_config(page_title="RTX 5070 Ti Preis-Monitor", layout="wide")
st.title("🎮 RTX 5070 Ti Preisüberwachung")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "⚙️ Einstellungen", "📁 Daten"])

# -- TAB 1: Dashboard --
with tab1:
    st.subheader("💹 Preisverlauf")
    df = load_all_data()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        date_range = st.slider("Zeitraum auswählen", min_date, max_date, (max_date - timedelta(days=30), max_date))
        filtered = df[(df['date'].dt.date >= date_range[0]) & (df['date'].dt.date <= date_range[1])]

        fig = px.line(filtered, x="date", y="price", color="product", title="📈 Preisentwicklung",
                      labels={"price": "Preis (€)", "date": "Datum"}, line_shape='spline')
        st.plotly_chart(fig, use_container_width=True)

        if 'alarm_price' in st.session_state:
            alarmed = filtered[filtered['price'] <= st.session_state.alarm_price]
            if not alarmed.empty:
                st.warning(f"⚠️ Preis unter {st.session_state.alarm_price}€ entdeckt!")
                st.write(alarmed[['product', 'price', 'date']].sort_values('date'))

# -- TAB 2: Einstellungen --
with tab2:
    st.subheader("🔔 Preisalarm & SMTP")
    with st.form("settings_form"):
        alarm_price = st.number_input("Preisgrenze (€)", min_value=100, value=700, step=10)
        email = st.text_input("Empfänger E-Mail")
        smtp_server = st.text_input("SMTP-Server", value="smtp.gmail.com")
        smtp_port = st.number_input("Port", value=465)
        smtp_user = st.text_input("Benutzername")
        smtp_pass = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("💾 Speichern")
        if submitted:
            st.session_state.alarm_price = alarm_price
            st.session_state.email = email
            st.session_state.smtp = {
                "server": smtp_server,
                "port": smtp_port,
                "user": smtp_user,
                "password": smtp_pass
            }
            st.success("✅ Einstellungen gespeichert!")

# -- TAB 3: Daten --
with tab3:
    st.subheader("🗃️ Datenverwaltung")
    if st.button("🔄 Preise abrufen"):
        with st.spinner("Lade aktuelle Preise..."):
            data = []
            for name, url in products.items():
                price, date = robust_scrape(url)
                if price:
                    data.append({'product': name, 'price': price, 'date': date, 'url': url})
                    time.sleep(1)
            if data:
                save_daily_data(data)
                st.success("✅ Preise aktualisiert!")

    df = load_all_data()
    if not df.empty:
        st.dataframe(df.sort_values("date", ascending=False))
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV Exportieren", data=csv, file_name="preise.csv", mime="text/csv")


                # Preisalarm prüfen & ggf. Benachrichtigung
        if 'alarm_price' in st.session_state and 'email' in st.session_state and 'smtp' in st.session_state:
            alarm_df = df[df['price'] <= st.session_state.alarm_price]
            if not alarm_df.empty and st.button("📧 Alarmbenachrichtigung senden"):
                message = "Preisalarm ausgelöst für folgende Produkte:\n\n"
                for _, row in alarm_df.iterrows():
                    message += f"- {row['product']} ({row['price']} € am {row['date'].strftime('%d.%m.%Y')})\n"
                success = send_email(
                    subject="🔔 Preisalarm RTX 5070 Ti",
                    body=message,
                    to_email=st.session_state.email,
                    **st.session_state.smtp
                )
                if success:
                    st.success("📨 Benachrichtigung erfolgreich gesendet!")

# === Automatisches Update alle 24 Stunden ===
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.min

if (datetime.now() - st.session_state.last_update) > timedelta(hours=24):
    with st.spinner("⏳ Automatisches Update läuft..."):
        auto_data = []
        for name, url in products.items():
            price, date = robust_scrape(url)
            if price:
                auto_data.append({'product': name, 'price': price, 'date': date, 'url': url})
                time.sleep(1)
        if auto_data:
            save_daily_data(auto_data)
            st.session_state.last_update = datetime.now()
            st.success("✅ Automatisches Update abgeschlossen! Bitte Seite manuell neu laden.")
