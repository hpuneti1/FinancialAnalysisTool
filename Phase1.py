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
        self.rateLimit()
        fromDate = (datetime.now() - timedelta(days = daysBack)).strftime('%Y-%m-%d')
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'from': fromDate, 
            'apikey': self.newsKey,
            'lang': 'en',
            'domains': 'reuters.com, bloomberg.com, cnbc.com, marketwatch.com'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'content': article.get('content'),
                    'url': article.get('url'),
                    'publishedAt': article.get('publishedAt'),
                    'src': article.get('source', {}).get('name')
                })
            return articles
        except Exception as e:
            print(f"Error fetching news for '{query}' : {e}")
            return []
    
    

class FinEntityExtractor:
    def __init__(self):
        self.sectorKeywords = {
            'Energy': ['oil', 'gas', 'energy', 'petroleum', 'drilling', 'refining'],
            'Materials': ['mining', 'chemicals', 'steel', 'aluminum', 'construction materials'],
            'Industrials': ['aerospace', 'defense', 'machinery', 'transportation', 'logistics'],
            'Consumer Discretionary': ['retail', 'automotive', 'media', 'entertainment', 'hotels'],
            'Consumer Staples': ['food', 'beverage', 'household products', 'tobacco'],
            'Health Care': ['pharmaceutical', 'biotech', 'medical device', 'healthcare'],
            'Financials': ['bank', 'insurance', 'financial services', 'investment'],
            'Information Technology': ['software', 'hardware', 'semiconductor', 'technology'],
            'Communication Services': ['telecom', 'social media', 'telecommunications'],
            'Utilities': ['electric', 'water', 'gas utility', 'renewable energy'],
            'Real Estate': ['reit', 'real estate', 'property management']
        }
        
        self.regulatoryKeywords = {
            'FDA': ['fda', 'drug approval', 'clinical trial', 'medical device'],
            'Federal Reserve': ['fed', 'interest rate', 'monetary policy', 'fomc'],
            'SEC': ['sec', 'securities', 'filing', 'investigation'],
            'EPA': ['epa', 'environmental', 'emissions', 'pollution']
        }
        
    def extractTickers(self, text: str) -> List[str]:
        import re
        tickerPattern = r'\b[A-Z]{2,5}\b'
        potentialTickers = re.findall(tickerPattern, text)
        falsePositives = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'HAD', 'WHO', 'OIL', 'GAS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'ITS', 'DID', 'GET', 'MAY', 'HIM', 'BOY', 'DAY', 'LET', 'PUT', 'END', 'WHY', 'TRY', 'GOD', 'SIX', 'DOG', 'EAT', 'AGO', 'SIT', 'FUN', 'BAD', 'YES', 'YET', 'ARM', 'OFF', 'TOP', 'TOO', 'OLD', 'ANY', 'APP', 'ADD', 'AGE', 'ASK', 'BAG', 'BIG', 'BOX', 'BUS', 'BUY', 'CAR', 'CUT', 'DOC', 'EAR', 'EYE', 'FAR', 'FEW', 'FIX', 'FLY', 'GUN', 'GUY', 'HIT', 'HOT', 'JOB', 'KEY', 'KID', 'LAW', 'LEG', 'LOT', 'LOW', 'MAN', 'MAP', 'MOM', 'NET', 'OWN', 'PAY', 'PEN', 'PET', 'RED', 'RUN', 'SAD', 'SAT', 'SET', 'SUN', 'TAX', 'TEA', 'TEN', 'USE', 'VAN', 'WAR', 'WIN', 'WON', 'ART', 'ETC', 'CEO', 'CTO', 'CFO'}
        return[ticker for ticker in potentialTickers if ticker not in falsePositives]
    
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
        self.graphBuilder.addStockPerformanceData(self.companiesDB)
  
  
class FinKG:
    def __init__(self):
        self.graph = Graph("neo4j://127.0.0.1:7687", auth = ("neo4j", "haradeep"))
    
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
            companyNode = Node("Company", 
                               ticker = ticker,
                               name = companyInfo.get('companyName', ''),
                               sector = companyInfo.get('sector', ''),
                               industry = companyInfo.get('industry', ''),
                               marketCap = companyInfo.get('marketCap', 0), 
                               exchange = companyInfo.get('exchange', ''),
                               country = companyInfo.get('country', ''))
            self.graph.merge(companyNode, "Company", "ticker")
            sector  = companyInfo.get('sector', '')
            if sector:
                sectorNode = self.graph.nodes.match("Sector", name = sector).first()
                if not sectorNode:
                    sectorNode = Node("Sector", name = sector, level = "sector")
                    self.graph.create(sectorNode)
                
                classifiedAs = Relationship(companyNode, "CLASSIFIED_AS", sectorNode)
                self.graph.merge(classifiedAs)
                
            if 'price' in companyInfo:
                stockNode = Node("StockPerformance",
                                    ticker = ticker,
                                    price = companyInfo.get('price', 0),
                                    change = companyInfo.get('change', 0),
                                    changePercent = companyInfo.get('changePercent', '0%'),
                                    volume = companyInfo.get('volume', 0),
                                    lastUpdated = companyInfo.get('lastUpdated', ''))
                self.graph.merge(stockNode, "StockPerfomance", "ticker")
                hasPerformance = Relationship(companyNode, "HAS_PERFORMANCE", stockNode)
                self.graph.merge(hasPerformance)
                
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

    
        
    
    