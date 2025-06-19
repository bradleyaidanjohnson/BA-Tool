from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    features = db.relationship('Feature', backref='project', lazy=True, cascade="all, delete-orphan")

class Feature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    parent_feature_id = db.Column(db.Integer, db.ForeignKey('feature.id'), nullable=True)
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Feature', remote_side=[id], backref='subfeatures')
    user_stories = db.relationship('UserStory', backref='feature', lazy=True, cascade="all, delete-orphan")

class UserStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.Integer, db.ForeignKey('feature.id'), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    details = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('personnel.id'))
    created_by = db.relationship('Personnel', foreign_keys=[created_by_id])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))
    ado_added = db.Column(db.Boolean, default=False)

    attachments = db.relationship('Attachment', backref='story', lazy=True, cascade="all, delete-orphan")
    notes = db.relationship('Note', back_populates='story', cascade="all, delete-orphan")

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('user_story.id'), nullable=False)

class Personnel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    role = db.Column(db.String(50))
    scope = db.Column(db.String(100))

    notes = db.relationship('Note', backref='personnel', lazy=True)

    def __repr__(self):
        return f"<Personnel {self.name}>"

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('user_story.id'), nullable=False)
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    note_type = db.Column(db.String(50))
    details = db.Column(db.Text)

    story = db.relationship('UserStory', back_populates='notes')
