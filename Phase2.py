import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from typing import Dict, List, Tuple
import json

class VectorDB:
    def __init__(self, model= "all-MiniLM-L6-v2"):
        self.embeddingMode = SentenceTransformer(model)
        self.chroma = chromadb.Client()
        try:
            self.chroma_client.delete_collection("financialNews")
        except:
            pass
        self.newsCollection = self.chroma.create_collection(
            name = "financialNews"
        )
