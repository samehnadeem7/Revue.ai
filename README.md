# 🚀 Startup Document Analyzer

**AI-powered analysis of startup documents with quantified insights and growth strategies using RAG (Retrieval-Augmented Generation)**

## ✨ Features

- **📄 PDF Analysis**: Upload any startup document (pitch deck, business plan, market research, financial model, customer feedback)
- **🤖 AI-Powered**: Uses Google Gemini Pro with RAG for intelligent, context-aware analysis
- **🔍 Smart Detection**: Automatically detects document type without manual selection
- **📊 Comprehensive Insights**: 200-400 words per section with actionable recommendations
- **🔗 Google Forms Integration**: Convert Google Forms URLs to PDF for instant analysis
- **💾 Data Persistence**: SQLite database stores analysis history and user metrics
- **📈 Analytics Dashboard**: Usage statistics and document type distribution
- **☁️ Cloud Ready**: Deployable on Render (backend) + Streamlit Cloud (frontend)

## 🏗️ Architecture

```
Frontend (Streamlit) ←→ Backend (FastAPI) ←→ Google Gemini API
                              ↓
                        SQLite Database
                              ↓
                        RAG System (Text Chunking + Embeddings)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Google Gemini API Key
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd fastapi
   ```

2. **Install dependencies**
   ```bash
   # Backend dependencies
   pip install -r requirements.txt
   
   # Frontend dependencies
   pip install -r requirements-streamlit.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy example file
   cp env.example .env
   
   # Edit .env with your API key
   GOOGLE_API_KEY=your-actual-gemini-api-key
   ```

4. **Run the application**
   ```bash
   # Option 1: Use the launcher (Windows)
   launch.bat
   
   # Option 2: Manual start
   # Terminal 1: Start FastAPI backend
   .venv\Scripts\activate
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   
   # Terminal 2: Start React frontend
   cd frontend
   npm start
   ```

5. **Access the application**
   - Backend: http://127.0.0.1:8000
   - Frontend: http://localhost:3000
   - API Docs: http://127.0.0.1:8000/docs

## ☁️ Cloud Deployment

### Backend (Render)

1. **Connect your GitHub repository to Render**
2. **Create a new Web Service**
3. **Configure environment variables in Render dashboard:**
   - `GOOGLE_API_KEY`: Your Google Gemini API key
4. **Deploy automatically on git push**

### Frontend (Streamlit Cloud)

1. **Connect your GitHub repository to Streamlit Cloud**
2. **Set the main file path to `frontend.py`**
3. **Deploy automatically on git push**

## 📚 API Endpoints

- `POST /upload-pdf/` - Upload and analyze PDF documents
- `POST /convert-google-form/` - Convert Google Forms to PDF and analyze
- `GET /analytics/` - Get usage analytics and insights
- `GET /history/` - Get analysis history
- `GET /health` - Health check for deployment monitoring

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google Gemini API key (required)

### Files
- `main.py`: FastAPI backend with AI analysis logic
- `frontend.py`: Streamlit frontend interface
- `config.py`: Configuration settings
- `requirements.txt`: Backend Python dependencies
- `requirements-streamlit.txt`: Frontend Python dependencies
- `render.yaml`: Render deployment configuration
- `.streamlit/config.toml`: Streamlit Cloud configuration

## 🧠 How It Works

### 1. Document Processing
- PDF text extraction using PyMuPDF
- Content validation for business relevance
- Automatic document type detection

### 2. RAG Analysis
- Text chunking into manageable segments
- Embedding generation for semantic search
- Context retrieval for relevant content
- AI analysis with retrieved context

### 3. AI Generation
- Google Gemini Pro processes the analysis
- Structured output with clear sections
- Actionable insights and growth strategies
- Professional, emoji-free business language

### 4. Data Storage
- SQLite database for analysis history
- User metrics tracking
- Export capabilities (CSV, Excel)

## 🎯 Use Cases

- **Startup Founders**: Analyze pitch decks and business plans
- **Investors**: Evaluate startup opportunities and growth potential
- **Business Analysts**: Extract insights from market research
- **Product Managers**: Analyze customer feedback and surveys
- **Consultants**: Generate strategic recommendations

## 🛠️ Technology Stack

- **Backend**: FastAPI, PyMuPDF, Google Gemini AI
- **Frontend**: Streamlit, Pandas, Requests
- **Database**: SQLite
- **AI/ML**: RAG (Retrieval-Augmented Generation), Text Embeddings
- **Deployment**: Render, Streamlit Cloud

## 📊 Sample Output

The AI generates comprehensive analysis including:
- Executive Summary
- Value Proposition & Competitive Advantage
- Market Opportunity Analysis
- Business Model & Revenue Projections
- Competitive Landscape
- Financial Highlights
- Team & Execution Capability
- Investment & Funding Strategy
- Risk Assessment
- Final Growth Strategy

## 🔒 Security

- API keys stored in environment variables
- No sensitive data committed to Git
- CORS middleware for secure cross-origin requests
- Input validation and sanitization

## 🚨 Troubleshooting

### Common Issues
1. **"API Rate Limit"**: Check Google Gemini API quota
2. **"Module not found"**: Install dependencies with pip
3. **"Database error"**: Ensure SQLite file permissions
4. **"Deployment failed"**: Check environment variables

### Debug Mode
```bash
# Run with debug logging
uvicorn main:app --reload --log-level debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini AI for powerful language model capabilities
- FastAPI for high-performance web framework
- Streamlit for rapid frontend development
- PyMuPDF for reliable PDF processing

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review deployment logs
- Open a GitHub issue

---

**Built with ❤️ for startup founders and business analysts**
