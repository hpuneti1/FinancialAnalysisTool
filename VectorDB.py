import streamlit as st
import numpy as np
from openai import OpenAI
from typing import List, Dict, Any

class VectorDatabase:
    def __init__(self, openai_key: str):
        self.openai_client = OpenAI(api_key=openai_key)
        self.use_chroma = False
        self.chroma_client = None
        self.collection = None
        
        # Simple in-memory fallback
        self.articles_store = []
        self.embeddings_store = []
        
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            
            try:
                self.collection = self.chroma_client.get_collection("financial_news")
                st.info(f"Using existing collection with {self.collection.count()} articles")
                self.use_chroma = True
            except:
                self.collection = self.chroma_client.create_collection(
                    "financial_news",
                    metadata={"hnsw:space": "cosine"}
                )
                st.info("Created new financial_news collection")
                self.use_chroma = True
        except Exception as e:
            st.info(f"Using fallback vector search (ChromaDB unavailable)")
            self.use_chroma = False
    
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
            
        if self.use_chroma and self.collection:
            self._add_articles_chroma(articles, mentioned_tickers)
        else:
            self._add_articles_fallback(articles, mentioned_tickers)
    
    def _add_articles_chroma(self, articles: list[dict], mentioned_tickers: list[list[str]]):
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
    
    def _add_articles_fallback(self, articles: list[dict], mentioned_tickers: list[list[str]]):
        existing_urls = {article.get('url', '') for article in self.articles_store}
        
        new_articles = []
        new_embeddings = []
        
        for article, tickers in zip(articles, mentioned_tickers):
            url = article.get('url', '')
            if url and url in existing_urls:
                continue
                
            content = f"Title: {article.get('title', '')} Content: {article.get('content', '')}"
            
            article_data = {
                'content': content,
                'metadata': {
                    'title': article.get('title', '')[:200],
                    'source': article.get('source', ''),
                    'url': url,
                    'tickers': ', '.join(tickers) if tickers else '',
                    'publishedAt': article.get('publishedAt', '')
                }
            }
            
            new_articles.append(article_data)
            
        if new_articles:
            embeddings = self.get_embeddings([a['content'] for a in new_articles])
            self.articles_store.extend(new_articles)
            self.embeddings_store.extend(embeddings)
            st.success(f"Added {len(new_articles)} new articles to fallback vector store")
        else:
            st.info("No new articles to add - all articles already exist in database")
    
    def search(self, query: str, n_results: int = 5) -> list[dict]:
        if self.use_chroma and self.collection:
            return self._search_chroma(query, n_results)
        else:
            return self._search_fallback(query, n_results)
    
    def _search_chroma(self, query: str, n_results: int = 5) -> list[dict]:
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
    
    def _search_fallback(self, query: str, n_results: int = 5) -> list[dict]:
        if not self.articles_store:
            return []
            
        try:
            query_embedding = self.get_embeddings([query])[0]
            
            similarities = []
            for i, article_embedding in enumerate(self.embeddings_store):
                similarity = np.dot(query_embedding, article_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(article_embedding)
                )
                similarities.append((similarity, i))
            
            similarities.sort(reverse=True)
            top_results = similarities[:n_results]
            
            formatted_results = []
            for similarity, idx in top_results:
                article = self.articles_store[idx]
                result = {
                    'content': article['content'],
                    'metadata': article['metadata'],
                    'similarity_score': similarity,
                    'id': f"fallback_{idx}"
                }
                formatted_results.append(result)
            
            return formatted_results
        except Exception as e:
            st.error(f"Fallback search error: {e}")
            return []