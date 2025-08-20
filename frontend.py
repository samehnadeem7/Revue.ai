import streamlit as st
import requests
import os

# Configure the app
st.set_page_config(
    page_title="Startup Document Analyzer",
    page_icon="🚀",
    layout="wide"
)

# Constants
API_URL = "http://localhost:8000"

def main():
    st.title("🚀 Startup Document Analyzer")
    st.write("Get instant insights from your startup documents")

    # Main content in columns
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("### 📤 Upload Document")
        
        # Document type selection
        doc_type = st.selectbox(
            "Document Type",
            [
                "Pitch Deck",
                "Business Plan",
                "Market Research",
                "Financial Model"
            ]
        )
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=['pdf'],
            help="Upload your startup document"
        )

        if uploaded_file:
            if st.button("🔄 Analyze Document"):
                with st.spinner("Analyzing your document..."):
                    try:
                        # Upload and get analysis
                        files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
                        response = requests.post(
                            f"{API_URL}/upload-pdf/",
                            files=files,
                            data={'document_type': doc_type}
                        )
                        
                        if response.status_code == 200:
                            # Store analysis in session state
                            st.session_state['analysis'] = response.json()['analysis']
                            st.success("Analysis complete!")
                        else:
                            st.error(f"Error: {response.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("Failed to connect to the analysis server!")

        # Show document guidelines
        with st.expander("📋 Document Guidelines"):
            st.markdown("""
            **Pitch Deck should include:**
            - Problem & Solution
            - Market Size
            - Business Model
            - Competition
            - Team
            - Financials
            
            **Business Plan should include:**
            - Executive Summary
            - Market Analysis
            - Product/Service
            - Marketing Strategy
            - Financial Projections
            
            **Market Research should include:**
            - Market Size & Trends
            - Customer Segments
            - Competitor Analysis
            - Market Drivers
            
            **Financial Model should include:**
            - Revenue Streams
            - Cost Structure
            - Projections
            - Unit Economics
            """)

    with col2:
        st.markdown("### 📊 Analysis Results")
        
        if 'analysis' in st.session_state:
            # Display analysis in tabs
            analysis = st.session_state['analysis']
            
            # Create expandable sections for each analysis part
            sections = analysis.split('\n\n')
            for section in sections:
                if section.strip():
                    # Try to extract section title (assuming it starts with number or header)
                    lines = section.strip().split('\n')
                    title = lines[0].strip('1234567890. ')
                    
                    with st.expander(f"📌 {title}", expanded=True):
                        # Display rest of the section content
                        content = '\n'.join(lines[1:]) if len(lines) > 1 else lines[0]
                        st.markdown(content)
            
            # Export options
            st.markdown("---")
            st.markdown("### 📑 Export Options")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Download Analysis"):
                    st.download_button(
                        label="Download Analysis (TXT)",
                        data=analysis,
                        file_name="startup_analysis.txt",
                        mime="text/plain"
                    )
            
            with col2:
                if st.button("📋 Copy to Clipboard"):
                    st.code(analysis, language=None)
                    st.info("Analysis copied to clipboard! Use Ctrl+C or Cmd+C to copy.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>🚀 Powered by AI - Get instant insights for your startup</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()