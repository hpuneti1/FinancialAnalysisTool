import numpy as np
from openai import OpenAI
import chromadb
from typing import Dict, List, Tuple
import json
import time
from Phase1 import FinDataCollector, FinEntityExtractor, FinKG, RAG
class FinancialVectorDB:
    def __init__(self, openAPIKey: str, embeddingModel: str = "text-embedding-3-small"):
        self.openaiClient =OpenAI(api_key=openAPIKey)
        self.embeddingModel = embeddingModel
        self.chromaClient = chromadb.Client()
        try:
            self.chromaClient.delete_collection("financialNews")
        except:
            pass
        self.newsCollection = self.chromaClient.create_collection(
            name = "financialNews"
        )
        
    def getEmbeddingStats(self):
        """Get statistics about embedded content"""
        try:
            # Get collection info
            count = self.newsCollection.count()
            
            print(f"\n=== Vector Database Stats ===")
            print(f"Total embedded articles: {count}")
            
            if count > 0:
                # Sample some metadata to understand content
                sample_results = self.newsCollection.get(limit=min(count, 10))
                
                if sample_results['metadatas']:
                    # Analyze metadata
                    ticker_counts = {}
                    sector_counts = {}
                    source_counts = {}
                    
                    for meta in sample_results['metadatas']:
                        # Count ticker mentions
                        for ticker in meta.get('tickers', []):
                            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
                        
                        # Count sector mentions
                        for sector in meta.get('sectors', []):
                            sector_counts[sector] = sector_counts.get(sector, 0) + 1
                        
                        # Count sources
                        source = meta.get('source', 'Unknown')
                        source_counts[source] = source_counts.get(source, 0) + 1
                    
                    if ticker_counts:
                        print(f"\nMost mentioned companies:")
                        for ticker, count in sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            print(f"  {ticker}: {count} mentions")
                    
                    if sector_counts:
                        print(f"\nMost mentioned sectors:")
                        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            print(f"  {sector}: {count} mentions")
                    
                    if source_counts:
                        print(f"\nNews sources:")
                        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            print(f"  {source}: {count} articles")
            else:
                print("No articles embedded yet")
        
        except Exception as e:
            print(f"Error getting stats: {e}")
        
    def getOpenAIEmbeddings(self, texts: List[str], batchSize: int = 100) -> List[List[float]]:
        allEmbeddings = []
        for i in range(0, len(texts), batchSize):
            batch = texts[i:i + batchSize]
            try:
                response = self.openaiClient.embeddings.create(
                    model = self.embeddingModel,
                    input = batch
                )
                
                batchEmbeddings = [data.embedding for data in response.data]
                allEmbeddings.extend(batchEmbeddings)
                
                if len(texts) > batchSize:
                    time.sleep(1)
            except Exception as e:
                print(f"Embedding error: {e}")
                embeddingDimensions = 1536
                batchEmbeddings = [[0.0] * embeddingDimensions] * len(batch)
                allEmbeddings.extend(batchEmbeddings)
        return allEmbeddings
    
    def embedNewsArticles(self, newsData: List[Dict], companiesData: Dict):
        print("Embedding news articles with OpenAI...")
        documents = []
        metadatas = []
        ids = []
        textToEmbed = []
        
        for i, article in enumerate(newsData):
            try:
                contentSections = []
                if article.get('title'):
                    contentSections.append(f"Title: {article['title']}")
                if article.get('description'):
                    contentSections.append(f"Description: {article['description']}")
                if article.get('content'):
                    contentSections.append(f"Content: {article['content'][:1000]}")
                content = ' '.join(contentSections)
                if not content.strip():
                    continue
                
                extractedEntities = article.get('extractedEntities', {})
                tickers = extractedEntities.get('tickers', [])
                sectors = extractedEntities.get('sectors', [])
                agencies = extractedEntities.get('regulatoryAgencies', [])
                
                companyInfo = []
                sectorInfo = []
                
                for ticker in tickers:
                    if ticker in companiesData:
                        companyData = companiesData[ticker]
                        companyInfo.append({
                            'ticker': ticker,
                            'name': companyData.get('companyName', ''),
                            'sector': companyData.get('sector', ''),
                            'industry': companyData.get('industry', '')
                        })
                enhancedContent = content
                if companyInfo:
                    companyContext = " Companies mentioned: " + ", ".join([
                        f"{c['name']} ({c['ticker']}) in {c['sector']}" 
                            for c in companyInfo
                    ])
                    enhancedContent += companyContext
                
                if agencies:
                    regulatoryContext = " Regulatory bodies: " + ", ".join(agencies)
                    enhancedContent += regulatoryContext
                
                metadata = {
                    'articleId': f"news_{i}",
                    'title': article.get('title', '')[:200],  # More space for OpenAI
                    'source': article.get('src', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'url': article.get('url', ''),
                    'querySource': article.get('query_source', ''),
                    # Knowledge graph links
                    'tickers': tickers,
                    'sectors': sectors + sectorInfo,  # Include both
                    'agencies': agencies,
                    'companyCount': len(companyInfo),
                    # Enhanced metadata for better search
                    'primarySector': sectorInfo[0] if sectorInfo else '',
                    'hasEarningsMention': any(word in content.lower() 
                                                for word in ['earnings', 'revenue', 'profit', 'loss']),
                    'hasRegulatoryMention': len(agencies) > 0,
                    'content_length': len(content),
                    # For filtering/search
                    'hasTickerMentions': len(tickers) > 0,
                    'hasSectorMentions': len(sectors + sectorInfo) > 0,
                    ' Keywords': self.extractSentimentKeywords(content)   
                }
                
                documents.append(content)
                textToEmbed.append(enhancedContent)
                metadatas.append(metadata)
                ids.append(f"article_{i}") 
            except Exception as e:
                print(f"Error processing article {i}: {e}")
        if textToEmbed:
            embeddings = self.getOpenAIEmbeddings(textToEmbed)
            
            self.newsCollection.add(
                documents = documents,
                embeddings = embeddings,
                metadatas = metadatas,
                ids = ids
            )
        else:
            print("No valid articles to embed")
            
    
            
    def extractSentimentKeywords(self, text: str) -> List[str]:
        positiveWords = ['growth', 'increase', 'profit', 'success', 'gain', 'up', 'rise', 'bull']
        negativeWords = ['decline', 'loss', 'decrease', 'fall', 'drop', 'bear', 'down', 'crash']
        textLower = text.lower()
        keywords = []
        
        for word in positiveWords:
            if word in textLower:
                keywords.append(f"positive_{word}")
        
        for word in negativeWords:
            if word in textLower:
                keywords.append(f"negative_{word}")
        
        return keywords[:5]

    def semanticSearch(self, query: str, nResults: int = 7, filterMetadata: Dict = None) -> List[Dict]:
        try:
            queryEmbedding = self.getOpenAIEmbeddings([query])[0]
            results = self.newsCollection.query(
                query_embeddings = [queryEmbedding],
                n_results = nResults,
            )

            formattedResults = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarityScore': 1 - results['distances'][0][i],
                        'articleId': results['ids'][0][i]
                    }
                    formattedResults.append(result)
            return formattedResults
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
    
    def advFinSearch(self, query: str, filters: Dict = None) -> List[Dict]:
        searchFilters = filters or {}
        
        results = self.semanticSearch(query, nResults = 10, filterMetadata=searchFilters)
        
        for result in results:
            metadata = result['metadata']
            
            booster = 0
            if metadata.get('hasTickerMentions'):
                booster += 1
            if metadata.get('hasEarningsMention'):
                booster += 1
            if metadata.get("hasRegulatoryMention"):
                booster += .05
            if metadata.get('companyCount', 0) > 0:
                booster += .05 * metadata['companyCount']
            
            result['boostedScore'] = result['similarityScore'] + booster
            
        results.sort(key= lambda x: x['boostedScore'], reverse=True)
        return results[:5]
    
    def searchBySentiment(self, query: str, sentiment: str = "positive") -> List[Dict]:
        sentimentFilter = {
            "sentimentKeywords": {"$in": [f"{sentiment}_growth", f"{sentiment}_increase", f"{sentiment}_profit"]}
        }
        
        return self.semanticSearch(query, filterMetadata = sentimentFilter)
    
    def searchByCompany(self, ticker: str, query: str = "", nResults: int = 7) -> List[Dict]:
        filterMetadata = {"tickers": {"$in": [ticker]}}
        
        if query:
            return self.semanticSearch(query, nResults, filterMetadata)
        else:
            try:
                results = self.newsCollection.get(where = filterMetadata, limit = nResults)
                return [{'content': doc, 'metadata': meta, 'article_id': id_}
                        for doc, meta, id_ in zip(results['documents'], results['metadatas'], results['ids'])]
            except Exception as e:
                print(f"Error searching by company: {e}")
                return []
class RAG:
    def __init__(self, openaiAPIKEY:str = None):
        self.collector = FinDataCollector()
        self.extractor = FinEntityExtractor()
        self.companiesDB = {}
        self.newsDB = []
        self.graphBuilder = FinKG()
        self.vectorDB = None
        self.openaiAPIKey = openaiAPIKEY
    
    def debug_news_data(self):
    
        print(f"=== Debugging News Data ===")
        print(f"Total articles: {len(self.newsDB)}")
        
        if self.newsDB:
            article = self.newsDB[0]
            print(f"First article keys: {list(article.keys())}")
            print(f"First article: {article}")
            
            if 'extractedEntities' in article:
                entities = article['extractedEntities']
                print(f"Extracted entities: {entities}")
                print(f"Entities type: {type(entities)}")
    def processSampleData(self, tickers: List[str] = None, newsQueries: List[str] = None):
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'JNJ', 'JPM', 'XOM', 'TSLA']
        if newsQueries is None:
            newsQueries = ['biotech FDA approval', 'bank earnings', 'tech regulation']
        for ticker in tickers:
            print(f"Processing {ticker}...")
            companyData = self.collector.getCompanyProfile(ticker)
            stockData = self.collector.getStockData(ticker)
            
            if companyData:
                combinedData = {**companyData, **stockData}
                self.companiesDB[ticker] = combinedData
        for query in newsQueries:
                articles = self.collector.getFinancialNews(query, daysBack=7)
                for article in articles:
                    tickersMentioned = self.extractor.extractTickers(article['content'] or '')
                    sectorsMentioned = self.extractor.classifySector(article['content'] or '')
                    regulatoryMentions = self.extractor.extractRegulatoryMentions(article['content'] or '')
                    enhancedArticle = {
                    **article,
                    'extractedEntities': {
                        'tickers': tickersMentioned,
                        'sectors': sectorsMentioned,
                        'regulatoryAgencies': regulatoryMentions
                    },
                    'query_source': query
                    }
                    self.newsDB.append(enhancedArticle)
    
    def buildKG(self):
        self.graphBuilder.clearDB()
        self.graphBuilder.createConstraints()
        self.graphBuilder.loadGICSHiearchy()
        self.graphBuilder.loadCompanies(self.companiesDB)
        self.graphBuilder.loadArticles(self.newsDB)
        self.graphBuilder.createRegulatoryEntities()
    
    def buildVectorDatabase(self, embedding_model: str = "text-embedding-3-small"):
        """Fixed vector database builder - creates the vector DB first"""
        
        print(f"\n=== Building Vector Database with OpenAI {embedding_model} ===")
        
        if not self.newsDB:
            print("❌ No news data to vectorize. Run processSampleData() first.")
            return
            return
        
        try:
            print("Creating FinancialVectorDB instance...")
            
            # Create the vector database instance FIRST
            self.vector_db = FinancialVectorDB(
                openAPIKey = self.openaiAPIKey,
                embeddingModel = embedding_model
            )
            
            print("✅ Vector DB instance created")
            
            # Now embed the articles
            print("Embedding articles...")
            self.vector_db.embedNewsArticles(self.newsDB, self.companiesDB)
            
            # Get statistics
            print("Getting statistics...")
            self.vector_db.getEmbeddingStats()
            
            print("✅ Vector database construction complete!")
            
        except Exception as e:
            print(f"❌ Error building vector database: {e}")
            import traceback
            traceback.print_exc()
    
    
    def testSearch(self):
        if not self.vectorDB:
            print("No Vector DB")
            return
        
        testQueries = [
            "pharmaceutical companies with FDA drug approvals",
            "technology sector regulatory challenges",
            "banking industry earnings and financial performance",
            "renewable energy companies stock performance",
            "biotech merger and acquisition activity"
        ]
        
        for query in testQueries:
            print(f"\nQuery: '{query}")
            results = self.vectorDB.advFinSearch(query)
            
            if results:
                for i, result in enumerate(results, 1):
                    metadata = result['metadata']
                    score = result.get('boostedScore', result['similiarityScore'])
                    title = metadata.get('title', 'No title')
                    tickers = metadata.get('tickers', [])
                    sectors = metadata.get('sectors', [])
                    print(f"  {i}. {title[:70]}... (score: {score:.3f})")
                    if tickers:
                        print(f"     Companies: {', '.join(tickers[:3])}")
                    if sectors:
                        print(f"     Sectors: {', '.join(sectors[:2])}")
            else:
                print("No results found")
if __name__ == "__main__":
    rag = RAG(openaiAPIKEY="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")
    rag.processSampleData()
    #rag.debug_news_data()
    rag.buildKG()
    rag.buildVectorDatabase()
    rag.testSearch()