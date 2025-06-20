from extensions import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class TeacherExercise(db.Model):
    __tablename__ = 'teacher_exercises'

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    exercise_type = Column(String(20), nullable=False)
    content = Column(JSON, nullable=False)
    difficulty = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = Column(Boolean, default=False, nullable=False)

    creator = relationship("Teacher", back_populates="created_exercises")

    def __repr__(self):
        return f'<TeacherExercise {self.title}>'

    def to_dict(self):
        """Serializes the object to a dictionary."""
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'title': self.title,
            'description': self.description,
            'exercise_type': self.exercise_type,
            'content': self.content,
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_published': self.is_published
        }