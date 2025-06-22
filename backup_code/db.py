from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(80), index=True)
    author = db.Column(db.String(120))
    rating = db.Column(db.Integer)
    time = db.Column(db.DateTime)
    text = db.Column(db.Text)
