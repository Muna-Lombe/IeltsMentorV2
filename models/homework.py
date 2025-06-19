from extensions import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

class Homework(db.Model):
    __tablename__ = 'homework'

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey('teacher_exercises.id'), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=True)
    instructions = Column(Text, nullable=True)

    # Relationships
    exercise = relationship("TeacherExercise")
    group = relationship("Group", back_populates="homework_assignments")
    assigned_by = relationship("Teacher")
    submissions = relationship("HomeworkSubmission", back_populates="homework", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Homework(id={self.id}, exercise_id={self.exercise_id}, group_id={self.group_id})>"


class HomeworkSubmission(db.Model):
    __tablename__ = 'homework_submissions'

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey('homework.id'), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    content = Column(JSON, nullable=False)
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    # Relationships
    homework = relationship("Homework", back_populates="submissions")
    student = relationship("User", back_populates="homework_submissions")

    def __repr__(self):
        return f"<HomeworkSubmission(id={self.id}, homework_id={self.homework_id}, student_id={self.student_id})>" 