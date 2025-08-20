# FastAPI Startup Document Analyzer - Deployment Guide

## 🚀 Quick Deploy to Render

### 1. Prerequisites
- GitHub repository with your code
- Supabase project (already configured)
- Google AI API key

### 2. Deploy to Render

#### Option A: Deploy via Render Dashboard
1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `startup-doc-analyzer`
   - **Runtime**: `Python 3.11`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### Option B: Deploy via render.yaml (Recommended)
1. Push your code to GitHub
2. In Render dashboard, click "New +" → "Blueprint"
3. Select your repository
4. Render will automatically use the `render.yaml` configuration

### 3. Environment Variables
Set these in Render dashboard:

```
GOOGLE_API_KEY=your_google_api_key_here
DATABASE_URL=postgresql://postgres:Sameh%40123@db.jxggbdboltmdzcrbyyqw.supabase.co:5432/postgres
SUPABASE_URL=https://jxggbdboltmdzcrbyyqw.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

**Note**: The `@` in your password is already URL-encoded as `%40` in the DATABASE_URL.

### 4. Alternative Deployment Platforms

#### Heroku
1. Install Heroku CLI
2. Create `Procfile` (already created)
3. Deploy: `heroku create && git push heroku main`

#### Railway
1. Go to [railway.app](https://railway.app)
2. Connect GitHub repository
3. Set environment variables
4. Deploy automatically

#### DigitalOcean App Platform
1. Go to [digitalocean.com](https://digitalocean.com)
2. Create new app from GitHub
3. Configure environment variables
4. Deploy

## 🔧 Local Testing

### Test Configuration
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Test config
python -c "from config import *; print('Config loaded successfully')"

# Test app
python -c "from main import app; print('FastAPI app loaded successfully')"

# Run locally
uvicorn main:app --reload
```

### Test Database Connection
```bash
python -c "
from config import DATABASE_URL
import psycopg2
try:
    conn = psycopg2.connect(DATABASE_URL)
    print('Database connection successful!')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

## 📁 Project Structure
```
fastapi/
├── main.py                 # Main FastAPI application
├── config.py               # Configuration and environment variables
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment configuration
├── Procfile               # Heroku deployment configuration
├── .env.example           # Environment variables template
├── uploads/               # File upload directory
└── README.md              # Project documentation
```

## 🌐 API Endpoints

Once deployed, your API will be available at:
- **Base URL**: `https://your-app-name.onrender.com`
- **Documentation**: `https://your-app-name.onrender.com/docs`
- **Health Check**: `https://your-app-name.onrender.com/health`

## 🔍 Troubleshooting

### Common Issues:
1. **Database Connection Failed**: Check DATABASE_URL and Supabase credentials
2. **Missing Dependencies**: Ensure all packages in requirements.txt are installed
3. **Port Issues**: Render automatically sets $PORT environment variable
4. **File Uploads**: Ensure uploads directory exists and has proper permissions

### Debug Commands:
```bash
# Check environment variables
python -c "import os; print(os.environ.get('DATABASE_URL', 'Not set'))"

# Test database connection
python -c "from config import DATABASE_URL; print(DATABASE_URL)"

# Check app startup
python -c "from main import app; print(app.title)"
```

## 📞 Support
- Check Render logs in dashboard
- Verify Supabase connection in Supabase dashboard
- Test locally before deploying
- Check environment variables are set correctly
