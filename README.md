# Financial Analysis Tool with Graph RAG

## Project Overview

Throughout this project, I explored the applications of Graph Retrieval Augmented Generation and modern AI/LLM technolgyies to create a financial analysis tool. I developed this tool to unserand how knowledge graphs, vector databased and LLMs can work together to produce meaningful insights and description from real world data. The core motivation behind this project was to move beyond just traditional RAG implementations and explore how graph structured knowledge representation could enhance the contextual understanding of data, in this case the financial field specifically. Rather than simply retrieving relevant documents, this system builds and maintains a dynamic knowledge graph that captures the intricate relationships between companies, sectors, market events, and news sentiment. This creates a more stronger foundation for AI-generated analysis.


**Graph RAG Implementation**: Unlike traditional RAG systems that rely solely on vector similarity, this implementation incorporates a Neo4j knowledge graph to model complex relationships between financial entities. This allows the system to understand not just semantic similarity, but structural relationships like sector connections, stock data, and market interdependencies.

**Multi-Modal Data Integration**: The system demonstrates real-world data pipeline challenges by integrating structured market data (via Yahoo Finance), unstructured news content (NewsAPI and RSS feeds), and graph-structured relationships - showcasing how different data modalities can be unified through embeddings and graph representations.

**Entity Recognition & Extraction**: Using OpenAI's GPT-4o-mini, the system performs sophisticated financial entity extraction that goes beyond simple NER tasks. It handles complex scenarios like separating company mentions from ticker symbols, identifying implicit sector references, and maintaining confidence scoring for extraction quality.

**Vector Database Operations**: ChromaDB integration provides hands-on experience with  vector operations including incremental updates, semantic search optimization, and embedding management at scale.

## System Components

### Entity Extractor
Leverages LLMs for intelligent parsing of financial queries, extracting companies, sectors, and stock groups with confidence scoring. Handles edge cases like unconventional ticker formats (C3.AI, BRK-A) and ambiguous references.

### Financial Data Collector  
Implements a sophisticated news aggregation pipeline with rate limiting, relevance scoring, and multi-source deduplication. Integrates with premium financial data sources including Reuters, WSJ, CNBC, and real-time market data.

### Vector Database (ChromaDB)
Provides semantic search capabilities over financial news articles using OpenAI's text-embedding-3-small model. Implements persistent storage with incremental updates and duplicate detection.

### Knowledge Graph (Neo4j)
Models complex financial relationships through a graph schema that captures company-sector hierarchies, performance metrics, and news article associations. Uses Cypher queries for contextual relationship extraction.

### Graph RAG System
Orchestrates all components to provide a unified query interface that combines semantic search, graph traversal, and LLM generation for comprehensive financial analysis.

## Key Technical Achievements

**Dynamic Search Strategy**: The system generates contextually relevant search terms using LLMs, moving beyond keyword matching to semantic understanding of financial queries.

**Confidence-Based Filtering**: Entity extraction includes confidence scoring, allowing the system to make informed decisions about data quality and relevance thresholds.

**Multi-Source Truth Assembly**: Combines real-time market data, historical news archives, and graph-structured knowledge to provide well-rounded analysis that accounts for both quantitative metrics and qualitative market sentiment.

**Scalable Architecture**: Designed with modularity in mind, each component can be independently scaled or replaced, following modern microservices principles.

## Future Development Directions

As I continue developing this tool, I want to work and improve several areas while also adding additional features. The main two things I plan to work on for now are:

- **Temporal Graph Evolution**: 
Implementing time-series capabilities in the knowledge graph to track how relationships and market dynamics evolve through certain events
- **Sentiment Analysis Integration**: 
Adding NLP-based sentiment scoring to news articles for more complex market analysis

## Technology Stack

- **Backend**: Python with asyncio for concurrent API operations
- **LLM Integration**: OpenAI GPT-4o-mini for entity extraction and analysis generation
- **Vector Store**: ChromaDB with persistent storage and incremental updates
- **Graph Database**: Neo4j with Cypher query optimization
- **Data Sources**: yfinance, NewsAPI, RSS feeds from major financial publications
- **Frontend**: Streamlit for rapid prototyping and interactive demonstration
- **Infrastructure**: Docker-compatible with cloud deployment capabilities

## Try the Live Application

**Access the deployed application here:** [https://your-app-url.streamlit.app/](https://your-app-url.streamlit.app/)

## Learning Outcomes

Through this project, I've gained practical experience in:
- Implementing RAG systems with knowledge graphs
- Managing complex data pipelines with multiple external APIs
- Designing graph schemas for domain-specific knowledge representation
- Optimizing vector search performance for real-time applications
- Building modular, scalable architectures for AI applications

This project represents not just a functional financial analysis tool, but an exploration of how AI can be used to gather and analyze data not only in the financial field, but all types of fields.