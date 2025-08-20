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
st.markdown("AI-powered analysis of startup documents with quantified insights")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page",
    ["Upload & Analyze", "Analysis History", "Analytics Dashboard"]
)

# API endpoint - can be changed for deployment
API_URL = st.sidebar.text_input(
    "API URL", 
    value="   https://revue-ai-1.onrender.com",
    help="Enter the URL of your FastAPI backend"
)

if page == "Upload & Analyze":
    st.header("📄 Upload & Analyze Document")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a startup document (pitch deck, business plan, etc.)"
    )
    
    # Document type selection
    document_type = st.selectbox(
        "Document Type",
        ["Pitch Deck", "Business Plan", "Market Research", "Financial Model"],
        help="Select the type of document for better analysis"
    )
    
    if uploaded_file is not None and st.button("🚀 Analyze Document"):
        with st.spinner("Analyzing document..."):
            try:
                # Prepare file for upload
                files = {"file": uploaded_file}
                data = {"document_type": document_type}
                
                # Make API request
                response = requests.post(f"{API_URL}/upload-pdf/", files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
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
                    
                else:
                    st.error(f"❌ Error: {response.text}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

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
st.markdown("Built with FastAPI, PyMuPDF, and Streamlit") 
