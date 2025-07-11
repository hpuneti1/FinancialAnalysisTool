# 🚀 Deployment Guide

This guide covers various deployment options for the Financial Analysis Tool, from local development to cloud production.

## 📋 Table of Contents
- [Local Development](#local-development)
- [Cloud Neo4j (Recommended)](#cloud-neo4j-recommended)
- [Docker Deployment](#docker-deployment)
- [Streamlit Cloud](#streamlit-cloud)
- [AWS Deployment](#aws-deployment)
- [Google Cloud Platform](#google-cloud-platform)

## 🏠 Local Development

### Prerequisites
- Python 3.8+
- Neo4j Desktop or Docker

### Setup
1. Clone and install dependencies
2. Set up local Neo4j instance
3. Configure environment variables
4. Run with `streamlit run app.py`

## ☁️ Cloud Neo4j (Recommended)

### Neo4j Aura (Managed Cloud)

**Best for production deployment without managing infrastructure.**

1. **Create Neo4j Aura Account**
   - Go to [neo4j.com/aura](https://neo4j.com/aura)
   - Sign up for free tier (suitable for development)

2. **Create Database Instance**
   - Choose "AuraDB Free" for development
   - Note down the connection URI and credentials

3. **Update Environment Variables**
   ```bash
   NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-generated-password
   ```

4. **Benefits**
   - ✅ Managed service (no maintenance)
   - ✅ Automatic backups
   - ✅ SSL/TLS encryption
   - ✅ Global accessibility
   - ✅ Free tier available

## 🐳 Docker Deployment

### Option 1: Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - NEWS_API_KEY=${NEWS_API_KEY}
      - NEO4J_URI=neo4j://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=admin123
    depends_on:
      - neo4j
    volumes:
      - ./chroma_db:/app/chroma_db

  neo4j:
    image: neo4j:5.0
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/admin123
      - NEO4J_PLUGINS=["graph-data-science"]
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

### Deploy with Docker Compose

```bash
# Set environment variables
export OPENAI_API_KEY=your_key
export NEWS_API_KEY=your_key

# Deploy
docker-compose up -d
```

### Option 2: Individual Containers

```bash
# Run Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/admin123 \
  neo4j:5.0

# Run Application
docker run -d \
  --name financial-analyzer \
  -p 8501:8501 \
  -e OPENAI_API_KEY=your_key \
  -e NEWS_API_KEY=your_key \
  -e NEO4J_URI=neo4j://neo4j:7687 \
  --link neo4j:neo4j \
  your-dockerhub-username/financial-analyzer
```

## 🌐 Streamlit Cloud

**Perfect for easy web deployment with minimal setup.**

### Steps:

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Add secrets in app settings

3. **Configure Secrets**
   In Streamlit Cloud dashboard → App Settings → Secrets:
   ```toml
   OPENAI_API_KEY = "your-openai-key"
   NEWS_API_KEY = "your-newsapi-key"
   NEO4J_URI = "neo4j+s://your-aura-instance.databases.neo4j.io"
   NEO4J_USER = "neo4j"
   NEO4J_PASSWORD = "your-aura-password"
   ```

4. **Benefits**
   - ✅ Free hosting
   - ✅ Automatic deployments from GitHub
   - ✅ Built-in secrets management
   - ✅ Custom domain support

## ☁️ AWS Deployment

### Option 1: AWS ECS with Fargate

1. **Push Docker image to ECR**
2. **Create ECS cluster**
3. **Deploy task with environment variables**
4. **Use Application Load Balancer**

### Option 2: AWS EC2

1. **Launch EC2 instance**
2. **Install Docker and Docker Compose**
3. **Deploy using docker-compose**
4. **Configure security groups**

### Managed Database Options

- **Amazon Neptune**: Graph database service
- **Amazon RDS**: For traditional databases
- **DocumentDB**: For document storage

## 🌐 Google Cloud Platform

### Option 1: Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/financial-analyzer
gcloud run deploy --image gcr.io/PROJECT_ID/financial-analyzer --platform managed
```

### Option 2: Google Kubernetes Engine (GKE)

1. **Create GKE cluster**
2. **Deploy using Kubernetes manifests**
3. **Use Google Cloud SQL or Bigtable**

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Use environment variables for all secrets
- [ ] Enable SSL/TLS encryption
- [ ] Use managed databases with authentication
- [ ] Implement rate limiting
- [ ] Monitor API usage
- [ ] Set up logging and monitoring
- [ ] Regular security updates

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
NEWS_API_KEY=...

# Neo4j (choose one setup)
NEO4J_URI=neo4j+s://cloud-instance.databases.neo4j.io  # Cloud
NEO4J_URI=neo4j://localhost:7687                        # Local
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Optional
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

## 📊 Monitoring & Maintenance

### Key Metrics to Monitor
- API response times
- Database connection health
- Vector database performance
- News article ingestion rates
- User query patterns

### Maintenance Tasks
- Regular database backups
- API key rotation
- Dependency updates
- Performance optimization
- Log analysis

## 💰 Cost Considerations

### Free Tier Options
- **Neo4j Aura Free**: 50K nodes, 175K relationships
- **Streamlit Cloud**: Free hosting
- **Google Cloud Run**: Pay per request
- **AWS ECS Fargate**: Pay for compute time

### Production Scaling
- Monitor OpenAI API usage (pay per token)
- NewsAPI rate limits (500 requests/day free)
- Database storage and compute costs
- CDN for static assets

## 🚀 Quick Cloud Setup

For the fastest cloud deployment:

1. **Use Neo4j Aura** for managed graph database
2. **Deploy on Streamlit Cloud** for easy web hosting
3. **Set up monitoring** with built-in Streamlit metrics

This gives you a production-ready system accessible globally with minimal setup time!

## 📞 Support

For deployment issues:
- Check the [GitHub Issues](https://github.com/yourusername/financial-analysis-tool/issues)
- Review logs in your deployment platform
- Verify all environment variables are set correctly