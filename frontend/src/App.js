import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

// Use environment variable or fallback to localhost
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState('Pitch Deck');
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const documentTypes = [
    'Pitch Deck',
    'Business Plan',
    'Market Research',
    'Financial Model'
  ];

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
      formData.append('document_type', documentType);

      const response = await axios.post(`${API_URL}/upload-pdf/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysis(response.data.analysis);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze document. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatAnalysis = (text) => {
    return text.split('\n').map((line, index) => {
      if (line.trim().match(/^\d+\./)) {
        return <h3 key={index} className="section-header">{line}</h3>;
      }
      if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
        return <li key={index} className="bullet-point">{line.replace(/^[•-]\s*/, '')}</li>;
      }
      if (line.trim()) {
        return <p key={index} className="analysis-text">{line}</p>;
      }
      return <br key={index} />;
    });
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🚀 Revue.ai</h1>
        <p>AI-powered startup document analyzer</p>
      </header>

      <main className="main">
        <div className="upload-section">
          <div className="form-group">
            <label htmlFor="documentType">Document Type</label>
            <select
              id="documentType"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="select"
            >
              {documentTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="fileInput">Upload PDF Document</label>
            <input
              id="fileInput"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="file-input"
            />
            {file && <p className="file-name">Selected: {file.name}</p>}
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!file || loading}
            className="analyze-button"
          >
            {loading ? 'Analyzing...' : 'Analyze Document'}
          </button>

          {error && <div className="error">{error}</div>}
        </div>

        {analysis && (
          <div className="results-section">
            <h2>📊 Analysis Results</h2>
            <div className="analysis-content">
              {formatAnalysis(analysis)}
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Powered by AI - Helping startups make data-driven decisions</p>
      </footer>
    </div>
  );
}

export default App;
