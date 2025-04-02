from fastapi import FastAPI
from pydantic import BaseModel

# Cria uma instância do FastAPI
app = FastAPI()

# Modelo Pydantic para validação de dados
class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

# Dados em memória (simulando um banco de dados)
fake_db = []

# Rota raiz
@app.get("/")
async def root():
    return {"message": "Bem-vindo à API FastAPI!"}

# Rota com parâmetro de caminho
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

# Rota com parâmetro de consulta
@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

# Rota POST para criar um item
@app.post("/items/")
async def create_item(item: Item):
    fake_db.append(item)
    return item

# Rota PUT para atualizar um item
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_id": item_id, **item.dict()}

# Rota DELETE para remover um item
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return {"message": f"Item {item_id} deletado com sucesso"}
