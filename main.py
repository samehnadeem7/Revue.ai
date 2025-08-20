from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
import fitz  # PyMuPDF library
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, List

app = FastAPI(
    title="Startup Document Analyzer",
    description="Automatic startup document analysis"
)

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
genai.configure(api_key=api_key)

# Create uploads directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    """Analyze document based on type and return structured insights"""
    
    analysis_prompts = {
        "Pitch Deck": """Analyze this pitch deck and provide:
        1. Executive Summary (2-3 sentences)
        2. Value Proposition
        3. Market Opportunity (size, growth)
        4. Business Model
        5. Competition & Advantages
        6. Financial Highlights
        7. Team Strengths
        8. Investment Ask
        9. Risk Assessment
        10. Growth Strategy

        Format in clear sections with bullet points where relevant.""",
        
        "Business Plan": """Analyze this business plan and provide:
        1. Business Overview
        2. Market Analysis
        3. Product/Service Details
        4. Revenue Model
        5. Marketing Strategy
        6. Operations Plan
        7. Financial Projections
        8. Risk Analysis
        9. Implementation Timeline
        10. Success Metrics

        Format in clear sections with bullet points where relevant.""",
        
        "Market Research": """Analyze this market research and provide:
        1. Market Size & Growth
        2. Key Trends
        3. Customer Segments
        4. Competitor Landscape
        5. Market Drivers
        6. Entry Barriers
        7. Opportunities
        8. Threats
        9. Regulatory Factors
        10. Future Predictions

        Format in clear sections with bullet points where relevant.""",
        
        "Financial Model": """Analyze this financial document and provide:
        1. Revenue Streams
        2. Cost Structure
        3. Unit Economics
        4. Growth Projections
        5. Key Metrics
        6. Cash Flow Analysis
        7. Funding Requirements
        8. Break-even Analysis
        9. Financial Risks
        10. Investment Highlights

        Format in clear sections with bullet points where relevant."""
    }

    prompt = f"""
    You are an expert startup analyst. Analyze this document and provide structured insights:

    Document Content:
    {text}

    {analysis_prompts.get(document_type, analysis_prompts["Pitch Deck"])}
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
        
        return {
            "filename": file.filename,
            "document_type": document_type,
            "analysis": analysis["analysis"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "name": "Startup Document Analyzer",
        "description": "Automatic analysis of startup documents",
        "endpoint": "/upload-pdf/ (POST with PDF file and document_type)"
    }