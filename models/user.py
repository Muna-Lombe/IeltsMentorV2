from extensions import db
from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger, JSON
from sqlalchemy.orm import relationship, attributes
import time
from typing import Dict, Any, Optional
from datetime import datetime

class User(db.Model):
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

    stats = Column(JSON, nullable=True, default=lambda: {
        'reading': {'correct': 0, 'total': 0, 'mcq_attempted': 0, 'mcq_correct': 0},
        'writing': {'tasks_submitted': 0, 'avg_score': 0},
        'listening': {'correct': 0, 'total': 0},
        'speaking': {'sessions_completed': 0, 'avg_fluency': 0}
    })
    placement_test_score = Column(Float, nullable=True)
    skill_level = Column(String(50), nullable=True, default="Beginner") # Default skill level

    # Relationships
    practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # taught_groups = relationship("Group", back_populates="teacher")
    
    # Relationship to HomeworkSubmissions
    homework_submissions = relationship("HomeworkSubmission", back_populates="student", cascade="all, delete-orphan")

    # Association for group membership
    group_associations = relationship("GroupMembership", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, username='{self.username}')>" 

    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'joined_at': self.joined_at,
            'is_admin': self.is_admin,
            'is_botmaster': self.is_botmaster,
            'preferred_language': self.preferred_language,
            'stats': self.stats,
            'placement_test_score': self.placement_test_score,
            'skill_level': self.skill_level
        }

    def update_stats(self, section: str, stats_update: Dict[str, Any]) -> None:
        if not self.stats:
            self.stats = {}
        if section not in self.stats:
            self.stats[section] = {}
        
        current_section_stats = self.stats[section].copy()
        current_section_stats.update(stats_update)
        self.stats[section] = current_section_stats
        
        attributes.flag_modified(self, "stats")

    def get_section_stats(self, section: str) -> Dict[str, Any]:
        if not self.stats or section not in self.stats:
            return {}
        return self.stats[section]

    def is_teacher(self) -> bool:
        return self.is_admin

    def get_full_name(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return ' '.join(parts) if parts else 'Unknown'

    def update_skill_level(self, new_level: str) -> None:
        self.skill_level = new_level

    def get_practice_sessions(self, section: Optional[str] = None) -> list:
        if section:
            return [session for session in self.practice_sessions if session.section == section]
        return self.practice_sessions 

    @property
    def groups(self):
        return [association.group for association in self.group_associations] 