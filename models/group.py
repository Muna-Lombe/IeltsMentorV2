from extensions import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class GroupMembership(db.Model):
    __tablename__ = 'group_memberships'
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", back_populates="group_associations")
    group = db.relationship("Group", back_populates="member_associations")

class Group(db.Model):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to the Teacher model
    teacher = db.relationship('Teacher', back_populates='taught_groups')
    homework_assignments = relationship("Homework", back_populates="group", cascade="all, delete-orphan")
    
    # Many-to-many relationship with User (students)
    member_associations = db.relationship('GroupMembership', back_populates='group', cascade="all, delete-orphan")

    # Helper to get members directly
    @property
    def members(self):
        return [association.student for association in self.member_associations]

    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}', teacher_id={self.teacher_id})>" 