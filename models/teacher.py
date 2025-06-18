from extensions import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    api_token = Column(String(255), unique=True, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    approval_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to the User model
    user = relationship("User", back_populates="teacher_profile")
    
    # Relationship to the Group model
    groups = relationship("Group", back_populates="teacher")

    # Relationship to the TeacherExercise model
    created_exercises = relationship("TeacherExercise", back_populates="creator", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Teacher(id={self.id}, user_id={self.user_id}, is_approved={self.is_approved})>" 