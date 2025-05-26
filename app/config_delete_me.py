
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# General Flask config
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-this-in-production")
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

# Database config
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "postgres":
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv(\"DB_USER\", \"postgres\")}:"
        f"{os.getenv(\"DB_PASSWORD\", \"postgres\")}@"
        f"{os.getenv(\"DB_HOST\", \"localhost\")}:"
        f"{os.getenv(\"DB_PORT\", \"5432\")}/"
        f"{os.getenv(\"DB_NAME\", \"" + os.path.basename(os.getcwd()) + "\")}"
    )
else:
    # SQLite default
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(os.path.dirname(__file__), \"../instance/app.db\")}"
    )

# Silence the deprecation warning
SQLALCHEMY_TRACK_MODIFICATIONS = False

