import json
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = FastAPI(title="Social Design Scraper API")

HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Poster Scraper</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white p-8 font-sans min-h-screen">
    <div class="max-w-7xl mx-auto">
        <div class="flex items-center gap-4 mb-2">
            <h1 class="text-4xl font-bold tracking-tight">Social Design API</h1>
            <div class="flex gap-2">
                <span class="bg-red-600 text-xs font-bold px-2 py-1 rounded">Pinterest</span>
                <span class="bg-pink-600 text-xs font-bold px-2 py-1 rounded">Dribbble</span>
                <span class="bg-gradient-to-r from-purple-500 to-orange-500 text-xs font-bold px-2 py-1 rounded">Instagram</span>
            </div>
        </div>
        <p class="text-gray-400 mb-8">Bypassing login walls using advanced site-dorking to extract high-res design assets.</p>
        
        <div class="flex gap-4 mb-8">
            <input id="searchInput" type="text" placeholder="e.g., Cyberpunk typography" 
                   class="w-full p-4 rounded-xl bg-gray-900 border border-gray-800 text-white focus:outline-none focus:border-pink-500 transition shadow-inner"
                   value="Cyberpunk typography">
            <button onclick="searchPosters()" id="btn"
                    class="px-8 py-4 bg-white text-black hover:bg-gray-200 rounded-xl font-bold transition whitespace-nowrap shadow-lg">
                Scrape Platforms
            </button>
        </div>
        
        <div id="loader" class="hidden flex justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-pink-500"></div>
        </div>
        
        <div id="grid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6"></div>
    </div>

    <script>
        function getBadge(domain) {
            if (domain.includes('pinterest')) return '<span class="bg-red-600 text-white text-[10px] font-bold px-2 py-1 rounded-full absolute top-3 left-3 shadow">Pinterest</span>';
            if (domain.includes('dribbble')) return '<span class="bg-pink-500 text-white text-[10px] font-bold px-2 py-1 rounded-full absolute top-3 left-3 shadow">Dribbble</span>';
            if (domain.includes('instagram')) return '<span class="bg-gradient-to-r from-purple-500 to-orange-500 text-white text-[10px] font-bold px-2 py-1 rounded-full absolute top-3 left-3 shadow">Instagram</span>';
            return `<span class="bg-gray-700 text-white text-[10px] font-bold px-2 py-1 rounded-full absolute top-3 left-3 shadow">${domain}</span>`;
        }

        async function searchPosters() {
            const topic = document.getElementById('searchInput').value;
            const btn = document.getElementById('btn');
            const loader = document.getElementById('loader');
            const grid = document.getElementById('grid');
            
            btn.disabled = true;
            btn.innerText = "Extracting...";
            grid.innerHTML = "";
            loader.classList.remove('hidden');
            
            try {
                const res = await fetch(`/api/search?topic=${encodeURIComponent(topic)}&limit=30`);
                const data = await res.json();
                
                grid.innerHTML = data.results.map(p => `
                    <div class="bg-gray-900 rounded-xl overflow-hidden border border-gray-800 hover:border-pink-500 transition group relative shadow-lg">
                        ${getBadge(p.platform_domain)}
                        <a href="${p.image_url}" target="_blank" class="block">
                            <img src="${p.thumbnail_url}" class="w-full h-72 object-cover" loading="lazy">
                            <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition duration-300 flex items-center justify-center pointer-events-none">
                                <span class="opacity-0 group-hover:opacity-100 bg-white text-black px-4 py-2 rounded-full text-sm font-bold shadow-2xl transform translate-y-4 group-hover:translate-y-0 transition">
                                    View Asset
                                </span>
                            </div>
                        </a>
                        <div class="p-4">
                            <p class="text-sm text-gray-300 truncate font-medium" title="${p.title}">${p.title}</p>
                            <a href="${p.source_page}" target="_blank" class="text-xs text-gray-500 mt-2 inline-block hover:text-pink-400 transition">View Original Post &rarr;</a>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                grid.innerHTML = `<p class="text-red-400 col-span-full text-center py-10">Error scraping data from platforms.</p>`;
            } finally {
                loader.classList.add('hidden');
                btn.disabled = false;
                btn.innerText = "Scrape Platforms";
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
def scrape_social_posters(
    topic: str = Query(..., description="E.g. 'cyberpunk typography'"), 
    limit: int = 30
):
    clean_topic = topic.strip()
    
    # 1. Inject target platforms directly into the search string using OR operators
    target_sites = "(site:pinterest.com OR site:dribbble.com OR site:instagram.com)"
    
    if "poster" in clean_topic.lower():
        search_term = f"{clean_topic} {target_sites}"
    else:
        search_term = f"{clean_topic} poster {target_sites}"

    # 2. Strict constraints: Tall aspect ratio (posters) + Large sizes only
    filters = "+filterui:aspect-tall+filterui:imagesize-large"
    url = f"https://www.bing.com/images/search?q={search_term.replace(' ', '+')}&qft={filters}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Target extraction failed: {str(e)}")
        
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    
    for a in soup.find_all("a", class_="iusc"):
        m_data = a.get("m")
        if m_data:
            try:
                data = json.loads(m_data)
                murl = data.get("murl") 
                turl = data.get("turl")
                source_url = data.get("purl", "")
                
                if not murl or murl.startswith("data:") or "icon" in murl.lower():
                    continue
                    
                # Extract clean domain name for the UI badges
                domain = urlparse(source_url).netloc.replace("www.", "")
                
                if murl not in [r["image_url"] for r in results]:
                    results.append({
                        "title": data.get("t", f"{clean_topic} Design"),
                        "image_url": murl,
                        "thumbnail_url": turl,
                        "source_page": source_url,
                        "platform_domain": domain
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
