from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import hashlib
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False  # Manter ordem dos campos no JSON

# Configurações globais
BASE_URL = "https://animefire.plus"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': BASE_URL
}
anime_db = {}

def generate_id(texto):
    return hashlib.md5(texto.encode()).hexdigest()[:8]

def fetch_anime_page(page_url):
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        animes = []
        for card in soup.select('div.divCardUltimosEps'):
            title = card.select_one('h3.animeTitle').get_text(strip=True)
            image = card.select_one('img')['src'] if card.select_one('img').has_attr('src') else card.select_one('img')['data-src']
            link = card.select_one('a')['href']
            
            if not link.startswith('http'):
                link = f"{BASE_URL}{link}"
                
            anime_id = generate_id(title)
            anime_db[anime_id] = link
            
            animes.append({
                'id': anime_id,
                'title': title,
                'image': image,
                'url': link
            })
        
        return animes
    except Exception as e:
        print(f"Error fetching {page_url}: {str(e)}")
        return []

def fetch_episode_links(anime_url):
    try:
        response = requests.get(anime_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        episodes = []
        for ep in soup.select('div.div_video_list a.lEp'):
            ep_url = ep['href']
            if not ep_url.startswith('http'):
                ep_url = f"{BASE_URL}{ep_url}"
                
            episodes.append({
                'title': ep.get_text(strip=True),
                'url': ep_url
            })
        
        return episodes
    except Exception as e:
        print(f"Error fetching episodes: {str(e)}")
        return []

def fetch_video_sources(episode_url):
    try:
        response = requests.get(episode_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except:
        return []

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'endpoints': {
            '/recent': 'Recent releases',
            '/updated': 'Recently updated',
            '/anime/<id>': 'Get anime episodes',
            '/search/<query>': 'Search anime'
        }
    })

@app.route('/recent')
def recent_releases():
    try:
        pages = 3
        urls = [f"{BASE_URL}/animes-lancamentos/{i}" for i in range(1, pages+1)]
        
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            with tqdm(total=len(urls), desc="Fetching recent") as pbar:
                for animes in executor.map(fetch_anime_page, urls):
                    results.extend(animes)
                    pbar.update(1)
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/updated')
def recently_updated():
    try:
        pages = 3
        urls = [f"{BASE_URL}/animes-atualizados/{i}" for i in range(1, pages+1)]
        
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            with tqdm(total=len(urls), desc="Fetching updated") as pbar:
                for animes in executor.map(fetch_anime_page, urls):
                    results.extend(animes)
                    pbar.update(1)
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/anime/<anime_id>')
def anime_details(anime_id):
    if anime_id not in anime_db:
        return jsonify({
            'status': 'error',
            'message': 'Anime not found'
        }), 404
    
    try:
        episodes = fetch_episode_links(anime_db[anime_id])
        
        # Fetch video sources for first 3 episodes (for demo)
        with ThreadPoolExecutor(max_workers=3) as executor:
            episodes[:3] = list(executor.map(
                lambda ep: {**ep, 'sources': fetch_video_sources(ep['url'])},
                episodes[:3]
            ))
        
        return jsonify({
            'status': 'success',
            'data': {
                'info': {
                    'id': anime_id,
                    'url': anime_db[anime_id]
                },
                'episodes': episodes
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/search/<query>')
def search_anime(query):
    try:
        search_url = f"{BASE_URL}/pesquisar?q={query}"
        animes = fetch_anime_page(search_url)
        
        return jsonify({
            'status': 'success',
            'count': len(animes),
            'data': animes
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
