from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger
from sqlalchemy.dialects.postgresql import JSONB # For JSONB type
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import time

# Define the base for declarative models
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)  # Telegram User ID
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    username = Column(String(100), unique=True, nullable=True, index=True) # Telegram username
    joined_at = Column(Float, default=time.time, nullable=False)  # Unix timestamp
    is_admin = Column(Boolean, default=False, nullable=False)  # Teacher flag
    is_botmaster = Column(Boolean, default=False, nullable=False)  # Super admin flag
    preferred_language = Column(String(10), nullable=True)

    # New fields for Phase 2 statistics
    stats = Column(JSONB, nullable=True, default=lambda: {
        'reading': {'correct': 0, 'total': 0, 'mcq_attempted': 0, 'mcq_correct': 0},
        'writing': {'tasks_submitted': 0, 'avg_score': 0},
        'listening': {'correct': 0, 'total': 0},
        'speaking': {'sessions_completed': 0, 'avg_fluency': 0}
        # Add more detailed stats as features develop
    })
    placement_test_score = Column(Float, nullable=True)
    skill_level = Column(String(50), nullable=True, default="Beginner") # Default skill level

    # Relationship to PracticeSession model
    practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, username='{self.username}')>" 