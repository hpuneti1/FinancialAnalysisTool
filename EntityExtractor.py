import re
import yfinance as yf
import json
from openai import OpenAI

class EntityExtractor:
    def __init__(self, open_api_key: str):
        self.openai_client = OpenAI(api_key=open_api_key)
        self.extraction_cache = {}
    
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
            "tickers_mentioned": ["AAPL", "MSFT", "GOOGL"]
        }

        Rules:
        1. Only include companies/entities actually mentioned in the text
        2. For company names, provide the most likely ticker symbol
        3. Include confidence scores (0-1) based on how certain you are
        4. Recognize common stock groups: FAANG, Magnificent 7, Big Tech, semiconductor stocks, bank stocks, etc.
        5. Map sectors to: Technology, Healthcare, Financial, Energy, Consumer Discretionary, Consumer Staples, Industrials, Materials, Communication Services, Utilities, Real Estate
        6. Handle variations: "Apple" = AAPL, "Microsoft Corp" = MSFT, "Alphabet" = GOOGL
        7. If text mentions stock groups, expand them to individual tickers
        8. Return empty arrays if no entities found
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
        for company in entities.get('companies', []):
            if company.get('confidence', 0) > 0.5:
                all_tickers.append(company['ticker'])
                
        for group in entities.get('stock_groups', []):
            if group.get('confidence', 0) > 0.5:
                all_tickers.extend(group['companies']) 
        
        all_tickers.extend(entities.get('tickers_mentioned', []))
        
        unique_tickers = list(set(all_tickers))
        validated_tickers = []
        
        for ticker in unique_tickers:
            if self._is_valid_ticker_format(ticker):
                validated_tickers.append(ticker) 
        return validated_tickers
          
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