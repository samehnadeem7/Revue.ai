Yimport os
from dotenv import load_dotenv

load_dotenv()

# Local SQLite Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./startup_analyzer.db")

# Google Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
