import re
import yfinance as yf
from typing import List

class EntityExtractor:
    def __init__(self):
        # AI Generated groups, keywords, and mappings
        self.stock_groups = {
            'faang': ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL'],
            'fang': ['META', 'AAPL', 'NFLX', 'GOOGL'],
            'mag 7': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'],
            'magnificent 7': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'],
            'big tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'],
            'mega cap tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'],
            'dow jones': ['DOW'], 
            'nasdaq': ['NASDAQ'],  
            'sp500': ['SPY'],  
            's&p 500': ['SPY'],
            'spy': ['SPY'],
            'qqq': ['QQQ'], 
            'semiconductor stocks': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'MU'],
            'chip stocks': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'MU'],
            'bank stocks': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS'],
            'oil stocks': ['XOM', 'CVX', 'COP', 'EOG', 'SLB'],
            'airline stocks': ['DAL', 'UAL', 'AAL', 'LUV'],
            'ev stocks': ['TSLA', 'F', 'GM', 'RIVN', 'LCID'],
            'electric vehicle stocks': ['TSLA', 'F', 'GM', 'RIVN', 'LCID'],
            'pharma stocks': ['JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'BMY'],
            'biotech stocks': ['GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX'],
            'reit stocks': ['AMT', 'PLD', 'CCI', 'EQIX', 'SPG', 'O'],
            'meme stocks': ['GME', 'AMC', 'BB', 'NOK'],
            'chinese stocks': ['BABA', 'JD', 'PDD', 'BIDU', 'NIO'],
            'social media stocks': ['META', 'SNAP', 'PINS', 'TWTR'],
            'streaming stocks': ['NFLX', 'DIS', 'ROKU', 'PARA']
        }
        self.sector_keywords = {
            'Technology': [
                'tech', 'software', 'hardware', 'semiconductor', 'cloud', 'saas', 'cybersecurity',
                'apple', 'microsoft', 'google', 'alphabet', 'amazon', 'meta', 'facebook', 'nvidia',
                'intel', 'amd', 'oracle', 'salesforce', 'adobe', 'cisco', 'ibm', 'dell', 'hp',
                'ai', 'artificial intelligence', 'machine learning', 'data analytics', 'automation',
                'robotics', 'virtual reality', 'augmented reality', 'blockchain', 'cryptocurrency'
            ],
            'Healthcare': [
                'pharmaceutical', 'biotech', 'medical', 'healthcare', 'drug', 'medicine', 'clinical',
                'johnson & johnson', 'pfizer', 'merck', 'abbvie', 'bristol myers', 'eli lilly',
                'moderna', 'gilead', 'amgen', 'biogen', 'regeneron', 'vertex', 'illumina',
                'medical device', 'diagnostics', 'vaccine', 'therapy', 'treatment', 'fda approval',
                'hospital', 'insurance', 'health plan', 'telemedicine', 'digital health'
            ],
            'Financial': [
                'bank', 'financial', 'insurance', 'credit', 'lending', 'mortgage', 'investment',
                'jpmorgan', 'jp morgan', 'goldman sachs', 'morgan stanley', 'bank of america',
                'wells fargo', 'citigroup', 'american express', 'visa', 'mastercard', 'paypal',
                'square', 'stripe', 'fintech', 'payment', 'trading', 'brokerage', 'asset management',
                'private equity', 'hedge fund', 'real estate', 'reit', 'cryptocurrency exchange'
            ],
            'Energy': [
                'oil', 'gas', 'energy', 'petroleum', 'natural gas', 'crude oil', 'refining',
                'exxon', 'chevron', 'conocophillips', 'bp', 'shell', 'total', 'marathon',
                'renewable energy', 'solar', 'wind', 'nuclear', 'hydroelectric', 'geothermal',
                'clean energy', 'green energy', 'carbon neutral', 'emissions', 'climate',
                'utilities', 'power generation', 'electricity', 'grid', 'infrastructure'
            ],
            'Consumer Discretionary': [
                'retail', 'consumer', 'automotive', 'car', 'vehicle', 'restaurant', 'hotel',
                'tesla', 'ford', 'general motors', 'toyota', 'honda', 'bmw', 'mercedes',
                'nike', 'adidas', 'walmart', 'target', 'costco', 'home depot', 'lowes',
                'amazon', 'alibaba', 'ebay', 'etsy', 'shopify', 'uber', 'lyft', 'airbnb',
                'ev', 'electric vehicle', 'luxury', 'fashion', 'entertainment', 'gaming',
                'streaming', 'media', 'social media', 'e-commerce', 'marketplace'
            ],
            'Consumer Staples': [
                'food', 'beverage', 'grocery', 'household products', 'personal care', 'tobacco',
                'coca cola', 'pepsi', 'nestle', 'unilever', 'procter gamble', 'colgate',
                'walmart', 'kroger', 'costco', 'general mills', 'kellogg', 'kraft heinz',
                'consumer goods', 'fmcg', 'packaged goods', 'supermarket', 'convenience store'
            ],
            'Industrials': [
                'aerospace', 'defense', 'machinery', 'transportation', 'logistics', 'shipping',
                'boeing', 'lockheed martin', 'raytheon', 'general electric', 'caterpillar',
                'deere', 'fedex', 'ups', 'union pacific', 'csx', 'norfolk southern',
                'manufacturing', 'construction', 'infrastructure', 'railway', 'airline',
                'industrial equipment', 'heavy machinery', 'supply chain', 'warehousing'
            ],
            'Materials': [
                'mining', 'chemicals', 'steel', 'aluminum', 'copper', 'gold', 'silver',
                'construction materials', 'cement', 'glass', 'paper', 'packaging',
                'dow', 'dupont', 'basf', 'linde', 'air products', 'sherwin williams',
                'commodities', 'raw materials', 'metals', 'forestry', 'agriculture'
            ],
            'Communication Services': [
                'telecom', 'telecommunications', 'wireless', 'broadband', 'internet',
                'verizon', 'att', 't-mobile', 'comcast', 'charter', 'dish',
                'social media', 'streaming', 'content', 'advertising', 'marketing',
                'google', 'facebook', 'twitter', 'netflix', 'disney', 'paramount'
            ],
            'Utilities': [
                'electric', 'electricity', 'power', 'water', 'gas utility', 'utility company',
                'renewable energy', 'solar power', 'wind power', 'nuclear power',
                'nextera', 'duke energy', 'southern company', 'dominion', 'american electric',
                'grid', 'transmission', 'distribution', 'regulated utility', 'infrastructure'
            ],
            'Real Estate': [
                'reit', 'real estate', 'property', 'commercial real estate', 'residential',
                'property management', 'development', 'construction', 'mortgage reit',
                'simon property', 'realty income', 'equity residential', 'boston properties',
                'housing', 'apartment', 'office', 'retail property', 'warehouse', 'data center'
            ]
        }
        
        self.company_mappings = {
            # Technology
            'apple': 'AAPL', 'apple inc': 'AAPL',
            'microsoft': 'MSFT', 'microsoft corp': 'MSFT', 'microsoft corporation': 'MSFT',
            'google': 'GOOGL', 'alphabet': 'GOOGL', 'alphabet inc': 'GOOGL',
            'amazon': 'AMZN', 'amazon.com': 'AMZN',
            'meta': 'META', 'facebook': 'META', 'meta platforms': 'META',
            'nvidia': 'NVDA', 'nvidia corp': 'NVDA', 'nvidia corporation': 'NVDA',
            'tesla': 'TSLA', 'tesla inc': 'TSLA', 'tesla motors': 'TSLA',
            'netflix': 'NFLX',
            'adobe': 'ADBE', 'adobe inc': 'ADBE',
            'salesforce': 'CRM', 'salesforce.com': 'CRM',
            'oracle': 'ORCL', 'oracle corp': 'ORCL',
            'intel': 'INTC', 'intel corp': 'INTC',
            'cisco': 'CSCO', 'cisco systems': 'CSCO',
            'ibm': 'IBM', 'international business machines': 'IBM',
            'advanced micro devices': 'AMD', 'amd': 'AMD',
            
            # Healthcare
            'johnson & johnson': 'JNJ', 'johnson and johnson': 'JNJ', 'j&j': 'JNJ',
            'pfizer': 'PFE', 'pfizer inc': 'PFE',
            'unitedhealth': 'UNH', 'united health': 'UNH', 'unitedhealth group': 'UNH',
            'merck': 'MRK', 'merck & co': 'MRK',
            'abbvie': 'ABBV', 'abbvie inc': 'ABBV',
            'eli lilly': 'LLY', 'lilly': 'LLY',
            'bristol myers squibb': 'BMY', 'bristol myers': 'BMY',
            'moderna': 'MRNA', 'moderna inc': 'MRNA',
            'gilead': 'GILD', 'gilead sciences': 'GILD',
            'amgen': 'AMGN', 'amgen inc': 'AMGN',
            
            # Financial
            'jpmorgan': 'JPM', 'jp morgan': 'JPM', 'jpmorgan chase': 'JPM', 'chase': 'JPM',
            'goldman sachs': 'GS', 'goldman': 'GS',
            'morgan stanley': 'MS',
            'bank of america': 'BAC', 'bofa': 'BAC',
            'wells fargo': 'WFC', 'wells': 'WFC',
            'citigroup': 'C', 'citi': 'C', 'citibank': 'C',
            'american express': 'AXP', 'amex': 'AXP',
            'visa': 'V', 'visa inc': 'V',
            'mastercard': 'MA', 'mastercard inc': 'MA',
            'paypal': 'PYPL', 'paypal holdings': 'PYPL',
            'berkshire hathaway': 'BRK.B', 'berkshire': 'BRK.B',
            
            # Energy
            'exxon': 'XOM', 'exxon mobil': 'XOM', 'exxonmobil': 'XOM',
            'chevron': 'CVX', 'chevron corp': 'CVX',
            'conocophillips': 'COP',
            'marathon petroleum': 'MPC',
            'valero': 'VLO', 'valero energy': 'VLO',
            'phillips 66': 'PSX',
            
            # Consumer Discretionary
            'walmart': 'WMT', 'walmart inc': 'WMT',
            'home depot': 'HD', 'the home depot': 'HD',
            'mcdonalds': 'MCD', "mcdonald's": 'MCD',
            'nike': 'NKE', 'nike inc': 'NKE',
            'starbucks': 'SBUX', 'starbucks corp': 'SBUX',
            'disney': 'DIS', 'walt disney': 'DIS',
            'ford': 'F', 'ford motor': 'F',
            'general motors': 'GM', 'gm': 'GM',
            'target': 'TGT', 'target corp': 'TGT',
            'lowes': "LOW", "lowe's": 'LOW',
            
            # Consumer Staples
            'coca cola': 'KO', 'coca-cola': 'KO', 'coke': 'KO',
            'pepsi': 'PEP', 'pepsico': 'PEP',
            'procter & gamble': 'PG', 'procter and gamble': 'PG', 'p&g': 'PG',
            'walmart': 'WMT',
            'costco': 'COST', 'costco wholesale': 'COST',
            'general mills': 'GIS',
            'kellogg': 'K', 'kellogg company': 'K',
            
            # Industrials
            'boeing': 'BA', 'boeing company': 'BA',
            'caterpillar': 'CAT', 'caterpillar inc': 'CAT',
            'general electric': 'GE', 'ge': 'GE',
            'lockheed martin': 'LMT',
            'raytheon': 'RTX', 'raytheon technologies': 'RTX',
            'fedex': 'FDX', 'federal express': 'FDX',
            'ups': 'UPS', 'united parcel service': 'UPS',
            'union pacific': 'UNP',
            
            # Communication Services
            'verizon': 'VZ', 'verizon communications': 'VZ',
            'at&t': 'T', 'att': 'T',
            't-mobile': 'TMUS', 'tmobile': 'TMUS',
            'comcast': 'CMCSA', 'comcast corp': 'CMCSA',
            'charter': 'CHTR', 'charter communications': 'CHTR',
            
            # Utilities
            'nextera energy': 'NEE', 'nextera': 'NEE',
            'duke energy': 'DUK',
            'southern company': 'SO',
            'dominion energy': 'D',
            
            # Real Estate
            'american tower': 'AMT',
            'prologis': 'PLD',
            'crown castle': 'CCI',
            'realty income': 'O',
            'simon property': 'SPG',
            
            # International
            'taiwan semiconductor': 'TSM', 'tsmc': 'TSM',
            'asml': 'ASML',
            'samsung': '005930.KS',
            'alibaba': 'BABA',
            'tencent': 'TCEHY'
        }
    
    def extract_tickers(self, text: str) -> List[str]:
        text_lower = text.lower()
        found_tickers = []
        
        for group_name, tickers in self.stock_groups.items():
            if group_name in text_lower:
                found_tickers.extend(tickers)
                print(f"DEBUG: Found stock group '{group_name}' -> {tickers}")
        
        sorted_companies = sorted(self.company_mappings.items(), key=lambda x: len(x[0]), reverse=True)
        
        for company_name, ticker in sorted_companies:
            if company_name in text_lower:
                found_tickers.append(ticker)
                text_lower = text_lower.replace(company_name, '')
        
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        potential_tickers = re.findall(ticker_pattern, text)
        
        valid_tickers = {
            # Technology
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'ADBE',
            'CRM', 'ORCL', 'INTC', 'CSCO', 'IBM', 'AMD', 'QCOM', 'PYPL', 'AVGO', 'TXN',
            'INTU', 'MU', 'LRCX', 'KLAC', 'MRVL', 'ADI', 'AMAT', 'SNPS', 'CDNS', 'FTNT',
            
            # Healthcare
            'JNJ', 'PFE', 'UNH', 'MRK', 'ABBV', 'LLY', 'BMY', 'MRNA', 'GILD', 'AMGN',
            'BIIB', 'REGN', 'VRTX', 'ISRG', 'DHR', 'TMO', 'ABT', 'SYK', 'BSX', 'MDT',
            
            # Financial
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'AXP', 'V', 'MA', 'BRK.A', 'BRK.B',
            'BLK', 'SPGI', 'AIG', 'TFC', 'USB', 'PNC', 'COF', 'SCHW', 'CME', 'ICE',
            
            # Energy
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'VLO', 'PSX', 'OXY', 'BKR',
            'HAL', 'DVN', 'FANG', 'MRO', 'APA', 'CVE', 'CNQ', 'SU', 'IMO', 'TRP',
            
            # Consumer Discretionary
            'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'DIS', 'F', 'GM', 'TGT', 'LOW',
            'TJX', 'ORLY', 'AZO', 'YUM', 'CMG', 'MAR', 'HLT', 'ABNB', 'BKNG', 'EXPE',
            
            # Consumer Staples
            'KO', 'PEP', 'PG', 'WMT', 'COST', 'GIS', 'K', 'HSY', 'MDLZ', 'KHC',
            'CL', 'CLX', 'CHD', 'SJM', 'CPB', 'CAG', 'TSN', 'HRL', 'MKC', 'LW',
            
            # Industrials
            'BA', 'CAT', 'GE', 'LMT', 'RTX', 'FDX', 'UPS', 'UNP', 'CSX', 'NSC',
            'MMM', 'HON', 'ETN', 'EMR', 'ITW', 'PH', 'CMI', 'DE', 'IR', 'ROK',
            
            # Communication Services
            'VZ', 'T', 'TMUS', 'CMCSA', 'CHTR', 'DISH', 'LUMN', 'SIRI', 'TWTR', 'SNAP',
            
            # Utilities
            'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'XEL', 'SRE', 'PCG', 'ED',
            
            # Real Estate
            'AMT', 'PLD', 'CCI', 'EQIX', 'DLR', 'SBAC', 'O', 'SPG', 'AVB', 'EQR',
            
            # Materials
            'LIN', 'APD', 'ECL', 'SHW', 'DD', 'DOW', 'NEM', 'FCX', 'NUE', 'VMC',
            
            # ETFs
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND', 'GLD'
        }
        
        false_positives = {
            'AI', 'IT', 'US', 'EU', 'CEO', 'CFO', 'IPO', 'ETF', 'SEC', 'FDA', 'API',
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'NEW',
            'ONE', 'TWO', 'GET', 'SEE', 'NOW', 'WAY', 'WHO', 'BOY', 'DID', 'ITS',
            'HER', 'OLD', 'HAS', 'HIM', 'HIS', 'SHE', 'TWO', 'HOW', 'ITS', 'OUR'
        }
        
        for ticker in potential_tickers:
            if ticker in valid_tickers and ticker not in false_positives and ticker not in found_tickers:
                found_tickers.append(ticker)
        
        return list(set(found_tickers))
    
    def extract_sectors(self, text: str) -> List[str]:
        """Extract relevant sectors from text"""
        text_lower = text.lower()
        found_sectors = []
        
        group_to_sector = {
            'faang': 'Technology',
            'fang': 'Technology', 
            'mag 7': 'Technology',
            'magnificent 7': 'Technology',
            'big tech': 'Technology',
            'mega cap tech': 'Technology',
            'semiconductor stocks': 'Technology',
            'chip stocks': 'Technology',
            'bank stocks': 'Financial',
            'oil stocks': 'Energy',
            'airline stocks': 'Industrials',
            'ev stocks': 'Consumer Discretionary',
            'electric vehicle stocks': 'Consumer Discretionary',
            'pharma stocks': 'Healthcare',
            'biotech stocks': 'Healthcare',
            'reit stocks': 'Real Estate',
            'chinese stocks': 'International',
            'social media stocks': 'Communication Services',
            'streaming stocks': 'Communication Services'
        }
        
        for group_name, sector in group_to_sector.items():
            if group_name in text_lower:
                found_sectors.append(sector)
        
        for sector, keywords in self.sector_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_sectors.append(sector)
        
        return list(set(found_sectors))
    
    def validate_ticker(self, ticker: str) -> bool:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return len(info) > 5 and 'symbol' in info
        except:
            return False