import streamlit as st
from py2neo import Graph, Node, Relationship
from typing import Dict, List

class FinancialKnowledgeGraph:
    def __init__(self):
        try:
            self.graph = Graph("neo4j://localhost:7687", auth=("neo4j", "admin123"))
            self.graph.run("MATCH () RETURN count(*) as count")
            st.success("Connected to Neo4j")
        except Exception as e:
            st.warning(f"Neo4j not available: {e}")
            self.graph = None
    
    def initialize_graph(self):
        if not self.graph:
            return
        
        try:
            constraints = [
                "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
                "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    self.graph.run(constraint)
                except:
                    pass
            
            st.success("Knowledge graph initialized")
        except Exception as e:
            st.error(f"Graph initialization error: {e}")
    
    def add_company(self, company_data: Dict):
        if not self.graph or not company_data:
            return
        
        try:
            ticker = company_data['ticker']
        
            def convert_value(value):
                if hasattr(value, 'item'):
                    return value.item()
                elif isinstance(value, (int, float, str, bool)) or value is None:
                    return value
                elif str(value).replace('.','').replace('-','').replace('%','').isdigit():
                    return float(str(value).replace('%',''))
                else:
                    return str(value)
            
            company_node = Node("Company",
                               ticker=ticker,
                               name=str(company_data.get('companyName', '')),
                               sector=str(company_data.get('sector', '')),
                               industry=str(company_data.get('industry', '')),
                               marketCap=convert_value(company_data.get('marketCap', 0)))
            
            self.graph.merge(company_node, "Company", "ticker")
            
            sector = company_data.get('sector', '')
            if sector:
                sector_node = Node("Sector", name=str(sector))
                self.graph.merge(sector_node, "Sector", "name")
                
                relationship = Relationship(company_node, "BELONGS_TO", sector_node)
                self.graph.merge(relationship)
            
            if 'price' in company_data:
                performance_node = Node("StockData",
                                       ticker=ticker,
                                       price=convert_value(company_data.get('price', 0)),
                                       change=convert_value(company_data.get('change', 0)),
                                       changePercent=str(company_data.get('changePercent', '0%')),
                                       volume=convert_value(company_data.get('volume', 0)),
                                       lastUpdated=str(company_data.get('lastUpdated', '')))
                
                self.graph.merge(performance_node, "StockData", "ticker")
                
                perf_relationship = Relationship(company_node, "HAS_PERFORMANCE", performance_node)
                self.graph.merge(perf_relationship)
                
            st.success(f"✅ Added {ticker} to knowledge graph")
                
        except Exception as e:
            st.warning(f"Error adding company {company_data.get('ticker', 'Unknown')}: {e}")
    
    def add_news_article(self, article: Dict, mentioned_tickers: List[str]):
        if not self.graph or not article:
            return
        
        try:
            article_id = f"article_{hash(article.get('title', ''))}"
            article_node = Node("NewsArticle",
                               id=article_id,
                               title=article.get('title', ''),
                               content=article.get('content', '')[:500],
                               source=article.get('source', ''),
                               publishedAt=article.get('publishedAt', ''),
                               url=article.get('url', ''))
            
            self.graph.merge(article_node, "NewsArticle", "id")
            
            for ticker in mentioned_tickers:
                company_match = self.graph.nodes.match("Company", ticker=ticker).first()
                if company_match:
                    mention_relationship = Relationship(article_node, "MENTIONS", company_match)
                    self.graph.merge(mention_relationship)
                    
        except Exception as e:
            st.warning(f"Error adding news article: {e}")
    
    def query_company_context(self, ticker: str) -> str:
        if not self.graph:
            return ""
        
        try:
            query = f"""
            MATCH (c:Company {{ticker: '{ticker}'}})
            OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Sector)
            OPTIONAL MATCH (c)-[:HAS_PERFORMANCE]->(p:StockData)
            RETURN c.name as company, s.name as sector, p.price as price, p.changePercent as change
            """
            
            result = self.graph.run(query).data()
            if result:
                info = result[0]
                return f"{info['company']} ({ticker}) operates in {info['sector']} sector, trading at ${info['price']} ({info['change']})"
            return ""
        except:
            return ""