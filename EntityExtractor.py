import re
import yfinance as yf
import json
from openai import OpenAI

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
            
        # Add stock group mappings
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
                {"sector": "Technology", "query_type": "broad_sector", "confidence": 0.95}
            ]
        }

        Rules:
        1. Only include companies/entities actually mentioned in the text
        2. For company names, provide the most likely ticker symbol
        3. Include confidence scores (0-1) based on how certain you are
        4. Recognize common stock groups: FAANG, Magnificent 7, Big Tech, semiconductor stocks, bank stocks, etc.
        5. Map sectors to: Technology, Healthcare, Financial, Energy, Consumer Discretionary, Consumer Staples, Industrials, Materials, Communication Services, Utilities, Real Estate
        6. Handle variations: "Apple" = AAPL, "Microsoft Corp" = MSFT, "Alphabet" = GOOGL
        7. If text mentions stock groups, expand them to individual tickers
        8. For broad sector queries like "technology sector trends" or "banking stocks", add to sector_queries
        9. Return empty arrays if no entities found
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
        
    
    def extract_tickers(self, text: str) -> list[str]:
            entities = self.extract_entities(text)
            all_tickers = []
            
            # Get tickers from companies
            for company in entities.get('companies', []):
                if company.get('confidence', 0) > 0.5:
                    all_tickers.append(company['ticker'])
                    
            # Get tickers from stock groups
            for group in entities.get('stock_groups', []):
                if group.get('confidence', 0) > 0.5:
                    all_tickers.extend(group['companies']) 
            
            all_tickers.extend(entities.get('tickers_mentioned', []))
            
            for sector_query in entities.get('sector_queries', []):
                if sector_query.get('confidence', 0) > 0.6:
                    sector_name = sector_query['sector']
                    # Map sector to representative tickers
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
        
    def get_sector_tickers(self, sector_name: str) -> list[str]:
        """Get representative tickers for a sector"""
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

    def extract_sectors(self, text: str) -> list[str]:
        entities = self.extract_entities(text)
        sectors = []
        for sector_data in entities.get('sectors', []):
            if sector_data.get('confidence', 0) > 0.5:
                sectors.append(sector_data['sector'])
                
        return list(set(sectors))
    
    def get_extraction_details(self, text: str) -> dict:
        return self.extract_entities(text)
    
    def _is_valid_ticker_format(self, ticker: str) -> bool:
        if not ticker or len(ticker) < 1 or len(ticker) > 6:
            return False
        
        if not re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', ticker):
            return False
        
        false_positives = {'AI', 'IT', 'US', 'EU', 'CEO', 'CFO', 'IPO', 'ETF', 'SEC', 'FDA'}
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