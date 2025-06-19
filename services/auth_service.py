import secrets
from models import Teacher, User
from extensions import db

class AuthService:
    """
    Handles authentication-related services, such as API token
    generation and validation for teachers.
    """

    @staticmethod
    def generate_api_token() -> str:
        """
        Generates a secure, URL-safe random token.
        Returns:
            A 64-character hex token.
        """
        return secrets.token_hex(32)

    @staticmethod
    def validate_token(api_token: str) -> User | None:
        """
        Validates an API token and returns the associated user if valid.
        Args:
            api_token: The API token to validate.
        Returns:
            The User object if the token is valid and the teacher is approved, otherwise None.
        """
        if not api_token:
            return None

        teacher = db.session.query(Teacher).filter_by(api_token=api_token).first()

        if teacher and teacher.is_approved:
            return teacher.user
        
        return None

    @staticmethod
    def assign_token_to_teacher(teacher: Teacher) -> str:
        """
        Generates and assigns a new API token to a teacher, ensuring it's unique.
        Args:
            teacher: The Teacher object to assign the token to.
        Returns:
            The newly generated token.
        """
        while True:
            token = AuthService.generate_api_token()
            if not db.session.query(Teacher).filter_by(api_token=token).first():
                teacher.api_token = token
                db.session.commit()
                return token 