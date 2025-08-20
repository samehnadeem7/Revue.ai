from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import fitz  # PyMuPDF library
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, List
import sqlite3
from datetime import datetime
import json

app = FastAPI(
    title="Startup Document Analyzer",
    description="Automatic startup document analysis"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
genai.configure(api_key=api_key)

# Database configuration
from config import DATABASE_URL

# Create uploads directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database setup
def get_db_connection():
    """Get SQLite database connection"""
    # Ensure database file exists and create tables if needed
    conn = sqlite3.connect('./startup_analyzer.db')
    # Create tables if they don't exist
    cursor = conn.cursor()
    
    # Create analysis history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            document_type TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT DEFAULT 'anonymous'
        )
    ''')
    
    # Create user metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL UNIQUE,
            analysis_count INTEGER DEFAULT 1,
            last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

def init_db():
    """Initialize SQLite database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create analysis history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            document_type TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT DEFAULT 'anonymous'
        )
    ''')
    
    # Create user metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL UNIQUE,
            analysis_count INTEGER DEFAULT 1,
            last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database (only when needed)
init_db()  # Create database tables on startup

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def analyze_startup_document(text: str, document_type: str) -> Dict:
    """Analyze document based on type and return structured insights with metrics"""
    
    analysis_prompts = {
        "Pitch Deck": """Analyze this pitch deck and provide QUANTIFIED insights:

        1. EXECUTIVE SUMMARY (2-3 sentences with key metrics)
        2. VALUE PROPOSITION & COMPETITIVE ADVANTAGE
           - What makes this startup unique?
           - How will it stand out from competitors?
           - Quantified benefits (e.g., "30% cost reduction", "5x faster")
        3. MARKET OPPORTUNITY (with numbers)
           - Market size (TAM, SAM, SOM)
           - Growth rate (CAGR)
           - Target market segments with sizes
        4. BUSINESS MODEL & REVENUE PROJECTIONS
           - Revenue streams with projected amounts
           - Unit economics (LTV, CAC, margins)
           - Break-even timeline
        5. COMPETITIVE LANDSCAPE & DIFFERENTIATION
           - Top 3 competitors
           - Competitive advantages with metrics
           - Market positioning strategy
        6. FINANCIAL HIGHLIGHTS & PROJECTIONS
           - Revenue projections (3-5 years)
           - Growth rates (monthly/quarterly)
           - Key financial metrics
        7. TEAM STRENGTHS & EXECUTION CAPABILITY
        8. INVESTMENT ASK & USE OF FUNDS
        9. RISK ASSESSMENT & MITIGATION
        10. GROWTH STRATEGY & SCALABILITY
            - Expansion plans with timelines
            - Scaling metrics and milestones

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES wherever possible.
        Focus on how this startup will STAND OUT and SCALE.""",
        
        "Business Plan": """Analyze this business plan and provide QUANTIFIED insights:

        1. BUSINESS OVERVIEW & VALUE PROPOSITION
           - Unique selling points with metrics
           - Competitive advantages quantified
        2. MARKET ANALYSIS & OPPORTUNITY
           - Market size with specific numbers
           - Growth rates and trends
           - Target segments with sizes
        3. PRODUCT/SERVICE DETAILS & DIFFERENTIATION
           - Key features with quantified benefits
           - How it stands out from alternatives
        4. REVENUE MODEL & PROJECTIONS
           - Revenue streams with amounts
           - Pricing strategy and margins
           - 3-5 year projections
        5. MARKETING STRATEGY & ACQUISITION
           - Customer acquisition channels
           - CAC and conversion rates
           - Growth marketing tactics
        6. OPERATIONS PLAN & SCALABILITY
           - Operational efficiency metrics
           - Scaling bottlenecks and solutions
        7. FINANCIAL PROJECTIONS & METRICS
           - Revenue, costs, and profitability
           - Key ratios and benchmarks
           - Cash flow projections
        8. RISK ANALYSIS & MITIGATION
           - Top risks with probability
           - Mitigation strategies
        9. IMPLEMENTATION TIMELINE & MILESTONES
           - Key milestones with dates
           - Success metrics for each phase
        10. SUCCESS METRICS & KPIs
            - Measurable success indicators
            - Tracking and optimization plans

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES.
        Focus on EXECUTION and SCALABILITY.""",
        
        "Market Research": """Analyze this market research and provide QUANTIFIED insights:

        1. MARKET SIZE & GROWTH METRICS
           - TAM, SAM, SOM with specific numbers
           - CAGR and growth drivers
           - Regional breakdowns
        2. KEY TRENDS & OPPORTUNITIES
           - Emerging trends with adoption rates
           - Market gaps and opportunities
           - Timing for market entry
        3. CUSTOMER SEGMENTS & BEHAVIOR
           - Segment sizes and characteristics
           - Customer acquisition costs
           - Lifetime value projections
        4. COMPETITOR LANDSCAPE & POSITIONING
           - Market share of top competitors
           - Competitive advantages and weaknesses
           - Positioning opportunities
        5. MARKET DRIVERS & BARRIERS
           - Growth drivers with impact metrics
           - Entry barriers and costs
           - Regulatory requirements
        6. OPPORTUNITIES & THREATS
           - Market opportunities with sizes
           - Threat assessment and mitigation
           - Risk-reward analysis
        7. REGULATORY & COMPLIANCE FACTORS
           - Regulatory requirements and costs
           - Compliance timeline and resources
        8. FUTURE PREDICTIONS & FORECASTS
           - Market evolution predictions
           - Technology adoption curves
           - Competitive landscape changes
        9. ENTRY STRATEGY & TIMING
           - Optimal entry timing
           - Market entry costs and timeline
           - Success probability factors
        10. INVESTMENT OPPORTUNITY ASSESSMENT
            - Market attractiveness score
            - Investment requirements
            - Expected returns and timeline

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES.
        Focus on ACTIONABLE INSIGHTS for startup success.""",
        
        "Financial Model": """Analyze this financial document and provide QUANTIFIED insights:

        1. REVENUE STREAMS & PROJECTIONS
           - Revenue breakdown by stream
           - Growth rates and projections
           - Seasonality and trends
        2. COST STRUCTURE & EFFICIENCY
           - Fixed vs variable costs
           - Cost optimization opportunities
           - Scaling cost implications
        3. UNIT ECONOMICS & PROFITABILITY
           - LTV, CAC, and payback period
           - Gross and net margins
           - Unit economics by segment
        4. GROWTH PROJECTIONS & SCALABILITY
           - Revenue growth rates (monthly/quarterly)
           - Customer growth projections
           - Scaling milestones and metrics
        5. KEY FINANCIAL METRICS & KPIs
           - Burn rate and runway
           - Revenue per customer
           - Customer acquisition efficiency
        6. CASH FLOW ANALYSIS & MANAGEMENT
           - Cash flow projections
           - Working capital requirements
           - Cash management strategies
        7. FUNDING REQUIREMENTS & STRATEGY
           - Funding needs with timeline
           - Use of funds breakdown
           - Funding milestones
        8. BREAK-EVEN ANALYSIS & PROFITABILITY
           - Break-even timeline
           - Profitability projections
           - Key profitability drivers
        9. FINANCIAL RISKS & MITIGATION
           - Risk factors with probability
           - Financial stress testing
           - Risk mitigation strategies
        10. INVESTMENT HIGHLIGHTS & RETURNS
            - Investment attractiveness
            - Expected returns and timeline
            - Exit strategy considerations

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES.
        Focus on FINANCIAL VIABILITY and INVESTMENT POTENTIAL."""
    }

    prompt = f"""
    You are an expert startup analyst and venture capitalist with 15+ years of experience. 
    Analyze this document and provide ACTIONABLE, QUANTIFIED insights that help founders understand:
    1. How their startup will STAND OUT from competitors
    2. Specific NUMBERS and METRICS for growth
    3. SCALABILITY potential with concrete milestones
    4. INVESTMENT attractiveness with quantified returns

    Document Content:
    {text}

    {analysis_prompts.get(document_type, analysis_prompts["Pitch Deck"])}

    IMPORTANT: 
    - Provide SPECIFIC NUMBERS (e.g., "20% market share by 2026", "30% cost reduction")
    - Include COMPETITIVE ADVANTAGES with metrics
    - Give ACTIONABLE recommendations with timelines
    - Focus on SCALABILITY and INVESTMENT potential
    - Use industry benchmarks and realistic projections
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return {"analysis": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...),
    document_type: str = "Pitch Deck"  # Default type
):
    """Upload and automatically analyze startup document"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract and analyze text
        pdf_text = extract_text_from_pdf(file_path)
        if not pdf_text:
            raise HTTPException(status_code=500, detail="Could not extract text from document")
        
        # Get analysis
        analysis = analyze_startup_document(pdf_text, document_type)
        
        # Store analysis in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analysis_history (filename, document_type, analysis_data)
            VALUES (?, ?, ?)
        ''', (file.filename, document_type, json.dumps(analysis["analysis"])))
        
        # Update metrics
        cursor.execute('''
            INSERT INTO user_metrics (document_type, analysis_count, last_analyzed)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (document_type) 
            DO UPDATE SET 
                analysis_count = user_metrics.analysis_count + 1,
                last_analyzed = CURRENT_TIMESTAMP
        ''', (document_type,))
        
        # Get the inserted ID
        analysis_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return {
            "filename": file.filename,
            "document_type": document_type,
            "analysis": analysis["analysis"],
            "analysis_id": analysis_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "name": "Startup Document Analyzer",
        "description": "AI-powered analysis with quantified insights",
        "endpoints": {
            "/upload-pdf/": "Upload and analyze startup documents",
            "/analytics/": "Get usage analytics",
            "/history/": "Get analysis history",
            "/health": "Health check for deployment monitoring"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Test database connection
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/analytics/")
async def get_analytics():
    """Get usage analytics and insights"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get document type distribution
    cursor.execute('''
        SELECT document_type, analysis_count 
        FROM user_metrics 
        ORDER BY analysis_count DESC
    ''')
    doc_types = cursor.fetchall()
    
    # Get total analyses
    cursor.execute('SELECT COUNT(*) FROM analysis_history')
    total_analyses = cursor.fetchone()[0]
    
    # Get recent activity (SQLite doesn't support INTERVAL, so we'll use a simple approach)
    cursor.execute('''
        SELECT COUNT(*) FROM analysis_history 
        WHERE created_at >= datetime('now', '-7 days')
    ''')
    recent_analyses = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_analyses": total_analyses,
        "recent_analyses_7_days": recent_analyses,
        "document_type_distribution": [
            {"type": doc_type, "count": count} 
            for doc_type, count in doc_types
        ]
    }

@app.get("/history/")
async def get_history(limit: int = 10):
    """Get recent analysis history"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT filename, document_type, created_at, id
        FROM analysis_history 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    history = cursor.fetchall()
    conn.close()
    
    return {
        "recent_analyses": [
            {
                "id": row[3],
                "filename": row[0],
                "document_type": row[1],
                "created_at": row[2]
            }
            for row in history
        ]
    }