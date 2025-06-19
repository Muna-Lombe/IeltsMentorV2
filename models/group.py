from extensions import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime

# Association Table for the many-to-many relationship between Users and Groups
group_membership_table = Table('group_membership', db.Model.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

class Group(db.Model):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to the Teacher model
    teacher = relationship("Teacher", back_populates="groups")
    
    # Many-to-many relationship with User (students)
    members = relationship("User", secondary=group_membership_table, back_populates="groups")
    
    # Relationship to Homework
    homework_assignments = relationship("Homework", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}', teacher_id={self.teacher_id})>" 