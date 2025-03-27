from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_db(app):
    db.init_app(app)
    # Import models here to avoid circular imports
    from models import BlogPost, User, Comment
    with app.app_context():
        db.create_all() 