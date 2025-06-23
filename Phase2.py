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
                        # Count ticker mentions (now comma-separated strings)
                        tickers_str = meta.get('tickers', '')
                        if tickers_str:
                            for ticker in tickers_str.split(', '):
                                if ticker.strip():
                                    ticker_counts[ticker.strip()] = ticker_counts.get(ticker.strip(), 0) + 1
                        
                        # Count sector mentions (now comma-separated strings)
                        sectors_str = meta.get('sectors', '')
                        if sectors_str:
                            for sector in sectors_str.split(', '):
                                if sector.strip():
                                    sector_counts[sector.strip()] = sector_counts.get(sector.strip(), 0) + 1
                        
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
                
                # Convert lists to strings for ChromaDB compatibility
                keywords = self.extractSentimentKeywords(content)
                
                metadata = {
                    'articleId': f"news_{i}",
                    'title': article.get('title', '')[:200],
                    'source': article.get('src', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'url': article.get('url', ''),
                    'querySource': article.get('query_source', ''),
                    
                    # Convert lists to comma-separated strings
                    'tickers': ', '.join(tickers) if tickers else '',
                    'sectors': ', '.join(sectors + [c.get('sector', '') for c in companyInfo]) if sectors or companyInfo else '',
                    'agencies': ', '.join(agencies) if agencies else '',
                    'keywords': ', '.join(keywords) if keywords else '',
                    
                    # Keep scalar values as-is
                    'companyCount': len(companyInfo),
                    'primarySector': companyInfo[0].get('sector', '') if companyInfo else '',
                    'hasEarningsMention': any(word in content.lower() 
                                                for word in ['earnings', 'revenue', 'profit', 'loss']),
                    'hasRegulatoryMention': len(agencies) > 0,
                    'content_length': len(content),
                    'hasTickerMentions': len(tickers) > 0,
                    'hasSectorMentions': len(sectors) > 0 or len(companyInfo) > 0,
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
            print(f"✅ Successfully embedded {len(textToEmbed)} articles")
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
                booster += 0.1
            if metadata.get('hasEarningsMention'):
                booster += 0.1
            if metadata.get("hasRegulatoryMention"):
                booster += 0.05
            if metadata.get('companyCount', 0) > 0:
                booster += 0.05 * metadata['companyCount']
            
            result['boostedScore'] = result['similarityScore'] + booster
            
        results.sort(key= lambda x: x['boostedScore'], reverse=True)
        return results[:5]
    
    def searchBySentiment(self, query: str, sentiment: str = "positive") -> List[Dict]:
        sentimentFilter = {
            "sentimentKeywords": {"$in": [f"{sentiment}_growth", f"{sentiment}_increase", f"{sentiment}_profit"]}
        }
        
        return self.semanticSearch(query, filterMetadata = sentimentFilter)
    
    def searchByCompany(self, ticker: str, query: str = "", nResults: int = 7) -> List[Dict]:
        # Since tickers are now stored as comma-separated strings, we need to search differently
        if query:
            results = self.semanticSearch(query, nResults, filterMetadata=None)
            # Filter results that contain the ticker in the tickers string
            filtered_results = []
            for result in results:
                tickers_str = result['metadata'].get('tickers', '')
                if ticker in tickers_str.split(', '):
                    filtered_results.append(result)
            return filtered_results[:nResults]
        else:
            try:
                # Get all documents and filter by ticker
                all_results = self.newsCollection.get()
                filtered_results = []
                
                for i, metadata in enumerate(all_results['metadatas']):
                    tickers_str = metadata.get('tickers', '')
                    if ticker in tickers_str.split(', '):
                        filtered_results.append({
                            'content': all_results['documents'][i],
                            'metadata': metadata,
                            'articleId': all_results['ids'][i]
                        })
                
                return filtered_results[:nResults]
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
    
    def debug_news_content(self):
        """Debug function to see what news content we actually got"""
        print(f"\n=== Debugging News Content ===")
        print(f"Total articles: {len(self.newsDB)}")
        
        for i, article in enumerate(self.newsDB[:3]):  # Show first 3 articles
            print(f"\n--- Article {i+1} ---")
            print(f"Title: {article.get('title', 'No title')}")
            print(f"Source: {article.get('src', 'No source')}")
            print(f"Query Source: {article.get('query_source', 'No query')}")
            
            content = article.get('content', '') or article.get('description', '')
            print(f"Content preview: {content[:200]}...")
            
            entities = article.get('extractedEntities', {})
            print(f"Extracted tickers: {entities.get('tickers', [])}")
            print(f"Extracted sectors: {entities.get('sectors', [])}")
            print(f"Extracted agencies: {entities.get('regulatoryAgencies', [])}")
            
            # Test ticker extraction on this specific content
            if content:
                raw_tickers = self.extractor.extractTickers(content)
                print(f"Raw ticker extraction: {raw_tickers}")

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
        if not self.vector_db:  # Fixed: was self.vectorDB
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
            print(f"\nQuery: '{query}'")  # Fixed: added missing quote
            results = self.vector_db.advFinSearch(query)  # Fixed: was self.vectorDB
            
            if results:
                for i, result in enumerate(results, 1):
                    metadata = result['metadata']
                    score = result.get('boostedScore', result['similarityScore'])  # Fixed typo: was 'similiarityScore'
                    title = metadata.get('title', 'No title')
                    
                    # Handle comma-separated strings
                    tickers_str = metadata.get('tickers', '')
                    sectors_str = metadata.get('sectors', '')
                    tickers = [t.strip() for t in tickers_str.split(', ') if t.strip()] if tickers_str else []
                    sectors = [s.strip() for s in sectors_str.split(', ') if s.strip()] if sectors_str else []
                    
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
    rag.debug_news_content()
    #rag.debug_news_data()
    rag.buildKG()
    rag.buildVectorDatabase()
    rag.testSearch()