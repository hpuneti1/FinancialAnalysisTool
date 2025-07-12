import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import time
import re
import feedparser
import json
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
#This class gathers financial data using a NEWS api key and also rss feeds.
class FinancialDataCollector:
    def __init__(self):
        self.news_api_key = None
        if "NEWS_API_KEY" in os.environ:
            self.news_api_key = os.environ["NEWS_API_KEY"]
        else:
            try:
                if hasattr(st, 'secrets') and "NEWS_API_KEY" in st.secrets:
                    self.news_api_key = st.secrets["NEWS_API_KEY"]
            except Exception:
                pass
            
            if not self.news_api_key:
                self.news_api_key = "d3e138fbb96d490ab6e203a441c32311"
        self.last_request_time = 0 
        self.min_request_interval = 1
        
        self.premium_rss_feeds = [
            # Wall Street Journal & Dow Jones
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
            "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
            
            # Reuters
            "http://feeds.reuters.com/reuters/businessNews",
            "http://feeds.reuters.com/reuters/companyNews",
            "http://feeds.reuters.com/reuters/technologyNews",
            
            # CNBC
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://www.cnbc.com/id/100727362/device/rss/rss.html",
            "https://www.cnbc.com/id/10000664/device/rss/rss.html",
            "https://www.cnbc.com/id/19854910/device/rss/rss.html",
            
            # Yahoo Finance
            "https://www.marketwatch.com/rss/topstories",
            "https://finance.yahoo.com/news/rssindex",
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            
            # Additional Financial Sources
            "https://www.investing.com/rss/news.rss",
            "https://www.thestreet.com/feeds/stocks.xml",
            "https://seekingalpha.com/feed.xml",
            "https://www.fool.com/feeds/index.aspx",
            "https://finance.yahoo.com/rss/headline?s=^GSPC",
            
            # Sector-specific feeds
            "https://www.cnbc.com/id/19746125/device/rss/rss.html",
            "https://www.cnbc.com/id/10000108/device/rss/rss.html", 
            
            # SEC filings
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
    #Retrieves stock data from yahoo
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
    
    def get_company_news_direct(self, ticker: str, company_name: str, days_back: int = 7, entity_extractor=None) -> list[dict]:
        articles = []
        
        if entity_extractor:
            try:
                search_terms = entity_extractor.generate_search_terms(company_name, ticker)
                if not isinstance(search_terms, list):
                    search_terms = []
                search_terms = [str(term).strip() for term in search_terms if term is not None and str(term).strip()]
            except Exception as e:
                print(f"Error generating search terms: {e}")
                search_terms = []
        else:
            search_terms = []
            
        if not search_terms:
            if ticker:
                search_terms.append(str(ticker))
            if company_name:
                search_terms.append(str(company_name))
                if ' ' in str(company_name):
                    search_terms.append(str(company_name).split()[0])
        
        if not search_terms:
            search_terms = ["stock news"]
        
        if self.news_api_key:
            for term in search_terms[:3]:
                try:
                    self.rate_limit()
                    
                    url = "https://newsapi.org/v2/everything"
                    params = {
                        'q': f'"{term}" AND (stock OR shares OR earnings OR revenue)',
                        'language': 'en',
                        'sortBy': 'relevancy',
                        'pageSize': 8,
                        'apiKey': self.news_api_key,
                        'from': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        for article in data.get('articles', []):
                            if self._is_quality_financial_article(article, ticker, company_name):
                                articles.append({
                                    'title': str(article.get('title', '') or ''),
                                    'description': str(article.get('description', '') or ''),
                                    'content': str(article.get('content', '') or article.get('description', '') or ''),
                                    'url': str(article.get('url', '') or ''),
                                    'publishedAt': str(article.get('publishedAt', '') or ''),
                                    'source': str(article.get('source', {}).get('name', 'News API') or 'News API'),
                                    'relevance_score': self._calculate_relevance_score(article, ticker, company_name)
                                })
                except Exception as e:
                    print(f"News API error for {term}: {e}")
                    continue
        
        return articles
    
    def get_sector_news(self, sector: str, days_back: int = 7) -> list[dict]:
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
                    title = str(getattr(entry, 'title', '') or '')
                    summary = str(getattr(entry, 'summary', '') or '')
                    content = f"{title} {summary}"
                    
                    if any(keyword.lower() in content.lower() for keyword in keywords):
                        articles.append({
                            'title': title,
                            'description': summary,
                            'content': summary,
                            'url': str(getattr(entry, 'link', '') or ''),
                            'publishedAt': str(getattr(entry, 'published', '') or ''),
                            'source': str(getattr(feed.feed, 'title', 'RSS Feed') or 'RSS Feed'),
                            'relevance_score': self._calculate_sector_relevance(content, keywords)
                        })
            except Exception as e:
                continue
        
        articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return articles[:15]
    #Finding relevant articles
    def search_news(self, query: str, days_back: int = 7, query_variants: Optional[list] = None, entity_extractor=None) -> list[dict]:
        all_articles = []
        
        if entity_extractor:
            entities = entity_extractor.extract_entities(query)
            
            for company in entities.get('companies', []):
                if company.get('confidence', 0) > 0.7:
                    company_articles = self.get_company_news_direct(
                        company['ticker'], 
                        company['name'], 
                        days_back,
                        entity_extractor=entity_extractor
                    )
                    all_articles.extend(company_articles)
                    
                    if len(company_articles) < 3:
                        company_sector = "Technology"
                        try:
                            import yfinance as yf
                            stock = yf.Ticker(company.get('ticker', ''))
                            company_sector = stock.info.get('sector', 'Technology')
                        except:
                            pass
                        
                        sector_fallback = self.get_sector_news(company_sector, days_back)
                        all_articles.extend(sector_fallback)
            
            for sector in entities.get('sectors', []):
                if sector.get('confidence', 0) > 0.7:
                    sector_articles = self.get_sector_news(sector['sector'], days_back)
                    all_articles.extend(sector_articles)
        
        if len(all_articles) < 5:
            all_articles.extend(self._search_rss_feeds(query, days_back))
        
        unique_articles = self._deduplicate_articles(all_articles)
        return sorted(unique_articles, key=lambda x: x.get('relevance_score', 0), reverse=True)[:20]
    
    def _is_quality_financial_article(self, article: dict, ticker: str, company_name: str) -> bool:
        title = str(article.get('title', '') or '').lower()
        description = str(article.get('description', '') or '').lower()
        content = f"{title} {description}"
        
        company_mentioned = (
            str(ticker).lower() in content or 
            (company_name and str(company_name).lower() in content)
        )
        
        has_financial_keywords = any(keyword in content for keyword in self.quality_keywords)
        
        source = str(article.get('source', {}).get('name', '') or '').lower()
        excluded_sources = ['blog', 'reddit', 'yahoo answers', 'wikipedia']
        is_quality_source = not any(excluded in source for excluded in excluded_sources)
        
        return company_mentioned and has_financial_keywords and is_quality_source
    
    def _calculate_relevance_score(self, article: dict, ticker: str, company_name: str) -> float:
        title = str(article.get('title', '') or '').lower()
        description = str(article.get('description', '') or '').lower()
        content = f"{title} {description}"
        
        score = 0.0
        
        if str(ticker).lower() in title:
            score += 0.4
        elif str(ticker).lower() in content:
            score += 0.2
        
        if company_name and str(company_name).lower() in title:
            score += 0.3
        elif company_name and str(company_name).lower() in content:
            score += 0.1
        
        financial_keywords_count = sum(1 for keyword in self.quality_keywords if keyword in content)
        score += min(financial_keywords_count * 0.05, 0.3)
        
        source = str(article.get('source', {}).get('name', '') or '').lower()
        if any(premium in source for premium in ['reuters', 'bloomberg', 'wsj', 'cnbc']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_sector_relevance(self, content: str, keywords: list[str]) -> float:
        content_lower = content.lower()
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
        financial_matches = sum(1 for keyword in self.quality_keywords if keyword in content_lower)
        
        return min((keyword_matches * 0.3 + financial_matches * 0.1), 1.0)
    
    def _search_rss_feeds(self, query: str, days_back: int) -> list[dict]:
        articles = []
        query_lower = query.lower()
        
        for feed_url in self.premium_rss_feeds[:3]:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    title = str(getattr(entry, 'title', '') or '')
                    summary = str(getattr(entry, 'summary', '') or '')
                    content = f"{title} {summary}".lower()
                    
                    if any(word in content for word in query_lower.split()):
                        articles.append({
                            'title': title,
                            'description': summary,
                            'content': summary,
                            'url': str(getattr(entry, 'link', '') or ''),
                            'publishedAt': str(getattr(entry, 'published', '') or ''),
                            'source': str(getattr(feed.feed, 'title', 'RSS Feed') or 'RSS Feed'),
                            'relevance_score': 0.5
                        })
            except:
                continue
        
        return articles
    
    def _deduplicate_articles(self, articles: list[dict]) -> list[dict]:
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            url = str(article.get('url', '') or '')
            title = str(article.get('title', '') or '').lower()
            
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