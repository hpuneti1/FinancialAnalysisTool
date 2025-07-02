import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import time
import re

class FinancialDataCollector:
    def __init__(self):
        self.news_api_key = "d3e138fbb96d490ab6e203a441c32311"
        self.last_request_time = 0
        self.min_request_interval = 1
        
    def rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def get_stock_data(self, ticker: str) -> dict:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            info = stock.info
            
            if not hist.empty:
                latest = hist.iloc[-1]
                previous = hist.iloc[-2] if len(hist) > 1 else latest
                
                current_price = latest['Close']
                previous_close = previous['Close']
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
                
                return {
                    'ticker': ticker,
                    'price': round(current_price, 2),
                    'change': round(change, 2),
                    'changePercent': f"{change_percent:.2f}%",
                    'volume': int(latest['Volume']) if latest['Volume'] else 0,
                    'marketCap': info.get('marketCap', 0),
                    'companyName': info.get('longName', ''),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'lastUpdated': str(hist.index[-1].date())
                }
            return {}
        except Exception as e:
            st.warning(f"Could not fetch data for {ticker}: {e}")
            return {}
    
    def search_news(self, query: str, days_back: int = 7) -> list[dict]:
        self.rate_limit()
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        url = "https://newsapi.org/v2/everything"
        
        params = {
            'q': query,
            'from': from_date,
            'apikey': self.news_api_key,
            'language': 'en',
            'sortBy': 'relevancy',
            'pageSize': 30, 
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            query_words = query.lower().split()
            
            meaningful_words = [word for word in query_words 
                            if len(word) > 2 and word not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'how', 'what', 'when', 'where']]
            
            for article in data.get('articles', []):
                title = article.get('title', '')
                description = article.get('description', '')
                content = article.get('content', '')
                
                title_lower = title.lower()
                description_lower = description.lower()
                content_lower = content.lower()
                full_text = f"{title_lower} {description_lower} {content_lower}"
                
                if len(full_text.strip()) < 100:
                    continue

                relevance_score = 0
                
                for word in meaningful_words:
                    if word in title_lower:
                        relevance_score += 3
                    elif word in description_lower:
                        relevance_score += 2
                    elif word in content_lower:
                        relevance_score += 1
            
                ticker_pattern = r'\b[A-Z]{2,5}\b'
                query_tickers = re.findall(ticker_pattern, query)
                for ticker in query_tickers:
                    if ticker in full_text.upper():
                        relevance_score += 4
                
                financial_keywords = ['stock', 'share', 'earnings', 'revenue', 'market', 'investment', 'company', 'financial', 'trading', 'price', 'analyst', 'forecast']
                has_financial = any(keyword in full_text for keyword in financial_keywords)
                
                context_keywords = ['quarterly', 'annual', 'guidance', 'outlook', 'performance', 'results', 'beat', 'miss', 'estimates']
                context_bonus = sum(1 for keyword in context_keywords if keyword in full_text)
                relevance_score += context_bonus
                
                if relevance_score >= 2 and has_financial:
                    articles.append({
                        'title': title,
                        'description': description,
                        'content': content,
                        'url': article.get('url'),
                        'publishedAt': article.get('publishedAt'),
                        'source': article.get('source', {}).get('name'),
                        'relevance_score': relevance_score
                    })
            
            articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            print(f"Query: '{query}' -> Found {len(articles)} relevant articles")
            if articles:
                top_scores = [article.get('relevance_score', 0) for article in articles[:3]]
                print(f"Top relevance scores: {top_scores}")
            
            return articles[:15] 
            
        except Exception as e:
            st.warning(f"News API unavailable: {e}")
            return []