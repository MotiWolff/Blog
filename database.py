from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        # Import models here to avoid circular imports
        from models import BlogPost, User, Comment
        # Create all tables
        db.create_all()
        print("Database tables created successfully!") 