from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import fitz  # PyMuPDF library
import openai
from dotenv import load_dotenv
from typing import Dict, List, Tuple
import re
import numpy as np
import sqlite3
from datetime import datetime
import json
import requests
from urllib.parse import urlparse, parse_qs

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

# Configure OpenAI API
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
openai.api_key = api_key

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

def analyze_startup_document(text: str, document_type: str = "Auto-Detect") -> Dict:
    """Analyze document based on type and return structured insights"""

    # Auto-detect document type based on content
    def detect_document_type(text: str) -> str:
        text_lower = text.lower()
        
        # Check for Google Forms indicators
        if any(keyword in text_lower for keyword in ["google forms", "form responses", "survey", "questionnaire", "feedback form"]):
            return "Google Forms Feedback"
        
        # Check for startup indicators
        startup_keywords = ["startup", "pitch", "business plan", "market", "revenue", "funding", "investor", "vc", "angel", "seed", "series a", "series b", "exit", "ipo", "acquisition"]
        if any(keyword in text_lower for keyword in startup_keywords):
            return "Startup Document"
        
        # Check for financial indicators
        financial_keywords = ["financial", "revenue", "profit", "cost", "margin", "cash flow", "balance sheet", "income statement", "ebitda", "roi"]
        if any(keyword in text_lower for keyword in financial_keywords):
            return "Financial Document"
        
        # Check for market research indicators
        market_keywords = ["market research", "competitor", "industry", "trend", "analysis", "survey", "customer", "demographic"]
        if any(keyword in text_lower for keyword in market_keywords):
            return "Market Research"
        
        return "Unknown Document"

    # Validate document content for startup analysis - More robust approach
    def validate_startup_content(text: str) -> bool:
        text_lower = text.lower()
        
        # Minimum content requirements - more lenient
        if len(text.strip()) < 50:
            return False
        
        # Check for business-related content - broader scope
        business_indicators = [
            "business", "company", "startup", "product", "service", "market", "customer", 
            "revenue", "strategy", "plan", "goal", "objective", "target", "growth",
            "feedback", "survey", "form", "response", "opinion", "suggestion", "improvement",
            "experience", "hackathon", "event", "participant", "user", "client", "feedback",
            "analysis", "research", "data", "insight", "trend", "opportunity", "challenge"
        ]
        
        business_score = sum(1 for indicator in business_indicators if indicator in text_lower)
        
        # Check for random/gibberish content - more specific
        random_indicators = [
            "lorem ipsum", "random text", "test document", "sample text", "placeholder",
            "asdf", "qwerty", "123456", "abcdef", "zzzzzz", "xxxxxx", "yyyyyy"
        ]
        
        random_score = sum(1 for indicator in random_indicators if indicator in text_lower)
        
        # More lenient validation - accept if minimal business content and very low random content
        return business_score >= 1 and random_score < 3

    # Auto-detect document type
    detected_type = detect_document_type(text)
    
    # Validate content for startup analysis
    if not validate_startup_content(text):
        raise HTTPException(
            status_code=400, 
            detail="Document content appears to be unrelated to business, feedback, or startup analysis. Please upload a document with business content, customer feedback, or startup-related information."
        )

    analysis_prompts = {
        "Google Forms Feedback": """Analyze this customer feedback and provide actionable startup insights:

        1. CUSTOMER INSIGHTS OVERVIEW (2-3 sentences with key metrics)
        2. FEEDBACK PATTERNS & TRENDS
           - Most common positive feedback themes
           - Most critical pain points identified
           - Customer satisfaction patterns
        3. PRODUCT/MARKET FIT ANALYSIS
           - How well the product meets customer needs
           - Market gaps and opportunities
           - Customer segment preferences
        4. IMPROVEMENT PRIORITIES
           - High-impact, low-effort improvements
           - Critical issues requiring immediate attention
           - Long-term enhancement opportunities
        5. CUSTOMER SENTIMENT ANALYSIS
           - Overall sentiment score and trends
           - Emotional triggers and pain points
           - Brand perception insights
        6. COMPETITIVE ADVANTAGE OPPORTUNITIES
           - Unique value propositions identified
           - Differentiation opportunities
           - Competitive positioning insights
        7. GROWTH STRATEGY & SCALING
           - Customer acquisition insights
           - Retention improvement strategies
           - Expansion opportunities
        8. FINAL GROWTH STRATEGY
           - 3-5 actionable steps to scale up
           - Priority order for implementation
           - Expected impact and timeline

        Focus on ACTIONABLE insights that drive growth and customer satisfaction.""",
        
        "Startup Document": """Analyze this startup document and provide QUANTIFIED insights:

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
        10. FINAL GROWTH STRATEGY
            - 3-5 specific steps to scale up
            - Priority order and timeline
            - Expected outcomes and metrics

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
        10. FINAL GROWTH STRATEGY
            - 3-5 actionable steps to scale up
            - Priority order and timeline
            - Expected outcomes and metrics

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
        10. FINAL GROWTH STRATEGY
            - 3-5 actionable steps to capitalize on opportunities
            - Priority order and timeline
            - Expected outcomes and metrics

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES.
        Focus on ACTIONABLE INSIGHTS for startup success.""",
        
        "Financial Document": """Analyze this financial document and provide QUANTIFIED insights:

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
        10. FINAL GROWTH STRATEGY
            - 3-5 actionable steps to improve financial performance
            - Priority order and timeline
            - Expected outcomes and metrics

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES.
        Focus on FINANCIAL VIABILITY and INVESTMENT POTENTIAL.""",
        
        "Unknown Document": """Analyze this document and provide startup-focused insights:

        1. DOCUMENT OVERVIEW (2-3 sentences identifying content type)
        2. BUSINESS RELEVANCE ASSESSMENT
           - How relevant is this to startup/business analysis?
           - Key business themes identified
           - Missing critical information
        3. CONTENT QUALITY & STRUCTURE
           - Information completeness
           - Data reliability indicators
           - Structural organization
        4. POTENTIAL INSIGHTS EXTRACTION
           - Actionable business insights
           - Market intelligence opportunities
           - Strategic implications
        5. LIMITATIONS & GAPS
           - Missing critical data
           - Unreliable information
           - Analysis constraints
        6. RECOMMENDATIONS
           - Additional information needed
           - Alternative analysis approaches
           - Next steps for better insights
        7. FINAL GROWTH STRATEGY
           - 3-5 actionable steps based on available information
           - Priority order and timeline
           - Expected outcomes and metrics

        Focus on what CAN be learned and what ADDITIONAL information is needed."""
    }

    # Use detected type or fallback to comprehensive analysis
    prompt_type = detected_type if detected_type in analysis_prompts else "Startup Document"
    
    # Template-based fallback analysis (when API is unavailable)
    def get_fallback_analysis(doc_type: str, content: str) -> str:
        """Provide template-based analysis when AI API is unavailable"""
        
        if doc_type == "Google Forms Feedback":
            return f"""
# 📊 Google Forms Analysis Report

## 🔍 FORM OVERVIEW
- **Document Type**: Google Forms Feedback
- **Content Length**: {len(content)} characters
- **Analysis Method**: Template-based (API unavailable)

## 📈 CUSTOMER INSIGHTS OVERVIEW
Based on the form structure and typical Google Forms patterns, here are the expected insights for startup growth.

## 🎯 FEEDBACK PATTERNS & TRENDS
- **Form Engagement**: Analyze response completion rates
- **Response Quality**: Monitor answer depth and detail
- **Time Patterns**: Identify peak response times

## 🚀 PRODUCT/MARKET FIT ANALYSIS
- **Customer Needs**: Extract pain points and desires
- **Market Validation**: Assess product-market fit signals
- **Segment Preferences**: Identify target customer groups

## ⚡ IMPROVEMENT PRIORITIES
- **High-Impact Changes**: Focus on customer-requested features
- **Critical Issues**: Address immediate pain points
- **Long-term Strategy**: Plan for sustainable growth

## 💡 CUSTOMER SENTIMENT ANALYSIS
- **Overall Satisfaction**: Track sentiment trends
- **Emotional Triggers**: Identify what drives engagement
- **Brand Perception**: Monitor customer brand sentiment

## 🏆 COMPETITIVE ADVANTAGE OPPORTUNITIES
- **Unique Features**: Highlight differentiation points
- **Market Gaps**: Identify underserved customer needs
- **Positioning**: Strengthen competitive positioning

## 📊 GROWTH STRATEGY & SCALING
- **Customer Acquisition**: Optimize acquisition channels
- **Retention**: Improve customer loyalty strategies
- **Expansion**: Identify new market opportunities

## 🎯 FINAL GROWTH STRATEGY
1. **Immediate Actions** (Next 30 days)
   - Analyze form responses for quick wins
   - Implement high-impact improvements
   - Set up response monitoring

2. **Short-term Goals** (3-6 months)
   - Optimize form structure based on feedback
   - Implement customer-requested features
   - Establish feedback collection processes

3. **Long-term Vision** (6-12 months)
   - Scale successful feedback mechanisms
   - Expand to new customer segments
   - Build data-driven decision culture

---
*Note: This is a template analysis. For detailed AI-powered insights, ensure your Google API key has available quota.*
            """
        
        elif doc_type == "Startup Document":
            return f"""
# 🚀 Startup Document Analysis Report

## 🔍 DOCUMENT OVERVIEW
- **Document Type**: Startup Document
- **Content Length**: {len(content)} characters
- **Analysis Method**: Template-based (API unavailable)

## 📊 EXECUTIVE SUMMARY
This startup document has been analyzed for key growth indicators and strategic insights.

## 💎 VALUE PROPOSITION & COMPETITIVE ADVANTAGE
- **Unique Selling Points**: Identify what makes this startup stand out
- **Competitive Analysis**: Assess differentiation from competitors
- **Market Positioning**: Evaluate strategic market position

## 🌍 MARKET OPPORTUNITY
- **Market Size**: Assess TAM, SAM, SOM potential
- **Growth Trends**: Identify market growth drivers
- **Target Segments**: Define primary customer groups

## 💰 BUSINESS MODEL & REVENUE
- **Revenue Streams**: Analyze multiple income sources
- **Unit Economics**: Evaluate LTV, CAC, and margins
- **Scalability**: Assess growth potential

## 🏆 COMPETITIVE LANDSCAPE
- **Competitor Analysis**: Identify key competitors
- **Advantage Assessment**: Evaluate competitive strengths
- **Market Entry**: Assess entry barriers and timing

## 📈 FINANCIAL PROJECTIONS
- **Revenue Forecasts**: Review 3-5 year projections
- **Growth Metrics**: Analyze monthly/quarterly trends
- **Key Ratios**: Evaluate financial health indicators

## 👥 TEAM & EXECUTION
- **Team Strengths**: Assess execution capabilities
- **Experience Relevance**: Evaluate industry expertise
- **Resource Allocation**: Review team structure

## 💼 INVESTMENT & FUNDING
- **Funding Requirements**: Assess capital needs
- **Use of Funds**: Review allocation strategy
- **Milestone Planning**: Define funding milestones

## ⚠️ RISK ASSESSMENT
- **Key Risks**: Identify primary risk factors
- **Mitigation Strategies**: Review risk management
- **Contingency Planning**: Assess backup plans

## 🎯 FINAL GROWTH STRATEGY
1. **Immediate Actions** (Next 30 days)
   - Validate key assumptions
   - Secure initial customer feedback
   - Establish key metrics tracking

2. **Short-term Goals** (3-6 months)
   - Achieve product-market fit
   - Build initial customer base
   - Establish operational processes

3. **Long-term Vision** (6-12 months)
   - Scale successful operations
   - Expand market presence
   - Prepare for funding rounds

---
*Note: This is a template analysis. For detailed AI-powered insights, ensure your Google API key has available quota.*
            """
        
        else:
            return f"""
# 📄 Document Analysis Report

## 🔍 DOCUMENT OVERVIEW
- **Document Type**: {doc_type}
- **Content Length**: {len(content)} characters
- **Analysis Method**: Template-based (API unavailable)

## 📊 BUSINESS RELEVANCE ASSESSMENT
This document has been analyzed for startup and business relevance.

## 🎯 KEY INSIGHTS
- **Content Quality**: Assess information completeness
- **Business Value**: Identify actionable insights
- **Strategic Implications**: Evaluate business impact

## 🚀 GROWTH OPPORTUNITIES
- **Market Insights**: Extract market intelligence
- **Customer Understanding**: Identify customer needs
- **Competitive Intelligence**: Assess market positioning

## 📈 ACTION ITEMS
- **Immediate Actions**: Quick wins and improvements
- **Strategic Planning**: Long-term growth initiatives
- **Resource Allocation**: Optimize resource usage

## 🎯 FINAL GROWTH STRATEGY
1. **Quick Wins** (Next 2 weeks)
   - Implement immediate improvements
   - Address low-hanging opportunities
   - Set up monitoring systems

2. **Strategic Initiatives** (1-3 months)
   - Develop comprehensive growth plan
   - Align team and resources
   - Establish success metrics

3. **Long-term Vision** (3-12 months)
   - Scale successful strategies
   - Expand market presence
   - Build sustainable competitive advantage

---
*Note: This is a template analysis. For detailed AI-powered insights, ensure your Google API key has available quota.*
            """

    # Try AI analysis first, fallback to template if API fails
    try:
        # Enhanced RAG implementation with better error handling
        def chunk_text(input_text: str, max_chars: int = 1500) -> List[str]:
            paragraphs = re.split(r"\n\s*\n", input_text)
            chunks: List[str] = []
            current: List[str] = []
            current_len = 0
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if current_len + len(para) + 1 > max_chars and current:
                    chunks.append("\n".join(current))
                    current = [para]
                    current_len = len(para)
                else:
                    current.append(para)
                    current_len += len(para) + 1
            if current:
                chunks.append("\n".join(current))
            # Fallback if text was not separable
            if not chunks:
                for i in range(0, len(input_text), max_chars):
                    chunks.append(input_text[i:i + max_chars])
            return chunks

        def embed_text(content: str) -> np.ndarray:
            try:
                response = openai.Embedding.create(
                    model="text-embedding-ada-002",
                    input=content
                )
                embedding = response['data'][0]['embedding']
                return np.array(embedding, dtype=float)
            except Exception as e:
                raise RuntimeError(f"Failed to get embedding: {str(e)}")

        def cosine_similarity(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
            vector_norm = np.linalg.norm(vector) + 1e-10
            matrix_norms = np.linalg.norm(matrix, axis=1) + 1e-10
            return (matrix @ vector) / (matrix_norms * vector_norm)

        def parse_section_queries(prompt_text: str) -> List[str]:
            lines = [line.strip() for line in prompt_text.strip().split("\n")]
            queries: List[str] = []
            for line in lines:
                # Capture numbered headings like 1., 4.1, 4.1. etc.
                if re.match(r"^\d+(?:\.\d+)*\.?\s+", line):
                    clean = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", line)
                    if clean:
                        queries.append(clean)
            # Fallback if parsing fails
            if not queries:
                queries = [
                    "Document Overview",
                    "Business Relevance",
                    "Key Insights",
                    "Market Analysis",
                    "Growth Opportunities",
                    "Action Items",
                    "Final Growth Strategy",
                ]
            return queries

        # Build RAG store: chunk -> embedding
        chunks = chunk_text(text, max_chars=1500)
        chunk_embeddings = []
        for chunk in chunks:
            try:
                chunk_embeddings.append(embed_text(chunk))
            except Exception:
                # If any chunk embedding fails, skip that chunk
                continue
        if not chunk_embeddings:
            # Fallback: if embeddings failed entirely, use original non-RAG prompt
            business_analyst_prompt = f"""
You are a seasoned startup analyst and business consultant. Provide structured, practical insights with bullet points, citing specific evidence from the document when possible. If information is missing, state "Not found". Focus on actionable growth strategies.

IMPORTANT: Write in a professional, business-focused tone. Use minimal emojis and maintain a formal yet accessible style suitable for startup founders and investors.

Document Content:
{text}

{analysis_prompts.get(prompt_type, analysis_prompts["Startup Document"]) }
"""
            model = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": business_analyst_prompt}]
            )
            return {"analysis": model.choices[0].message.content}

        embeddings_matrix = np.vstack(chunk_embeddings)

        # Build per-section retrieval
        section_names = parse_section_queries(analysis_prompts.get(prompt_type, list(analysis_prompts.values())[0]))
        section_to_context: List[Tuple[str, str]] = []
        for section in section_names:
            try:
                query_vec = embed_text(section)
                sims = cosine_similarity(embeddings_matrix, query_vec)
                top_indices = np.argsort(-sims)[:3]
                retrieved = []
                for idx in top_indices:
                    # Guard against mismatches if some chunks failed to embed
                    if 0 <= idx < len(chunks):
                        retrieved.append(f"[Chunk {int(idx)+1}]\n{chunks[int(idx)]}")
                context = "\n\n".join(retrieved)
                section_to_context.append((section, context))
            except Exception:
                section_to_context.append((section, ""))

        rag_context_lines = []
        for section, context in section_to_context:
            rag_context_lines.append(f"### {section}\n{context if context else 'No relevant content found.'}")
        rag_context = "\n\n".join(rag_context_lines)

        # Compose final prompt with RAG context and startup-analyst persona
        prompt = f"""
You are a seasoned startup analyst and business consultant with 15+ years of experience. Using ONLY the provided RAG Context, produce a concise, structured analysis with clear section headers and bullet points where helpful. If a section lacks evidence in the RAG Context, write "Not found" for that section. Do not invent facts.

IMPORTANT: Write in a professional, business-focused tone. Use minimal emojis and maintain a formal yet accessible style suitable for startup founders and investors.

Focus on ACTIONABLE insights that help founders:
1. Scale their startup
2. Correct mistakes
3. Identify growth opportunities
4. Make data-driven decisions

RAG Context (retrieved chunks per section):
{rag_context}

Task:
{analysis_prompts.get(prompt_type, list(analysis_prompts.values())[0]) }
"""

        model = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return {"analysis": model.choices[0].message.content}
        
    except Exception as e:
        # If AI analysis fails (rate limit, API error, etc.), use template fallback
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            # API rate limit hit - use template analysis
            fallback_analysis = get_fallback_analysis(detected_type, text)
            return {"analysis": fallback_analysis, "api_status": "rate_limited", "fallback": True}
        else:
            # Other API error - still use template but indicate the issue
            fallback_analysis = get_fallback_analysis(detected_type, text)
            return {"analysis": fallback_analysis, "api_status": "error", "fallback": True, "error": error_msg}

@app.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...)
):
    """Upload and automatically analyze startup document (auto-detects type)"""
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
        
        # Auto-detect document type and get analysis
        analysis = analyze_startup_document(pdf_text)
        
        # Extract detected document type from analysis
        detected_type = "Auto-Detected"
        
        # Store analysis in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analysis_history (filename, document_type, analysis_data)
            VALUES (?, ?, ?)
        ''', (file.filename, detected_type, json.dumps(analysis["analysis"])))
        
        # Update metrics
        cursor.execute('''
            INSERT INTO user_metrics (document_type, analysis_count, last_analyzed)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (document_type) 
            DO UPDATE SET 
                analysis_count = user_metrics.analysis_count + 1,
                last_analyzed = CURRENT_TIMESTAMP
        ''', (detected_type,))
        
        # Get the inserted ID
        analysis_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return {
            "filename": file.filename,
            "document_type": detected_type,
            "analysis": analysis["analysis"],
            "analysis_id": analysis_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert-google-form/")
async def convert_google_form(
    form_url: str = Form(...),
    form_title: str = Form("Untitled Form")
):
    """Convert Google Forms to PDF and analyze responses"""
    
    try:
        # Extract form ID from Google Forms URL
        parsed_url = urlparse(form_url)
        if "forms.gle" in parsed_url.netloc:
            # Handle shortened URLs
            response = requests.get(form_url, allow_redirects=True)
            form_url = response.url
            parsed_url = urlparse(form_url)
        
        # Extract form ID from various Google Forms URL formats
        form_id = None
        if "docs.google.com/forms" in form_url:
            # Standard Google Forms URL
            path_parts = parsed_url.path.split('/')
            if 'forms' in path_parts:
                form_index = path_parts.index('forms')
                if form_index + 1 < len(path_parts):
                    form_id = path_parts[form_index + 1]
        
        if not form_id:
            raise HTTPException(
                status_code=400, 
                detail="Invalid Google Forms URL. Please provide a valid Google Forms link."
            )
        
        # Create a mock PDF content based on form analysis
        # In a production system, you'd use Google Forms API to get actual responses
        pdf_content = f"""
Google Forms Analysis Report
Form Title: {form_title}
Form ID: {form_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ANALYSIS SUMMARY:
This Google Form has been processed and analyzed for startup insights.

FORM METADATA:
- Form URL: {form_url}
- Form ID: {form_id}
- Analysis Date: {datetime.now().strftime('%Y-%m-%d')}

CUSTOMER FEEDBACK INSIGHTS:
Based on the form structure and typical Google Forms patterns, here are the expected insights:

1. RESPONSE PATTERNS:
   - Form engagement metrics
   - Response completion rates
   - Time-based response trends

2. FEEDBACK THEMES:
   - Customer satisfaction indicators
   - Product improvement suggestions
   - Market validation signals

3. GROWTH OPPORTUNITIES:
   - Customer pain points identification
   - Feature request prioritization
   - Market gap analysis

Note: This is a template analysis. For detailed insights, the form should contain actual response data.
        """
        
        # Create a temporary PDF file
        temp_pdf_path = os.path.join(UPLOAD_DIR, f"google_form_{form_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        # Create PDF using PyMuPDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), pdf_content, fontsize=12)
        doc.save(temp_pdf_path)
        doc.close()
        
        # Analyze the generated content
        analysis = analyze_startup_document(pdf_content, "Google Forms Feedback")
        
        # Store analysis in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analysis_history (filename, document_type, analysis_data)
            VALUES (?, ?, ?)
        ''', (f"Google Form: {form_title}", "Google Forms Feedback", json.dumps(analysis["analysis"])))
        
        # Update metrics
        cursor.execute('''
            INSERT INTO user_metrics (document_type, analysis_count, last_analyzed)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (document_type) 
            DO UPDATE SET 
                analysis_count = user_metrics.analysis_count + 1,
                last_analyzed = CURRENT_TIMESTAMP
        ''', ("Google Forms Feedback",))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "filename": f"Google Form: {form_title}",
            "document_type": "Google Forms Feedback",
            "analysis": analysis["analysis"],
            "analysis_id": analysis_id,
            "form_url": form_url,
            "form_id": form_id
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