from openai import OpenAI
from FinDataCollector import FinancialDataCollector
from EntityExtractor import EntityExtractor
from KG import FinancialKnowledgeGraph
from VectorDB import VectorDatabase

#This class is resposible for understanding the query, gathering information, and synthesizing an analysis
class GraphRAGSystem:
    def __init__(self, openai_key: str):
        self.data_collector = FinancialDataCollector()
        self.entity_extractor = EntityExtractor(openai_key)
        self.knowledge_graph = FinancialKnowledgeGraph()
        self.vector_db = VectorDatabase(openai_key)
        self.openai_client = OpenAI(api_key=openai_key)
        self.knowledge_graph.initialize_graph()
    
    def process_user_query(self, user_query: str) -> dict:
        
        mentioned_tickers = self.entity_extractor.extract_tickers(user_query)
        mentioned_sectors = self.entity_extractor.extract_sectors(user_query)
        
        extraction_details = self.entity_extractor.get_extraction_details(user_query)
        
        sector_tickers = []
        has_specific_companies = len(mentioned_tickers) > 0
        has_explicit_sector_queries = any(
            sq.get('query_type') == 'broad_sector' 
            for sq in extraction_details.get('sector_queries', [])
        )
        
        if extraction_details.get('sector_queries') and has_explicit_sector_queries:
            for sector_query in extraction_details['sector_queries']:
                if sector_query.get('confidence', 0) > 0.5 and sector_query.get('query_type') == 'broad_sector':
                    sector_name = sector_query['sector']
                    tickers = self.entity_extractor.get_sector_tickers(sector_name)
                    sector_tickers.extend(tickers)
        
        all_tickers = list(set(mentioned_tickers + sector_tickers))
        
        stock_data = {}
        for ticker in all_tickers:
            data = self.data_collector.get_stock_data(ticker)
            if data:
                stock_data[ticker] = data
                self.knowledge_graph.add_company(data)
        
        search_queries = []
        
        for sector_query in extraction_details.get('sector_queries', []):
            if sector_query.get('confidence', 0) > 0.5:
                sector_name = sector_query['sector']
                search_queries.append(f"{sector_name} sector performance trends analysis")
                search_queries.append(f"{sector_name} stocks outlook earnings")
        
        for company_data in extraction_details.get('companies', []):
            if company_data.get('confidence', 0) > 0.7:
                company_name = company_data.get('name', '')
                ticker = company_data.get('ticker', '')
                if company_name and ticker:
                    search_queries.append(f"{company_name} {ticker} stock analysis earnings")
        
        for group_data in extraction_details.get('stock_groups', []):
            if group_data.get('confidence', 0) > 0.6:
                group_name = group_data.get('group', '')
                search_queries.append(f"{group_name} stocks performance analysis")
        
        for sector_data in extraction_details.get('sectors', []):
            if sector_data.get('confidence', 0) > 0.6:
                sector_name = sector_data.get('sector', '')
                search_queries.append(f"{sector_name} sector outlook analysis")
        
        query_variants = set()
        for company in [c.get('name', '') for c in extraction_details.get('companies', []) if c.get('name', '')]:
            query_variants.add(company)
            if " " in company:
                query_variants.add(company.split()[0])
        for ticker in all_tickers:
            query_variants.add(ticker)
        for sector in mentioned_sectors:
            query_variants.add(sector)
        for sector_query in extraction_details.get('sector_queries', []):
            query_variants.add(sector_query['sector'])
        if not query_variants:
            query_variants.add(user_query)

        all_articles = []
        all_article_tickers = []
        
        for query in search_queries[:6]:  
            articles = self.data_collector.search_news(query, days_back=21, query_variants=list(query_variants), entity_extractor=self.entity_extractor)
            for article in articles:
                article_tickers = self.entity_extractor.extract_tickers(
                    f"{article.get('title', '')} {article.get('content', '')}"
                )
                all_articles.append(article)
                all_article_tickers.append(article_tickers)

                self.knowledge_graph.add_news_article(article, article_tickers)
        

        if self.entity_extractor is not None:
            relevant_articles = []
            for article in all_articles:
                entities = self.entity_extractor.extract_entities(article['title'] + ' ' + article['content'])
                found = False
                for variant in query_variants:
                    if variant in [c['name'] for c in entities.get('companies', [])]:
                        found = True
                    if variant in entities.get('tickers_mentioned', []):
                        found = True
                    if variant in [s['sector'] for s in entities.get('sectors', [])]:
                        found = True
                if found:
                    relevant_articles.append(article)
            articles = relevant_articles
        else:
            articles = all_articles

        seen = set()
        unique_articles = []
        for article in articles:
            if article['url'] not in seen:
                unique_articles.append(article)
                seen.add(article['url'])

        unique_articles_db = []
        unique_tickers_db = []
        seen_urls_db = set()
        for article, tickers in zip(all_articles, all_article_tickers):
            url = article.get('url')
            if url and url not in seen_urls_db:
                unique_articles_db.append(article)
                unique_tickers_db.append(tickers)
                seen_urls_db.add(url)

        if unique_articles_db:
            self.vector_db.add_articles(unique_articles_db, unique_tickers_db)
        
        is_sector_query = bool(extraction_details.get('sector_queries'))
        
        if is_sector_query and extraction_details.get('sector_queries'):
            sector_query = extraction_details['sector_queries'][0]
            sector_name = sector_query.get('sector', '')
            
            sector_search_queries = {
                'Banking': "banking sector stocks performance JPMorgan Wells Fargo Goldman Sachs Bank of America Citigroup earnings financial results",
                'Healthcare': "healthcare sector stocks performance Johnson Johnson Pfizer UnitedHealth Abbott Thermo Fisher medical pharmaceutical biotech earnings",
                'Technology': "technology sector stocks performance Apple Microsoft Google Amazon Meta Tesla Nvidia tech earnings software hardware",
                'Energy': "energy sector stocks performance ExxonMobil Chevron ConocoPhillips oil gas renewable earnings",
                'Financial': "financial sector stocks performance banks insurance investment earnings financial services"
            }
            
            if sector_name in sector_search_queries:
                relevant_articles = self.vector_db.search(sector_search_queries[sector_name], n_results=15)
            else:
                relevant_articles = self.vector_db.search(user_query, n_results=15)
        else:
            relevant_articles = self.vector_db.search(user_query, n_results=15)
        
        if is_sector_query:
            filtered_articles = []
            sector_keywords = {
                'Banking': ['bank', 'banking', 'JPM', 'BAC', 'WFC', 'Citigroup', 'Goldman Sachs', 'Wells Fargo', 'JPMorgan'],
                'Technology': ['tech', 'technology', 'AAPL', 'MSFT', 'GOOGL', 'Apple', 'Microsoft', 'Google', 'software', 'hardware'],
                'Healthcare': ['healthcare', 'health', 'medical', 'pharmaceutical', 'pharma', 'biotech', 'drug', 'medicine', 'clinical', 'JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'johnson', 'pfizer', 'abbott', 'unitedhealth', 'thermo fisher'],
                'Energy': ['energy', 'oil', 'gas', 'renewable', 'petroleum', 'drilling'],
                'Financial': ['financial', 'finance', 'bank', 'investment', 'insurance']
            }
            
            search_keywords = []
            for sector_query in extraction_details.get('sector_queries', []):
                sector_name = sector_query.get('sector', '')
                if sector_name in sector_keywords:
                    search_keywords.extend(sector_keywords[sector_name])
            
            search_keywords.extend(all_tickers)
            
            for article in relevant_articles:
                content = article.get('content', '')
                title = article.get('metadata', {}).get('title', '') if 'metadata' in article else ''
                full_text = f"{title} {content}".lower()
                
                article_is_relevant = False
                
                for sector_query in extraction_details.get('sector_queries', []):
                    sector_name = sector_query.get('sector', '')
                    if sector_name in sector_keywords:
                        sector_terms = sector_keywords[sector_name]
                        
                        term_matches = sum(1 for term in sector_terms if term.lower() in full_text)
                        
                        if term_matches >= 2:  # At least 2 sector-specific terms
                            article_is_relevant = True
                            break
                        elif any(term in full_text for term in sector_terms[:3]):
                            article_is_relevant = True
                            break
                
                if article_is_relevant:
                    filtered_articles.append(article)
            
            relevant_articles = filtered_articles
        else:
            filtered_articles = []
            for article in relevant_articles:
                content = article.get('content', '')
                title = article.get('metadata', {}).get('title', '') if 'metadata' in article else ''
                full_text = f"{title} {content}".lower()
                
                if any(variant.lower() in full_text for variant in query_variants if variant):
                    filtered_articles.append(article)
            
            relevant_articles = filtered_articles
        
        if not relevant_articles:
            relevant_articles = self.vector_db.search(user_query, n_results=5)

        graph_context = ""
        for ticker in all_tickers:
            context = self.knowledge_graph.query_company_context(ticker)
            if context:
                graph_context += context + " "
        
        response = self.generate_response(
            user_query, 
            relevant_articles, 
            stock_data, 
            graph_context,
            extraction_details  
        )
        
        return {
            'response': response,
            'mentioned_tickers': all_tickers,
            'mentioned_sectors': mentioned_sectors,
            'stock_data': stock_data,
            'relevant_articles': relevant_articles,
            'graph_context': graph_context,
            'extraction_details': extraction_details, 
            'search_queries_used': search_queries[:6],
            'cache_stats': self.entity_extractor.get_cache_stats()
        }
    #Generate Analysis
    def generate_response(self, query: str, articles: list[dict], stock_data: dict, graph_context: str, extraction_details: dict) -> str:
        relevant_articles = [article for article in articles if article.get('similarity_score', 0) > 0.1][:5]
        
        article_context = "\n\n".join([
            f"Article: {article['metadata']['title']}\n"
            f"Source: {article['metadata']['source']}\n"
            f"Content: {article['content'][:400]}..."
            for article in relevant_articles
        ])
        
        stock_context = "\n".join([
            f"{data['companyName']} ({ticker}) is currently priced at ${data['price']}"
            for ticker, data in stock_data.items()
        ])
        
        extraction_context = ""
        if extraction_details.get('companies'):
            companies_found = [f"{c['name']} ({c['ticker']}, confidence: {c['confidence']:.2f})" 
                             for c in extraction_details['companies']]
            extraction_context += f"Companies identified: {', '.join(companies_found)}. "
        
        if extraction_details.get('stock_groups'):
            groups_found = [f"{g['group']} (confidence: {g['confidence']:.2f})" 
                          for g in extraction_details['stock_groups']]
            extraction_context += f"Stock groups: {', '.join(groups_found)}. "

        if extraction_details.get('sector_queries'):
            sector_queries_found = [f"{sq['sector']} sector analysis (confidence: {sq['confidence']:.2f})" 
                                  for sq in extraction_details['sector_queries']]
            extraction_context += f"Sector queries: {', '.join(sector_queries_found)}. "
        
        is_sector_analysis = bool(extraction_details.get('sector_queries')) or len(stock_data) > 3

        
        system_prompt = f"""
            You are a senior financial analyst providing detailed investment analysis. 

            CRITICAL FORMATTING RULES - FOLLOW EXACTLY:
            
            CORRECT FORMAT EXAMPLES:
            - "Abbott Laboratories (ABT) is trading at $132.02, down 1.18%, with a market cap of $229.69 billion."
            - "Johnson & Johnson (JNJ) is priced at $156.90, down 0.50%, with a market capitalization of $377.51 billion."
            
            WRONG FORMATS TO AVOID:
            - DO NOT WRITE: "$132.02withadecreaseof1.18" 
            - DO NOT WRITE: "$132.02 w i t h a d e c r e a s e o f 1.18"
            - DO NOT WRITE: "132.02withadecreaseof1.18229.69"
            
            RULES:
            - Always put spaces between words
            - Always use complete sentences with proper grammar
            - Write "trading at $X.XX, up/down X.XX%" not concatenated numbers
            - Write "with a market cap of $X.XX billion" with spaces
            - Use normal sentence structure, not fragmented text
            - Never join numbers and words without spaces
            
            {"SECTOR ANALYSIS MODE: You are analyzing a broad sector or group of stocks. Provide sector-wide trends, compare performance across companies, and give sector outlook." if is_sector_analysis else "COMPANY ANALYSIS MODE: Focus on specific companies mentioned in the query."}
            
            Your responses should:
            - Provide specific, actionable insights based on the data
            - Analyze both current performance and future outlook
            - Consider market trends, sector dynamics, and company fundamentals
            - Explain the reasoning behind your analysis with specific evidence
            - Be comprehensive but clear and well-structured
            - Include both opportunities and risks
            - Reference the entity extraction confidence when relevant
            {"- For sector analysis: Compare performance across companies, identify sector leaders/laggards, discuss sector-wide trends" if is_sector_analysis else ""}
            """
        
        user_prompt = f"""
            User Question: {query}

            AI Entity Extraction Results:
            {extraction_context}

            Current Stock Data:
            {stock_context}

            Knowledge Graph Context:
            {graph_context}

            Recent Relevant News:
            {article_context}

            Please provide a comprehensive financial analysis that:
            1. Directly answers the user's question
            2. References SPECIFIC articles from the news section with details and insights
            3. Incorporates the stock price naturally (e.g., "Apple is trading at $211.16")
            4. Cites analyst opinions, ratings, and forecasts from the articles
            5. Discusses company-specific developments mentioned in the news
            6. Provides outlook based on the article content and trends
            7. Uses direct quotes or paraphrases from the news articles
            
            IMPORTANT: Your analysis should heavily reference the provided news articles. Cite specific analyst names, firms, price targets, and developments mentioned in the articles.
            """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1200,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content or ""
            
            import re
            
            response_text = re.sub(r'(\$\d+\.\d+)([a-z])', r'\1 \2', response_text)
            response_text = re.sub(r'(\d+\.\d+%)([a-z])', r'\1 \2', response_text)
            response_text = re.sub(r'(\d+)([a-z])', r'\1 \2', response_text)
            
            response_text = re.sub(r'withadecreaseof', 'with a decrease of ', response_text)
            response_text = re.sub(r'withanincreaseof', 'with an increase of ', response_text)
            response_text = re.sub(r'withadecrease', 'with a decrease', response_text)
            response_text = re.sub(r'withanincrease', 'with an increase', response_text)
            
            response_text = re.sub(r'(\d+\.\d+)\s*,\s*([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s*(\d+\.\d+)', r'\1, \2\3\4\5 \6', response_text)
            
            response_text = re.sub(r'(\d)\s+(\d)\s+(\d)\s*\.\s*(\d)\s+(\d)', r'\1\2\3.\4\5', response_text)
            response_text = re.sub(r'(\d)\s+(\d)\s*\.\s*(\d)\s+(\d)', r'\1\2.\3\4', response_text)
            response_text = re.sub(r'(\d)\s*\.\s*(\d)\s+(\d)', r'\1.\2\3', response_text)
            
            response_text = re.sub(r'([a-z])\s*\n\s*([a-z])\s*\n\s*([a-z])\s*\n\s*([a-z])', r'\1\2\3\4', response_text)
            response_text = re.sub(r'([a-z])\s*\n\s*([a-z])\s*\n\s*([a-z])', r'\1\2\3', response_text)
            response_text = re.sub(r'([a-z])\s*\n\s*([a-z])', r'\1\2', response_text)
            
            response_text = re.sub(r'\b([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\b', r'\1\2\3\4\5\6\7\8', response_text)
            response_text = re.sub(r'\b([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\b', r'\1\2\3\4\5\6\7', response_text)
            response_text = re.sub(r'\b([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\b', r'\1\2\3\4\5\6', response_text)
            response_text = re.sub(r'\b([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\b', r'\1\2\3\4\5', response_text)
            response_text = re.sub(r'\b([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\b', r'\1\2\3\4', response_text)
            response_text = re.sub(r'\b([a-z])\s+([a-z])\s+([a-z])\b', r'\1\2\3', response_text)
            
            response_text = re.sub(r'(\d+\.\d+)([a-z]+)(\d+\.\d+)', r'\1, \2 \3', response_text)
            
            return response_text
        except Exception as e:
            return f"Error generating response: {e}"