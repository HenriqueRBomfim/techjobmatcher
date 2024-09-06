from fastapi import FastAPI, Query
import os
import uvicorn

class DummyModel:
    def predict(self, X):
        return "dummy prediction"

def load_model():
    predictor = DummyModel()
    return predictor

app = FastAPI()
app.predictor = load_model()

from fastapi import FastAPI, Query
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import uvicorn
import os

# Carregar base de dados de vagas de emprego
def load_data():
    try:
        df = pd.read_excel("techjobmatcher\indeed_jobs_big.xlsx")
        print(f"Loaded data with {len(df)} records.")
        if df['content'].isnull().all():
            raise ValueError("The content column is empty.")
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame(columns=["title", "content"])
    return df

# Função para calcular relevância com base no TF-IDF e similaridade do cosseno
def calculate_relevance(df, query):
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df['content'])  # Vetorizando o conteúdo das vagas
    query_vector = vectorizer.transform([query])  # Vetorizando a consulta
    cosine_similarities = np.dot(query_vector, X.T).toarray().flatten()  # Similaridade cosseno
    related_docs_indices = cosine_similarities.argsort()[::-1]  # Ordenando por relevância
    return related_docs_indices, cosine_similarities

# Carregando dados e inicializando a aplicação
df = load_data()

@app.get("/hello")
def read_hello():
    return {"message": "hello world"}

@app.get("/predict")
def predict(X: str = Query(..., description="Input text for prediction")):
    result = app.predictor.predict(X)
    return {"input_value": X, "predicted_value": result, "message": "prediction successful"}

@app.get("/query")
def query_route(query: str = Query(..., description="Search query")):
    related_docs_indices, cosine_similarities = calculate_relevance(df, query)
    print(f"Query: {query}")
    
    # Montando os resultados com base na relevância
    results = []
    for idx in related_docs_indices[:10]:  # Retornando os 10 resultados mais relevantes
        results.append({
            "title": df['title'].iloc[idx],
            "content": df['content'].iloc[idx][:500],  # Limitar o conteúdo aos primeiros 500 caracteres
            "relevance": cosine_similarities[idx]
        })
    
    return {"results": results, "message": "OK"}

def run():
    uvicorn.run("main:app", host="0.0.0.0", port=8435, reload=True)

if __name__ == "__main__":
    run()