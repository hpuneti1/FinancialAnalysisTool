import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import time
import re
import feedparser
import json
from typing import Optional
class FinancialDataCollector:
    def __init__(self):
        self.news_api_key = "d3e138fbb96d490ab6e203a441c32311"
        self.last_request_time = 0 
        self.min_request_interval = 1
        
        self.premium_rss_feeds = [
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
            "http://feeds.reuters.com/reuters/businessNews",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://www.marketwatch.com/rss/topstories",
            "https://finance.yahoo.com/news/rssindex",
            
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "https://www.cnbc.com/id/100727362/device/rss/rss.html",
            "https://www.cnbc.com/id/10000664/device/rss/rss.html",
            
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-k&output=atom",
        ]
         
        self.quality_keywords = [
            'earnings', 'revenue', 'profit', 'guidance', 'outlook', 'forecast',
            'acquisition', 'merger', 'ipo', 'stock', 'shares', 'market cap',
            'quarterly', 'annual', 'financial results', 'beat estimates',
            'analyst', 'rating', 'price target', 'upgrade', 'downgrade'
        ]
        
    def rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def get_stock_data(self, ticker: str) -> dict:
        """Enhanced stock data with more metrics"""
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
                    'lastUpdated': str(hist.index[-1]),
                    
                    'peRatio': info.get('trailingPE', 0),
                    'eps': info.get('trailingEps', 0),
                    'dividendYield': info.get('dividendYield', 0),
                    'beta': info.get('beta', 0),
                    'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
                    'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0)
                }
            return {}
        except Exception as e:
            st.warning(f"Could not fetch data for {ticker}: {e}")
            return {}
    
    def get_company_news_direct(self, ticker: str, company_name: str, days_back: int = 7) -> list[dict]:
        """Get news directly about a specific company"""
        articles = []
        
        search_terms = [ticker]
        if company_name:
            search_terms.append(company_name)
            if ' ' in company_name:
                search_terms.append(company_name.split()[0])
        
        if self.news_api_key:
            for term in search_terms[:2]:
                try:
                    self.rate_limit()
                    
                    url = "https://newsapi.org/v2/everything"
                    params = {
                        'q': f'"{term}" AND (stock OR shares OR earnings OR revenue)',
                        'language': 'en',
                        'sortBy': 'relevancy',
                        'pageSize': 10,
                        'apiKey': self.news_api_key,
                        'from': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        for article in data.get('articles', []):
                            if self._is_quality_financial_article(article, ticker, company_name):
                                articles.append({
                                    'title': article.get('title', ''),
                                    'description': article.get('description', ''),
                                    'content': article.get('content', '') or article.get('description', ''),
                                    'url': article.get('url', ''),
                                    'publishedAt': article.get('publishedAt', ''),
                                    'source': article.get('source', {}).get('name', 'News API'),
                                    'relevance_score': self._calculate_relevance_score(article, ticker, company_name)
                                })
                except Exception as e:
                    st.warning(f"News API error for {term}: {e}")
        
        return articles
    
    def get_sector_news(self, sector: str, days_back: int = 7) -> list[dict]:
        """Get sector-specific news"""
        articles = []
        
        sector_keywords = {
            'Technology': ['tech', 'software', 'AI', 'cloud', 'semiconductor'],
            'Healthcare': ['healthcare', 'pharmaceutical', 'biotech', 'medical'],
            'Financial': ['banking', 'fintech', 'insurance', 'financial services'],
            'Energy': ['oil', 'gas', 'renewable energy', 'solar', 'wind'],
            'Consumer': ['retail', 'consumer', 'e-commerce', 'shopping']
        }
        
        keywords = sector_keywords.get(sector, [sector.lower()])
        
        for feed_url in self.premium_rss_feeds[:5]:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    content = f"{title} {summary}"
                    
                    if any(keyword.lower() in content.lower() for keyword in keywords):
                        articles.append({
                            'title': title,
                            'description': summary,
                            'content': summary,
                            'url': getattr(entry, 'link', ''),
                            'publishedAt': getattr(entry, 'published', ''),
                            'source': getattr(feed.feed, 'title', 'RSS Feed'),
                            'relevance_score': self._calculate_sector_relevance(content, keywords)
                        })
            except Exception as e:
                continue
        
        articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return articles[:15]
    
    def search_news(self, query: str, days_back: int = 7, query_variants: Optional[list] = None, entity_extractor=None) -> list[dict]:
        """Enhanced news search with better targeting"""
        all_articles = []
        
        if entity_extractor:
            entities = entity_extractor.extract_entities(query)
            
            for company in entities.get('companies', []):
                if company.get('confidence', 0) > 0.7:
                    company_articles = self.get_company_news_direct(
                        company['ticker'], 
                        company['name'], 
                        days_back
                    )
                    all_articles.extend(company_articles)
            
            for sector in entities.get('sectors', []):
                if sector.get('confidence', 0) > 0.7:
                    sector_articles = self.get_sector_news(sector['sector'], days_back)
                    all_articles.extend(sector_articles)
        
        if len(all_articles) < 5:
            all_articles.extend(self._search_rss_feeds(query, days_back))
        
        unique_articles = self._deduplicate_articles(all_articles)
        return sorted(unique_articles, key=lambda x: x.get('relevance_score', 0), reverse=True)[:20]
    
    def _is_quality_financial_article(self, article: dict, ticker: str, company_name: str) -> bool:
        """Filter for high-quality financial articles"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"
        
        company_mentioned = (
            ticker.lower() in content or 
            (company_name and company_name.lower() in content)
        )
        
        has_financial_keywords = any(keyword in content for keyword in self.quality_keywords)
        
        source = article.get('source', {}).get('name', '').lower()
        excluded_sources = ['blog', 'reddit', 'yahoo answers', 'wikipedia']
        is_quality_source = not any(excluded in source for excluded in excluded_sources)
        
        return company_mentioned and has_financial_keywords and is_quality_source
    
    def _calculate_relevance_score(self, article: dict, ticker: str, company_name: str) -> float:
        """Calculate relevance score for articles"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"
        
        score = 0.0
        
        if ticker.lower() in title:
            score += 0.4
        elif ticker.lower() in content:
            score += 0.2
        
        if company_name and company_name.lower() in title:
            score += 0.3
        elif company_name and company_name.lower() in content:
            score += 0.1
        
        financial_keywords_count = sum(1 for keyword in self.quality_keywords if keyword in content)
        score += min(financial_keywords_count * 0.05, 0.3)
        
        source = article.get('source', {}).get('name', '').lower()
        if any(premium in source for premium in ['reuters', 'bloomberg', 'wsj', 'cnbc']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_sector_relevance(self, content: str, keywords: list[str]) -> float:
        """Calculate sector relevance score"""
        content_lower = content.lower()
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
        financial_matches = sum(1 for keyword in self.quality_keywords if keyword in content_lower)
        
        return min((keyword_matches * 0.3 + financial_matches * 0.1), 1.0)
    
    def _search_rss_feeds(self, query: str, days_back: int) -> list[dict]:
        """Search RSS feeds for query"""
        articles = []
        query_lower = query.lower()
        
        for feed_url in self.premium_rss_feeds[:3]:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    content = f"{title} {summary}".lower()
                    
                    if any(word in content for word in query_lower.split()):
                        articles.append({
                            'title': title,
                            'description': summary,
                            'content': summary,
                            'url': getattr(entry, 'link', ''),
                            'publishedAt': getattr(entry, 'published', ''),
                            'source': getattr(feed.feed, 'title', 'RSS Feed'),
                            'relevance_score': 0.5
                        })
            except:
                continue
        
        return articles
    
    def _deduplicate_articles(self, articles: list[dict]) -> list[dict]:
        """Remove duplicate articles by URL and title similarity"""
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', '').lower()
            
            if url and url in seen_urls:
                continue
            
            if any(title in seen_title or seen_title in title for seen_title in seen_titles):
                continue
            
            unique_articles.append(article)
            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)
        
        return unique_articles