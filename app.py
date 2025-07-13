import streamlit as st
import os
from GraphRag import GraphRAGSystem

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
#Streamlit file which is the front end for the query handling and response.
def main():
    st.set_page_config(
        page_title="Financial Graph RAG Analyzer",
        layout="wide"
    )
    
    st.title("Financial Analyzer")
    st.markdown("Financial analysis using Knowledge Graphs and Retrieval Augmented Generation")
    
    with st.sidebar:
        st.header("API Configuration")
        
        user_api_key = st.text_input(
            "Enter your OpenAI API Key:",
            type="password",
            placeholder="sk-...",
            help="Your API key is not stored and only used for this session. The model being used is gpt4o-mini"
        )
        
        if user_api_key:
            if user_api_key.startswith("sk-"):
                openai_key = user_api_key
                st.success("✅ API Key accepted!")
            else:
                st.error("❌ Please enter a valid OpenAI API key")
                st.stop()
        else:
            st.warning("🔑 OpenAI API Key Required")
            st.info("💡 Enter your OpenAI API key above to get started")
            st.stop()
        
        st.divider()
        
        st.header("💡 Example Queries")
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
            clean_response = result['response']
            clean_response = clean_response.replace('**', '').replace('*', '').replace('__', '')
            clean_response = clean_response.replace('\n', '\n\n')
            st.markdown(clean_response, unsafe_allow_html=False)
            
            tab1, tab2 = st.tabs(["Stock Data", "News Articles"])
            
            with tab1:
                st.subheader("Stock Data")
                mentioned_tickers = result.get('mentioned_tickers', [])
                original_tickers = result.get('original_tickers', mentioned_tickers)
                relevant_stock_data = {ticker: data for ticker, data in result['stock_data'].items() 
                                     if ticker in original_tickers}
                
                if relevant_stock_data:
                    for ticker, data in relevant_stock_data.items():
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
                    st.subheader("Relevant News Articles")
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