from extensions import db
from sqlalchemy.orm import relationship
import datetime
from .user import JSONBType

class TeacherExercise(db.Model):
    __tablename__ = 'teacher_exercises'

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    exercise_type = db.Column(db.String(20), nullable=False)
    content = db.Column(JSONBType, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False, nullable=False)

    creator = relationship("User", back_populates="created_exercises")

    def __repr__(self):
        return f'<TeacherExercise {self.title}>' 