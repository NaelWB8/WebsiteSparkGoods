from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import inspect, text
from config import Config
from app.models import db, Badge

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    CORS(app, supports_credentials=True, resources={
        r"/api/*": {
            "origins": ["http://localhost:5000", "http://127.0.0.1:5000",
                        "http://localhost:8000", "http://127.0.0.1:8000"],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True
        }
    })

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('index.html'), 404

    return app

def initialize_database(app):
    with app.app_context():
        db.create_all()
        _migrate_legacy_schema()

        initial_badges = [
            'Pemula Dermawan',
            'Multi Kontributor',
            'Fashion Giver',
            'Live Warrior',
            'Sultan Dermawan'
        ]

        for badge_name in initial_badges:
            if not Badge.query.filter_by(name=badge_name).first():
                db.session.add(Badge(name=badge_name))

        db.session.commit()


def _migrate_legacy_schema():
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()

    if 'user' in table_names:
        user_columns = {col['name'] for col in inspector.get_columns('user')}
        with db.engine.begin() as conn:
            if 'password_hash' not in user_columns:
                conn.execute(text(
                    "ALTER TABLE user ADD COLUMN password_hash VARCHAR(200) DEFAULT ''"))
            if 'points' not in user_columns:
                conn.execute(text(
                    "ALTER TABLE user ADD COLUMN points INTEGER DEFAULT 0"))
            if 'tiktok_id' not in user_columns:
                conn.execute(text(
                    "ALTER TABLE user ADD COLUMN tiktok_id VARCHAR(100)"))
            if 'level' not in user_columns:
                conn.execute(text(
                    "ALTER TABLE user ADD COLUMN level VARCHAR(20) DEFAULT 'Bronze'"))

    if 'donation' in table_names:
        donation_columns = {col['name'] for col in inspector.get_columns('donation')}
        with db.engine.begin() as conn:
            if 'points_earned' not in donation_columns:
                conn.execute(text(
                    "ALTER TABLE donation ADD COLUMN points_earned INTEGER DEFAULT 0"))
            if 'created_at' not in donation_columns:
                conn.execute(text(
                    "ALTER TABLE donation ADD COLUMN created_at DATETIME"))
