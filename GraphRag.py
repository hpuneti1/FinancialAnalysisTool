from openai import OpenAI
from typing import Dict, List
from FinDataCollector import FinancialDataCollector
from EntityExtractor import EntityExtractor
from KG import FinancialKnowledgeGraph
from VectorDB import VectorDatabase

class GraphRAGSystem:
    def __init__(self, openai_key: str):
        self.data_collector = FinancialDataCollector()
        self.entity_extractor = EntityExtractor()
        self.knowledge_graph = FinancialKnowledgeGraph()
        self.vector_db = VectorDatabase(openai_key)
        self.openai_client = OpenAI(api_key=openai_key)
        self.knowledge_graph.initialize_graph()
    
    def process_user_query(self, user_query: str) -> Dict:
        
        mentioned_tickers = self.entity_extractor.extract_tickers(user_query)
        mentioned_sectors = self.entity_extractor.extract_sectors(user_query)
        
        stock_data = {}
        for ticker in mentioned_tickers:
            data = self.data_collector.get_stock_data(ticker)
            if data:
                stock_data[ticker] = data
                self.knowledge_graph.add_company(data)
        
        search_queries = []
        
        search_queries.append(user_query)
        
        for ticker in mentioned_tickers:
            company_name = stock_data.get(ticker, {}).get('companyName', '')
            if company_name:
                search_queries.append(f"{company_name} stock outlook earnings")
                search_queries.append(f"{ticker} financial performance")
        
        for sector in mentioned_sectors:
            search_queries.append(f"{sector} sector analysis outlook")
        
        all_articles = []
        all_tickers = []
        
        for query in search_queries[:4]:  
            articles = self.data_collector.search_news(query, days_back=21)
            for article in articles:
                article_tickers = self.entity_extractor.extract_tickers(
                    f"{article.get('title', '')} {article.get('content', '')}"
                )
                all_articles.append(article)
                all_tickers.append(article_tickers)
                
                self.knowledge_graph.add_news_article(article, article_tickers)
        
        if all_articles:
            self.vector_db.add_articles(all_articles, all_tickers)
        
        relevant_articles = self.vector_db.search(user_query, n_results=8)
        
        graph_context = ""
        for ticker in mentioned_tickers:
            context = self.knowledge_graph.query_company_context(ticker)
            if context:
                graph_context += context + " "
        
        response = self.generate_response(user_query, relevant_articles, stock_data, graph_context)
        
        return {
            'response': response,
            'mentioned_tickers': mentioned_tickers,
            'mentioned_sectors': mentioned_sectors,
            'stock_data': stock_data,
            'relevant_articles': relevant_articles,
            'graph_context': graph_context
        }
    
    def generate_response(self, query: str, articles: List[Dict], stock_data: Dict, graph_context: str) -> str:
        relevant_articles = [article for article in articles if article['similarity_score'] > 0.3][:3]
        
        article_context = "\n\n".join([
            f"Article: {article['metadata']['title']}\n"
            f"Source: {article['metadata']['source']}\n"
            f"Content: {article['content'][:400]}..."
            for article in relevant_articles
        ])
        
        stock_context = "\n".join([
            f"{ticker}: {data['companyName']} - ${data['price']} ({data['changePercent']}) "
            f"Sector: {data['sector']}, Market Cap: ${data.get('marketCap', 'N/A'):,}"
            for ticker, data in stock_data.items()
        ])
        
        system_prompt = """You are a senior financial analyst providing detailed investment analysis. 

Your responses should:
- Provide specific, actionable insights based on the data
- Analyze both current performance and future outlook
- Consider market trends, sector dynamics, and company fundamentals
- Explain the reasoning behind your analysis with specific evidence
- Be comprehensive but clear and well-structured
- Include both opportunities and risks"""
        
        user_prompt = f"""
User Question: {query}

Current Stock Data:
{stock_context}

Knowledge Graph Context:
{graph_context}

Recent Relevant News:
{article_context}

Please provide a comprehensive financial analysis that:
1. Directly answers the user's question
2. Analyzes the current stock performance with specific data points
3. Discusses relevant market trends and news
4. Provides outlook based on available information
5. Highlights key factors investors should monitor

Use specific numbers, percentages, and facts from the provided data.
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {e}"