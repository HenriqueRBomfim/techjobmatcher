from fastapi import FastAPI, Query
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import uvicorn
import os

class DummyModel:
    def predict(self, X):
        return "dummy prediction"

def load_model():
    predictor = DummyModel()
    return predictor

app = FastAPI()
app.predictor = load_model()

# Carregar base de dados de vagas de emprego
def load_data():
    try:
        # Usar o caminho relativo para acessar o arquivo dentro da pasta dataset
        file_path = os.path.join("dataset", "indeed_jobs_big.csv")
        df = pd.read_csv(file_path)
        if df['content'].isnull().all():
            raise ValueError("The content column is empty.")
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame(columns=["title", "content"])
    return df

# Função para calcular relevância com base no TF-IDF e similaridade do cosseno
def calculate_relevance(df, query):
    # Remover entradas com conteúdo NaN
    df = df.dropna(subset=['content'])
    
    if df['content'].empty:
        raise ValueError("The content column is empty or all values are NaN.")
    
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(df['content'].astype(str))  # Certificar-se de que todos os dados são strings
    query_vector = vectorizer.transform([query])
    cosine_similarities = np.dot(query_vector, X.T).toarray().flatten()
    related_docs_indices = cosine_similarities.argsort()[::-1]
    return related_docs_indices, cosine_similarities

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
    results = []
    try:
        related_docs_indices, cosine_similarities = calculate_relevance(df, query)
        for idx in related_docs_indices[:10]:
            if cosine_similarities[idx] > 0.18:
                results.append({
                    "title": df['title'].iloc[idx],
                    "content": df['content'].iloc[idx][:500],
                    "relevance": cosine_similarities[idx]
                })
    except Exception as e:
        return {"results": results, "error": str(e), "message": "Failed to process query"}

    return {"results": results, "message": "OK"}

def run():
    uvicorn.run("main:app", host="0.0.0.0", port=8435, reload=True)

if __name__ == "__main__":
    run()