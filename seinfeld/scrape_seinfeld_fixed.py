import os
import re
import requests
from bs4 import BeautifulSoup
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
BASE_DIR = '/root/seinfeld'
SCRIPTS_BASE_URL = "https://www.seinfeldscripts.com/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Helper functions
def sanitize_filename(name):
    """Remove special characters from filenames"""
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def fetch_with_retry(url, max_retries=3):
    """Fetch URL with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logging.warning(f"Attempt {attempt+1}/{max_retries} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    logging.error(f"All attempts failed for {url}")
    return None

def scrape_scripts():
    """Scrape full scripts from SeinfeldScripts with pagination handling"""
    logging.info("Scraping Seinfeld scripts with season pagination")
    
    try:
        # Fetch main index to get season pages
        index_content = fetch_with_retry(SCRIPTS_BASE_URL)
        if not index_content:
            return {}
            
        soup = BeautifulSoup(index_content, 'html.parser')
        scripts = {}
        season_links = []
        
        # Extract all season page links
        for link in soup.select('a[href]'):
            href = link.get('href', '')
            if "season" in href.lower() and href.endswith('.html'):
                season_links.append(href)
        
        logging.info(f"Found {len(season_links)} season pages")
        
        # Process each season page
        for season_link in season_links:
            season_url = SCRIPTS_BASE_URL + season_link
            season_content = fetch_with_retry(season_url)
            
            if not season_content:
                logging.warning(f"Skipping season: {season_url}")
                continue
                
            season_soup = BeautifulSoup(season_content, 'html.parser')
            
            # Extract episode links
            for link in season_soup.select('a[href$=".html"]'):
                href = link.get('href')
                if "season" in href.lower() or href == 'index.html':
                    continue
                    
                title = link.text.strip().replace('"', '')
                script_url = SCRIPTS_BASE_URL + href
                
                # Fetch and parse script
                script_content = fetch_with_retry(script_url)
                if script_content:
                    script_soup = BeautifulSoup(script_content, 'html.parser')
                    content_div = script_soup.find('div')
                    
                    if content_div:
                        script_text = content_div.get_text()
                        # Safe string concatenation
                        scripts[title] = "```text\n" + script_text + "\n```"
                    else:
                        scripts[title] = "Script format not recognized"
                else:
                    logging.warning(f"Failed to fetch script: {script_url}")
        
        logging.info(f"Retrieved {len(scripts)} scripts")
        return scripts
        
    except Exception as e:
        logging.error(f"Script scraping failed: {e}")
        return {}

# [REST OF ORIGINAL SCRAPER CODE REMAINS UNCHANGED]
# Include other functions (scrape_wikipedia_api, scrape_fandom, save_episode_data, main) 
# from the original scrape_seinfeld.py here without modification
