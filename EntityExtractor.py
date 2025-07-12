import re
import yfinance as yf
import json
from openai import OpenAI

#This classes extracts entities from the user query
class EntityExtractor:
    def __init__(self, open_api_key: str):
        self.openai_client = OpenAI(api_key=open_api_key)
        self.extraction_cache = {}
        self.sector_tickers = {
                'Technology': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'CRM', 'ORCL', 'ADBE'],
                'Banking': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'COF'],
                'Financial': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BRK-B', 'V', 'MA', 'AXP'],
                'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'DHR', 'BMY', 'ABBV', 'MRK', 'LLY'],
                'Energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'OXY', 'KMI'],
                'Consumer Discretionary': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TJX', 'LOW', 'TGT', 'F'],
                'Consumer Staples': ['PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'KHC', 'GIS', 'K', 'HSY'],
                'Industrials': ['BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'UNP'],
                'Materials': ['LIN', 'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'DOW', 'DD', 'PPG', 'IFF'],
                'Communication Services': ['GOOGL', 'META', 'DIS', 'VZ', 'T', 'NFLX', 'CMCSA', 'TMUS', 'CHTR', 'DISH'],
                'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'XEL', 'SRE', 'PEG', 'ED'],
                'Real Estate': ['AMT', 'PLD', 'CCI', 'EQIX', 'SPG', 'O', 'WELL', 'DLR', 'PSA', 'EQR']
            }
            
        self.stock_groups = {
            'FAANG': ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL'],
            'Magnificent 7': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'],
            'Big Tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'CRM', 'ORCL'],
            'Semiconductor': ['NVDA', 'AMD', 'INTC', 'TSM', 'AVGO', 'QCOM', 'TXN', 'AMAT', 'LRCX', 'KLAC'],
            'Banking': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'COF'],
            'REIT': ['AMT', 'PLD', 'CCI', 'EQIX', 'SPG', 'O', 'WELL', 'DLR', 'PSA', 'EQR'],
            'EV': ['TSLA', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'F', 'GM'],
            'Biotech': ['GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'ILMN', 'MRNA', 'BNTX']
            }
    #Using GPT to handle the extraction of entities
    def extract_entities(self, text: str) -> dict:
        if text in self.extraction_cache:
            return self.extraction_cache[text]
        
        prompt = """
        You are a financial entity extraction expert. Extract all mentioned companies, stock groups, and sectors from the given text.

        Return a JSON object with this exact structure:
        {
            "companies": [
                {"name": "Apple Inc", "ticker": "AAPL", "confidence": 0.95},
                {"name": "Microsoft", "ticker": "MSFT", "confidence": 0.90}
            ],
            "stock_groups": [
                {"group": "FAANG", "companies": ["META", "AAPL", "AMZN", "NFLX", "GOOGL"], "confidence": 0.85}
            ],
            "sectors": [
                {"sector": "Technology", "confidence": 0.90},
                {"sector": "Healthcare", "confidence": 0.75}
            ],
            "tickers_mentioned": ["AAPL", "MSFT", "GOOGL"],
            "sector_queries": [
                {"sector": "Banking", "query_type": "broad_sector", "confidence": 0.95}
            ]
        }

        Rules:
        1. Only include companies/entities actually mentioned in the text
        2. For company names, provide the most likely ticker symbol
        3. Include confidence scores (0-1) based on how certain you are
        4. Recognize common stock groups: FAANG, Magnificent 7, Big Tech, semiconductor stocks, bank stocks, banking stocks, etc.
        5. Map sectors to: Technology, Healthcare, Financial, Banking, Energy, Consumer Discretionary, Consumer Staples, Industrials, Materials, Communication Services, Utilities, Real Estate
        6. Handle variations: "Apple" = AAPL, "Microsoft Corp" = MSFT, "Alphabet" = GOOGL
        7. If text mentions stock groups, expand them to individual tickers
        8. For broad sector queries like "technology sector trends", "banking stocks", "bank stocks", or "how are X stocks doing", add to sector_queries with high confidence
        9. Return empty arrays if no entities found
        10. Handle company names: "C3.ai" → company="C3.ai Inc", ticker="C3.AI"
        11. AI companies should be mapped to Technology sector
        12. Don't filter out valid ticker symbols and handle tickers with dots and numbers
        13. IMPORTANT: For queries like "banking stocks", "bank stocks", "how are banking stocks doing", always add {"sector": "Banking", "query_type": "broad_sector", "confidence": 0.95} to sector_queries
        14. IMPORTANT: "banking stocks" should map to Banking sector, not Financial sector
        """
        
        user_prompt = f"Extract the financial entities contained in this text: {text}"
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            if not isinstance(content, str):
                content = ""
            entities = json.loads(content)
            
            self.extraction_cache[text] = entities
            
            return entities
            
        except Exception as e:
            print(f"LLM entity extraction failed: {e}")
            return {}
        
    #Extracting tickers for ticker information
    def extract_tickers(self, text: str) -> list[str]:
            entities = self.extract_entities(text)
            all_tickers = []
            
            for company in entities.get('companies', []):
                if company.get('confidence', 0) > 0.5:
                    all_tickers.append(company['ticker'])
                    
            for group in entities.get('stock_groups', []):
                if group.get('confidence', 0) > 0.5:
                    all_tickers.extend(group['companies']) 
            
            all_tickers.extend(entities.get('tickers_mentioned', []))
            
            for sector_query in entities.get('sector_queries', []):
                if sector_query.get('confidence', 0) > 0.5:
                    sector_name = sector_query['sector']
                    sector_tickers = self.get_sector_tickers(sector_name)
                    all_tickers.extend(sector_tickers)
            
            for sector_data in entities.get('sectors', []):
                if sector_data.get('confidence', 0) > 0.7:
                    sector_name = sector_data['sector']
                    sector_tickers = self.get_sector_tickers(sector_name)
                    all_tickers.extend(sector_tickers)
            
            unique_tickers = list(set(all_tickers))
            validated_tickers = []
            
            for ticker in unique_tickers:
                if self._is_valid_ticker_format(ticker):
                    validated_tickers.append(ticker) 
            return validated_tickers

    #Getting sector tickers    
    def get_sector_tickers(self, sector_name: str) -> list[str]:
        if sector_name in self.sector_tickers:
            return self.sector_tickers[sector_name][:5]
            
        sector_variations = {
            'tech': 'Technology',
            'technology': 'Technology',
            'bank': 'Banking',
            'banking': 'Banking',
            'finance': 'Financial',
            'financial': 'Financial',
            'healthcare': 'Healthcare',
            'pharma': 'Healthcare',
            'energy': 'Energy',
            'oil': 'Energy',
            'consumer': 'Consumer Discretionary',
            'retail': 'Consumer Discretionary'
        }
        
        normalized_sector = sector_variations.get(sector_name.lower(), sector_name)
        
        if normalized_sector in self.sector_tickers:
            return self.sector_tickers[normalized_sector][:5]
        
        return []

    #Extract sectors from entities
    def extract_sectors(self, text: str) -> list[str]:
        entities = self.extract_entities(text)
        sectors = []
        for sector_data in entities.get('sectors', []):
            if sector_data.get('confidence', 0) > 0.5:
                sectors.append(sector_data['sector'])
                
        return list(set(sectors))
    
    def get_extraction_details(self, text: str) -> dict:
        return self.extract_entities(text)
    #Create search terms that have relevance to a company to aid in search
    def generate_search_terms(self, company_name: str, ticker: str, sector: str = "") -> list[str]:
        company_name = str(company_name) if company_name is not None else ""
        ticker = str(ticker) if ticker is not None else ""
        sector = str(sector) if sector is not None else ""
        
        prompt = f"""
        Generate 5-7 diverse search terms for finding financial news about this company:
        Company: {company_name}
        Ticker: {ticker}
        Sector: {sector}
        
        Include:
        1. Company name variations (full name, short name, common abbreviations)
        2. Stock-related terms combining ticker/company with financial keywords
        3. Business description terms (what the company is known for)
        4. Industry-specific terms
        
        Return only the search terms as a JSON array:
        ["term1", "term2", "term3", ...]
        
        Example for Apple Inc (AAPL):
        ["Apple Inc", "AAPL stock", "iPhone maker", "Apple earnings", "Tim Cook Apple", "Apple technology", "Apple revenue"]
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial search expert. Generate precise search terms."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            if not isinstance(content, str):
                return [company_name, ticker] if company_name and ticker else ["stock news"]
            
            search_terms = json.loads(content)
            if isinstance(search_terms, list):
                filtered_terms = [str(term).strip() for term in search_terms if term is not None and str(term).strip()]
                return filtered_terms if filtered_terms else ([company_name, ticker] if company_name and ticker else ["stock news"])
            else:
                return [company_name, ticker] if company_name and ticker else ["stock news"]
            
        except Exception as e:
            basic_terms = []
            if company_name:
                basic_terms.extend([company_name, f"{company_name} earnings"])
            if ticker:
                basic_terms.extend([ticker, f"{ticker} stock"])
            if sector and company_name:
                basic_terms.append(f"{sector} {company_name}")
            return basic_terms if basic_terms else ["stock news"]
    
    def _is_valid_ticker_format(self, ticker: str) -> bool:
        if not ticker or len(ticker) < 1 or len(ticker) > 8:  # Extended length for tickers like "C3.AI"
            return False
        
        if not re.match(r'^[A-Z0-9]{1,6}(\.[A-Z0-9]{1,4})?$', ticker):
            return False
        
        valid_tickers = {'AI', 'IT', 'ON', 'UP', 'TV', 'GM', 'GE', 'HP', 'AT', 'GO', 'C3.AI'}
        if ticker in valid_tickers:
            return True
        
        false_positives = {'US', 'EU', 'CEO', 'CFO', 'IPO', 'ETF', 'SEC', 'FDA', 'LLC', 'INC', 'LTD'}
        return ticker not in false_positives
    
    def validate_ticker(self, ticker: str) -> bool:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return len(info) > 5 and ('symbol' in info or 'shortName' in info)
        except:
            return False
        
    def clear_cache(self):
        self.extraction_cache = {}
        
    def get_cache_stats(self) -> dict:
        return {
            "cached_extractions": len(self.extraction_cache),
            "cache_keys": list(self.extraction_cache.keys())[:5]
        }