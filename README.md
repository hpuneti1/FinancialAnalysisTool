# 📈 Financial Analysis Tool with Graph RAG

A sophisticated financial analysis application that combines **Knowledge Graphs**, **Vector Databases**, and **Large Language Models** to provide comprehensive stock market insights.

## 🎯 Features

- **AI-Powered Entity Extraction**: Automatically identifies companies, sectors, and stock groups from natural language queries
- **Graph RAG Architecture**: Combines knowledge graphs with retrieval-augmented generation for contextual analysis
- **Multi-Source News Aggregation**: Pulls from NewsAPI, RSS feeds (Reuters, WSJ, CNBC, etc.)
- **Vector Semantic Search**: Uses OpenAI embeddings for intelligent article retrieval
- **Real-Time Stock Data**: Live market data via yfinance API
- **Knowledge Graph Storage**: Persistent Neo4j graph database for company relationships
- **Dynamic Search Generation**: LLM-generated search terms for better news coverage

## 🏗️ Architecture

```
User Query → Entity Extraction → Stock Data + News Search → Vector DB + Knowledge Graph → LLM Analysis
```

### Components:
- **EntityExtractor**: OpenAI-powered company/sector identification
- **FinDataCollector**: Multi-source financial news aggregation
- **VectorDB**: ChromaDB for semantic article search
- **KnowledgeGraph**: Neo4j for relationship storage
- **GraphRAG**: Orchestrates all components

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Neo4j Database (local or cloud)
- OpenAI API Key
- NewsAPI Key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/financial-analysis-tool.git
cd financial-analysis-tool
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
OPENAI_API_KEY=your_openai_key_here
NEWS_API_KEY=your_newsapi_key_here
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

4. **Start Neo4j Database**
```bash
# Using Docker
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/your_password neo4j

# Or install Neo4j Desktop from neo4j.com
```

5. **Run the application**
```bash
streamlit run app.py
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=sk-...
NEWS_API_KEY=...
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=admin123
```

### News Sources
The tool aggregates from:
- NewsAPI
- Reuters Business Feed
- Wall Street Journal
- CNBC
- MarketWatch
- Yahoo Finance
- Seeking Alpha
- And more...

## 📊 Usage Examples

### Individual Company Analysis
```
"How is Apple performing in the current market?"
```

### Sector Analysis  
```
"Technology sector outlook for 2024"
```

### Comparative Analysis
```
"Compare FAANG stocks performance"
```

### Market Trends
```
"Banking stocks after interest rate changes"
```

## 🛠️ Technical Implementation

### Entity Extraction
- Uses GPT-4o-mini for company/sector identification
- Confidence scoring for extraction accuracy
- Dynamic search term generation
- Handles complex ticker formats (C3.AI, BRK.A, etc.)

### Vector Database
- ChromaDB for persistent storage
- OpenAI text-embedding-3-small
- Semantic similarity search
- Incremental updates with deduplication

### Knowledge Graph
- Neo4j for relationship modeling
- Company → Sector → Performance relationships
- News article → Company mentions
- Cypher query optimization

### News Aggregation
- Rate-limited API calls
- Relevance scoring algorithms
- Content quality filtering
- Multi-source deduplication

## 🎯 API Reference

### Core Classes

#### `GraphRAGSystem`
Main orchestrator class that coordinates all components.

```python
system = GraphRAGSystem(openai_key)
result = system.process_user_query("How is Tesla doing?")
```

#### `EntityExtractor`
Identifies financial entities from text.

```python
extractor = EntityExtractor(openai_key)
entities = extractor.extract_entities("Apple stock analysis")
tickers = extractor.extract_tickers("Technology sector trends")
```

#### `VectorDatabase`
Semantic search over news articles.

```python
vector_db = VectorDatabase(openai_key)
articles = vector_db.search("Tesla earnings", n_results=5)
```

## 🔒 Security Notes

- API keys should be stored in environment variables
- Neo4j should use authentication in production
- Rate limiting implemented for external APIs
- Input validation for user queries

## 🚀 Deployment Options

### Local Development
- Streamlit local server
- Local Neo4j instance
- ChromaDB local storage

### Cloud Deployment
- **Streamlit Cloud**: Easy web deployment
- **Neo4j Aura**: Managed graph database
- **AWS/GCP**: Full cloud infrastructure
- **Docker**: Containerized deployment

## 📈 Performance Optimizations

- Vector database persistence across sessions
- Entity extraction caching
- News article deduplication
- Incremental knowledge graph updates
- Rate limiting for API calls

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT and embedding models
- Neo4j for graph database technology
- ChromaDB for vector storage
- NewsAPI for financial news data
- Yahoo Finance for stock data

## 📞 Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/financial-analysis-tool](https://github.com/yourusername/financial-analysis-tool)