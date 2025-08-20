import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Supabase Database Configuration
password = quote_plus('Sameh@123')
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://postgres:{password}@db.jxggbdboltmdzcrbyyqw.supabase.co:5432/postgres")

# Google AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jxggbdboltmdzcrbyyqw.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
