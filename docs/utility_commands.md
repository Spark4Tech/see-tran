# Utility Commands

Update these based on production hostname etc.

### Copy app.db to production
scp ./instance/app.db user@vm:/srv/resource2/instance/app.db

### Make backup of local database, for seeding of production
sqlite3 ./instance/app.db ".backup 'backups/app-prod-seed.sqlite'"

