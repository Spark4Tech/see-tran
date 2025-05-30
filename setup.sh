#!/usr/bin/env bash
# new_flask.sh
# Run inside an **empty** project folder you've already created, e.g.:
#   mkdir awesome_app && cd awesome_app && chmod +x setup.sh && ./setup.sh
# TODO: Set up forms director and install Flask-WTF
# TODO: Create command line option to allow user to choose between python venv or pyenv
#   as the virtual environment manager
set -uo pipefail

# ---- derive project name ---------------------------------------------------
PROJECT="$(basename "$PWD")"
echo "📦  Initializing Flask project: $PROJECT"

# ---- prerequisite checks ---------------------------------------------------
install_pyenv() {
  echo "🔧 pyenv not found, attempting to install..."
  
  if command -v brew >/dev/null 2>&1; then
    echo "Using Homebrew to install pyenv..."
    brew install pyenv pyenv-virtualenv
  elif command -v apt-get >/dev/null 2>&1; then
    echo "Using apt to install pyenv dependencies..."
    sudo apt-get update
    sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
      libreadline-dev libsqlite3-dev curl llvm libncurses5-dev libncursesw5-dev \
      xz-utils tk-dev libffi-dev liblzma-dev python3-openssl
    
    curl https://pyenv.run | bash
    
    # Add to shell config if not already present
    SHELL_CONFIG="$HOME/.bashrc"
    if [ -f "$HOME/.zshrc" ]; then
      SHELL_CONFIG="$HOME/.zshrc"
    fi
    
    if ! grep -q "pyenv init" "$SHELL_CONFIG"; then
      echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> "$SHELL_CONFIG"
      echo 'eval "$(pyenv init -)"' >> "$SHELL_CONFIG"
      echo 'eval "$(pyenv virtualenv-init -)"' >> "$SHELL_CONFIG"
      
      echo "Added pyenv to $SHELL_CONFIG. Please restart your shell or run:"
      echo "source $SHELL_CONFIG"
    fi
  else
    echo "❌ Could not install pyenv automatically. Please install manually:"
    echo "https://github.com/pyenv/pyenv#installation"
    exit 1
  fi
  
  # Try to initialize pyenv in the current shell
  if [ -f "$HOME/.pyenv/bin/pyenv" ]; then
    export PATH="$HOME/.pyenv/bin:$PATH"
  fi
  
  if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init -)"
    if command -v pyenv-virtualenv-init >/dev/null 2>&1; then
      eval "$(pyenv virtualenv-init -)"
    fi
    echo "✅ pyenv installed successfully!"
  else
    echo "🔄 pyenv installed but needs shell restart. Please run this script again after restarting your shell."
    exit 0
  fi
}

check_node_version() {
  if command -v node >/dev/null 2>&1; then
    local current_version=$(node -v | sed 's/v//' | cut -d. -f1)
    local required_version="18"
    
    if [ "$current_version" -lt "$required_version" ]; then
      echo "⚠️  Node.js $required_version+ required, found v$current_version"
      echo "   Consider updating Node.js or using nvm/fnm for version management"
    else
      echo "✅ Node.js v$current_version detected"
    fi
  fi
}

check_prerequisites() {
  for cmd in git node npm; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "❌ $cmd is required but not installed."
      if [ "$cmd" = "node" ] || [ "$cmd" = "npm" ]; then
        echo "   Install Node.js from https://nodejs.org/ or use nvm/fnm"
      fi
      exit 1
    fi
  done
  
  check_node_version
  
  if ! command -v pyenv >/dev/null 2>&1; then
    install_pyenv
  fi
  
  # Initialize pyenv in the current shell
  eval "$(pyenv init -)" || true
  eval "$(pyenv virtualenv-init -)" 2>/dev/null || true
}

check_prerequisites

# ---- git -------------------------------------------------------------------
if [ ! -d .git ]; then
  git init -q
  echo "✅ Git repository initialized"
else
  echo "✅ Git repository already exists"
fi

# ---- pyenv & dependencies --------------------------------------------------
setup_python_env() {
  local python_version="3.12"
  local latest_patch=$(pyenv install --list | grep -E "^\s*$python_version\.[0-9]+$" | tail -1 | xargs)
  
  if [ -z "$latest_patch" ]; then
    echo "❌ Could not find Python $python_version.x version"
    exit 1
  fi
  
  # Check if Python version is installed
  if ! pyenv versions --bare | grep -q "$latest_patch"; then
    echo "🔄 Installing Python $latest_patch..."
    pyenv install -s "$latest_patch" || {
      echo "❌ Failed to install Python $latest_patch"
      exit 1
    }
  else
    echo "✅ Python $latest_patch already installed"
  fi
  
  # Check if virtualenv exists
  if ! pyenv versions --bare | grep -q "$PROJECT"; then
    echo "🔄 Creating virtualenv '$PROJECT'..."
    pyenv virtualenv "$latest_patch" "$PROJECT" || {
      echo "❌ Failed to create virtualenv"
      exit 1
    }
  else
    echo "✅ Virtualenv '$PROJECT' already exists"
  fi
  
  # Set local Python version
  pyenv local "$PROJECT" || {
    echo "❌ Failed to set local Python version"
    exit 1
  }
  
  # Install dependencies if requirements.txt doesn't exist or is outdated
  if [ ! -f requirements.txt ] || [ "$0" -nt requirements.txt ]; then
    echo "🔄 Installing Python dependencies..."
    pip install --upgrade pip
    pip install \
      "Flask>=3.1.0,<4.0" \
      "SQLAlchemy>=2.0.40,<3.0" \
      "Flask-SQLAlchemy>=3.1.1,<4.0" \
      "Flask-Migrate>=4.1.0,<5.0" \
      "python-dotenv>=1.0" \
      "psycopg2-binary>=2.9.9" \
      "pytest>=7.4.0" \
      "gunicorn>=21.2.0"
    
    pip freeze > requirements.txt
    echo "✅ Dependencies installed and requirements.txt updated"
  else
    echo "✅ requirements.txt exists - skipping dependency installation"
    echo "   (Delete requirements.txt and run again to reinstall dependencies)"
  fi
}

setup_python_env

# ---- project structure -----------------------------------------------------
create_project_structure() {
  mkdir -p \
    app/{routes,static/js,static/css,templates,models} \
    tailwind \
    migrations \
    tests
  
  touch app/__init__.py app/routes/__init__.py tests/__init__.py
  
  echo "✅ Project directory structure created"
}

if [ ! -d app ]; then
  create_project_structure
else
  echo "✅ Project structure already exists"
fi

# ---- Create files only if they don't exist ---------------------------------
create_file_if_missing() {
  local file="$1"
  local content="$2"
  
  if [ ! -f "$file" ]; then
    echo "🔄 Creating $file..."
    echo "$content" > "$file"
    echo "✅ Created $file"
  else
    echo "✅ $file already exists"
  fi
}

# routes/main.py
create_file_if_missing "app/routes/main.py" '
from flask import Blueprint, render_template, jsonify

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/api/health")
def health_check():
    return jsonify({"status": "ok"})
'

# app/__init__.py
create_file_if_missing "app/__init__.py" '
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config:
        app.config.update(test_config)
    else:
        app.config.from_pyfile("config.py")
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # register blueprints
    from app.routes.main import main as main_bp
    app.register_blueprint(main_bp)
    
    return app
'

# models package
create_file_if_missing "app/models/__init__.py" '# Example model - create more files in app/models/ as needed
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app import db

class Example(db.Model):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<Example id={self.id} name={self.name!r}>"
'

# Create configuration files
create_file_if_missing "app/config.py" '
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
'

# Create .env file
create_file_if_missing ".env" '# Flask configuration
FLASK_APP=app:create_app
FLASK_DEBUG=1

# Database configuration
# Set to "postgres" to use PostgreSQL, or "sqlite" to use SQLite
DB_TYPE=sqlite

# PostgreSQL configuration (only used when DB_TYPE=postgres)
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME='"$PROJECT"'

# Security
SECRET_KEY=dev-key-change-this-in-production
'

create_file_if_missing ".flaskenv" 'FLASK_APP=app:create_app'

# Create a test file
create_file_if_missing "tests/test_app.py" '
import pytest
from app import create_app, db

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
'

# ---- Node.js setup ----------------------------------------------------------
setup_node_env() {
  # Add Node version specification
  create_file_if_missing ".nvmrc" "20"
  
  if [ ! -f package.json ]; then
    echo "🔄 Initializing package.json..."
    npm init -y >/dev/null 2>&1
    echo "✅ package.json created"
  fi
  
  # Install frontend dependencies
  if [ ! -d node_modules ] || [ ! -f node_modules/.package-lock.json ]; then
    echo "🔄 Installing frontend dependencies..."
    npm install -D tailwindcss@^4.1.4 postcss autoprefixer
    npm install htmx.org@^2.0.4
    echo "✅ Frontend dependencies installed"
  else
    echo "✅ Frontend dependencies already installed"
  fi
  
  # Setup Tailwind config
  if [ ! -f tailwind.config.js ]; then
    echo "🔄 Initializing Tailwind CSS..."
    npx tailwindcss init -p
    echo "✅ Tailwind CSS initialized"
  fi
  
  # Create Tailwind input file
  create_file_if_missing "tailwind/input.css" '
@tailwind base;
@tailwind components;
@tailwind utilities;
'
  
  # Update build scripts in package.json
  if ! grep -q '"dev":' package.json; then
    echo "🔄 Adding npm scripts to package.json..."
    npm set-script dev "npm run build:css -- --watch"
    npm set-script build "npm run build:css && npm run copy:htmx"
    npm set-script build:css "tailwindcss -i ./tailwind/input.css -o ./app/static/css/tailwind.css --minify"
    npm set-script copy:htmx "cp node_modules/htmx.org/dist/htmx.min.js app/static/js/"
    echo "✅ npm scripts added"
  fi
  
  # Ensure static directories exist
  mkdir -p app/static/css app/static/js
  touch app/static/css/.keep app/static/js/.keep
}

setup_node_env

# ---- Build initial assets --------------------------------------------------
if [ ! -f app/static/css/tailwind.css ] || [ ! -f app/static/js/htmx.min.js ]; then
  echo "🔄 Building initial assets..."
  npm run build
  echo "✅ Initial assets built"
fi

# ---- templates -------------------------------------------------------------
create_file_if_missing "app/templates/base.html" '<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title|default("Flask-HTMX App") }}</title>
  <link rel="stylesheet" href="{{ url_for("static", filename="css/tailwind.css") }}">
</head>
<body class="min-h-screen bg-gray-50 flex flex-col">
  <nav class="bg-indigo-600 text-white p-4">
    <div class="container mx-auto">
      <a href="/" class="font-bold">{{ config.APP_NAME|default(""'$(basename "$PWD")'"") }}</a>
    </div>
  </nav>
  
  <main class="container mx-auto flex-grow p-4">
    {% block content %}{% endblock %}
  </main>
  
  <footer class="bg-gray-100 p-4 text-center text-gray-500 text-sm">
    <div class="container mx-auto">
      &copy; {% now "Y" %} {{ config.APP_NAME|default(""'$(basename "$PWD")'"") }}
    </div>
  </footer>
  
  <script src="{{ url_for("static", filename="js/htmx.min.js") }}"></script>
  {% block scripts %}{% endblock %}
</body>
</html>'

create_file_if_missing "app/templates/index.html" '{% extends "base.html" %}
{% block content %}
<div class="max-w-lg mx-auto my-12 p-6 bg-white rounded-lg shadow-md">
  <h1 class="text-4xl font-bold text-indigo-600 text-center">It works! 🎉</h1>
  <p class="mt-4 text-center">Edit <code class="bg-gray-100 px-2 py-1 rounded">app/routes/main.py</code> & reload.</p>
  
  <div class="mt-8 border-t pt-4">
    <h2 class="text-lg font-medium text-gray-700 mb-2">Try HTMX:</h2>
    <button hx-get="/api/health" hx-swap="innerHTML" hx-target="#htmx-demo" class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">
      Click me
    </button>
    <div id="htmx-demo" class="mt-2 p-3 bg-gray-50 rounded"></div>
  </div>
</div>
{% endblock %}'

# ---- misc ------------------------------------------------------------------
create_file_if_missing ".gitignore" '# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.python-version

# Flask
instance/
.webassets-cache

# Frontend
node_modules/
app/static/css/tailwind.css
app/static/js/htmx.min.js

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Editor directories and files
.idea/
.vscode/
*.swp
*.swo
*~
'

create_file_if_missing "README.md" '# '"$PROJECT"'

Bootstrapped with `new_flask.sh`.

## Development Setup

```bash
# Activate virtual environment
pyenv activate '"$PROJECT"'

# Install dependencies (if you deleted requirements.txt)
# pip install -r requirements.txt

# Start frontend watcher (in a separate terminal)
npm run dev

# Run development server
flask run
```

## Database Setup

This project supports both SQLite (default) and PostgreSQL.

### Using SQLite (default)
No additional setup required. The database will be created at `instance/app.db` when you run:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Using PostgreSQL
1. Install and start PostgreSQL on your system
2. Create a database: `createdb '"$PROJECT"'`
3. Update the `.env` file:
   ```
   DB_TYPE=postgres
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME='"$PROJECT"'
   ```
4. Run migrations:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

## Frontend Development

### Tailwind CSS
- **Development**: `npm run dev` - Watches for changes and rebuilds CSS
- **Production**: `npm run build` - Builds minified CSS and copies HTMX

### HTMX
HTMX is managed via npm and copied to static files during build. The library is available at `/static/js/htmx.min.js`.

## Testing
```bash
pytest
```

## Production Deployment
For production, remember to:
1. Set a strong `SECRET_KEY` in the `.env` file
2. Set `FLASK_DEBUG=0` in the `.env` file
3. Use a proper database (PostgreSQL recommended)
4. Build assets for production: `npm run build`
5. Use a production WSGI server like gunicorn

## Node.js Version
This project targets Node.js 20+. Use nvm/fnm for version management:
```bash
nvm use  # or fnm use
```
'

echo "✅ $PROJECT setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate your virtual environment:   pyenv activate $PROJECT"
echo "2. Start frontend watcher:              npm run dev"
echo "3. Initialize the database:             flask db init && flask db migrate -m 'Initial migration' && flask db upgrade"
echo "4. Start the Flask development server:  flask run"
echo ""
echo "Happy building! 🚀"