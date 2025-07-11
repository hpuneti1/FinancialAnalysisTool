import streamlit as st
import os
from GraphRag import GraphRAGSystem

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

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

    st.title("Financial Analyzer")
    st.markdown("###Financial analysis using Knowledge Graphs and Retrieval Augmented Generation")
    
    # Get OpenAI API key from environment variables, Streamlit secrets, or fallback to hardcoded
    openai_key = None
    if "OPENAI_API_KEY" in os.environ:
        openai_key = os.environ["OPENAI_API_KEY"]
    else:
        try:
            if hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
                openai_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass  # Ignore secrets parsing errors
        
        if not openai_key:
            # Fallback to hardcoded key (your original key)
            openai_key = "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"
    
    if not openai_key or openai_key.startswith("sk-your") or openai_key.startswith("your-"):
        st.error("❌ Please set your OpenAI API key in environment variables or Streamlit secrets!")
        st.info("💡 Set OPENAI_API_KEY environment variable or add it to .streamlit/secrets.toml")
        st.stop()
    
    if 'rag_system' not in st.session_state:
        with st.spinner("Initializing Graph RAG System..."):
            st.session_state.rag_system = GraphRAGSystem(openai_key)
        st.success("System initialized!")
    
    st.header("Ask Your Financial Question")
    
    user_query = st.text_input(
        "Enter your financial question:",
        value=st.session_state.get('user_query', ''),
        placeholder="e.g., How is Tesla performing in the EV market?"
    )
    
    if st.button("Analyze", type="primary") and user_query:
        with st.spinner("Analyzing your query..."):
        
            result = st.session_state.rag_system.process_user_query(user_query)
            
            st.header("Analysis")
            st.write(result['response'])
            
            tab1, tab2 = st.tabs(["Stock Data", "News Articles"])
            
            with tab1:
                st.subheader("Stock Data")
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
            
            with tab2:
                if result['relevant_articles']:
                    st.subheader("📰 Relevant News Articles")
                    for i, article in enumerate(result['relevant_articles'][:5], 1):
                        with st.expander(f"{i}. {article['metadata']['title']} (Score: {article['similarity_score']:.3f})"):
                            st.write(f"**Source:** {article['metadata']['source']}")
                            st.write(f"**Similarity Score:** {article['similarity_score']:.3f}")
                            if article['metadata']['url']:
                                st.write(f"**URL:** {article['metadata']['url']}")
                            st.write(f"**Content:** {article['content'][:400]}...")
                            
                            tickers_in_metadata = article['metadata'].get('tickers', '')
                            if tickers_in_metadata:
                                st.write(f"**Companies Mentioned:** {tickers_in_metadata}")
                else:
                    st.info("No relevant articles found")
            

if __name__ == "__main__":
    main()