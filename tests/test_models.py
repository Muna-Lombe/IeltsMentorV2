import unittest
import time

from models.user import User # Adjust import path if your models are elsewhere

class TestUserModel(unittest.TestCase):

    def test_user_creation_defaults(self):
        """Test basic User model creation and default values."""
        telegram_id = 123456789
        user = User(user_id=telegram_id)

        self.assertEqual(user.user_id, telegram_id)
        self.assertIsNone(user.first_name)
        self.assertIsNone(user.last_name)
        self.assertIsNone(user.username)
        self.assertIsNone(user.preferred_language)
        
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_botmaster)
        
        self.assertIsNotNone(user.joined_at)
        self.assertIsInstance(user.joined_at, float)
        # Check if joined_at is a recent timestamp (e.g., within the last 5 seconds)
        self.assertAlmostEqual(user.joined_at, time.time(), delta=5)

    def test_user_creation_with_all_fields(self):
        """Test User model creation with all fields provided."""
        telegram_id = 987654321
        first_name = "Test"
        last_name = "User"
        username = "testuser"
        lang = "en"
        join_time = time.time() - 3600 # An hour ago

        user = User(
            user_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            preferred_language=lang,
            is_admin=True,
            is_botmaster=True,
            joined_at=join_time
        )

        self.assertEqual(user.user_id, telegram_id)
        self.assertEqual(user.first_name, first_name)
        self.assertEqual(user.last_name, last_name)
        self.assertEqual(user.username, username)
        self.assertEqual(user.preferred_language, lang)
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_botmaster)
        self.assertEqual(user.joined_at, join_time)

if __name__ == '__main__':
    unittest.main() 