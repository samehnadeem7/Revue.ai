from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import fitz  # PyMuPDF library
import google.generativeai
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

# Configure Google Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
google.generativeai.configure(api_key=api_key)

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
            "analysis", "research", "data", "insight", "trend", "opportunity", "challenge",
            "innovation", "technology", "digital", "online", "app", "platform", "solution",
            "problem", "need", "pain", "benefit", "value", "quality", "performance",
            "team", "leadership", "management", "process", "workflow", "efficiency",
            "cost", "price", "investment", "funding", "profit", "loss", "margin",
            "competition", "competitive", "advantage", "differentiation", "positioning",
            "brand", "marketing", "sales", "customer service", "support", "help",
            "review", "rating", "satisfaction", "happiness", "success", "failure",
            "learning", "education", "training", "development", "improvement", "optimization"
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
        "Google Forms Feedback": """Analyze this customer feedback and provide comprehensive, actionable startup insights with detailed analysis:

        1. CUSTOMER INSIGHTS OVERVIEW (Detailed analysis with specific metrics)
           - Total response volume and completion rates with numerical breakdown
           - Key demographic or segment insights with specific examples
           - Overall sentiment score (1-10 scale) with trend analysis
           - Response quality indicators and data reliability assessment
           - Customer engagement patterns and response timing analysis

        2. FEEDBACK PATTERNS & TRENDS (Comprehensive analysis with examples)
           - Most common positive feedback themes with specific quotes and frequency
           - Most critical pain points identified with impact assessment and priority ranking
           - Customer satisfaction patterns across different segments with detailed breakdown
           - Response time patterns and engagement metrics with actionable insights
           - Seasonal or time-based trends in feedback with correlation analysis
           - Customer behavior patterns and decision-making factors

        3. PRODUCT/MARKET FIT ANALYSIS (Quantified insights with examples)
           - How well the product meets customer needs with specific examples and metrics
           - Market gaps and underserved customer segments with size estimates
           - Customer segment preferences and priorities with detailed breakdown
           - Feature adoption and usage patterns with success metrics
           - Customer journey pain points and friction areas with impact assessment
           - Market validation signals and product-market fit indicators

        4. IMPROVEMENT PRIORITIES (Comprehensive roadmap with ROI)
           - High-impact, low-effort improvements with expected ROI and timeline
           - Critical issues requiring immediate attention with risk assessment and urgency
           - Long-term enhancement opportunities with strategic roadmap and milestones
           - Customer-requested features prioritized by demand and business impact
           - Technical debt and infrastructure improvements with cost-benefit analysis
           - Process optimization opportunities with efficiency gains

        5. CUSTOMER SENTIMENT ANALYSIS (Deep dive with emotional intelligence)
           - Overall sentiment score and trends over time with detailed analysis
           - Emotional triggers and pain points with specific examples and context
           - Brand perception insights and reputation indicators with trend analysis
           - Customer loyalty signals and churn risk factors with probability assessment
           - Sentiment variations across different customer segments with demographic insights
           - Customer satisfaction drivers and engagement factors

        6. COMPETITIVE ADVANTAGE OPPORTUNITIES (Strategic insights with examples)
           - Unique value propositions identified from feedback with competitive analysis
           - Differentiation opportunities and market positioning with strategic recommendations
           - Competitive positioning insights and gaps with market analysis
           - Customer switching barriers and retention factors with strength assessment
           - Innovation opportunities based on customer needs with implementation roadmap
           - Market positioning strategies and competitive moats

        7. GROWTH STRATEGY & SCALING (Comprehensive execution plan)
           - Customer acquisition insights and channel optimization with performance metrics
           - Retention improvement strategies and loyalty programs with success indicators
           - Expansion opportunities and new market segments with entry strategy
           - Pricing strategy insights and optimization with elasticity analysis
           - Partnership and collaboration opportunities with strategic fit assessment
           - International expansion potential with market readiness analysis

        8. FINAL GROWTH STRATEGY (Detailed action plan with implementation)
           - Immediate actions (Next 30 days) with specific tasks, owners, and timelines
           - Short-term goals (3-6 months) with measurable milestones and success criteria
           - Long-term vision (6-12 months) with strategic objectives and KPIs
           - Resource requirements and investment needs with detailed breakdown
           - Risk mitigation strategies and contingency plans with probability assessment
           - Expected outcomes and ROI projections with measurement framework
           - Success metrics and performance indicators for tracking progress

        CRITICAL REQUIREMENTS: Provide comprehensive, detailed analysis for each section. Include specific examples, numbers, actionable insights, and implementation details. Address edge cases, potential challenges, and alternative scenarios. Focus on insights that drive measurable growth and customer satisfaction improvements. Each section should contain 200-400 words of detailed analysis.""",
        
        "Startup Document": """Analyze this startup document and provide comprehensive, quantified insights with strategic depth:

        1. EXECUTIVE SUMMARY (4-5 sentences with key metrics and positioning)
           - Core value proposition in one sentence
           - Market opportunity size and growth potential
           - Competitive positioning and differentiation
           - Key success factors and risk factors
           - Investment potential and funding readiness

        2. VALUE PROPOSITION & COMPETITIVE ADVANTAGE (Detailed analysis)
           - What makes this startup unique? (specific features and benefits)
           - How will it stand out from competitors? (detailed comparison)
           - Quantified benefits (e.g., "30% cost reduction", "5x faster", "2x ROI")
           - Intellectual property and defensibility factors
           - Scalability and replication potential
           - Customer acquisition and retention advantages

        3. MARKET OPPORTUNITY (Comprehensive market analysis)
           - Market size breakdown: TAM, SAM, SOM with specific numbers
           - Growth rate (CAGR) and market evolution trends
           - Target market segments with sizes and characteristics
           - Market entry timing and window of opportunity
           - Regulatory environment and compliance requirements
           - Market maturity and adoption curve position

        4. BUSINESS MODEL & REVENUE PROJECTIONS (Financial deep dive)
           - Revenue streams with projected amounts and growth rates
           - Unit economics: LTV, CAC, payback period, margins
           - Break-even timeline and profitability projections
           - Pricing strategy and price elasticity analysis
           - Customer acquisition and retention economics
           - Revenue diversification and risk mitigation

        5. COMPETITIVE LANDSCAPE & DIFFERENTIATION (Strategic positioning)
           - Top 3-5 competitors with market share and positioning
           - Competitive advantages with specific metrics and evidence
           - Market positioning strategy and brand differentiation
           - Competitive response scenarios and counter-strategies
           - Barriers to entry and competitive moats
           - Partnership and collaboration opportunities

        6. FINANCIAL HIGHLIGHTS & PROJECTIONS (Comprehensive financial analysis)
           - Revenue projections (3-5 years) with monthly/quarterly breakdowns
           - Growth rates and seasonal patterns
           - Key financial metrics and ratios
           - Cash flow projections and working capital requirements
           - Funding requirements and use of funds
           - Exit strategy and valuation projections

        7. TEAM STRENGTHS & EXECUTION CAPABILITY (Human capital analysis)
           - Team composition and key personnel backgrounds
           - Relevant experience and industry expertise
           - Execution track record and capabilities
           - Team scalability and hiring plans
           - Advisory board and network strength
           - Cultural fit and team dynamics

        8. INVESTMENT ASK & USE OF FUNDS (Funding strategy)
           - Funding amount and valuation justification
           - Use of funds breakdown with specific allocations
           - Milestone-based funding approach
           - Investor value proposition and returns
           - Exit timeline and strategy
           - Risk factors and mitigation strategies

        9. RISK ASSESSMENT & MITIGATION (Comprehensive risk analysis)
           - Market risks with probability and impact assessment
           - Technology risks and technical debt
           - Team risks and key person dependencies
           - Financial risks and cash flow challenges
           - Regulatory and compliance risks
           - Mitigation strategies and contingency plans

        10. FINAL GROWTH STRATEGY (Detailed execution roadmap)
            - Immediate actions (Next 30 days) with specific tasks, owners, and timelines
            - Short-term goals (3-6 months) with measurable milestones
            - Long-term vision (6-12 months) with strategic objectives
            - Resource requirements and investment needs
            - Risk mitigation strategies and contingency plans
            - Expected outcomes and ROI projections
            - Success metrics and KPIs for tracking progress

        IMPORTANT: Provide SPECIFIC NUMBERS, PERCENTAGES, TIMELINES, and ACTIONABLE insights. If information is missing, state "Not found" and explain what additional data would be valuable. Focus on how this startup will STAND OUT, SCALE, and achieve sustainable competitive advantage. Include edge cases and potential challenges that could impact success.""",
        
        "Business Plan": """Analyze this business plan and provide comprehensive, quantified insights with strategic depth:

        1. BUSINESS OVERVIEW & VALUE PROPOSITION (Strategic positioning)
           - Unique selling points with specific metrics and evidence
           - Competitive advantages quantified and validated
           - Market positioning and brand differentiation
           - Core competencies and strategic capabilities
           - Business model innovation and sustainability

        2. MARKET ANALYSIS & OPPORTUNITY (Comprehensive market intelligence)
           - Market size with specific numbers and growth projections
           - Growth rates, trends, and market evolution drivers
           - Target segments with sizes, characteristics, and behaviors
           - Market entry timing and competitive landscape
           - Regulatory environment and compliance requirements
           - Market maturity and adoption curve analysis

        3. PRODUCT/SERVICE DETAILS & DIFFERENTIATION (Feature analysis)
           - Key features with quantified benefits and user impact
           - How it stands out from alternatives (detailed comparison)
           - Technology stack and technical advantages
           - Scalability and performance characteristics
           - User experience and design differentiation
           - Quality assurance and reliability factors

        4. REVENUE MODEL & PROJECTIONS (Financial strategy)
           - Revenue streams with amounts and growth projections
           - Pricing strategy and price elasticity analysis
           - 3-5 year projections with monthly/quarterly breakdowns
           - Customer acquisition and retention economics
           - Revenue diversification and risk mitigation
           - International expansion and market penetration

        5. MARKETING STRATEGY & ACQUISITION (Growth marketing)
           - Customer acquisition channels with CAC analysis
           - Conversion rates and funnel optimization
           - Growth marketing tactics and viral mechanisms
           - Brand building and market positioning
           - Customer segmentation and targeting
           - Marketing ROI and efficiency metrics

        6. OPERATIONS PLAN & SCALABILITY (Operational excellence)
           - Operational efficiency metrics and benchmarks
           - Scaling bottlenecks and solutions
           - Supply chain and vendor management
           - Quality control and process optimization
           - Technology infrastructure and automation
           - International expansion and localization

        7. FINANCIAL PROJECTIONS & METRICS (Comprehensive financial analysis)
           - Revenue, costs, and profitability projections
           - Key ratios and financial health indicators
           - Cash flow projections and working capital
           - Break-even analysis and sensitivity testing
           - Funding requirements and use of funds
           - Exit strategy and valuation projections

        8. RISK ANALYSIS & MITIGATION (Risk management)
           - Top risks with probability and impact assessment
           - Mitigation strategies and contingency plans
           - Market risks and competitive threats
           - Technology risks and technical challenges
           - Financial risks and cash flow challenges
           - Regulatory and compliance risks

        9. IMPLEMENTATION TIMELINE & MILESTONES (Execution roadmap)
           - Key milestones with specific dates and deliverables
           - Success metrics for each phase
           - Resource allocation and team requirements
           - Critical path analysis and dependencies
           - Risk mitigation timeline
           - Quality gates and validation checkpoints

        10. FINAL GROWTH STRATEGY (Comprehensive execution plan)
            - Immediate actions (Next 30 days) with specific tasks, owners, and timelines
            - Short-term goals (3-6 months) with measurable milestones
            - Long-term vision (6-12 months) with strategic objectives
            - Resource requirements and investment needs
            - Risk mitigation strategies and contingency plans
            - Expected outcomes and ROI projections
            - Success metrics and KPIs for tracking progress

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES. Focus on EXECUTION, SCALABILITY, and MEASURABLE SUCCESS. Include edge cases, potential challenges, and alternative scenarios that could impact business success.""",
        
        "Market Research": """Analyze this market research and provide comprehensive, quantified insights with strategic depth:

        1. MARKET SIZE & GROWTH METRICS (Comprehensive market quantification)
           - TAM, SAM, SOM with specific numbers and methodology
           - CAGR and growth drivers with impact analysis
           - Regional breakdowns and geographic opportunities
           - Market maturity and evolution stages
           - Seasonal patterns and cyclical factors
           - Market segmentation and niche opportunities

        2. KEY TRENDS & OPPORTUNITIES (Emerging market intelligence)
           - Emerging trends with adoption rates and timing
           - Market gaps and underserved customer needs
           - Technology adoption curves and disruption potential
           - Regulatory changes and policy impacts
           - Consumer behavior shifts and preferences
           - Industry convergence and collaboration opportunities

        3. CUSTOMER SEGMENTS & BEHAVIOR (Deep customer insights)
           - Segment sizes and characteristics with detailed profiles
           - Customer acquisition costs and lifetime value
           - Customer behavior patterns and decision-making factors
           - Pain points and unmet needs by segment
           - Customer journey and touchpoint analysis
           - Brand loyalty and switching behavior

        4. COMPETITOR LANDSCAPE & POSITIONING (Competitive intelligence)
           - Market share of top competitors with trends
           - Competitive advantages and weaknesses analysis
           - Positioning opportunities and differentiation strategies
           - Competitive response scenarios and strategies
           - Market entry barriers and competitive moats
           - Partnership and collaboration opportunities

        5. MARKET DRIVERS & BARRIERS (Growth and constraint analysis)
           - Growth drivers with impact metrics and timing
           - Entry barriers and costs with mitigation strategies
           - Regulatory requirements and compliance costs
           - Technology adoption barriers and facilitators
           - Economic factors and market sensitivity
           - Social and cultural factors

        6. OPPORTUNITIES & THREATS (Strategic risk-reward analysis)
           - Market opportunities with sizes and timing
           - Threat assessment and probability analysis
           - Risk-reward analysis and prioritization
           - Emerging competitive threats
           - Market disruption scenarios
           - Regulatory and policy risks

        7. REGULATORY & COMPLIANCE FACTORS (Compliance landscape)
           - Regulatory requirements and compliance costs
           - Compliance timeline and resource requirements
           - International regulatory differences
           - Policy changes and their impact
           - Compliance risk mitigation strategies
           - Regulatory advantage opportunities

        8. FUTURE PREDICTIONS & FORECASTS (Strategic foresight)
           - Market evolution predictions with scenarios
           - Technology adoption curves and disruption timing
           - Competitive landscape changes and consolidation
           - Regulatory evolution and policy trends
           - Consumer behavior evolution and preferences
           - Industry convergence and collaboration trends

        9. ENTRY STRATEGY & TIMING (Market entry planning)
           - Optimal entry timing with market readiness assessment
           - Market entry costs and timeline with milestones
           - Success probability factors and risk assessment
           - Entry strategy options and recommendations
           - Market penetration approach and tactics
           - International expansion opportunities

        10. FINAL GROWTH STRATEGY (Comprehensive action plan)
            - 3-5 actionable steps to capitalize on opportunities
            - Priority order and timeline with specific milestones
            - Expected outcomes and metrics for success
            - Resource requirements and investment needs
            - Risk mitigation strategies and contingency plans
            - Success metrics and KPIs for tracking progress
            - Market monitoring and adaptation strategies

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES. Focus on ACTIONABLE INSIGHTS for startup success. Include edge cases, market uncertainties, and alternative scenarios that could impact market entry and growth strategies.""",
        
        "Financial Document": """Analyze this financial document and provide comprehensive, quantified insights with strategic depth:

        1. REVENUE STREAMS & PROJECTIONS (Revenue analysis)
           - Revenue breakdown by stream with growth rates
           - Growth rates and projections with seasonal patterns
           - Seasonality and trends with cyclical analysis
           - Revenue quality and sustainability factors
           - Customer concentration and dependency risks
           - International revenue and currency exposure

        2. COST STRUCTURE & EFFICIENCY (Cost optimization)
           - Fixed vs variable costs with break-even analysis
           - Cost optimization opportunities and savings potential
           - Scaling cost implications and economies of scale
           - Cost structure benchmarking and industry comparison
           - Operational efficiency metrics and improvements
           - Technology automation and cost reduction potential

        3. UNIT ECONOMICS & PROFITABILITY (Unit analysis)
           - LTV, CAC, and payback period with trends
           - Gross and net margins with industry benchmarks
           - Unit economics by segment and customer type
           - Profitability drivers and optimization opportunities
           - Break-even analysis and sensitivity testing
           - Margin expansion potential and strategies

        4. GROWTH PROJECTIONS & SCALABILITY (Growth analysis)
           - Revenue growth rates (monthly/quarterly) with drivers
           - Customer growth projections and acquisition strategies
           - Scaling milestones and metrics with timelines
           - Growth constraints and bottleneck identification
           - International expansion and market penetration
           - Product expansion and diversification opportunities

        5. KEY FINANCIAL METRICS & KPIs (Performance indicators)
           - Burn rate and runway with funding requirements
           - Revenue per customer and customer efficiency
           - Customer acquisition efficiency and optimization
           - Working capital requirements and management
           - Cash conversion cycle and efficiency
           - Return on investment and capital efficiency

        6. CASH FLOW ANALYSIS & MANAGEMENT (Cash management)
           - Cash flow projections with scenario analysis
           - Working capital requirements and optimization
           - Cash management strategies and investment policies
           - Seasonal cash flow patterns and management
           - International cash flow and currency management
           - Cash flow risk mitigation and contingency planning

        7. FUNDING REQUIREMENTS & STRATEGY (Funding analysis)
           - Funding needs with timeline and milestones
           - Use of funds breakdown with ROI projections
           - Funding milestones and success criteria
           - Funding sources and investor value proposition
           - Debt vs equity financing analysis
           - International funding and investor landscape

        8. BREAK-EVEN ANALYSIS & PROFITABILITY (Profitability analysis)
           - Break-even timeline with sensitivity analysis
           - Profitability projections and drivers
           - Key profitability drivers and optimization
           - Profitability by segment and product line
           - Profitability benchmarking and industry comparison
           - Long-term profitability sustainability

        9. FINANCIAL RISKS & MITIGATION (Risk management)
           - Risk factors with probability and impact assessment
           - Financial stress testing and scenario analysis
           - Risk mitigation strategies and contingency plans
           - Market and economic risk exposure
           - Currency and international risk factors
           - Regulatory and compliance financial risks

        10. FINAL GROWTH STRATEGY (Financial execution plan)
            - 3-5 actionable steps to improve financial performance
            - Priority order and timeline with specific milestones
            - Expected outcomes and metrics for success
            - Resource requirements and investment needs
            - Risk mitigation strategies and contingency plans
            - Success metrics and KPIs for tracking progress
            - Financial monitoring and adaptation strategies

        Provide SPECIFIC NUMBERS, PERCENTAGES, and TIMELINES. Focus on FINANCIAL VIABILITY, INVESTMENT POTENTIAL, and SUSTAINABLE GROWTH. Include edge cases, financial risks, and alternative scenarios that could impact financial performance and investment decisions.""",
        
        "Business Analysis": """Analyze this document and provide comprehensive, detailed business insights with strategic depth:

        1. OVERALL SUMMARY (Comprehensive business overview)
           - Executive summary with key business metrics and positioning
           - Core business model and value proposition identification
           - Market position and competitive landscape overview
           - Key success factors and risk factors assessment
           - Business maturity and growth stage evaluation

        2. COMPANY VISION AND OVERVIEW (Strategic positioning)
           - Business type identification with industry classification
           - Clear vision statement with strategic objectives
           - Mission statement and core values identification
           - Business model analysis and revenue streams
           - Strategic positioning and market differentiation
           - Growth trajectory and expansion plans

        3. INDUSTRY AND MARKET ANALYSIS (Comprehensive market intelligence)
           - Industry analysis with market size and growth trends
           - Competitive positioning and market share analysis
           - Market opportunities with size and timing assessment
           - Risk factors with probability and impact analysis
           - Regulatory environment and compliance requirements
           - Market maturity and evolution stage assessment

        4. FEEDBACK ANALYSIS (Customer and stakeholder insights)
           4.1 POSITIVE POINTS (3-4 most common with specific examples)
               - Customer satisfaction drivers and success factors
               - Product/service strengths and competitive advantages
               - Operational excellence indicators and best practices
               - Brand perception and reputation strengths
               - Customer loyalty and retention factors

           4.2 NEGATIVE POINTS (3-4 most common with impact assessment)
               - Customer pain points and dissatisfaction drivers
               - Product/service weaknesses and improvement areas
               - Operational challenges and inefficiencies
               - Brand perception issues and reputation risks
               - Customer churn and retention challenges

           4.3 NON-BUSINESS RELATED FACTORS (Operational and environmental)
               - Staff performance and customer service quality
               - Cleanliness and facility maintenance standards
               - Customer behavior and interaction patterns
               - Environmental factors and location considerations
               - Operational processes and efficiency factors

           4.4 SPAM REVIEWS CHECK (Quality and authenticity assessment)
               - Irrelevant or spam-like review identification
               - Review authenticity and credibility assessment
               - Data quality and reliability factors
               - Review moderation and quality control needs
               - Customer feedback validation and verification

        5. FINAL VERDICT (Strategic conclusion and recommendations)
           - Comprehensive conclusion combining all insights
           - Strategic recommendations with implementation priority
           - Improvement direction with specific action items
           - Risk mitigation strategies and contingency plans
           - Success metrics and KPIs for tracking progress
           - Long-term strategic vision and growth roadmap

        IMPORTANT: Provide detailed, comprehensive analysis for each section. Include specific examples, actionable insights, and strategic recommendations. Address edge cases, potential challenges, and alternative scenarios. Use clear sections with bullet points for clarity and actionable insights.""",
        
        "Unknown Document": """Analyze this document and provide comprehensive, startup-focused insights with strategic depth:

        1. DOCUMENT OVERVIEW (Comprehensive content analysis)
           - Content type identification with specific characteristics
           - Document structure and organization quality
           - Information completeness and reliability assessment
           - Key themes and business relevance indicators
           - Document purpose and intended audience
           - Quality indicators and credibility factors

        2. BUSINESS RELEVANCE ASSESSMENT (Strategic relevance)
           - How relevant is this to startup/business analysis?
           - Key business themes identified with examples
           - Missing critical information and data gaps
           - Business intelligence value and insights potential
           - Strategic implications and decision-making value
           - Competitive intelligence and market insights

        3. CONTENT QUALITY & STRUCTURE (Quality assessment)
           - Information completeness and comprehensiveness
           - Data reliability indicators and validation factors
           - Structural organization and presentation quality
           - Source credibility and verification factors
           - Methodology and analytical approach quality
           - Bias identification and objectivity assessment

        4. POTENTIAL INSIGHTS EXTRACTION (Value extraction)
           - Actionable business insights with specific examples
           - Market intelligence opportunities and data value
           - Strategic implications and decision-making support
           - Competitive intelligence and positioning insights
           - Customer and market understanding opportunities
           - Innovation and growth opportunity identification

        5. LIMITATIONS & GAPS (Constraint analysis)
           - Missing critical data and information gaps
           - Unreliable information and validation challenges
           - Analysis constraints and methodology limitations
           - Data quality issues and reliability concerns
           - Scope limitations and coverage gaps
           - Temporal relevance and currency issues

        6. RECOMMENDATIONS (Action planning)
           - Additional information needed for better insights
           - Alternative analysis approaches and methodologies
           - Next steps for better insights and understanding
           - Data collection and validation strategies
           - Analysis enhancement and expansion opportunities
           - Resource allocation and investment recommendations

        7. FINAL GROWTH STRATEGY (Comprehensive action plan)
           - 3-5 actionable steps based on available information
           - Priority order and timeline with specific milestones
           - Expected outcomes and metrics for success
           - Resource requirements and investment needs
           - Risk mitigation strategies and contingency plans
           - Success metrics and KPIs for tracking progress
           - Continuous improvement and adaptation strategies

        Focus on what CAN be learned and what ADDITIONAL information is needed. Provide SPECIFIC examples, actionable insights, and strategic recommendations. Include edge cases, limitations, and alternative approaches that could enhance the analysis and decision-making process."""
    }

    # Use detected type or fallback to comprehensive analysis
    prompt_type = detected_type if detected_type in analysis_prompts else "Startup Document"
    
    # Template-based fallback analysis (when API is unavailable)
    def get_fallback_analysis(doc_type: str, content: str) -> str:
        """Provide template-based analysis when AI API is unavailable"""
        
        if doc_type == "Google Forms Feedback":
            return f"""
# Google Forms Analysis Report

## FORM OVERVIEW
- **Document Type**: Google Forms Feedback
- **Content Length**: {len(content)} characters
- **Analysis Method**: Template-based (API unavailable)

## CUSTOMER INSIGHTS OVERVIEW
Based on the form structure and typical Google Forms patterns, here are the expected insights for startup growth.

## FEEDBACK PATTERNS & TRENDS
- **Form Engagement**: Analyze response completion rates and quality
- **Response Quality**: Monitor answer depth, detail, and actionable insights
- **Time Patterns**: Identify peak response times and engagement windows
- **Segment Analysis**: Understand different user groups and their feedback patterns
- **Trend Identification**: Track feedback evolution over time

## PRODUCT/MARKET FIT ANALYSIS
- **Customer Needs**: Extract pain points, desires, and unmet needs
- **Market Validation**: Assess product-market fit signals and validation
- **Segment Preferences**: Identify target customer groups and their priorities
- **Feature Validation**: Understand which features resonate with users
- **Gap Analysis**: Identify market gaps and opportunity areas

## IMPROVEMENT PRIORITIES
- **High-Impact Changes**: Focus on customer-requested features with high ROI
- **Critical Issues**: Address immediate pain points and urgent concerns
- **Long-term Strategy**: Plan for sustainable growth and scalability
- **Technical Improvements**: Identify infrastructure and performance enhancements
- **Process Optimization**: Streamline user experience and operational efficiency

## CUSTOMER SENTIMENT ANALYSIS
- **Overall Satisfaction**: Track sentiment trends and satisfaction scores
- **Emotional Triggers**: Identify what drives engagement and satisfaction
- **Brand Perception**: Monitor customer brand sentiment and loyalty
- **Pain Point Analysis**: Understand customer frustrations and challenges
- **Success Indicators**: Identify what customers love and value most

## COMPETITIVE ADVANTAGE OPPORTUNITIES
- **Unique Features**: Highlight differentiation points and competitive edges
- **Market Gaps**: Identify underserved customer needs and opportunities
- **Positioning**: Strengthen competitive positioning and market differentiation
- **Innovation Areas**: Discover new feature and service opportunities
- **Partnership Potential**: Identify collaboration and integration opportunities

## GROWTH STRATEGY & SCALING
- **Customer Acquisition**: Optimize acquisition channels and conversion rates
- **Retention**: Improve customer loyalty strategies and engagement
- **Expansion**: Identify new market opportunities and customer segments
- **Pricing Strategy**: Optimize pricing based on customer feedback and value
- **International Growth**: Explore expansion into new markets and regions

## FINAL GROWTH STRATEGY
1. **Immediate Actions** (Next 30 days)
   - Analyze form responses for quick wins and immediate improvements
   - Implement high-impact changes based on customer feedback
   - Set up response monitoring and feedback collection systems
   - Address critical pain points and urgent customer concerns
   - Establish feedback response and customer communication processes

2. **Short-term Goals** (3-6 months)
   - Optimize form structure and questions based on feedback analysis
   - Implement customer-requested features and improvements
   - Establish comprehensive feedback collection and analysis processes
   - Develop customer satisfaction measurement and tracking systems
   - Create customer feedback response and follow-up procedures

3. **Long-term Vision** (6-12 months)
   - Scale successful feedback mechanisms across all customer touchpoints
   - Expand to new customer segments and market opportunities
   - Build data-driven decision culture and customer-centric processes
   - Develop predictive analytics for customer needs and preferences
   - Create comprehensive customer experience optimization framework

## RISK MITIGATION & CONTINGENCIES
- **Data Quality**: Ensure feedback accuracy and representativeness
- **Response Bias**: Address potential sampling and response biases
- **Implementation Challenges**: Plan for technical and operational hurdles
- **Customer Expectations**: Manage expectations around feedback implementation
- **Competitive Response**: Prepare for competitive reactions and market changes

---
*Note: This is a comprehensive template analysis. For detailed AI-powered insights, ensure your Google Gemini API key has available quota.*
            """
        
        elif doc_type == "Startup Document":
            return f"""
# Startup Document Analysis Report

## DOCUMENT OVERVIEW
- **Document Type**: Startup Document
- **Content Length**: {len(content)} characters
- **Analysis Method**: Template-based (API unavailable)

## EXECUTIVE SUMMARY
This startup document has been analyzed for key growth indicators and strategic insights.

## VALUE PROPOSITION & COMPETITIVE ADVANTAGE
- **Unique Selling Points**: Identify what makes this startup stand out
- **Competitive Analysis**: Assess differentiation from competitors
- **Market Positioning**: Evaluate strategic market position

## MARKET OPPORTUNITY
- **Market Size**: Assess TAM, SAM, SOM potential
- **Growth Trends**: Identify market growth drivers
- **Target Segments**: Define primary customer groups

## BUSINESS MODEL & REVENUE
- **Revenue Streams**: Analyze multiple income sources
- **Unit Economics**: Evaluate LTV, CAC, and margins
- **Scalability**: Assess growth potential

## COMPETITIVE LANDSCAPE
- **Competitor Analysis**: Identify key competitors
- **Advantage Assessment**: Evaluate competitive strengths
- **Market Entry**: Assess entry barriers and timing

## FINANCIAL PROJECTIONS
- **Revenue Forecasts**: Review 3-5 year projections
- **Growth Metrics**: Analyze monthly/quarterly trends
- **Key Ratios**: Evaluate financial health indicators

## TEAM & EXECUTION
- **Team Strengths**: Assess execution capabilities
- **Experience Relevance**: Evaluate industry expertise
- **Resource Allocation**: Review team structure

## INVESTMENT & FUNDING
- **Funding Requirements**: Assess capital needs
- **Use of Funds**: Review allocation strategy
- **Milestone Planning**: Define funding milestones

## RISK ASSESSMENT
- **Key Risks**: Identify primary risk factors
- **Mitigation Strategies**: Review risk management
- **Contingency Planning**: Assess backup plans

## FINAL GROWTH STRATEGY
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
*Note: This is a template analysis. For detailed AI-powered insights, ensure your Google Gemini API key has available quota.*
            """
        
        else:
            return f"""
# Document Analysis Report

## DOCUMENT OVERVIEW
- **Document Type**: {doc_type}
- **Content Length**: {len(content)} characters
- **Analysis Method**: Template-based (API unavailable)

## BUSINESS RELEVANCE ASSESSMENT
This document has been analyzed for startup and business relevance.

## KEY INSIGHTS
- **Content Quality**: Assess information completeness
- **Business Value**: Identify actionable insights
- **Strategic Implications**: Evaluate business impact

## GROWTH OPPORTUNITIES
- **Market Insights**: Extract market intelligence
- **Customer Understanding**: Identify customer needs
- **Competitive Intelligence**: Assess market positioning

## ACTION ITEMS
- **Immediate Actions**: Quick wins and improvements
- **Strategic Planning**: Long-term growth initiatives
- **Resource Allocation**: Optimize resource usage

## FINAL GROWTH STRATEGY
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
*Note: This is a template analysis. For detailed AI-powered insights, ensure your Google Gemini API key has available quota.*
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
                model = google.generativeai.embed_content(
                    model="models/embedding-001",
                    content=content
                )
                embedding = model.embedding
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
            model = google.generativeai.generate_content(
                model="gemini-1.5-flash",
                contents=business_analyst_prompt
            )
            return {"analysis": model.text}

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
You are a seasoned startup analyst and business consultant with 15+ years of experience. Using ONLY the provided RAG Context, produce a comprehensive, detailed analysis with clear section headers and bullet points where helpful. If a section lacks evidence in the RAG Context, write "Not found" for that section. Do not invent facts.

IMPORTANT: Write in a professional, business-focused tone. Use NO emojis and maintain a formal yet accessible style suitable for startup founders and investors.

CRITICAL REQUIREMENTS:
1. Provide DETAILED, COMPREHENSIVE analysis for each section (minimum 200-400 words per major section)
2. Include SPECIFIC examples, numbers, and actionable insights with implementation details
3. Address edge cases and potential challenges in each section with mitigation strategies
4. Provide alternative scenarios and contingency plans for risk management
5. Include risk assessments and mitigation strategies with probability analysis
6. Give concrete, implementable recommendations with timelines and success metrics
7. Use bullet points and structured formatting for clarity and readability
8. Provide detailed explanations, not just brief statements
9. Include specific action items with owners, timelines, and expected outcomes
10. Address potential objections and challenges with proactive solutions

Focus on ACTIONABLE insights that help founders:
1. Scale their startup with specific strategies and implementation steps
2. Correct mistakes with detailed solutions and prevention measures
3. Identify growth opportunities with implementation plans and success metrics
4. Make data-driven decisions with clear metrics and measurement frameworks
5. Handle edge cases and unexpected challenges with contingency planning
6. Plan for multiple scenarios and contingencies with risk mitigation

RAG Context (retrieved chunks per section):
{rag_context}

Task:
{analysis_prompts.get(prompt_type, list(analysis_prompts.values())[0]) }
"""

        model = google.generativeai.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return {"analysis": model.text}
        
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
         # In a production system, you'd use actual form response data
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