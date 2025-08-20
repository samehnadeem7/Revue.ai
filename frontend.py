import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Startup Document Analyzer",
    page_icon="🚀",
    layout="wide"
)

# Title and description
st.title("🚀 Startup Document Analyzer")
st.markdown("AI-powered analysis of startup documents with quantified insights and growth strategies")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page",
    ["Upload & Analyze", "Analysis History", "Analytics Dashboard"]
)

# API endpoint - can be changed for deployment
API_URL = st.sidebar.text_input(
    "API URL", 
    value="https://revue-ai-1.onrender.com",
    help="Enter the URL of your FastAPI backend"
)

if page == "Upload & Analyze":
    st.header("📄 Upload & Analyze Document")
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["📁 Upload PDF", "🔗 Google Forms Converter"])
    
    with tab1:
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload any startup document (pitch deck, business plan, market research, financial model, customer feedback, etc.)"
        )
        
        # Document type info
        st.info("💡 **Smart Analysis**: Our AI automatically detects document type and provides relevant insights!")
        
        if uploaded_file is not None and st.button("🚀 Analyze Document"):
            with st.spinner("Analyzing document with AI..."):
                try:
                    # Prepare file for upload
                    files = {"file": uploaded_file}
                    
                    # Make API request (no document type needed - auto-detected)
                    response = requests.post(f"{API_URL}/upload-pdf/", files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Check if using fallback mode
                        if result.get("fallback"):
                            if result.get("api_status") == "rate_limited":
                                st.warning("⚠️ **API Rate Limit Reached** - Using template analysis. For full AI insights, check your Google API quota.")
                            else:
                                st.warning("⚠️ **API Error** - Using template analysis. For full AI insights, check your API configuration.")
                        
                        st.success("✅ Analysis completed successfully!")
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Document", result["filename"])
                            st.metric("Type", result["document_type"])
                        with col2:
                            st.metric("Analysis ID", result["analysis_id"])
                        
                        # Display analysis
                        st.subheader("📊 AI Analysis Results")
                        st.markdown(result["analysis"])
                        
                        # Show API status if available
                        if result.get("api_status"):
                            st.info(f"**API Status**: {result['api_status']}")
                        
                    else:
                        st.error(f"❌ Error: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.subheader("🔗 Convert Google Forms to PDF & Analyze")
        st.info("💡 **Convert Google Forms**: Paste your Google Forms URL and get instant analysis!")
        
        # Google Forms URL input
        form_url = st.text_input(
            "Google Forms URL",
            placeholder="https://forms.gle/... or https://docs.google.com/forms/...",
            help="Paste your Google Forms URL here"
        )
        
        form_title = st.text_input(
            "Form Title (Optional)",
            placeholder="Customer Feedback Survey",
            help="Give your form a descriptive title"
        )
        
        if form_url and st.button("🔄 Convert & Analyze Form"):
            with st.spinner("Converting Google Form and analyzing responses..."):
                try:
                    # Prepare form data
                    form_data = {
                        "form_url": form_url,
                        "form_title": form_title or "Untitled Form"
                    }
                    
                    # Make API request to convert Google Form
                    response = requests.post(f"{API_URL}/convert-google-form/", data=form_data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.success("✅ Google Form converted and analyzed successfully!")
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Form", result["filename"])
                            st.metric("Type", result["document_type"])
                        with col2:
                            st.metric("Analysis ID", result["analysis_id"])
                            st.metric("Form ID", result.get("form_id", "N/A"))
                        
                        # Display analysis
                        st.subheader("📊 Google Forms Analysis Results")
                        st.markdown(result["analysis"])
                        
                        # Show form details
                        st.info(f"🔗 **Form URL**: {result.get('form_url', 'N/A')}")
                        
                    else:
                        st.error(f"❌ Error: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Google Forms tips
        st.markdown("---")
        st.markdown("**💡 Google Forms Tips:**")
        st.markdown("""
        - **Supported URLs**: forms.gle, docs.google.com/forms
        - **Best for**: Customer feedback, surveys, market research
        - **Analysis**: AI extracts insights and growth strategies
        - **Output**: Structured analysis with actionable recommendations
        """)

elif page == "Analysis History":
    st.header("📚 Analysis History")
    
    try:
        # Fetch analysis history
        response = requests.get(f"{API_URL}/history/")
        
        if response.status_code == 200:
            history = response.json()
            
            if history["recent_analyses"]:
                # Convert to DataFrame for better display
                df = pd.DataFrame(history["recent_analyses"])
                df["created_at"] = pd.to_datetime(df["created_at"])
                
                # Display table
                st.dataframe(df, use_container_width=True)
                
                # Download option
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download History as CSV",
                    data=csv,
                    file_name=f"analysis_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No analysis history found.")
        else:
            st.error(f"❌ Error fetching history: {response.text}")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

elif page == "Analytics Dashboard":
    st.header("📊 Analytics Dashboard")
    
    try:
        # Fetch analytics
        response = requests.get(f"{API_URL}/analytics/")
        
        if response.status_code == 200:
            analytics = response.json()
            
            # Metrics row
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Analyses", analytics["total_analyses"])
            with col2:
                st.metric("Recent (7 days)", analytics["recent_analyses_7_days"])
            with col3:
                st.metric("Document Types", len(analytics["document_type_distribution"]))
            
            # Document type distribution chart
            if analytics["document_type_distribution"]:
                st.subheader("📈 Document Type Distribution")
                
                df_dist = pd.DataFrame(analytics["document_type_distribution"])
                
                # Use Streamlit's built-in charts (no plotly needed)
                st.write("**Document Type Distribution:**")
                for doc_type in df_dist.itertuples():
                    st.write(f"• {doc_type.type}: {doc_type.count} analyses")
                
                # Create bar chart using Streamlit's built-in chart
                st.bar_chart(df_dist.set_index('type')['count'])
                
                # Create a simple pie chart representation
                st.write("**Chart Representation:**")
                total = df_dist['count'].sum()
                for doc_type in df_dist.itertuples():
                    percentage = (doc_type.count / total) * 100
                    st.write(f"📊 {doc_type.type}: {percentage:.1f}% ({doc_type.count} analyses)")
            else:
                st.info("No analytics data available yet.")
                
        else:
            st.error(f"❌ Error fetching analytics: {response.text}")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("Built with FastAPI, PyMuPDF, RAG-powered AI, and Streamlit") 
