import pytest
import time

from models.user import User # Adjust import path if your models are elsewhere

class TestUserModel:
    def test_user_creation(self, db_session):
        """Test basic user creation and default values."""
        user = User(
            user_id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser",
            preferred_language="en"
        )
        db_session.add(user)
        db_session.commit()
        
        # Query the user back from the database
        retrieved_user = db_session.query(User).filter_by(user_id=123456789).first()
        
        assert retrieved_user is not None
        assert retrieved_user.id is not None
        assert retrieved_user.username == "testuser"
        assert retrieved_user.is_admin is False
        assert retrieved_user.is_botmaster is False
        assert "reading" in retrieved_user.stats  # Check default stats
        assert retrieved_user.skill_level == "Beginner"
        assert abs(retrieved_user.joined_at - time.time()) < 5

    def test_get_full_name(self, db_session):
        """Test the get_full_name helper method."""
        user1 = User(user_id=1, first_name="John", last_name="Doe")
        user2 = User(user_id=2, first_name="Jane")
        user3 = User(user_id=3, last_name="Smith")
        user4 = User(user_id=4)
        
        assert user1.get_full_name() == "John Doe"
        assert user2.get_full_name() == "Jane"
        assert user3.get_full_name() == "Smith"
        assert user4.get_full_name() == "Unknown"

    def test_update_stats(self, sample_user, db_session):
        """Test the update_stats method."""
        # sample_user is already in the session from the fixture
        sample_user.update_stats("reading", {"correct": 5, "total": 10})
        
        db_session.commit()
        
        retrieved_user = db_session.query(User).get(sample_user.id)
        
        assert retrieved_user.stats["reading"]["correct"] == 5
        assert retrieved_user.stats["reading"]["total"] == 10
        # Ensure other stats are untouched
        assert retrieved_user.stats["writing"]["tasks_submitted"] == 0

    def test_to_dict(self, sample_user):
        """Test the to_dict method."""
        user_dict = sample_user.to_dict()
        
        assert isinstance(user_dict, dict)
        assert user_dict['user_id'] == 123456789
        assert user_dict['username'] == "testuser"
        assert user_dict['is_admin'] is False
        assert 'stats' in user_dict
        assert 'skill_level' in user_dict

    def test_role_helpers(self, sample_user):
        """Test the is_teacher and is_botmaster helpers."""
        assert sample_user.is_teacher() is False
        assert sample_user.is_botmaster() is False
        
        sample_user.is_admin = True
        sample_user.is_botmaster = True
        
        assert sample_user.is_teacher() is True
        assert sample_user.is_botmaster() is True

if __name__ == '__main__':
    pytest.main() 