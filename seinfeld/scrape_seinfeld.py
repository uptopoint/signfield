import os
import re
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import time
import logging
import wikipedia

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
BASE_DIR = '/root/seinfeld'
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Seinfeld_episodes"
FANDOM_URL = "https://seinfeld.fandom.com/wiki/List_of_Seinfeld_episodes"
SCRIPTS_URL = "https://www.seinfeldscripts.com/index.html"
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

def scrape_wikipedia_api():
    """Scrape episode data using Wikipedia API"""
    logging.info("Scraping Wikipedia episode data using API")
    wikipedia.set_lang("en")
    episodes = {}
    
    try:
        # Get the page content
        page = wikipedia.page("List_of_Seinfeld_episodes")
        content = page.html()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all season tables
        season_tables = soup.find_all('table', {'class': 'wikitable'})
        logging.info(f"Found {len(season_tables)} season tables via API")
        
        for i, table in enumerate(season_tables):
            season = i + 1
            
            # Process each episode row
            for row in table.find_all('tr')[1:]:  # Skip header row
                cells = row.find_all(['th', 'td'])
                if len(cells) < 5:
                    continue
                
                try:
                    ep_num = cells[0].text.strip()
                    title = cells[1].text.strip()
                    plot = cells[4].text.strip()  # Plot is in the 5th cell
                    
                    key = f"S{season}E{ep_num}"
                    episodes[key] = {
                        'season': season,
                        'episode': ep_num,
                        'title': title,
                        'plot': plot
                    }
                except Exception as e:
                    logging.error(f"Error processing Wikipedia row: {e}")
    except Exception as e:
        logging.error(f"Wikipedia API error: {e}")
    
    logging.info(f"Found {len(episodes)} episodes on Wikipedia")
    return episodes

def scrape_fandom():
    """Scrape character insights from Fandom"""
    logging.info("Scraping Fandom character insights")
    content = fetch_with_retry(FANDOM_URL)
    if not content:
        return {}
    
    soup = BeautifulSoup(content, 'html.parser')
    insights = {}
    
    # Find episode links in the main table
    table = soup.find('table', {'class': 'wikitable'})
    if not table:
        logging.error("Fandom episode table not found")
        return {}
        
    for row in table.select('tr')[1:]:  # Skip header row
        cells = row.select('td')
        if len(cells) < 2:
            continue
            
        link = cells[1].find('a')
        if not link:
            continue
            
        episode_url = "https://seinfeld.fandom.com" + link['href']
        ep_content = fetch_with_retry(episode_url)
        
        if not ep_content:
            continue
            
        ep_soup = BeautifulSoup(ep_content, 'html.parser')
        title = ep_soup.find('h1').text.replace('"', '').strip()
        
        # Extract character insights section
        insights_section = ep_soup.find('span', {'id': 'Characters'})
        if insights_section:
            content = ''
            next_node = insights_section.parent.find_next_sibling()
            while next_node and next_node.name != 'h2':
                content += str(next_node)
                next_node = next_node.find_next_sibling()
            insights[title] = md(content)
        else:
            insights[title] = "Character insights not found"
    
    logging.info(f"Found {len(insights)} character insights on Fandom")
    return insights

def scrape_scripts():
    """Scrape full scripts from SeinfeldScripts"""
    logging.info("Scraping Seinfeld scripts")
    content = fetch_with_retry(SCRIPTS_URL)
    if not content:
        return {}
    
    soup = BeautifulSoup(content, 'html.parser')
    scripts = {}
    
    # Find all script links
    for link in soup.select('a[href$=".html"]'):
        href = link.get('href')
        if "seinfeld" in href.lower():
            title = link.text.strip().replace('"', '')
            script_url = f"https://www.seinfeldscripts.com/{href}"
            script_content = fetch_with_retry(script_url)
            if script_content:
                script_soup = BeautifulSoup(script_content, 'html.parser')
                # Extract content from the main div
                content_div = script_soup.find('div')
                if content_div:
                    script_text = content_div.get_text()
                    scripts[title] = f"```text\n{script_text}\n```"
                else:
                    scripts[title] = "Script format not recognized"
    
    logging.info(f"Found {len(scripts)} scripts")
    return scripts

def save_episode_data(wiki_data, fandom_data, scripts_data):
    """Save collected data to directory structure"""
    logging.info("Organizing data into directory structure")
    os.makedirs(BASE_DIR, exist_ok=True)
    
    for key, ep in wiki_data.items():
        try:
            # Create directory
            sanitized_title = sanitize_filename(ep['title'])
            dir_name = f"Season_{ep['season']}/Episode_{ep['episode']}_{sanitized_title}"
            dir_path = os.path.join(BASE_DIR, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            
            # Save Wikipedia data
            wiki_file = os.path.join(dir_path, 'wikipedia.md')
            with open(wiki_file, 'w', encoding='utf-8') as f:
                f.write(f"# {ep['title']}\n\n{ep['plot']}")
            
            # Save Fandom data
            fandom_content = fandom_data.get(ep['title'], "Character insights not found for this episode")
            fandom_file = os.path.join(dir_path, 'fandom.md')
            with open(fandom_file, 'w', encoding='utf-8') as f:
                f.write(f"# Character Insights\n\n{fandom_content}")
            
            # Save script
            script_content = scripts_data.get(ep['title'], "Script not available for this episode")
            script_file = os.path.join(dir_path, 'seinfeldscripts.md')
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            logging.info(f"Saved data for {ep['title']}")
        except Exception as e:
            logging.error(f"Error saving data for {ep.get('title', 'unknown')}: {e}")
    
    logging.info("Data organization complete")

def main():
    """Main orchestration function"""
    try:
        wiki_data = scrape_wikipedia_api()
        fandom_data = scrape_fandom()
        scripts_data = scrape_scripts()
        save_episode_data(wiki_data, fandom_data, scripts_data)
        logging.info("Scraping process completed successfully")
    except Exception as e:
        logging.critical(f"Fatal error in main process: {e}")

if __name__ == "__main__":
    main()
