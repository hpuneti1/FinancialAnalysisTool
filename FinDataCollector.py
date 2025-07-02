import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import time
import re
import feedparser
from typing import Optional

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
                    'lastUpdated': str(hist.index[-1])
                }
            return {}
        except Exception as e:
            st.warning(f"Could not fetch data for {ticker}: {e}")
            return {}
    
    def fetch_from_rss(self, query, feed_url):
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries:
            title = getattr(entry, 'title', '')
            summary = getattr(entry, 'summary', '')
            if query.lower() in title.lower() or query.lower() in summary.lower():
                articles.append({
                    'title': title,
                    'description': summary,
                    'content': summary,
                    'url': getattr(entry, 'link', ''),
                    'publishedAt': getattr(entry, 'published', ''),
                    'source': getattr(feed.feed, 'title', '')
                })
        return articles
    
    def fetch_all_from_rss(self, feed_url):
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries:
            title = getattr(entry, 'title', '')
            summary = getattr(entry, 'summary', '')
            articles.append({
                'title': title,
                'description': summary,
                'content': summary,
                'url': getattr(entry, 'link', ''),
                'publishedAt': getattr(entry, 'published', ''),
                'source': getattr(feed.feed, 'title', '')
            })
        return articles

    def search_news(self, query: str, days_back: int = 7, query_variants: Optional[list] = None, entity_extractor=None) -> list[dict]:
        self.rate_limit()
        articles = []

        # List of RSS feeds to search
        rss_feeds = [
            "https://finance.yahoo.com/news/rssindex",
            "http://feeds.reuters.com/reuters/businessNews",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://www.marketwatch.com/rss/topstories",
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ
            "https://www.ft.com/?format=rss",                # Financial Times
            "https://techcrunch.com/feed/",                  # TechCrunch
            "https://www.theverge.com/rss/index.xml",        # The Verge
            "https://www.bloomberg.com/feed/podcast/etf-report.xml", # Bloomberg ETF (example)
            # Add more as needed
        ]

        # If query_variants not provided, use the original query
        if query_variants is None:
            query_variants = [query]

        # Fetch all articles from all feeds
        all_articles = []
        for feed_url in rss_feeds:
            all_articles += self.fetch_all_from_rss(feed_url)

        # If entity_extractor is provided, filter articles for relevance
        if entity_extractor is not None:
            relevant_articles = []
            for article in all_articles:
                entities = entity_extractor.extract_entities(article['title'] + ' ' + article['content'])
                # Check if any query_variant matches a company name, ticker, or sector
                found = False
                for variant in query_variants:
                    if variant in [c['name'] for c in entities.get('companies', [])]:
                        found = True
                    if variant in entities.get('tickers_mentioned', []):
                        found = True
                    if variant in [s['sector'] for s in entities.get('sectors', [])]:
                        found = True
                if found:
                    relevant_articles.append(article)
            articles = relevant_articles
        else:
            articles = all_articles

        # Optionally, deduplicate by URL
        seen = set()
        unique_articles = []
        for article in articles:
            if article['url'] not in seen:
                unique_articles.append(article)
                seen.add(article['url'])

        return unique_articles[:50]