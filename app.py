import streamlit as st
from GraphRag import GraphRAGSystem

def main():
    st.set_page_config(
        page_title="Financial Graph RAG Analyzer",
        page_icon="📈",
        layout="wide"
    )
    
    with st.sidebar:
        st.header("Example Queries")
        examples = [
            "How is Apple performing in the current market?",
            "What's the outlook for Tesla stock?",
            "Compare Microsoft and Google stock performance",
            "What are the trends in the technology sector?",
            "How are banking stocks doing lately?"
        ]
        
        for example in examples:
            if st.button(example, key=f"example_{example}"):
                st.session_state.user_query = example

    st.title("📈 Financial Graph RAG Analyzer")
    st.markdown("### AI-powered financial analysis using Knowledge Graphs and Retrieval Augmented Generation")
    
    openai_key = "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"
    
    # Debug: Verify the API key
    print(f"DEBUG: Using OpenAI key starting with: {openai_key[:15]}...")
    if "your-ope" in openai_key:
        st.error("❌ Still using template OpenAI key!")
        st.stop()
    
    # Initialize the system
    if 'rag_system' not in st.session_state:
        with st.spinner("Initializing Graph RAG System..."):
            st.session_state.rag_system = GraphRAGSystem(openai_key)
        st.success("System initialized!")
    
    # Main interface
    st.header("Ask Your Financial Question")
    
    # Query input
    user_query = st.text_input(
        "Enter your financial question:",
        value=st.session_state.get('user_query', ''),
        placeholder="e.g., How is Tesla performing in the EV market?"
    )
    
    if st.button("Analyze", type="primary") and user_query:
        with st.spinner("Analyzing your query..."):
            
            # Process the query
            result = st.session_state.rag_system.process_user_query(user_query)
            
            # Display response
            st.header("📋 Analysis")
            st.write(result['response'])
            
            # Display additional information in columns
            tab1, tab2, tab3 = st.tabs(["📊 Stock Data & Entities", "🤖 AI Extraction Details", "📰 Sources & Context"])
            
            with tab1:
                # Display stock data and basic entities
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Stock Data")
                    if result['stock_data']:
                        for ticker, data in result['stock_data'].items():
                            with st.container():
                                st.metric(
                                    label=f"{data['companyName']} ({ticker})",
                                    value=f"${data['price']}",
                                    delta=f"{data['changePercent']}"
                                )
                    else:
                        st.info("No specific stock data found for this query")
                
                with col2:
                    st.subheader("🏢 Detected Entities")
                    if result['mentioned_tickers']:
                        st.write("**Companies:**", ", ".join(result['mentioned_tickers']))
                    if result['mentioned_sectors']:
                        st.write("**Sectors:**", ", ".join(result['mentioned_sectors']))
                    if not result['mentioned_tickers'] and not result['mentioned_sectors']:
                        st.info("No specific companies or sectors detected")
            
            with tab2:
                st.subheader("🤖 LLM Entity Extraction Details")
                
                # Check if extraction_details exists in result
                extraction = result.get('extraction_details', {})
                
                if extraction:
                    # Companies with confidence scores
                    if extraction.get('companies'):
                        st.write("**🏢 Companies Identified:**")
                        for company in extraction['companies']:
                            confidence = company.get('confidence', 0)
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                            st.write(f"{confidence_color} {company['name']} → {company['ticker']} (confidence: {confidence:.2f})")
                    
                    # Stock Groups
                    if extraction.get('stock_groups'):
                        st.write("**📊 Stock Groups Identified:**")
                        for group in extraction['stock_groups']:
                            confidence = group.get('confidence', 0)
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                            companies_list = group.get('companies', [])
                            companies_display = ', '.join(companies_list[:5])
                            if len(companies_list) > 5:
                                companies_display += f" (and {len(companies_list)-5} more)"
                            st.write(f"{confidence_color} {group['group']}: {companies_display} (confidence: {confidence:.2f})")
                    
                    # Sectors with confidence
                    if extraction.get('sectors'):
                        st.write("**🏭 Sectors Identified:**")
                        for sector in extraction['sectors']:
                            confidence = sector.get('confidence', 0)
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                            st.write(f"{confidence_color} {sector['sector']} (confidence: {confidence:.2f})")
                    
                    # Show search queries that were generated
                    if result.get('search_queries_used'):
                        st.write("**🔍 AI-Generated Search Queries:**")
                        for i, query in enumerate(result['search_queries_used'], 1):
                            st.write(f"{i}. {query}")
                    
                    # Cache performance
                    if result.get('cache_stats'):
                        cache_stats = result['cache_stats']
                        st.write(f"**⚡ Cache Performance:** {cache_stats['cached_extractions']} cached extractions")
                        
                else:
                    st.info("Detailed extraction information not available. Your GraphRag module may need updating.")
            
            with tab3:
                # Knowledge graph context
                if result.get('graph_context'):
                    st.subheader("🕸️ Knowledge Graph Context")
                    st.write(result['graph_context'])
                
                # Show relevant articles
                if result['relevant_articles']:
                    st.subheader("📰 Relevant News Articles")
                    for i, article in enumerate(result['relevant_articles'][:5], 1):
                        with st.expander(f"{i}. {article['metadata']['title']} (Score: {article['similarity_score']:.3f})"):
                            st.write(f"**Source:** {article['metadata']['source']}")
                            st.write(f"**Similarity Score:** {article['similarity_score']:.3f}")
                            if article['metadata']['url']:
                                st.write(f"**URL:** {article['metadata']['url']}")
                            st.write(f"**Content:** {article['content'][:400]}...")
                            
                            # Show companies mentioned in this specific article
                            tickers_in_metadata = article['metadata'].get('tickers', '')
                            if tickers_in_metadata:
                                st.write(f"**Companies Mentioned:** {tickers_in_metadata}")
                else:
                    st.info("No relevant articles found")
                    
                # Show any additional context
                if result.get('graph_context'):
                    st.subheader("🔗 Knowledge Graph Relationships")
                    st.text(result['graph_context'])
            
            # Summary metrics at the bottom
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Companies Found", len(result.get('mentioned_tickers', [])))
            
            with col2:
                st.metric("Sectors Identified", len(result.get('mentioned_sectors', [])))
            
            with col3:
                st.metric("Articles Analyzed", len(result.get('relevant_articles', [])))
            
            with col4:
                avg_confidence = 0
                extraction = result.get('extraction_details', {})
                if extraction.get('companies'):
                    confidences = [c.get('confidence', 0) for c in extraction['companies']]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                st.metric("Avg Confidence", f"{avg_confidence:.2f}")

if __name__ == "__main__":
    main()