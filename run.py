# run.py
from app import create_app, db
from app.models.tran import (
    Agency, FunctionalArea, Vendor, Component,
    IntegrationPoint, UserRole, UpdateLog
)
import os

# Create the Flask app using the factory pattern
# The create_app() function now handles config selection internally
app = create_app()

# Ensure models are imported so Flask-Migrate can detect them
@app.shell_context_processor
def make_shell_context():
    return {
        'app': app,
        'db': db,
        'Agency': Agency,                    # was TransitSystem
        'FunctionalArea': FunctionalArea,
        'Vendor': Vendor,
        'Component': Component,              # was System
        'IntegrationPoint': IntegrationPoint,
        'UserRole': UserRole,
        'UpdateLog': UpdateLog
    }

if __name__ == '__main__':
    app.run(debug=True)