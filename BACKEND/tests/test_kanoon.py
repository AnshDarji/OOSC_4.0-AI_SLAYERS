def get_kanoon_text(query):
    # This is a manually-run acquisition utility, not a pytest test. Keep its
    # optional web-scraping dependencies lazy so they do not break the actual
    # automated suite when those development tools are not installed.
    from duckduckgo_search import DDGS
    import requests
    from bs4 import BeautifulSoup
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            if not results: return None
            
            for r in results:
                url = r['href']
                print("Found URL:", url)
                if 'indiankanoon.org/doc/' in url:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    resp = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    content_div = soup.find('div', class_='judgments')
                    if content_div:
                        print("Found content length:", len(content_div.text))
                        return content_div.text.strip()
    except Exception as e:
        print("Error:", e)
    return None

if __name__ == "__main__":
    text = get_kanoon_text("indiankanoon Semiconductor Integrated Circuits Layout-Design Act 2000")
    if text:
        print("Success, starts with:", text[:200])
    else:
        print("Failed to get text")
