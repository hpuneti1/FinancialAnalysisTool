import streamlit as st
import numpy as np
from openai import OpenAI
import chromadb

class VectorDatabase:
    def __init__(self, openai_key: str):
        self.openai_client = OpenAI(api_key=openai_key)
        
        try:
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            
            try:
                self.collection = self.chroma_client.get_collection("financial_news")
                st.info(f"Using existing collection with {self.collection.count()} articles")
            except:
                self.collection = self.chroma_client.create_collection(
                    "financial_news",
                    metadata={"hnsw:space": "cosine"}
                )
                st.info("Created new financial_news collection")
        except Exception as e:
            st.error(f"ChromaDB initialization failed: {e}")
            raise
    
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            st.error(f"Embedding error: {e}")
            return [[0.0] * 1536] * len(texts)
    
    def add_articles(self, articles: list[dict], mentioned_tickers: list[list[str]]):
        if not articles:
            return
        
        existing_urls = set()
        try:
            existing_data = self.collection.get()
            for metadata in existing_data.get('metadatas', []):
                if metadata and 'url' in metadata:
                    existing_urls.add(metadata['url'])
        except:
            pass
        
        documents = []
        metadatas = []
        ids = []
        
        for article, tickers in zip(articles, mentioned_tickers):
            url = article.get('url', '')
            if url and url in existing_urls:
                continue
                
            content = f"Title: {article.get('title', '')} Content: {article.get('content', '')}"
            metadata = {
                'title': article.get('title', '')[:200],
                'source': article.get('source', ''),
                'url': url,
                'tickers': ', '.join(tickers) if tickers else '',
                'publishedAt': article.get('publishedAt', '')
            }
            
            documents.append(content)
            metadatas.append(metadata)
            ids.append(f"article_{hash(url) if url else hash(content)}")
        
        if documents:
            embeddings = np.array(self.get_embeddings(documents), dtype=np.float32)
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            st.success(f"Added {len(documents)} new articles to vector database")
        else:
            st.info("No new articles to add - all articles already exist in database")
    
    def search(self, query: str, n_results: int = 5) -> list[dict]:
        try:
            query_embedding = self.get_embeddings([query])[0]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            formatted_results = []
            documents = results.get('documents', [[]])
            documents = documents[0] if documents and len(documents) > 0 else []
            metadatas = results.get('metadatas', [[]])
            metadatas = metadatas[0] if metadatas and len(metadatas) > 0 else []
            distances = results.get('distances', [[]])
            distances = distances[0] if distances and len(distances) > 0 else []
            ids = results.get('ids', [[]])
            ids = ids[0] if ids and len(ids) > 0 else []

            for content, metadata, distance, id_ in zip(documents, metadatas, distances, ids):
                result = {
                    'content': content,
                    'metadata': metadata,
                    'similarity_score': 1 - distance,
                    'id': id_
                }
                formatted_results.append(result)
            
            return formatted_results
        except Exception as e:
            st.error(f"Search error: {e}")
            return []