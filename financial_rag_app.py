from Phase2 import RAG  # Import your existing RAG class
from openai import OpenAI
from typing import Dict, List

class FinancialRAGApp:
    def __init__(self, openai_api_key: str):
        self.rag_system = RAG(openaiAPIKEY=openai_api_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.is_initialized = False
        
    def initialize_system(self):
        """Load comprehensive financial data for the app"""
        if self.is_initialized:
            print("✅ System already initialized")
            return
            
        print("🚀 Initializing Financial RAG System...")
        
        # Expand to cover major market sectors
        major_companies = [
            # Tech Giants
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
            # Healthcare/Pharma
            'JNJ', 'PFE', 'UNH', 'ABBV', 'TMO',
            # Financial
            'JPM', 'BAC', 'WFC', 'GS', 'V', 'MA',
            # Energy
            'XOM', 'CVX', 'COP',
            # Consumer
            'KO', 'PG', 'WMT', 'HD'
        ]
        
        # More comprehensive news queries for broad coverage
        comprehensive_queries = [
            # Direct company searches
            'Apple AAPL earnings revenue quarterly',
            'Microsoft MSFT Azure cloud computing earnings',
            'Johnson & Johnson JNJ pharmaceutical drug development',
            'JPMorgan Chase JPM banking financial results',
            'Tesla TSLA electric vehicle deliveries earnings',
            'Exxon Mobil XOM oil energy earnings',
            
            # By sector
            'technology earnings Q2 2025',
            'pharmaceutical drug approvals FDA',
            'banking sector financial results',
            'energy companies oil prices',
            'healthcare stocks medical devices',
            
            # By themes
            'artificial intelligence stocks',
            'electric vehicle market',
            'renewable energy investments',
            'biotech mergers acquisitions',
            'fintech regulation',
            
            # Market-wide
            'S&P 500 earnings outlook',
            'Federal Reserve interest rates',
            'inflation impact stocks'
        ]
        
        self.rag_system.processSampleData(
            tickers=major_companies,
            newsQueries=comprehensive_queries
        )
        self.rag_system.buildKG()
        self.rag_system.buildVectorDatabase()
        self.is_initialized = True
        print("✅ System ready for user queries!")
    
    def answer_user_query(self, user_question: str) -> dict:
        """
        Main method to answer user questions using Graph RAG
        """
        if not self.is_initialized:
            return {
                'error': 'System not initialized. Please wait for data loading to complete.'
            }
            
        print(f"🔍 Processing: '{user_question}'")
        
        try:
            # Step 1: Semantic search for relevant content
            relevant_docs = self.rag_system.vector_db.advFinSearch(user_question)
            
            # Step 2: Extract entities from user question
            question_entities = self._extract_question_entities(user_question)
            
            # Step 3: Query knowledge graph for relationships
            graph_context = self._get_graph_context(question_entities)
            
            # Step 4: Generate comprehensive answer
            answer = self._generate_answer(user_question, relevant_docs, graph_context)
            
            return {
                'question': user_question,
                'answer': answer,
                'sources': self._format_sources(relevant_docs),
                'related_companies': question_entities['tickers'],
                'confidence_score': self._calculate_confidence(relevant_docs),
                'graph_context': graph_context[:200] + "..." if len(graph_context) > 200 else graph_context
            }
            
        except Exception as e:
            return {
                'error': f'Error processing query: {str(e)}',
                'question': user_question
            }
    
    def _extract_question_entities(self, question: str) -> dict:
        """Extract relevant entities from user question"""
        tickers = self.rag_system.extractor.extractTickers(question)
        sectors = self.rag_system.extractor.classifySector(question)
        agencies = self.rag_system.extractor.extractRegulatoryMentions(question)
        
        return {
            'tickers': tickers,
            'sectors': sectors,
            'agencies': agencies
        }
    
    def _get_graph_context(self, entities: dict) -> str:
        """Query Neo4j knowledge graph for entity relationships"""
        context_parts = []
        
        try:
            # Get company information
            for ticker in entities['tickers'][:3]:  # Limit to top 3 to avoid overwhelming context
                company_query = f"""
                MATCH (c:Company {{ticker: '{ticker}'}})
                OPTIONAL MATCH (c)-[:CLASSIFIED_AS]->(s:Sector)
                OPTIONAL MATCH (c)-[:HAS_PERFORMANCE]->(p:StockPerformance)
                RETURN c.name as company, s.name as sector, p.price as price, p.changePercent as change
                """
                
                result = self.rag_system.graphBuilder.graph.run(company_query).data()
                if result:
                    company_info = result[0]
                    context_parts.append(
                        f"{company_info['company']} ({ticker}) operates in {company_info['sector']} "
                        f"sector with current price ${company_info['price']} ({company_info['change']} change)"
                    )
            
            # Get sector relationships
            for sector in entities['sectors'][:2]:  # Limit to top 2 sectors
                sector_query = f"""
                MATCH (s:Sector {{name: '{sector}'}})
                OPTIONAL MATCH (s)<-[:CLASSIFIED_AS]-(c:Company)
                OPTIONAL MATCH (s)-[:REGULATED_BY]->(r:RegulatoryBody)
                RETURN s.name as sector, collect(c.ticker)[0..3] as companies, collect(r.name) as regulators
                """
                
                result = self.rag_system.graphBuilder.graph.run(sector_query).data()
                if result:
                    sector_info = result[0]
                    companies_str = ', '.join([c for c in sector_info['companies'] if c]) if sector_info['companies'] else 'various companies'
                    regulators_str = ', '.join(sector_info['regulators']) if sector_info['regulators'] else 'multiple agencies'
                    context_parts.append(
                        f"{sector_info['sector']} sector includes {companies_str} "
                        f"and is regulated by {regulators_str}"
                    )
                    
        except Exception as e:
            print(f"Error querying graph: {e}")
            context_parts.append("Graph context temporarily unavailable")
        
        return " ".join(context_parts)
    
    def _generate_answer(self, question: str, docs: list, graph_context: str) -> str:
        """Generate comprehensive answer using OpenAI with RAG context"""
        
        # Prepare context from retrieved documents
        doc_context = "\n\n".join([
            f"Article: {doc['metadata']['title']}\n"
            f"Content: {doc['content'][:400]}...\n"
            f"Source: {doc['metadata']['source']}"
            for doc in docs[:3]  # Use top 3 most relevant
        ])
        
        system_prompt = """You are a financial analyst AI that provides insightful, accurate analysis based on current market data and company information. 

Your responses should:
- Be factual and data-driven
- Cite specific sources when making claims
- Explain the reasoning behind your analysis
- Consider both opportunities and risks
- Be accessible to both novice and experienced investors
- Keep responses concise but comprehensive (2-3 paragraphs max)

Format your response with clear structure and mention specific companies, sectors, or market factors when relevant."""

        user_prompt = f"""
Question: {question}

Knowledge Graph Context:
{graph_context}

Recent News & Market Data:
{doc_context}

Please provide a comprehensive analysis that answers the user's question using the provided context. Include:
1. Direct answer to the question
2. Supporting evidence from the sources
3. Key factors to consider

Keep the response focused and actionable. Cite article titles when referencing specific information.
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I apologize, but I encountered an error generating the response. Based on the available data: {doc_context[:200]}..."
    
    def _format_sources(self, docs: list) -> list:
        """Format source information for user"""
        sources = []
        for doc in docs[:5]:  # Limit to top 5 sources
            sources.append({
                'title': doc['metadata']['title'],
                'source': doc['metadata']['source'],
                'url': doc['metadata'].get('url', ''),
                'relevance_score': round(doc.get('boostedScore', 0), 3)
            })
        return sources
    
    def _calculate_confidence(self, docs: list) -> str:
        """Calculate confidence based on source quality and relevance"""
        if not docs:
            return "Low"
        
        avg_score = sum(doc.get('boostedScore', 0) for doc in docs) / len(docs)
        
        if avg_score > 0.3:
            return "High"
        elif avg_score > 0.0:
            return "Medium"
        else:
            return "Low"

# Command line interface for testing
def main():
    # Replace with your actual OpenAI API key
    API_KEY = "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"
    
    app = FinancialRAGApp(openai_api_key=API_KEY)
    
    print("Initializing system... This may take a few minutes.")
    app.initialize_system()
    
    print("\n" + "="*60)
    print("🔍 Financial RAG App - Ready for Questions!")
    print("="*60)
    print("Example queries:")
    print("- How is Tesla performing lately?")
    print("- What's happening with bank stocks?")
    print("- Tell me about AI companies")
    print("- Type 'quit' to exit")
    print("-"*60)
    
    while True:
        user_query = input("\n💭 Your question: ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            print("👋 Thanks for using Financial RAG App!")
            break
            
        if not user_query:
            continue
            
        print("\n🤔 Thinking...")
        result = app.answer_user_query(user_query)
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            continue
            
        print(f"\n📊 **Answer:**")
        print(result['answer'])
        
        print(f"\n📈 **Related Companies:** {', '.join(result['related_companies']) if result['related_companies'] else 'None detected'}")
        print(f"🎯 **Confidence:** {result['confidence_score']}")
        print(f"📰 **Sources:** {len(result['sources'])} articles")
        
        if result['sources']:
            print("\n📚 **Top Sources:**")
            for i, source in enumerate(result['sources'][:3], 1):
                print(f"  {i}. {source['title']} ({source['source']}) - Score: {source['relevance_score']}")

if __name__ == "__main__":
    main()