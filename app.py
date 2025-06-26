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
    
    # Hardcoded API key for development - FIXED
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
            
            # Show relevant articles
            if result['relevant_articles']:
                st.subheader("📰 Relevant News Articles")
                for i, article in enumerate(result['relevant_articles'][:3], 1):
                    with st.expander(f"{i}. {article['metadata']['title']}"):
                        st.write(f"**Source:** {article['metadata']['source']}")
                        st.write(f"**Similarity Score:** {article['similarity_score']:.3f}")
                        if article['metadata']['url']:
                            st.write(f"**URL:** {article['metadata']['url']}")
                        st.write(f"**Content:** {article['content'][:400]}...")

if __name__ == "__main__":
    main()