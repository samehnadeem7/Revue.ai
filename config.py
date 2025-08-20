import os
from dotenv import load_dotenv

load_dotenv()

# Local SQLite Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./startup_analyzer.db")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
