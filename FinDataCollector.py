import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List
import time

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
    
    def get_stock_data(self, ticker: str) -> Dict:
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
    
    def search_news(self, query: str, days_back: int = 7) -> List[Dict]:
        """Search for relevant financial news"""
        self.rate_limit()
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        url = "https://newsapi.org/v2/everything"
        
        params = {
            'q': query,
            'from': from_date,
            'apikey': self.news_api_key,
            'language': 'en',
            'sortBy': 'relevancy',
            'pageSize': 20,
            'domains': 'reuters.com,bloomberg.com,cnbc.com,marketwatch.com,yahoo.com,wsj.com,barrons.com'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                title = article.get('title', '')
                description = article.get('description', '')
                content = article.get('content', '')
                
                full_text = f"{title} {description} {content}".lower()
                
                if len(full_text.strip()) > 100:
                    financial_keywords = ['stock', 'share', 'earnings', 'revenue', 'market', 'investment', 'company']
                    if any(keyword in full_text for keyword in financial_keywords):
                        articles.append({
                            'title': title,
                            'description': description,
                            'content': content,
                            'url': article.get('url'),
                            'publishedAt': article.get('publishedAt'),
                            'source': article.get('source', {}).get('name')
                        })
            
            return articles
        except Exception as e:
            st.warning(f"News API unavailable: {e}")
            return []