import re

# Read original scraper
with open('/root/seinfeld/scrape_seinfeld.py', 'r') as f:
    content = f.read()

# Define fixed scrape_scripts function with escaped newlines
fixed_function = '''
def scrape_scripts():
    """Scrape full scripts from SeinfeldScripts"""
    logging.info("Scraping Seinfeld scripts")
    base_url = "https://www.seinfeldscripts.com/"
    index_content = fetch_with_retry(base_url)
    if not index_content:
        return {}
    
    soup = BeautifulSoup(index_content, 'html.parser')
    scripts = {}
    
    # Find all season pages
    season_links = []
    for link in soup.select('a[href$=".html"]'):
        href = link.get('href')
        if "season" in href.lower():
            season_links.append(href)
    
    logging.info(f"Found {len(season_links)} season pages")
    
    # Process each season page
    for season_link in season_links:
        season_url = base_url + season_link
        season_content = fetch_with_retry(season_url)
        if not season_content:
            continue
            
        season_soup = BeautifulSoup(season_content, 'html.parser')
        
        # Find episode links in season page
        for link in season_soup.select('a[href$=".html"]'):
            href = link.get('href')
            if "season" in href.lower() or href == 'index.html':
                continue
                
            title = link.text.strip().replace('"', '')
            script_url = base_url + href
            script_content = fetch_with_retry(script_url)
            if script_content:
                script_soup = BeautifulSoup(script_content, 'html.parser')
                content_div = script_soup.find('div')
                if content_div:
                    script_text = content_div.get_text()
                    # Use escaped newline characters
                    scripts[title] = "```text\n" + script_text + "\n```"
                else:
                    scripts[title] = "Script format not recognized"
    
    logging.info(f"Found {len(scripts)} scripts")
    return scripts
'''

# Replace old function with fixed version
pattern = r'def scrape_scripts\(\).*?return scripts'
new_content = re.sub(pattern, fixed_function, content, flags=re.DOTALL)

# Write fixed scraper
with open('/root/seinfeld/scrape_seinfeld_fixed.py', 'w') as f:
    f.write(new_content)
