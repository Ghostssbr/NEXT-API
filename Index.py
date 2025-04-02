import requests
from flask import Flask, jsonify, request
import cloudscraper
from bs4 import BeautifulSoup
import hashlib
import concurrent.futures  # Importação necessária
from tqdm import tqdm  # Para a barra de progresso

app = Flask(__name__)
scraper = cloudscraper.create_scraper()
anime_db = {}  # Dicionário para armazenar os animes indexados

def generate_id(nome):
    """Gera um ID único para o anime baseado no nome"""
    return hashlib.md5(nome.encode()).hexdigest()[:8]  # ID com 8 caracteres

def fetch_page(url):
    """Faz o scraping da página principal do AnimeFire"""
    response = scraper.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    itens = soup.select("div.divCardUltimosEps")
    animes = []

    for item in itens:
        nome = item.select_one("h3.animeTitle").text.strip()
        capa = item.select_one("img").get("data-src", "")
        link = item.select_one("a")["href"]  # Link necessário para pegar os episódios

        anime_id = generate_id(nome)  # Gerar um ID único

        anime_db[anime_id] = link  # Salva o link no banco de dados

        animes.append({"id": anime_id, "nome": nome, "capa": capa})

    return animes

def fetch_video_links(episode_url):
    """Faz uma requisição para pegar os links dos vídeos de diferentes qualidades"""
    response = requests.get(episode_url)
    if response.status_code != 200:
        return []

    data = response.json()
    video_links = []

    for video in data.get("data", []):
        video_links.append({
            "label": video.get("label"),
            "src": video.get("src")
        })

    return video_links

def get_animefire_animes(tipo="lancamentos", max_paginas=10):
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
        return {"erro": "Anime não encontrado"}

    url = anime_db[anime_id]
    response = scraper.get(url)
    if response.status_code != 200:
        return {"erro": "Falha ao carregar episódios"}

    soup = BeautifulSoup(response.text, 'html.parser')
    episodios = []

    for ep in soup.select(".div_video_list a.lEp"):
        ep_nome = ep.text.strip()
        ep_link = ep["href"]
        
        # Remove a parte 'https://animefire.plus/animes/' e junta com 'https://animefire.plus/video/'
        ep_link = "https://animefire.plus/video/" + ep_link.split("https://animefire.plus/animes/")[1]
        
        # Adiciona os parâmetros no final do link
        ep_link += "?tempsubs=0&1705074917"
        
        # Faz a requisição para pegar os links dos vídeos do episódio
        video_links = fetch_video_links(ep_link)

        episodios.append({
            "episodio": ep_nome,
            "video_links": video_links
        })

    return {"id": anime_id, "episodios": episodios}

@app.route('/lancamentos', methods=['GET'])
def get_lancamentos():
    return jsonify(get_animefire_animes("lancamentos"))

@app.route('/atualizados', methods=['GET'])
def get_atualizados():
    return jsonify(get_animefire_animes("atualizados"))

@app.route('/id=<anime_id>', methods=['GET'])
def get_episodios(anime_id):
    return jsonify(fetch_episodes(anime_id))

if __name__ == "__main__":
    app.run(debug=True)
