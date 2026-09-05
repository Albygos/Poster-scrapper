import os
import json
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from curl_cffi import requests
from bs4 import BeautifulSoup
import uvicorn

app = FastAPI(title="Advanced Poster Scraper API")

# Embedded UI for immediate testing in the browser
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Limitless Poster Scraper</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white p-8 font-sans">
    <div class="max-w-6xl mx-auto">
        <h1 class="text-4xl font-bold mb-2">Live Poster API</h1>
        <p class="text-gray-400 mb-8">Bypasses bot-protection using curl_cffi and scrapes tall aspect-ratio posters.</p>
        
        <div class="flex gap-4 mb-8">
            <input id="searchInput" type="text" placeholder="e.g., Cyberpunk Synthwave" 
                   class="w-full p-4 rounded-lg bg-gray-800 border border-gray-700 text-white focus:outline-none focus:border-blue-500"
                   value="Vintage Jazz">
            <button onclick="searchPosters()" id="btn"
                    class="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition">
                Scrape
            </button>
        </div>
        
        <div id="loader" class="hidden text-center py-10 text-gray-400">Scraping the web... (impersonating Chrome)</div>
        
        <div id="grid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"></div>
    </div>

    <script>
        async function searchPosters() {
            const topic = document.getElementById('searchInput').value;
            const btn = document.getElementById('btn');
            const loader = document.getElementById('loader');
            const grid = document.getElementById('grid');
            
            btn.disabled = true;
            btn.innerText = "Working...";
            grid.innerHTML = "";
            loader.classList.remove('hidden');
            
            try {
                const res = await fetch(`/api/search?topic=${encodeURIComponent(topic)}&limit=20`);
                const data = await res.json();
                
                grid.innerHTML = data.results.map(p => `
                    <div class="bg-gray-800 rounded-lg overflow-hidden border border-gray-700 hover:border-blue-500 transition">
                        <a href="${p.image_url}" target="_blank">
                            <img src="${p.thumbnail_url}" class="w-full h-72 object-cover" loading="lazy">
                        </a>
                        <div class="p-4">
                            <p class="text-sm text-gray-300 truncate" title="${p.title}">${p.title}</p>
                            <a href="${p.source_page}" target="_blank" class="text-xs text-blue-400 mt-2 inline-block">View Source &rarr;</a>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                grid.innerHTML = `<p class="text-red-400">Error scraping data.</p>`;
            } finally {
                loader.classList.add('hidden');
                btn.disabled = false;
                btn.innerText = "Scrape";
            }
        }
        // Auto-load on open
        searchPosters();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return HTML_UI

@app.get("/api/search")
def scrape_posters(
    topic: str = Query(..., description="Theme, e.g. 'vintage jazz'"), 
    limit: int = 20
):
    # Enforce poster aspect ratio (tall) directly at the search engine level
    query = f"{topic} poster design"
    url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}&qft=+filterui:aspect-tall"
    
    # curl_cffi spoofs the exact TLS/JA3 fingerprints of Google Chrome
    session = requests.Session(impersonate="chrome")
    
    try:
        response = session.get(url, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
        
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    
    for a in soup.find_all("a", class_="iusc"):
        m_data = a.get("m")
        if m_data:
            try:
                data = json.loads(m_data)
                murl = data.get("murl") # High resolution source
                turl = data.get("turl") # Thumbnail
                
                # Deduplicate and validate
                if murl and murl not in [r["image_url"] for r in results]:
                    results.append({
                        "title": data.get("t", f"{topic} Poster"),
                        "image_url": murl,
                        "thumbnail_url": turl,
                        "source_page": data.get("purl")
                    })
                    
                if len(results) >= limit:
                    break
            except Exception:
                continue
                
    return {
        "topic": topic, 
        "count": len(results), 
        "results": results
    }

if __name__ == "__main__":
    # Dynamically binds to Render's required PORT environment variable
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
