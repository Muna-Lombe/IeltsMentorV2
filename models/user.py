from extensions import db  # Import the db instance from extensions
from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger, TypeDecorator, JSON
from sqlalchemy.dialects.postgresql import JSONB # For JSONB type
from sqlalchemy.orm import relationship, attributes
import time
from typing import Dict, Any, Optional
import json
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import JSON
from sqlalchemy import types

class JSONBType(TypeDecorator):
    """
    Use JSONB for PostgreSQL and JSON for other databases.
    This allows using a unified model definition for both production (PostgreSQL)
    and testing (e.g., SQLite) environments.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

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

    # New fields for Phase 2 statistics
    stats = Column(JSONBType, nullable=True, default=lambda: {
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
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    groups_taught = relationship("Group", back_populates="teacher", foreign_keys='Group.teacher_id')
    created_exercises = relationship("TeacherExercise", back_populates="creator", foreign_keys='TeacherExercise.creator_id')

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
        """
        Update user statistics for a specific section.
        
        Args:
            section: The section to update (reading, writing, listening, speaking)
            stats_update: Dictionary of statistics to update
        """
        if not self.stats:
            self.stats = {}
        if section not in self.stats:
            self.stats[section] = {}
        
        # Update the section stats
        current_section_stats = self.stats[section].copy()
        current_section_stats.update(stats_update)
        self.stats[section] = current_section_stats
        
        # Flag the 'stats' attribute as modified to ensure it's saved
        attributes.flag_modified(self, "stats")

    def get_section_stats(self, section: str) -> Dict[str, Any]:
        """
        Get statistics for a specific section.
        
        Args:
            section: The section to get stats for
            
        Returns:
            Dictionary of section statistics
        """
        if not self.stats or section not in self.stats:
            return {}
        return self.stats[section]

    def is_teacher(self) -> bool:
        """Check if user is a teacher."""
        return self.is_admin

    def is_botmaster(self) -> bool:
        """Check if user is a botmaster."""
        return self.is_botmaster

    def get_full_name(self) -> str:
        """Get user's full name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return ' '.join(parts) if parts else 'Unknown'

    def update_skill_level(self, new_level: str) -> None:
        """
        Update user's skill level.
        
        Args:
            new_level: New skill level (e.g., 'Beginner', 'Intermediate', 'Advanced')
        """
        self.skill_level = new_level

    def get_practice_sessions(self, section: Optional[str] = None) -> list:
        """
        Get user's practice sessions, optionally filtered by section.
        
        Args:
            section: Optional section to filter by
            
        Returns:
            List of practice sessions
        """
        if section:
            return [session for session in self.practice_sessions if session.section == section]
        return self.practice_sessions 