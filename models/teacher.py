from extensions import db
from sqlalchemy.orm import relationship
import datetime

class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    api_token = db.Column(db.String(255), unique=True, nullable=True)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approval_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="teacher_profile")

    def __repr__(self):
        return f'<Teacher for {self.user.username}>' 