import json
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup

# Vercel will now find this because standard 'requests' won't crash the server build
app = FastAPI(title="High-Res Poster Scraper API on Vercel")

HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HD Poster Scraper</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white p-8 font-sans">
    <div class="max-w-6xl mx-auto">
        <div class="flex items-center gap-4 mb-2">
            <h1 class="text-4xl font-bold">HD Poster API</h1>
            <span class="bg-green-600 text-xs font-bold px-2 py-1 rounded">Strict High-Res</span>
        </div>
        <p class="text-gray-400 mb-8">Scraping exact queries with forced vertical and large-size filters.</p>
        
        <div class="flex gap-4 mb-8">
            <input id="searchInput" type="text" placeholder="e.g., Onam malayalam poster" 
                   class="w-full p-4 rounded-lg bg-gray-800 border border-gray-700 text-white focus:outline-none focus:border-blue-500"
                   value="Onam malayalam poster">
            <button onclick="searchPosters()" id="btn"
                    class="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition whitespace-nowrap">
                Scrape HD
            </button>
        </div>
        
        <div id="loader" class="hidden text-center py-10 text-blue-400 font-bold animate-pulse">
            Fetching High-Quality Posters...
        </div>
        
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
                    <div class="bg-gray-800 rounded-lg overflow-hidden border border-gray-700 hover:border-green-500 transition group">
                        <a href="${p.image_url}" target="_blank" class="block relative">
                            <img src="${p.thumbnail_url}" class="w-full h-80 object-cover" loading="lazy">
                            <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition flex items-center justify-center">
                                <span class="opacity-0 group-hover:opacity-100 bg-green-600 text-white px-3 py-1 rounded-full text-sm font-bold shadow-lg">
                                    View Full HD
                                </span>
                            </div>
                        </a>
                        <div class="p-4">
                            <p class="text-sm text-gray-300 truncate" title="${p.title}">${p.title}</p>
                            <a href="${p.source_page}" target="_blank" class="text-xs text-blue-400 mt-2 inline-block hover:underline">Website Source &rarr;</a>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                grid.innerHTML = `<p class="text-red-400">Error scraping data.</p>`;
            } finally {
                loader.classList.add('hidden');
                btn.disabled = false;
                btn.innerText = "Scrape HD";
            }
        }
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
    topic: str = Query(..., description="Exact search query, e.g. 'Onam malayalam poster'"), 
    limit: int = 20
):
    clean_topic = topic.strip()
    
    if "poster" in clean_topic.lower():
        search_term = clean_topic
    else:
        search_term = f"{clean_topic} poster"

    filters = "+filterui:aspect-tall+filterui:imagesize-large"
    url = f"https://www.bing.com/images/search?q={search_term.replace(' ', '+')}&qft={filters}"
    
    # Standard requests with Chrome headers works natively on Vercel
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
        
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    
    for a in soup.find_all("a", class_="iusc"):
        m_data = a.get("m")
        if m_data:
            try:
                data = json.loads(m_data)
                murl = data.get("murl") 
                turl = data.get("turl") 
                
                if not murl or murl.startswith("data:") or "icon" in murl.lower():
                    continue
                
                if murl not in [r["image_url"] for r in results]:
                    results.append({
                        "title": data.get("t", f"{clean_topic} Poster"),
                        "image_url": murl,
                        "thumbnail_url": turl,
                        "source_page": data.get("purl")
                    })
                    
                if len(results) >= limit:
                    break
            except Exception:
                continue
                
    return {
        "topic": clean_topic,
        "count": len(results), 
        "results": results
    }
