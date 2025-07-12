import streamlit as st
import os
from neo4j import GraphDatabase

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
#This class deals with the neo4j graph
class FinancialKnowledgeGraph:
    def __init__(self):
        try:
            neo4j_uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
            neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
            neo4j_password = os.environ.get("NEO4J_PASSWORD", "admin123")
            
            try:
                if hasattr(st, 'secrets'):
                    neo4j_uri = st.secrets.get("NEO4J_URI", neo4j_uri)
                    neo4j_user = st.secrets.get("NEO4J_USER", neo4j_user)
                    neo4j_password = st.secrets.get("NEO4J_PASSWORD", neo4j_password)
            except Exception:
                pass
            
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with self.driver.session() as session:
                session.run("MATCH () RETURN count(*) as count")
            st.success("Connected to Neo4j")
        except Exception as e:
            st.warning(f"Neo4j not available: {e}")
            self.driver = None
    #Intialization of the graph
    def initialize_graph(self):
        if not self.driver:
            return
        
        try:
            constraints = [
                "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
                "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE"
            ]
            
            with self.driver.session() as session:
                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except:
                        pass
            
            st.success("Knowledge graph initialized")
        except Exception as e:
            st.error(f"Graph initialization error: {e}")
    #Add a company node to the graph
    def add_company(self, company_data: dict):
        if not company_data:
            return
            
        if not self.driver:
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
            
            with self.driver.session() as session:
                session.run("""
                    MERGE (c:Company {ticker: $ticker})
                    SET c.name = $name,
                        c.sector = $sector,
                        c.industry = $industry,
                        c.marketCap = $marketCap
                """, {
                    'ticker': ticker,
                    'name': str(company_data.get('companyName', '')),
                    'sector': str(company_data.get('sector', '')),
                    'industry': str(company_data.get('industry', '')),
                    'marketCap': convert_value(company_data.get('marketCap', 0))
                })
                
                sector = company_data.get('sector', '')
                if sector:
                    session.run("""
                        MERGE (s:Sector {name: $sector})
                        WITH s
                        MATCH (c:Company {ticker: $ticker})
                        MERGE (c)-[:BELONGS_TO]->(s)
                    """, {'sector': str(sector), 'ticker': ticker})
                
                if 'price' in company_data:
                    session.run("""
                        MERGE (sd:StockData {ticker: $ticker})
                        SET sd.price = $price,
                            sd.change = $change,
                            sd.changePercent = $changePercent,
                            sd.volume = $volume,
                            sd.lastUpdated = $lastUpdated
                        WITH sd
                        MATCH (c:Company {ticker: $ticker})
                        MERGE (c)-[:HAS_PERFORMANCE]->(sd)
                    """, {
                        'ticker': ticker,
                        'price': convert_value(company_data.get('price', 0)),
                        'change': convert_value(company_data.get('change', 0)),
                        'changePercent': str(company_data.get('changePercent', '0%')),
                        'volume': convert_value(company_data.get('volume', 0)),
                        'lastUpdated': str(company_data.get('lastUpdated', ''))
                    })
                
        except Exception as e:
            st.warning(f"Error adding company {company_data.get('ticker', 'Unknown')}: {e}")
    
    #Add article node to the graph
    def add_news_article(self, article: dict, mentioned_tickers: list[str]):
        if not self.driver or not article:
            return
        
        try:
            article_id = f"article_{hash(article.get('title', ''))}"
            
            with self.driver.session() as session:
                session.run("""
                    MERGE (a:NewsArticle {id: $id})
                    SET a.title = $title,
                        a.content = $content,
                        a.source = $source,
                        a.publishedAt = $publishedAt,
                        a.url = $url
                """, {
                    'id': article_id,
                    'title': article.get('title', ''),
                    'content': article.get('content', '')[:500],
                    'source': article.get('source', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'url': article.get('url', '')
                })
                
                for ticker in mentioned_tickers:
                    session.run("""
                        MATCH (a:NewsArticle {id: $article_id})
                        MATCH (c:Company {ticker: $ticker})
                        MERGE (a)-[:MENTIONS]->(c)
                    """, {'article_id': article_id, 'ticker': ticker})
                    
        except Exception as e:
            st.warning(f"Error adding news article: {e}")
    
    def query_company_context(self, ticker: str) -> str:
        if not self.driver:
            return ""
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Company {ticker: $ticker})
                    OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Sector)
                    OPTIONAL MATCH (c)-[:HAS_PERFORMANCE]->(p:StockData)
                    RETURN c.name as company, s.name as sector, p.price as price, p.changePercent as change
                """, {'ticker': ticker})
                
                record = result.single()
                if record:
                    return f"{record['company']} ({ticker}) operates in {record['sector']} sector, trading at ${record['price']}"
                return ""
        except:
            return ""
    
    def get_graph_stats(self) -> dict:
        if not self.driver:
            return {"companies": 0, "sectors": 0, "articles": 0, "status": "Neo4j not connected"}
        
        try:
            with self.driver.session() as session:
                companies_result = session.run("MATCH (c:Company) RETURN count(c) as count")
                companies = companies_result.single()['count']
                
                unique_result = session.run("MATCH (c:Company) RETURN count(DISTINCT c.ticker) as count")
                unique_companies = unique_result.single()['count']
                
                incomplete_result = session.run("MATCH (c:Company) WHERE c.name IS NULL OR c.name = '' RETURN count(c) as count")
                incomplete_companies = incomplete_result.single()['count']
                
                duplicates_result = session.run("MATCH (c:Company) WITH c.ticker as ticker, count(c) as cnt WHERE cnt > 1 RETURN count(ticker) as count")
                duplicates = duplicates_result.single()['count']
                
                sectors_result = session.run("MATCH (s:Sector) RETURN count(s) as count")
                sectors = sectors_result.single()['count']
                
                articles_result = session.run("MATCH (a:NewsArticle) RETURN count(a) as count")
                articles = articles_result.single()['count']
            
            return {
                "companies": companies,
                "unique_companies": unique_companies,
                "incomplete_companies": incomplete_companies,
                "duplicate_tickers": duplicates,
                "sectors": sectors,
                "articles": articles,
                "status": "Connected"
            }
        except Exception as e:
            return {"companies": 0, "sectors": 0, "articles": 0, "status": f"Error: {e}"}
    
    def cleanup_graph(self) -> dict:
        if not self.driver:
            return {"removed": 0, "error": "Neo4j not connected"}
        
        try:
            removed_count = 0
            
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Company) 
                    WHERE c.name IS NULL OR c.name = ''
                    DETACH DELETE c
                    RETURN count(c) as removed
                """)
                incomplete_removed = result.single()['removed']
                removed_count += incomplete_removed
                
                result = session.run("""
                    MATCH (c:Company)
                    WITH c.ticker as ticker, collect(c) as companies
                    WHERE size(companies) > 1
                    UNWIND companies[1..] as duplicateCompany
                    DETACH DELETE duplicateCompany
                    RETURN count(duplicateCompany) as removed
                """)
                duplicate_removed = result.single()['removed']
                removed_count += duplicate_removed
                
                result = session.run("""
                    MATCH (s:StockData)
                    WHERE NOT (s)<-[:HAS_PERFORMANCE]-()
                    DELETE s
                    RETURN count(s) as removed
                """)
                orphan_removed = result.single()['removed']
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
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Company)
                    OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Sector)
                    RETURN c.ticker as ticker, c.name as name, s.name as sector
                    ORDER BY c.ticker
                """)
                
                companies = []
                for record in result:
                    companies.append({
                        'ticker': record['ticker'],
                        'name': record['name'] or 'N/A',
                        'sector': record['sector'] or 'N/A'
                    })
                
                return companies
                
        except Exception as e:
            return []