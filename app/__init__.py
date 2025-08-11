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
        # Import config classes
        from config import DevelopmentConfig, ProductionConfig, TestConfig
        
        # Use DevelopmentConfig by default, or based on environment
        flask_env = os.environ.get('FLASK_ENV', 'development')
        if flask_env == 'production':
            app.config.from_object(ProductionConfig)
        elif flask_env == 'testing':
            app.config.from_object(TestConfig)
        else:
            app.config.from_object(DevelopmentConfig)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models so Flask-Migrate can detect them
    with app.app_context():
        from app.models import tran  # Import existing models
        from app.models import gtfs  # Import GTFS models
    
    # register blueprints
    from app.routes.main import main as main_bp
    app.register_blueprint(main_bp)

    from app.routes.agency import agency_bp
    app.register_blueprint(agency_bp)
    from app.routes.integrations import integration_bp
    app.register_blueprint(integration_bp)
    
    return app
