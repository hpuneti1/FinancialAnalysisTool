from openai import OpenAI
from FinDataCollector import FinancialDataCollector
from EntityExtractor import EntityExtractor
from KG import FinancialKnowledgeGraph
from VectorDB import VectorDatabase

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
        
        # Enhanced: Handle sector queries with representative tickers
        sector_tickers = []
        if extraction_details.get('sector_queries'):
            for sector_query in extraction_details['sector_queries']:
                if sector_query.get('confidence', 0) > 0.6:
                    sector_name = sector_query['sector']
                    tickers = self.entity_extractor.get_sector_tickers(sector_name)
                    sector_tickers.extend(tickers)
                    print(f"Added {len(tickers)} tickers for {sector_name} sector: {tickers}")
        
        # Combine all tickers
        all_tickers = list(set(mentioned_tickers + sector_tickers))
        
        stock_data = {}
        for ticker in all_tickers:  # Changed from mentioned_tickers to all_tickers
            data = self.data_collector.get_stock_data(ticker)
            if data:
                stock_data[ticker] = data
                self.knowledge_graph.add_company(data)
        
        stock_data = {}
        for ticker in mentioned_tickers:
            data = self.data_collector.get_stock_data(ticker)
            if data:
                stock_data[ticker] = data
                self.knowledge_graph.add_company(data)
        
        search_queries = []
        
        for sector_query in extraction_details.get('sector_queries', []):
            if sector_query.get('confidence', 0) > 0.6:
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
        for ticker in all_tickers:  # Changed from mentioned_tickers to all_tickers
            query_variants.add(ticker)
        for sector in mentioned_sectors:
            query_variants.add(sector)
        # Add sector query terms
        for sector_query in extraction_details.get('sector_queries', []):
            query_variants.add(sector_query['sector'])
        if not query_variants:
            query_variants.add(user_query)

        all_articles = []
        all_tickers = []
        
        for query in search_queries[:6]:  
            articles = self.data_collector.search_news(query, days_back=21, query_variants=list(query_variants), entity_extractor=self.entity_extractor)
            for article in articles:
                article_tickers = self.entity_extractor.extract_tickers(
                    f"{article.get('title', '')} {article.get('content', '')}"
                )
                all_articles.append(article)
                all_tickers.append(article_tickers)

                self.knowledge_graph.add_news_article(article, article_tickers)
        
        print(f"Fetched {len(all_articles)} articles from RSS feeds.")

        if self.entity_extractor is not None:
            relevant_articles = []
            for article in all_articles:
                entities = self.entity_extractor.extract_entities(article['title'] + ' ' + article['content'])
                # Check if any query_variant matches a company name, ticker, or sector
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
            # --- Debug: Print number of articles after entity extraction filtering ---
            print(f"{len(articles)} articles after entity extraction filtering.")
            # ------------------------------------------------------------------------
        else:
            articles = all_articles

        seen = set()
        unique_articles = []
        for article in articles:
            if article['url'] not in seen:
                unique_articles.append(article)
                seen.add(article['url'])
        # --- Debug: Print number of unique articles after deduplication ---
        print(f"{len(unique_articles)} unique articles after deduplication.")
        # ------------------------------------------------------------------

        # --- Deduplicate articles by URL before adding to vector DB ---
        unique_articles_db = []
        unique_tickers_db = []
        seen_urls_db = set()
        for article, tickers in zip(all_articles, all_tickers):
            url = article.get('url')
            if url and url not in seen_urls_db:
                unique_articles_db.append(article)
                unique_tickers_db.append(tickers)
                seen_urls_db.add(url)
        # ------------------------------------------------------------

        if unique_articles_db:
            self.vector_db.add_articles(unique_articles_db, unique_tickers_db)
        
        relevant_articles = self.vector_db.search(user_query, n_results=8)
        
        # --- Show all articles regardless of similarity score for debugging ---
        print(f"{len(relevant_articles)} articles after vector DB search (no score filtering).")
        for a in relevant_articles:
            print(f"Title: {a['title'] if 'title' in a else a.get('metadata', {}).get('title', '')}, Score: {a.get('similarity_score', 0)}")
        # ---------------------------------------------------------------------

        # --- Stricter entity-based post-filtering: only include articles where the main company matches a query variant ---
        is_sector_query = bool(extraction_details.get('sector_queries'))
        
        if is_sector_query:
            filtered_articles = []
            for article in relevant_articles:
                content = article.get('content', '')
                if not content and 'metadata' in article:
                    content = article['metadata'].get('title', '')
                entities = self.entity_extractor.extract_entities(content)
                
                article_tickers = entities.get('tickers_mentioned', [])
                if any(ticker in all_tickers for ticker in article_tickers):
                    filtered_articles.append(article)
                    continue
                
                companies = entities.get('companies', [])
                if any(company.get('ticker') in all_tickers for company in companies):
                    filtered_articles.append(article)
                    continue
                
                sectors = [s['sector'] for s in entities.get('sectors', [])]
                if any(sector in mentioned_sectors for sector in sectors):
                    filtered_articles.append(article)
            
            relevant_articles = filtered_articles
            print(f"{len(relevant_articles)} articles after sector-aware filtering.")
        else:
            filtered_articles = []
            for article in relevant_articles:
                content = article.get('content', '')
                if not content and 'metadata' in article:
                    content = article['metadata'].get('title', '')
                entities = self.entity_extractor.extract_entities(content)
                companies = entities.get('companies', [])
                if companies:
                    main_company = companies[0]
                    if (
                        main_company.get('name') in query_variants or
                        main_company.get('ticker') in query_variants
                    ):
                        filtered_articles.append(article)
            relevant_articles = filtered_articles
            print(f"{len(relevant_articles)} articles after company-specific filtering.")
        # -------------------------------------------------------------------------

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
    
    def generate_response(self, query: str, articles: list[dict], stock_data: dict, graph_context: str, extraction_details: dict) -> str:
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
        
        # Detect if this is a sector-wide analysis
        is_sector_analysis = bool(extraction_details.get('sector_queries')) or len(stock_data) > 3

        
        system_prompt = f"""
            You are a senior financial analyst providing detailed investment analysis. 

            IMPORTANT FORMATTING RULES:
            - Use simple, clean text without special formatting
            - Write numbers clearly: $315.00 and 4.75% (no bold, no asterisks)
            - Use bullet points with simple dashes (-)
            - Keep formatting minimal and readable
            - Do not use markdown formatting like **bold** or *italics*
            
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
                max_tokens=1200,
                temperature=0.2
            )
            
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error generating response: {e}"