from extensions import db  # Import the db instance from extensions
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For default datetime

# Import Base from the user model file or a central base file
# from .user import Base # Assuming Base is defined in models/user.py

class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    section = Column(String(50), nullable=False)  # e.g., 'speaking_part1', 'reading_mcq', 'writing_task2'
    
    score = Column(Float, nullable=True)
    total_questions = Column(Integer, nullable=True)
    correct_answers = Column(Integer, nullable=True)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    session_data = Column(JSON, nullable=True) # For storing questions, user answers, AI feedback, etc.

    # Relationship to User model (optional, but good for ORM features)
    user = relationship("User", back_populates="practice_sessions") # Define back_populates on User model later

    def __repr__(self):
        return f"<PracticeSession(id={self.id}, user_id={self.user_id}, section='{self.section}', score={self.score})>"

# To make the relationship work, you would add the following to your User model in models/user.py:
# from sqlalchemy.orm import relationship
# practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan") 