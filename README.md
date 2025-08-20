# Revue.ai - Startup Document Analyzer

AI-powered analysis of startup documents using FastAPI backend and React frontend.

## Features

- **Document Types**: Pitch Decks, Business Plans, Market Research, Financial Models
- **AI Analysis**: Powered by Google's Gemini AI
- **Minimalist Design**: Clean, professional interface
- **Instant Results**: Upload PDF and get structured insights

## Project Structure

```
├── main.py              # FastAPI backend
├── frontend.py          # Streamlit frontend (legacy)
├── frontend/            # React frontend
│   ├── src/            # React source code
│   │   ├── App.js      # Main React component
│   │   ├── App.css     # Styles
│   │   └── index.js    # React entry point
│   ├── public/         # Static files
│   ├── package.json    # React dependencies
│   └── node_modules/   # Installed packages
├── requirements.txt    # Python dependencies
└── render.yaml         # Deployment config
```

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 16+
- Git

### Backend Setup

1. **Clone and navigate to project:**
   ```bash
   cd C:\Users\sameh\OneDrive\Documents\fastapi
   ```

2. **Activate virtual environment:**
   ```bash
   .venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   - Create `.env` file with your Google API key:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```

5. **Run backend:**
   ```bash
   uvicorn main:app --reload
   ```
   Backend will run on http://localhost:8000

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file:**
   ```bash
   copy env.example .env.local
   ```

4. **Run React frontend:**
   ```bash
   npm start
   ```
   Frontend will run on http://localhost:3000

## Usage

1. Open http://localhost:3000 in your browser
2. Select document type (Pitch Deck, Business Plan, etc.)
3. Upload a PDF file
4. Click "Analyze Document"
5. View structured AI analysis results

## Deployment

### Backend (Render)
1. Push code to GitHub
2. Create Web Service on Render
3. Connect GitHub repository
4. Set environment variables:
   - `GOOGLE_API_KEY`: Your Google API key
5. Deploy with:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend (Vercel/Netlify)
1. Update `.env.local` with your backend URL:
   ```
   REACT_APP_API_URL=https://your-render-app.onrender.com
   ```
2. Build: `npm run build`
3. Deploy build folder to Vercel/Netlify

## Git Workflow

```bash
# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Your commit message"

# Push to GitHub
git push origin main
```

## API Endpoints

- `GET /` - API information
- `POST /upload-pdf/` - Upload and analyze PDF
- `GET /docs` - API documentation

## Tech Stack

- **Backend**: FastAPI, Python, Google Gemini AI
- **Frontend**: React, Axios, CSS3
- **Deployment**: Render (backend), Vercel/Netlify (frontend)
- **Storage**: Temporary file storage

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test locally
5. Submit pull request
