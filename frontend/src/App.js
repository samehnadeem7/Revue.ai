import React, { useState, useRef } from 'react';
import axios from 'axios';
import './App.css';

// Direct connection to Render backend
const API_URL = 'https://revue-ai-8.onrender.com';
console.log('Connecting to backend:', API_URL);

function App() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selectedFile = e.dataTransfer.files[0];
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError('');
      } else {
        setError('Please select a PDF file');
        setFile(null);
      }
    }
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Please select a PDF file');
      setFile(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please select a PDF file first');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysis('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      console.log('Sending request to:', `${API_URL}/upload-pdf/`);
      const response = await axios.post(`${API_URL}/upload-pdf/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });

      const newAnalysis = {
        id: Date.now(),
        filename: file.name,
        analysis: response.data.analysis,
        timestamp: new Date().toLocaleString(),
        documentType: response.data.document_type
      };

      setAnalysis(response.data.analysis);
      setAnalysisHistory(prev => [newAnalysis, ...prev.slice(0, 4)]);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      console.error('Analysis error:', err);
      setError(`Error: ${errorMessage}. Status: ${err.response?.status || 'Network Error'}`);
    } finally {
      setLoading(false);
    }
  };

  const formatAnalysis = (text) => {
    return text.split('\n').map((line, index) => {
      const trimmedLine = line.trim();
      
      // Handle headers with ##
      if (trimmedLine.startsWith('## ')) {
        return <h2 key={index} className="section-header">{trimmedLine.replace('## ', '')}</h2>;
      }
      
      // Handle headers with ###
      if (trimmedLine.startsWith('### ')) {
        return <h3 key={index} className="section-header">{trimmedLine.replace('### ', '')}</h3>;
      }
      
      // Handle numbered lists
      if (trimmedLine.match(/^\d+\./)) {
        return <h3 key={index} className="section-header">{trimmedLine}</h3>;
      }
      
      // Handle bullet points with *
      if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
        return <h4 key={index} className="subsection-header">{trimmedLine.replace(/\*\*/g, '')}</h4>;
      }
      
      // Handle bullet points with • or -
      if (trimmedLine.startsWith('•') || trimmedLine.startsWith('-')) {
        return <li key={index} className="bullet-point">{trimmedLine.replace(/^[•-]\s*/, '')}</li>;
      }
      
      // Handle bold text with **text**
      if (trimmedLine.includes('**')) {
        const parts = trimmedLine.split('**');
        return (
          <p key={index} className="analysis-text">
            {parts.map((part, i) => 
              i % 2 === 1 ? <strong key={i}>{part}</strong> : part
            )}
          </p>
        );
      }
      
      // Handle regular paragraphs
      if (trimmedLine) {
        return <p key={index} className="analysis-text">{trimmedLine}</p>;
      }
      
      return <br key={index} />;
    });
  };

  const onButtonClick = () => {
    fileInputRef.current.click();
  };

  const testConnection = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      if (response.ok) {
        alert('✅ Backend connection SUCCESS! Both servers are connected.');
      } else {
        alert('❌ Backend responded but with error');
      }
    } catch (error) {
      alert('❌ Cannot connect to backend: ' + error.message);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">🚀</div>
            <div className="logo-text">
              <h1>Revue.ai</h1>
              <p>AI-Powered Startup Document Analyzer</p>
            </div>
          </div>
          <div className="header-stats">
            <div className="stat">
              <span className="stat-number">{analysisHistory.length}</span>
              <span className="stat-label">Analyses</span>
            </div>
            <button 
              onClick={testConnection}
              style={{
                marginLeft: '20px',
                padding: '8px 16px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Test Connection
            </button>
          </div>
        </div>
      </header>

      <main className="main">
        <div className="container">
          <div className="upload-section">
            <div className="upload-header">
              <h2>Upload Your Document</h2>
              <p>Get instant AI-powered insights from your startup documents</p>
            </div>

            <div 
              className={`upload-area ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="file-input"
                style={{ display: 'none' }}
              />
              
              <div className="upload-content">
                <div className="upload-icon">📄</div>
                <h3>Drop your PDF here</h3>
                <p>or</p>
                <button 
                  className="browse-button"
                  onClick={onButtonClick}
                >
                  Browse Files
                </button>
                <p className="file-types">Supports: PDF documents</p>
              </div>

              {file && (
                <div className="file-info">
                  <div className="file-icon">📎</div>
                  <div className="file-details">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                  <button 
                    className="remove-file"
                    onClick={() => setFile(null)}
                  >
                    ×
                  </button>
                </div>
              )}
            </div>

            <button
              onClick={handleAnalyze}
              disabled={!file || loading}
              className={`analyze-button ${loading ? 'loading' : ''}`}
            >
              {loading ? (
                <>
                  <div className="spinner"></div>
                  Analyzing Document...
                </>
              ) : (
                <>
                  <span className="button-icon">🔍</span>
                  Analyze Document
                </>
              )}
            </button>

            {error && (
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                {error}
              </div>
            )}
          </div>

          {analysis && (
            <div className="results-section">
              <div className="results-header">
                <h2>📊 Analysis Results</h2>
                <div className="results-meta">
                  <span className="document-type">Auto-detected</span>
                  <span className="analysis-time">{new Date().toLocaleTimeString()}</span>
                </div>
              </div>
              <div className="analysis-content">
                {formatAnalysis(analysis)}
              </div>
            </div>
          )}

          {analysisHistory.length > 0 && (
            <div className="history-section">
              <h3>Recent Analyses</h3>
              <div className="history-grid">
                {analysisHistory.map((item) => (
                  <div key={item.id} className="history-item">
                    <div className="history-icon">📋</div>
                    <div className="history-content">
                      <h4>{item.filename}</h4>
                      <p className="history-type">{item.documentType}</p>
                      <p className="history-time">{item.timestamp}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="footer-content">
          <p>Powered by AI - Helping startups make data-driven decisions</p>
          <div className="footer-links">
            <span>Built with ❤️ for entrepreneurs</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
