import requests
from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
import hashlib
import concurrent.futures
from tqdm import tqdm

app = Flask(__name__)
anime_db = {}  # Dicionário para armazenar os animes indexados

# Configuração de headers para evitar bloqueios
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://animefire.plus/'
}

def generate_id(nome):
    """Gera um ID único para o anime baseado no nome"""
    return hashlib.md5(nome.encode()).hexdigest()[:8]  # ID com 8 caracteres

def fetch_page(url):
    """Faz o scraping da página principal do AnimeFire"""
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        itens = soup.select("div.divCardUltimosEps")
        animes = []

        for item in itens:
            nome = item.select_one("h3.animeTitle").text.strip()
            capa = item.select_one("img").get("src", "")
            if not capa:
                capa = item.select_one("img").get("data-src", "")
            link = item.select_one("a")["href"]  # Link necessário para pegar os episódios

            anime_id = generate_id(nome)  # Gerar um ID único
            anime_db[anime_id] = link  # Salva o link no banco de dados

            animes.append({
                "id": anime_id,
                "nome": nome,
                "capa": capa,
                "link": link
            })

        return animes
    except Exception as e:
        print(f"Error fetching page {url}: {str(e)}")
        return []

def fetch_video_links(episode_url):
    """Faz uma requisição para pegar os links dos vídeos de diferentes qualidades"""
    try:
        response = requests.get(episode_url, headers=HEADERS)
        if response.status_code != 200:
            return []

        data = response.json()
        video_links = []

        for video in data.get("data", []):
            video_links.append({
                "quality": video.get("label"),
                "url": video.get("src")
            })

        return video_links
    except Exception as e:
        print(f"Error fetching video links: {str(e)}")
        return []

def get_animefire_animes(tipo="lancamentos", max_paginas=5):
    """Busca os animes de várias páginas em paralelo com barra de progresso"""
    urls = [f"https://animefire.plus/animes-{tipo}/{i}" for i in range(1, max_paginas + 1)]
    animes = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        with tqdm(total=len(urls), desc="🔄 Carregando páginas") as pbar:
            resultados = executor.map(fetch_page, urls)
            for resultado in resultados:
                animes.extend(resultado)
                pbar.update(1)

    return animes

def fetch_episodes(anime_id):
    """Faz o scraping dos episódios de um anime pelo ID e adiciona os links de vídeo"""
    if anime_id not in anime_db:
        return {"error": "Anime não encontrado"}

    url = anime_db[anime_id]
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return {"error": "Falha ao carregar episódios"}

        soup = BeautifulSoup(response.text, 'html.parser')
        episodios = []

        for ep in soup.select(".div_video_list a.lEp"):
            ep_nome = ep.text.strip()
            ep_link = ep["href"]
            
            # Verifica se o link já está completo
            if not ep_link.startswith('http'):
                ep_link = f"https://animefire.plus{ep_link}"
            
            # Tenta obter os links de vídeo
            video_links = fetch_video_links(ep_link)

            episodios.append({
                "episodio": ep_nome,
                "link": ep_link,
                "video_links": video_links
            })

        return {
            "id": anime_id,
            "url": url,
            "episodios": episodios
        }
    except Exception as e:
        return {"error": f"Erro ao processar episódios: {str(e)}"}

@app.route('/lancamentos', methods=['GET'])
def get_lancamentos():
    return jsonify({
        "status": "success",
        "data": get_animefire_animes("lancamentos")
    })

@app.route('/atualizados', methods=['GET'])
def get_atualizados():
    return jsonify({
        "status": "success",
        "data": get_animefire_animes("atualizados")
    })

@app.route('/anime/<anime_id>', methods=['GET'])
def get_episodios(anime_id):
    return jsonify(fetch_episodes(anime_id))

@app.route('/')
def home():
    return jsonify({
        "message": "Bem-vindo à API do AnimeFire",
        "endpoints": {
            "/lancamentos": "Lista de lançamentos recentes",
            "/atualizados": "Lista de animes atualizados",
            "/anime/<id>": "Detalhes e episódios de um anime específico"
        }
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
