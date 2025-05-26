import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import cloudscraper
import logging
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

# ========== LOGGING KONFIGURATION ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('price_tracker.log')
    ]
)

logger = logging.getLogger(__name__)

# ========== KONSTANTEN ==========
@dataclass
class Config:
    TIMEZONE: Optional[str] = None
    DATA_DIR: Path = Path("preis_daten")
    REFRESH_INTERVAL: int = 3600  # 1 Stunde in Sekunden
    MAX_RETRIES: int = 3
    TIMEOUT: int = 10
    MAX_WORKERS: int = 5
    HEADERS: Dict[str, str] = None
    
    def __post_init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)
        self.HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }

config = Config()

# ========== DESIGN-EINSTELLUNGEN ==========
class ThemeConfig:
    PRIMARY_COLOR = "#FF4B4B"
    SECONDARY_COLOR = "#1F77B4"
    BG_COLOR = "#F4F4F4"
    TEXT_COLOR = "#333"
    FONT = "Helvetica Neue, sans-serif"

    @classmethod
    def apply_theme(cls):
        st.set_page_config(
            page_title="GPU Preis-Tracker Pro",
            page_icon="💻",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.markdown(f"""
            <style>
                .main {{
                    background-color: {cls.BG_COLOR};
                    color: {cls.TEXT_COLOR};
                    font-family: {cls.FONT};
                }}
                .stButton>button {{
                    background-color: {cls.PRIMARY_COLOR};
                    color: white;
                    border-radius: 5px;
                    padding: 0.5rem 1rem;
                    transition: background-color 0.3s ease;
                }}
                .stButton>button:hover {{
                    background-color: #FF6464;
                }}
                .stAlert {{
                    border-left: 4px solid {cls.PRIMARY_COLOR};
                }}
                .stProgress > div > div > div {{
                    background-color: {cls.PRIMARY_COLOR};
                }}
                .price-card {{
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 15px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .price-change-positive {{
                    color: #e74c3c;
                    font-weight: bold;
                }}
                .price-change-negative {{
                    color: #2ecc71;
                    font-weight: bold;
                }}
            </style>
        """, unsafe_allow_html=True)

# ========== DATENMODELLE ==========
@dataclass
class Product:
    name: str
    url: str
    price: Optional[float] = None
    date: Optional[datetime] = None

class ProductCatalog:
    def __init__(self):
        self.products_5070ti = {
            "Gainward RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
            "MSI RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html",
            "Palit RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-v186845.html",
            "Gainward Phoenix": "https://geizhals.at/gainward-geforce-rtx-5070-ti-phoenix-v1-5509-ne7507t019t2-gb2031c-a3470768.html",
            "MSI Gaming Trio": "https://geizhals.at/msi-geforce-rtx-5070-ti-16g-gaming-trio-oc-a3445122.html",
            "ASUS ROG Strix": "https://geizhals.at/asus-rog-strix-geforce-rtx-5070-ti-oc-a3382464.html",
        }
        
        self.products_5080 = {
            "Palit GeForce RTX 5080 GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-v1-ne75080019t2-gb2031y-a3487808.html",
            "Zotac GeForce RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html",
            "INNO3D GeForce RTX 5080 X3": "https://geizhals.at/inno3d-geforce-rtx-5080-x3-n50803-16d7-176068n-a3382794.html",
            "Gainward GeForce RTX 5080 Phoenix GS V1": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
        }

# ========== SCRAPING & DATENVERARBEITUNG ==========
class PriceScraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        
    @st.cache_data(ttl=3600)
    def scrape_price(self, url: str) -> Tuple[Optional[float], Optional[datetime]]:
        """Verbesserte Version der Scraping-Funktion mit Caching und besserer Fehlerbehandlung."""
        for attempt in range(config.MAX_RETRIES):
            try:
                res = self.scraper.get(url, headers=config.HEADERS, timeout=config.TIMEOUT)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, 'html.parser')

                price_element = (
                    soup.find('strong', id='pricerange-min') or
                    soup.find('span', class_='price') or
                    soup.find('div', class_='gh_price')
                )

                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = float(''.join(c for c in price_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                    date = datetime.now(config.TIMEZONE)
                    
                    if self._validate_price_data(price, date):
                        logger.info(f"Erfolgreich gescraped: {url} - Preis: {price}€")
                        return price, date
                    
            except Exception as e:
                logger.error(f"Fehler bei Versuch {attempt + 1} für {url}: {str(e)}")
                time.sleep(2 ** attempt)
                
        return None, None

    def _validate_price_data(self, price: float, date: datetime) -> bool:
        """Validiert die gescrapten Preisdaten."""
        return price is not None and price > 0 and date is not None

class DataManager:
    def __init__(self):
        self.scraper = PriceScraper()
        
    def save_data(self, data: List[Dict], filepath: Path) -> None:
        """Speichert die Preisdaten mit Backup-Funktion."""
        try:
            df = pd.DataFrame(data)
            if not df.empty:
                existing = self.load_data(filepath)
                
                updated = pd.concat([existing, df]).drop_duplicates(subset=['product', 'date'])
                updated = updated.sort_values('date')
                
                backup_path = filepath.with_suffix('.backup')
                if filepath.exists():
                    filepath.rename(backup_path)
                
                updated.to_json(filepath, orient='records', indent=2)
                
                if backup_path.exists():
                    backup_path.unlink()
                    
                logger.info(f"Daten erfolgreich gespeichert in {filepath}")
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Daten: {str(e)}")
            if backup_path.exists():
                backup_path.rename(filepath)

    def load_data(self, filepath: Path) -> pd.DataFrame:
        """Lädt die Preisdaten aus einer Datei."""
        try:
            if filepath.exists():
                return pd.read_json(filepath)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten: {str(e)}")
        return pd.DataFrame()

    def scrape_products(self, products: Dict[str, str]) -> List[Dict]:
        """Scrapt die Preise für mehrere Produkte parallel."""
        data = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_product = {
                executor.submit(self.scraper.scrape_price, url): (name, url)
                for name, url in products.items()
            }
            
            for future in future_to_product:
                name, url = future_to_product[future]
                try:
                    price, date = future.result()
                    if price is not None and date is not None:
                        data.append({
                            'product': name,
                            'price': price,
                            'date': date,
                            'url': url
                        })
                except Exception as e:
                    logger.error(f"Fehler beim Scrapen von {name}: {str(e)}")
        
        return data

# ========== UI KOMPONENTEN ==========
class PriceCard:
    @staticmethod
    def create(product: str, current_price: float, price_change: Optional[float], percent_change: Optional[float]):
        if price_change is not None and percent_change is not None:
            change_direction = "positive" if price_change > 0 else "negative"
            change_icon = "📈" if price_change > 0 else "📉"
            
            st.markdown(f"""
            <div class="price-card">
                <h3>{product}</h3>
                <h2>{current_price:.2f}€</h2>
                <p>{change_icon} <span class="price-change-{change_direction}">
                {price_change:+.2f}€ ({percent_change:+.2f}%)</span></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="price-card">
                <h3>{product}</h3>
                <h2>{current_price:.2f}€</h2>
                <p>Keine Vergleichsdaten</p>
            </div>
            """, unsafe_allow_html=True)

class PriceDashboard:
    def __init__(self):
        self.data_manager = DataManager()
        self.catalog = ProductCatalog()
        
    def run(self):
        ThemeConfig.apply_theme()
        
        st.title("💻 GPU Preis-Tracker Pro")
        
        tab1, tab2, tab3 = st.tabs(["5070 Ti", "5080", "📈 Preis-Dashboard"])
        
        with tab1:
            self.show_product_tab("5070 Ti", self.catalog.products_5070ti)
            
        with tab2:
            self.show_product_tab("5080", self.catalog.products_5080)
            
        with tab3:
            self.show_dashboard()

    def show_product_tab(self, title: str, products: Dict[str, str]):
        st.header(f"Preisübersicht für {title}")
        
        data = self.data_manager.scrape_products(products)
        filepath = config.DATA_DIR / f"preise_{title.lower().replace(' ', '')}.json"
        
        self.data_manager.save_data(data, filepath)
        df = self.data_manager.load_data(filepath)
        
        if not df.empty:
            st.dataframe(df[['product', 'price', 'date', 'url']], use_container_width=True)
        else:
            st.warning("Keine Daten verfügbar")

    def show_dashboard(self):
        df_5070ti = self.data_manager.load_data(config.DATA_DIR / "preise_5070ti.json")
        df_5080 = self.data_manager.load_data(config.DATA_DIR / "preise_5080.json")
        
        df = pd.concat([df_5070ti, df_5080], ignore_index=True)
        
        if not df.empty:
            self.show_timeframe_selection()
            self.show_quick_selection(df)
            self.show_price_trends(df)
            self.show_statistics(df)
        else:
            st.warning("Keine Daten für das Dashboard verfügbar")

    def show_timeframe_selection(self):
        st.subheader("Zeitraum auswählen")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("1 Woche", key="week_btn"):
                st.session_state.timeframe = "1 Woche"
        with col2:
            if st.button("1 Monat", key="month_btn"):
                st.session_state.timeframe = "1 Monat"
        with col3:
            if st.button("1 Jahr", key="year_btn"):
                st.session_state.timeframe = "1 Jahr"
                
        if 'timeframe' not in st.session_state:
            st.session_state.timeframe = "1 Monat"

    def show_quick_selection(self, df: pd.DataFrame):
        st.subheader("Schnellauswahl")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Alle RTX 5070 Ti Modelle"):
                st.session_state.selected_products = [p for p in df['product'].unique() if "5070" in p]
                st.rerun()
        with col2:
            if st.button("Alle RTX 5080 Modelle"):
                st.session_state.selected_products = [p for p in df['product'].unique() if "5080" in p]
                st.rerun()
        with col3:
            if st.button("Auswahl zurücksetzen"):
                st.session_state.selected_products = []
                st.rerun()

    def show_price_trends(self, df: pd.DataFrame):
        try:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            days = 7 if st.session_state.timeframe == "1 Woche" else 30 if st.session_state.timeframe == "1 Monat" else 365
            cutoff_date = datetime.now() - timedelta(days=days)
            df_filtered = df[df['date'] >= cutoff_date].copy()
            
            if 'selected_products' not in st.session_state:
                st.session_state.selected_products = df['product'].unique()[:3]
            
            selected_products = st.multiselect(
                "Modelle auswählen",
                options=df['product'].unique(),
                default=st.session_state.selected_products,
                key="model_selection"
            )
            
            if not selected_products:
                st.warning("Bitte wählen Sie mindestens ein Modell aus")
                return
            
            self.show_price_cards(df_filtered, selected_products, days)
            self.show_price_chart(df_filtered, selected_products)
            
        except Exception as e:
            logger.error(f"Fehler bei der Preisanalyse: {str(e)}")
            st.error("Fehler bei der Anzeige der Preistrends")

    def show_price_cards(self, df: pd.DataFrame, selected_products: List[str], days: int):
        st.subheader("Aktuelle Preise")
        cols = st.columns(len(selected_products))
        
        for idx, product in enumerate(selected_products):
            with cols[idx]:
                product_data = df[df['product'] == product]
                if not product_data.empty:
                    current_price = product_data.iloc[-1]['price']
                    price_change, pct_change = self.calculate_price_change(product_data, product, days)
                    PriceCard.create(product, current_price, price_change, pct_change)

    def show_price_chart(self, df: pd.DataFrame, selected_products: List[str]):
        st.subheader("Preisverlauf")
        fig = go.Figure()
        
        for product in selected_products:
            product_data = df[df['product'] == product]
            if not product_data.empty:
                fig.add_trace(go.Scatter(
                    x=product_data['date'],
                    y=product_data['price'],
                    name=product,
                    mode='lines+markers'
                ))
        
        fig.update_layout(
            title=f"Preisentwicklung - {st.session_state.timeframe}",
            xaxis_title="Datum",
            yaxis_title="Preis (€)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    def show_statistics(self, df: pd.DataFrame):
        with st.expander("Statistische Analyse"):
            try:
                st.subheader("Preisstatistiken")
                stats = df.groupby('product')['price'].agg(['min', 'max', 'mean', 'std', 'count'])
                st.dataframe(stats.style.format("{:.2f}"))
            except Exception as e:
                logger.error(f"Fehler bei Statistiken: {str(e)}")
                st.error("Fehler bei der Anzeige der Statistiken")

    @staticmethod
    def calculate_price_change(df: pd.DataFrame, product: str, days: int) -> Tuple[Optional[float], Optional[float]]:
        try:
            product_data = df[df['product'] == product].sort_values('date')
            if len(product_data) < 2:
                return None, None
            
            current_price = product_data.iloc[-1]['price']
            cutoff_date = datetime.now() - timedelta(days=days)
            past_data = product_data[product_data['date'] >= cutoff_date.strftime('%Y-%m-%d')]
            
            if len(past_data) == 0:
                return None, None
            
            past_price = past_data.iloc[0]['price']
            price_change = current_price - past_price
            percent_change = (price_change / past_price) * 100
            
            return price_change, percent_change
            
        except Exception as e:
            logger.error(f"Fehler bei der Preisänderungsberechnung: {str(e)}")
            return None, None

if __name__ == "__main__":
    dashboard = PriceDashboard()
    dashboard.run()
