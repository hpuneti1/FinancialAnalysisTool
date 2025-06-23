import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import yfinance as yf
from py2neo import Graph, Node, Relationship
from typing import Dict, List

class FinDataCollector:
    def __init__(self):
        self.alphaKey = "22YNLVLWJUXRH9DV"
        self.fmpKey = "OHc4PfZ8pUkgYjnqC9Og2KR1D3zeX6To"
        self.newsKey = "d3e138fbb96d490ab6e203a441c32311"
        self.lastReqTime = 0
        self.minReqInterval = 1
        
    def rateLimit(self):
        currTime = time.time()
        timeSinceLast = currTime - self.lastReqTime
        if timeSinceLast < self.minReqInterval:
            time.sleep(self.minReqInterval - timeSinceLast)
        self.lastReqTime = time.time()
        
    def getStockData(self, ticker: str) -> Dict:
        """Use Yahoo Finance instead of Alpha Vantage"""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            
            if not hist.empty:
                latest = hist.iloc[-1]
                previous = hist.iloc[-2] if len(hist) > 1 else latest
                
                current_price = latest['Close']
                previous_close = previous['Close']
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
                
                print(f"  ✅ Got {ticker} stock data from Yahoo Finance")
                return {
                    'price': round(current_price, 2),
                    'change': round(change, 2),
                    'changePercent': f"{change_percent:.2f}%",
                    'volume': int(latest['Volume']) if latest['Volume'] else 0,
                    'lastUpdated': str(hist.index[-1].date())
                }
            else:
                print(f"  ✗ No stock data for {ticker}")
                return {}
                
        except Exception as e:
            print(f"  ✗ Yahoo Finance error for {ticker}: {e}")
            return {}
    
    def getCompanyProfile(self, ticker: str) -> Dict:
        print(f"  Getting company profile for {ticker}...")
        
        # Try FMP first, but fall back to Yahoo Finance if 401 error
        try:
            fmp_data = self._try_fmp_profile(ticker)
            if fmp_data:
                print(f"  ✅ Got {ticker} data from FMP")
                return fmp_data
        except Exception as e:
            print(f"  FMP failed for {ticker}: {e}")
        
        # Fallback to Yahoo Finance
        try:
            yahoo_data = self._get_yahoo_profile(ticker)
            if yahoo_data:
                print(f"  ✅ Got {ticker} data from Yahoo Finance")
                return yahoo_data
        except Exception as e:
            print(f"  Yahoo Finance failed for {ticker}: {e}")
    
    def _try_fmp_profile(self, ticker: str) -> Dict:
        """Try to get data from FMP"""
        self.rateLimit()
        url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}"
        params = {"apikey": self.fmpKey}
        
        response = requests.get(url, params=params)
        
        if response.status_code == 401:
            print(f"  ❌ FMP API key invalid (401 error)")
            return {}
        elif response.status_code == 403:
            print(f"  ❌ FMP API key expired or rate limited (403 error)")
            return {}
        elif response.status_code != 200:
            print(f"  ❌ FMP API error: {response.status_code}")
            return {}
        
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            company = data[0]
            return {
                'ticker': ticker,
                'companyName': company.get('companyName'),
                'sector': company.get('sector'),
                'industry': company.get('industry'),
                'exchange': company.get('exchange'),
                'marketCap': company.get('mktCap'),
                'description': company.get('description'),
                'website': company.get('website'),
                'country': company.get('country'),
            }
        return {}
    
    def _get_yahoo_profile(self, ticker: str) -> Dict:
        """Get company data from Yahoo Finance (FREE)"""
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or len(info) < 5:  # Check if we got meaningful data
            return {}
        
        return {
            'ticker': ticker,
            'companyName': info.get('longName') or info.get('shortName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'exchange': info.get('exchange'),
            'marketCap': info.get('marketCap'),
            'description': info.get('longBusinessSummary', '')[:300] + '...' if info.get('longBusinessSummary') else '',
            'website': info.get('website'),
            'country': info.get('country'),
        }
    
    def getFinancialNews(self, query: str, daysBack: int = 7) -> List[Dict]:
        """Improved news collection with better parameters"""
        self.rateLimit()
        fromDate = (datetime.now() - timedelta(days=daysBack)).strftime('%Y-%m-%d')
        url = "https://newsapi.org/v2/everything"
        
        params = {
            'q': query,
            'from': fromDate, 
            'apikey': self.newsKey,
            'language': 'en',
            'sortBy': 'relevancy',  # Changed to relevancy for better matching
            'pageSize': 30,  # Increased from default
            # Better financial news sources
            'domains': 'reuters.com,bloomberg.com,cnbc.com,marketwatch.com,yahoo.com,wsj.com,barrons.com,seekingalpha.com,fool.com'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                # Better content filtering
                title = article.get('title', '')
                description = article.get('description', '')
                content = article.get('content', '')
                
                # Combine all text for better analysis
                full_text = f"{title} {description} {content}".lower()
                
                # Skip if no meaningful content
                if len(full_text.strip()) < 100:
                    continue
                
                # Skip if it's clearly not financial/business content
                financial_keywords = ['stock', 'share', 'earnings', 'revenue', 'market', 'investment', 'company', 'financial', 'business', 'sector', 'industry']
                if not any(keyword in full_text for keyword in financial_keywords):
                    continue
                
                articles.append({
                    'title': title,
                    'description': description,
                    'content': content,
                    'url': article.get('url'),
                    'publishedAt': article.get('publishedAt'),
                    'src': article.get('source', {}).get('name')
                })
            
            print(f"  📰 Retrieved {len(articles)} relevant financial articles for '{query}'")
            return articles
            
        except Exception as e:
            print(f"  ❌ Error fetching news for '{query}': {e}")
            return []
    
    

class FinEntityExtractor:
    def __init__(self):
        self.sectorKeywords = {
            'Energy': ['oil', 'gas', 'energy', 'petroleum', 'drilling', 'refining', 'crude', 'exxon'],
            'Materials': ['mining', 'chemicals', 'steel', 'aluminum', 'construction materials'],
            'Industrials': ['aerospace', 'defense', 'machinery', 'transportation', 'logistics'],
            'Consumer Discretionary': ['retail', 'automotive', 'media', 'entertainment', 'hotels', 'tesla', 'electric vehicle', 'ev'],
            'Consumer Staples': ['food', 'beverage', 'household products', 'tobacco'],
            'Health Care': ['pharmaceutical', 'biotech', 'medical device', 'healthcare', 'drug', 'johnson', 'pfizer'],
            'Financials': ['bank', 'insurance', 'financial services', 'investment', 'jpmorgan', 'chase', 'banking'],
            'Information Technology': ['software', 'hardware', 'semiconductor', 'technology', 'apple', 'microsoft', 'tech', 'ai', 'artificial intelligence'],
            'Communication Services': ['telecom', 'social media', 'telecommunications'],
            'Utilities': ['electric', 'water', 'gas utility', 'renewable energy'],
            'Real Estate': ['reit', 'real estate', 'property management']
        }
        
        # Company name mappings for better detection
        self.companyMappings = {
            'apple': 'AAPL',
            'microsoft': 'MSFT', 
            'johnson & johnson': 'JNJ',
            'johnson and johnson': 'JNJ',
            'jpmorgan': 'JPM',
            'jp morgan': 'JPM',
            'jpmorgan chase': 'JPM',
            'exxon': 'XOM',
            'exxon mobil': 'XOM',
            'tesla': 'TSLA'
        }
        
        self.regulatoryKeywords = {
            'FDA': ['fda', 'drug approval', 'clinical trial', 'medical device', 'pharmaceutical'],
            'Federal Reserve': ['fed', 'federal reserve', 'interest rate', 'monetary policy', 'fomc'],
            'SEC': ['sec', 'securities', 'filing', 'investigation', 'securities and exchange'],
            'EPA': ['epa', 'environmental', 'emissions', 'pollution']
        }
        

    def extractTickers(self, text: str) -> List[str]:
        import re
        
        # Find ticker patterns
        tickerPattern = r'\b[A-Z]{2,5}\b'
        potentialTickers = re.findall(tickerPattern, text)
        
        # Your target companies - highest priority
        targetTickers = {'AAPL', 'MSFT', 'JNJ', 'JPM', 'XOM', 'TSLA'}
        
        # Common valid tickers (expand this list)
        validTickers = {
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'DIS', 'MA', 'PYPL', 'ADBE', 
            'NFLX', 'CRM', 'CMCSA', 'XOM', 'VZ', 'KO', 'PFE', 'INTC', 'CSCO', 
            'ABT', 'PEP', 'TMO', 'COST', 'AVGO', 'BAC', 'WFC', 'GS', 'C', 'MS'
        }
        
        # Definitely NOT tickers
        falsePositives = {
            'AI', 'NA', 'IT', 'OR', 'IN', 'ON', 'TO', 'OF', 'AT', 'BY', 'UP', 'SO',
            'CNBC', 'CNN', 'BBC', 'WSJ', 'NYSE', 'NASDAQ', 'DOW', 'SNP', 'FTSE',
            'USA', 'UK', 'EU', 'US', 'FDA', 'SEC', 'EPA', 'CEO', 'CFO', 'IPO', 'ETF',
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'NEW'
        }
        
        foundTickers = []
        
        # Prioritize target tickers
        for ticker in potentialTickers:
            if ticker in targetTickers:
                foundTickers.append(ticker)
            elif ticker in validTickers and ticker not in falsePositives:
                foundTickers.append(ticker)
        
        # Also check for company name mentions
        textLower = text.lower()
        companyMappings = {
            'apple': 'AAPL', 'microsoft': 'MSFT', 'tesla': 'TSLA',
            'johnson & johnson': 'JNJ', 'johnson and johnson': 'JNJ',
            'jpmorgan': 'JPM', 'jp morgan': 'JPM', 'jpmorgan chase': 'JPM',
            'exxon': 'XOM', 'exxon mobil': 'XOM',
            'amazon': 'AMZN', 'google': 'GOOGL', 'meta': 'META', 'facebook': 'META'
        }
        
        for companyName, ticker in companyMappings.items():
            if companyName in textLower and ticker not in foundTickers:
                foundTickers.append(ticker)
        
        return list(set(foundTickers))
        
    def classifySector(self, text: str) -> List[str]:
        textLower = text.lower()
        foundSectors = []
        for sector, keywords in self.sectorKeywords.items():
            if any(keyword in textLower for keyword in keywords):
                foundSectors.append(sector)
        return foundSectors
    
    def extractRegulatoryMentions(self, text: str) -> List[str]:
        textLower = text.lower()
        agencies = []
        for agency, keywords in self.regulatoryKeywords.items():
            if any(keyword in textLower for keyword in keywords):
                agencies.append(agency)
        return agencies
    
class RAG:
    def __init__(self):
        self.collector = FinDataCollector()
        self.extractor = FinEntityExtractor()
        self.companiesDB = {}
        self.newsDB = []
        self.graphBuilder = FinKG()

    def processSampleData(self, tickers: List[str] = None, newsQueries: List[str] = None):
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'JNJ', 'JPM', 'XOM', 'TSLA']
        
        # IMPROVED: Target specific companies AND broader topics
        if newsQueries is None:
            newsQueries = [
                # Direct company mentions with multiple keywords
                'Apple AAPL iPhone earnings revenue quarterly',
                'Microsoft MSFT Azure cloud computing earnings',
                'Johnson & Johnson JNJ pharmaceutical drug development',
                'JPMorgan Chase JPM banking financial results',
                'Exxon Mobil XOM oil energy earnings',
                'Tesla TSLA electric vehicle deliveries earnings',
                
                # Broader sector searches likely to mention your companies
                'big tech earnings Apple Microsoft',
                'pharmaceutical industry Johnson & Johnson drug approvals',
                'major banks JPMorgan Chase earnings results',
                'oil companies Exxon energy sector performance',
                'electric vehicle market Tesla automotive',
                'cloud computing Microsoft Azure technology'
            ]
        
        # Process companies first
        for ticker in tickers:
            print(f"Processing {ticker}...")
            companyData = self.collector.getCompanyProfile(ticker)
            stockData = self.collector.getStockData(ticker)
            
            if companyData:
                combinedData = {**companyData, **stockData}
                self.companiesDB[ticker] = combinedData
        
        # Process news with better error handling and filtering
        for query in newsQueries:
            print(f"Searching news for: '{query}'...")
            articles = self.collector.getFinancialNews(query, daysBack=14)  # Increased to 14 days
            
            if not articles:
                print(f"  No articles found for '{query}'")
                continue
                
            print(f"  Found {len(articles)} articles")
            
            for article in articles:
                # Skip articles with no meaningful content
                content = article.get('content', '') or article.get('description', '')
                if not content or len(content) < 50:
                    continue
                    
                # Extract entities
                tickersMentioned = self.extractor.extractTickers(content)
                sectorsMentioned = self.extractor.classifySector(content)
                regulatoryMentions = self.extractor.extractRegulatoryMentions(content)
                
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
        
        print(f"\nCollected {len(self.newsDB)} total articles")


    def simpleQuery(self, question: str) -> Dict:
        questionTickers = self.extractor.extractTickers(question)
        questionSectors = self.extractor.classifySector(question)
        questionAgencies = self.extractor.extractRegulatoryMentions(question)
        
        relevantCompanies = []
        for ticker, companyData in self.companiesDB.items():
            if(ticker in questionTickers or companyData.get('sector') in questionSectors):
                relevantCompanies.append(companyData)
        relevantNews = []
        for article in self.newsDB:
            entities = article['extractedEntities']
            if (any(ticker in entities['tickers'] for ticker in questionTickers) or
                any(sector in entities['sectors'] for sector in questionSectors) or
                any(agency in entities['regulatoryAgencies'] for agency in questionAgencies)):
                relevantNews.append(article)
        return {
            'question': question,
            'relevantCompanies': relevantCompanies[:5],
            'relevantNews': relevantNews[:5],
            'extractedEntities': {
                'tickers': questionTickers,
                'sectors': questionSectors,
                'agencies': questionAgencies
            }
        }     
    def printSummary(self):
        sectorCounts = {}
        print(f"\n=== Data Collection Summary ===")
        print(f"Companies in database: {len(self.companiesDB)}")
        print(f"News articles collected: {len(self.newsDB)}")
        for company in self.companiesDB.values():
            sector = company.get('sector', 'Unknown')
            sectorCounts[sector] = sectorCounts.get(sector, 0) + 1
        for sector, count in sorted(sectorCounts.items()):
            print(f" {sector}: {count}")
    def buildKG(self):
        self.graphBuilder.clearDB()
        self.graphBuilder.createConstraints()
        self.graphBuilder.loadGICSHiearchy()
        self.graphBuilder.loadCompanies(self.companiesDB)
        self.graphBuilder.loadArticles(self.newsDB)
        self.graphBuilder.createRegulatoryEntities()
  
class FinKG:
    def __init__(self):
        self.graph = Graph("neo4j://127.0.0.1:7687", auth = ("neo4j", "admin123"))
    
    def clearDB(self):
        self.graph.run("MATCH (n) DETACH DELETE n")
        print("Database cleared")
        print("Database cleared")
    
    def createConstraints(self):
        constraints = [
            "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
            "CREATE CONSTRAINT sector_code IF NOT EXISTS FOR (s:Sector) REQUIRE s.gics_code IS UNIQUE",
            "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:NewsArticle) REQUIRE a.id IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                self.graph.run(constraint)
                print(f"Created constriant: {constraint}")
            except Exception as e:
                print(f"Constraint already exists : {e}")
    def loadGICSHiearchy(self):
        gicsSectors = {
            "45": {"name": "Information Technology", "companies": ["AAPL", "MSFT"]},
            "35": {"name": "Health Care", "companies": ["JNJ"]}, 
            "40": {"name": "Financials", "companies": ["JPM"]},
            "10": {"name": "Energy", "companies": ["XOM"]},
            "25": {"name": "Consumer Discretionary", "companies": ["TSLA"]}
        }
        for gicsCode, sectorInfo in gicsSectors.items():
            sectorNode = Node("Sector", gicsCode = gicsCode, name = sectorInfo["name"], level = "sector")
            self.graph.merge(sectorNode, "Sector", "gicsCode")
    
    def loadCompanies(self, companiesData: Dict):
        for ticker, companyInfo in companiesData.items():
            try:
                # Convert numpy types to Python native types
                def convert_value(value):
                    if hasattr(value, 'item'):  # numpy scalar
                        return value.item()
                    elif isinstance(value, (int, float, str, bool)) or value is None:
                        return value
                    else:
                        return float(value) if str(value).replace('.','').replace('-','').isdigit() else str(value)
                
                # Create company node with converted values
                companyNode = Node("Company", 
                                ticker=ticker,
                                name=str(companyInfo.get('companyName', '')),
                                sector=str(companyInfo.get('sector', '')),
                                industry=str(companyInfo.get('industry', '')),
                                marketCap=convert_value(companyInfo.get('marketCap', 0)), 
                                exchange=str(companyInfo.get('exchange', '')),
                                country=str(companyInfo.get('country', '')))
                
                self.graph.merge(companyNode, "Company", "ticker")
                
                # Handle sector relationship
                sector = companyInfo.get('sector', '')
                if sector:
                    sectorNode = self.graph.nodes.match("Sector", name=sector).first()
                    if not sectorNode:
                        sectorNode = Node("Sector", name=str(sector), level="sector")
                        self.graph.create(sectorNode)
                    
                    classifiedAs = Relationship(companyNode, "CLASSIFIED_AS", sectorNode)
                    self.graph.merge(classifiedAs)
                
                # Handle stock performance with data type conversion
                if 'price' in companyInfo:
                    stockNode = Node("StockPerformance", 
                                    ticker=ticker,
                                    price=convert_value(companyInfo.get('price', 0)),
                                    change=convert_value(companyInfo.get('change', 0)),
                                    changePercent=str(companyInfo.get('change_percent', '0%')),  
                                    volume=convert_value(companyInfo.get('volume', 0)),
                                    lastUpdated=str(companyInfo.get('last_updated', '')))
                    
                    self.graph.merge(stockNode, "StockPerformance", "ticker")  # Fixed spelling
                    
                    hasPerformance = Relationship(companyNode, "HAS_PERFORMANCE", stockNode)
                    self.graph.merge(hasPerformance)
                
                print(f"✅ Loaded company: {ticker} - {companyInfo.get('companyName', '')}")
                
            except Exception as e:
                print(f"❌ Error loading {ticker}: {e}")
                print(f"   Data types: price={type(companyInfo.get('price'))}, change={type(companyInfo.get('change'))}")
                    
                print(f"Loaded company: {ticker} - {companyInfo.get('companyName', '')}")
    
    def loadArticles(self, newsData: List[Dict]):
        for i, article in enumerate(newsData):
            articleId = f"news_{i}_{hash(article.get('title', ''))}"
            articleNode = Node("NewsArticle",
                               id = articleId,
                               title = article.get('title', ''),
                               description = article.get('description', ''),
                               content = article.get('content', ''),
                               url = article.get('url', ''),
                               publishedAt = article.get('publishedAt', ''),
                               source = article.get('source', ''))
            self.graph.merge(articleNode, "NewsArticle", 'id')
            extractedEntities = article.get('extractedEntities', {})
            mentionedTickers = extractedEntities.get('tickers', [])
            
            for ticker in mentionedTickers:
                companyNode = self.graph.nodes.match("Company", ticker = ticker).first()
                if companyNode:
                    mentionsRelationship = Relationship(articleNode, "MENTIONS", companyNode)
                    self.graph.merge(mentionsRelationship)
    
    def createRegulatoryEntities(self):
        regulatoryBodies = [
            {"name": "FDA", "fullName": "Food and Drug Administration", "jurisdiction": "US"},
            {"name": "Federal Reserve", "fullName": "Federal Reserve System", "jurisdiction": "US"},
            {"name": "SEC", "fullName": "Securities and Exchange Commission", "jurisdiction": "US"},
            {"name": "EPA", "fullName": "Environmental Protection Agency", "jurisdiction": "US"}
        ]
        
        for agency in regulatoryBodies:
            regulatoryNode = Node("RegulatoryBody",
                                  name = agency["name"],
                                  fullName = agency["fullName"],
                                  jurisdiction = agency["jurisdiction"]
                                  )
            self.graph.merge(regulatoryNode, "RegulatoryBody", "name")
            print(f"Created regulatory body: {agency['name']}")
        
        sectorRegulations = {
            "Health Care": ["FDA"],
            "Financials": ["Federal Reserve", "SEC"],
            "Information Technology": ["SEC"],
            "Energy": ["EPA, SEC"],
            "Consumer Discretionary": ["SEC"],
        }
        
        for sectorName, agencies in sectorRegulations.items():
            sectorNode = self.graph.nodes.match("Sector", name = sectorName).first()
            if sectorNode:
                for agencyName in agencies:
                    agencyNode = self.graph.nodes.match("RegulatoryBody", name = agencyName).first()
                    if agencyNode:
                        regulatedBy = Relationship(sectorNode, "REGULATED_BY", agencyNode)
                        self.graph.merge(regulatedBy)
     

            
if __name__  == "__main__":
    ragSystem = RAG()
    ragSystem.processSampleData()
    ragSystem.printSummary()
    ragSystem.buildKG()

    
        
    
    