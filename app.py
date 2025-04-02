from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import hashlib

app = Flask(__name__)

BASE_URL = "https://animefire.plus"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def generate_id(texto):
    return hashlib.md5(texto.encode()).hexdigest()[:8]

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "routes": ["/recent", "/anime/<id>"]
    })

@app.route('/recent')
def recent():
    try:
        url = f"{BASE_URL}/animes-lancamentos/1"
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        animes = []
        for card in soup.select('div.divCardUltimosEps')[:5]:  # Limite para demo
            title = card.select_one('h3.animeTitle').get_text(strip=True)
            image = card.select_one('img')['src']
            
            animes.append({
                'id': generate_id(title),
                'title': title,
                'image': image
            })
        
        return jsonify({"status": "success", "data": animes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Adicione outras rotas conforme necessário
