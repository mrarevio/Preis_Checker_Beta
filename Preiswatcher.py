async def async_scrape(session, url, name):
    cache_key = f"{url}_{datetime.now().strftime('%Y-%m-%d-%H')}"
    if cache_key in price_cache:
        return price_cache[cache_key]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                preis_element = soup.find('strong', id='pricerange-min') or soup.find('span', class_='price')

                if preis_element:
                    preis_text = preis_element.get_text(strip=True)
                    preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                    datum = datetime.now(TIMEZONE)
                    result = {'product': name, 'price': preis, 'date': datum, 'url': url}
                    price_cache[cache_key] = result
                    return result
    except Exception as e:
        print(f"Fehler beim Scrapen von {url}: {e}")
    return None

async def fetch_all_prices(products):
    async with aiohttp.ClientSession() as session:
        tasks = [async_scrape(session, url, name) for name, url in products.items()]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

@st.cache_data(ttl=3600)
def load_and_process_data(file_path):
    if os.path.exists(file_path):
        return pd.read_json(file_path)
    return pd.DataFrame()

def speichere_tagesdaten(daten, dateipfad):
    if not daten:
        return
        
    df = pd.DataFrame(daten)
    if not df.empty:
        vorhanden = load_and_process_data(dateipfad)
        aktualisiert = pd.concat([vorhanden, df], ignore_index=True)
        aktualisiert.to_json(dateipfad, orient='records', indent=2)

async def main():
    # === Preisübersichten ===
    st.header("Preisübersicht für 5070 Ti")
    daten_5070ti = await fetch_all_prices(produkte_5070ti)
    speichere_tagesdaten(daten_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))
    df_5070ti = load_and_process_data(os.path.join(DATA_DIR, "preise_5070ti.json"))
    st.dataframe(df_5070ti[['product', 'price', 'date', 'url']], use_container_width=True)

    st.header("Preisübersicht für 5080")
    daten_5080 = await fetch_all_prices(produkte_5080)
    speichere_tagesdaten(daten_5080, os.path.join(DATA_DIR, "preise_5080.json"))
    df_5080 = load_and_process_data(os.path.join(DATA_DIR, "preise_5080.json"))
    st.dataframe(df_5080[['product', 'price', 'date', 'url']], use_container_width=True)

if __name__ == "__main__":
    asyncio.run(main())
