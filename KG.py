import streamlit as st
import os
from py2neo import Graph, Node, Relationship

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class FinancialKnowledgeGraph:
    def __init__(self):
        try:
            # Get Neo4j connection details from environment variables or Streamlit secrets
            neo4j_uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
            neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
            neo4j_password = os.environ.get("NEO4J_PASSWORD", "admin123")
            
            try:
                if hasattr(st, 'secrets'):
                    neo4j_uri = st.secrets.get("NEO4J_URI", neo4j_uri)
                    neo4j_user = st.secrets.get("NEO4J_USER", neo4j_user)
                    neo4j_password = st.secrets.get("NEO4J_PASSWORD", neo4j_password)
            except Exception:
                pass  # Ignore secrets parsing errors
            
            self.graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
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
    
    def add_company(self, company_data: dict):
        if not company_data:
            return
            
        if not self.graph:
            st.warning(f"❌ Neo4j not connected - cannot add {company_data.get('ticker', 'Unknown')} to knowledge graph")
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
            
                
        except Exception as e:
            st.warning(f"Error adding company {company_data.get('ticker', 'Unknown')}: {e}")
    
    def add_news_article(self, article: dict, mentioned_tickers: list[str]):
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
    
    def get_graph_stats(self) -> dict:
        """Get knowledge graph statistics with detailed debugging"""
        if not self.graph:
            return {"companies": 0, "sectors": 0, "articles": 0, "status": "Neo4j not connected"}
        
        try:
            # Get total company count
            companies = self.graph.run("MATCH (c:Company) RETURN count(c) as count").data()
            
            # Get unique companies by ticker
            unique_companies = self.graph.run(
                "MATCH (c:Company) RETURN count(DISTINCT c.ticker) as count"
            ).data()
            
            # Get companies with missing data
            incomplete_companies = self.graph.run(
                "MATCH (c:Company) WHERE c.name IS NULL OR c.name = '' RETURN count(c) as count"
            ).data()
            
            # Get duplicate tickers
            duplicates = self.graph.run(
                "MATCH (c:Company) WITH c.ticker as ticker, count(c) as cnt WHERE cnt > 1 RETURN count(ticker) as count"
            ).data()
            
            sectors = self.graph.run("MATCH (s:Sector) RETURN count(s) as count").data()
            articles = self.graph.run("MATCH (a:NewsArticle) RETURN count(a) as count").data()
            
            return {
                "companies": companies[0]['count'] if companies else 0,
                "unique_companies": unique_companies[0]['count'] if unique_companies else 0,
                "incomplete_companies": incomplete_companies[0]['count'] if incomplete_companies else 0,
                "duplicate_tickers": duplicates[0]['count'] if duplicates else 0,
                "sectors": sectors[0]['count'] if sectors else 0,
                "articles": articles[0]['count'] if articles else 0,
                "status": "Connected"
            }
        except Exception as e:
            return {"companies": 0, "sectors": 0, "articles": 0, "status": f"Error: {e}"}
    
    def cleanup_graph(self) -> dict:
        """Clean up duplicate and incomplete entries in the knowledge graph"""
        if not self.graph:
            return {"removed": 0, "error": "Neo4j not connected"}
        
        try:
            removed_count = 0
            
            # Remove companies with missing/empty names
            result = self.graph.run("""
                MATCH (c:Company) 
                WHERE c.name IS NULL OR c.name = ''
                DETACH DELETE c
                RETURN count(c) as removed
            """)
            incomplete_removed = result.data()[0]['removed'] if result.data() else 0
            removed_count += incomplete_removed
            
            # Remove duplicate companies (keep the most recent one)
            result = self.graph.run("""
                MATCH (c:Company)
                WITH c.ticker as ticker, collect(c) as companies
                WHERE size(companies) > 1
                UNWIND companies[1..] as duplicateCompany
                DETACH DELETE duplicateCompany
                RETURN count(duplicateCompany) as removed
            """)
            duplicate_removed = result.data()[0]['removed'] if result.data() else 0
            removed_count += duplicate_removed
            
            # Remove orphaned StockData nodes
            result = self.graph.run("""
                MATCH (s:StockData)
                WHERE NOT (s)<-[:HAS_PERFORMANCE]-()
                DELETE s
                RETURN count(s) as removed
            """)
            orphan_removed = result.data()[0]['removed'] if result.data() else 0
            removed_count += orphan_removed
            
            return {
                "removed": removed_count,
                "incomplete_removed": incomplete_removed,
                "duplicate_removed": duplicate_removed,
                "orphan_removed": orphan_removed,
                "status": "Success"
            }
            
        except Exception as e:
            return {"removed": 0, "error": str(e)}
    
    def list_all_companies(self) -> list:
        """List all companies in the knowledge graph"""
        if not self.graph:
            return []
        
        try:
            result = self.graph.run("""
                MATCH (c:Company)
                OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Sector)
                RETURN c.ticker as ticker, c.name as name, s.name as sector
                ORDER BY c.ticker
            """)
            
            companies = []
            for record in result.data():
                companies.append({
                    'ticker': record['ticker'],
                    'name': record['name'] or 'N/A',
                    'sector': record['sector'] or 'N/A'
                })
            
            return companies
            
        except Exception as e:
            return []