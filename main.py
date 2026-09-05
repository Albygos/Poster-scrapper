    topic: str = Query(..., description="E.g. 'cyberpunk typography'"), 
    limit: int = 30
):
    clean_topic = topic.strip()
    
    # 1. Advanced dorking to isolate the sources at the search engine level
    target_sites = "(site:pinterest.com OR site:dribbble.com OR site:instagram.com)"
    search_term = f"{clean_topic} poster {target_sites}"
    
    # Force vertical layouts and large resolution
    filters = "+filterui:aspect-tall+filterui:imagesize-large"
    url = f"https://www.bing.com/images/search?q={search_term.replace(' ', '+')}&qft={filters}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Target extraction failed: {str(e)}")
        
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    
    # 2. Hardcoded backend verification list
    allowed_domains = ["pinterest.", "dribbble.", "instagram."]
    
    for a in soup.find_all("a", class_="iusc"):
        m_data = a.get("m")
        if m_data:
            try:
                data = json.loads(m_data)
                murl = data.get("murl") 
                turl = data.get("turl")
                source_url = data.get("purl", "")
                
                # Verify domain validity
                if not source_url:
                    continue
                    
                domain_netloc = urlparse(source_url).netloc.lower()
                
                # 3. STRICT ENFORCEMENT: Kill the row if it's not one of our 3 targets
                if not any(allowed in domain_netloc for allowed in allowed_domains):
                    continue
                
                # Kill bad image links
                if not murl or murl.startswith("data:") or "icon" in murl.lower():
                    continue
                
                # Clean up the domain name for the UI tag
                clean_domain = domain_netloc.replace("www.", "")
                
                # Deduplicate
                if murl not in [r["image_url"] for r in results]:
                    results.append({
                        "title": data.get("t", f"{clean_topic} Design"),
                        "image_url": murl,
                        "thumbnail_url": turl,
                        "source_page": source_url,
                        "platform_domain": clean_domain
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
