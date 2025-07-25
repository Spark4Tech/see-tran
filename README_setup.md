# see-tran

Bootstrapped with `new_flask.sh`.

## Development Setup

```bash
# Activate virtual environment
pyenv activate see-tran

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
2. Create a database: `createdb see-tran`
3. Update the `.env` file:
   ```
   DB_TYPE=postgres
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME=see-tran
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

