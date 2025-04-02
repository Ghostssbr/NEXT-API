import requests
from flask import Flask, jsonify
from bs4 import BeautifulSoup
import hashlib
import concurrent.futures
from tqdm import tqdm

app = Flask(__name__)
BASE_URL = "https://animefire.plus"
anime_db = {}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': BASE_URL
}

def generate_id(nome):
    return hashlib.md5(nome.encode()).hexdigest()[:8]

def fetch_page(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        animes = []
        
        for item in soup.select("div.divCardUltimosEps"):
            nome = item.select_one("h3.animeTitle").get_text(strip=True)
            capa = item.select_one("img")['src'] if item.select_one("img").has_attr('src') else item.select_one("img")['data-src']
            link = item.select_one("a")['href']
            
            anime_id = generate_id(nome)
            anime_db[anime_id] = f"{BASE_URL}{link}" if not link.startswith('http') else link
            
            animes.append({
                "id": anime_id,
                "nome": nome,
                "capa": capa,
                "link": anime_db[anime_id]
            })
        
        return animes
    except Exception as e:
        print(f"Erro ao processar {url}: {str(e)}")
        return []

def fetch_video_links(episode_url):
    try:
        response = requests.get(episode_url, headers=HEADERS)
        response.raise_for_status()
        return [{"quality": v['label'], "url": v['src']} for v in response.json().get('data', [])]
    except:
        return []

def get_animes(tipo, pages=3):
    urls = [f"{BASE_URL}/animes-{tipo}/{i}" for i in range(1, pages+1)]
    results = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        with tqdm(total=len(urls), desc=f"Carregando {tipo}") as pbar:
            for result in executor.map(fetch_page, urls):
                results.extend(result)
                pbar.update(1)
    
    return results

@app.route('/')
def index():
    return jsonify({
        "message": "API AnimeFire Plus",
        "endpoints": {
            "/lancamentos": "Últimos lançamentos",
            "/atualizados": "Animes atualizados",
            "/anime/<id>": "Episódios de um anime",
            "/search/<query>": "Buscar animes"
        }
    })

@app.route('/lancamentos')
def lancamentos():
    return jsonify({
        "status": "success",
        "data": get_animes("lancamentos")
    })

@app.route('/atualizados')
def atualizados():
    return jsonify({
        "status": "success",
        "data": get_animes("atualizados")
    })

@app.route('/anime/<anime_id>')
def anime(anime_id):
    if anime_id not in anime_db:
        return jsonify({"status": "error", "message": "Anime não encontrado"}), 404
    
    try:
        response = requests.get(anime_db[anime_id], headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        episodios = []
        
        for ep in soup.select(".div_video_list a.lEp"):
            ep_link = ep['href']
            ep_link = f"{BASE_URL}{ep_link}" if not ep_link.startswith('http') else ep_link
            
            episodios.append({
                "episodio": ep.get_text(strip=True),
                "link": ep_link,
                "video_links": fetch_video_links(ep_link)
            })
        
        return jsonify({
            "status": "success",
            "data": {
                "id": anime_id,
                "episodios": episodios
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/search/<query>')
def search(query):
    try:
        url = f"{BASE_URL}/pesquisar?q={query}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for item in soup.select("div.divCardUltimosEps"):
            nome = item.select_one("h3.animeTitle").get_text(strip=True)
            capa = item.select_one("img")['src'] if item.select_one("img").has_attr('src') else item.select_one("img")['data-src']
            link = item.select_one("a")['href']
            
            anime_id = generate_id(nome)
            anime_db[anime_id] = f"{BASE_URL}{link}" if not link.startswith('http') else link
            
            results.append({
                "id": anime_id,
                "nome": nome,
                "capa": capa,
                "link": anime_db[anime_id]
            })
        
        return jsonify({
            "status": "success",
            "data": results
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
