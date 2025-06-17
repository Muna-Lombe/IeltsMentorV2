import json
import re

class InputValidator:
    """A utility class for validating and sanitizing user inputs."""

    @staticmethod
    def validate_user_id(user_id: int) -> int | None:
        """
        Validates a Telegram user ID.
        
        Args:
            user_id: The user ID to validate.
            
        Returns:
            The user ID if it is valid, otherwise None.
        """
        if not isinstance(user_id, int):
            return None
        # Telegram user IDs are positive integers.
        if user_id <= 0:
            return None
        return user_id

    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 500) -> str:
        """
        Sanitizes text input to prevent injection attacks and limit length.
        
        Args:
            text: The text to sanitize.
            max_length: The maximum allowed length of the text.
            
        Returns:
            The sanitized text.
        """
        if not isinstance(text, str):
            return ""
        
        # Remove characters that could be used for injection attacks.
        # This is a basic example; a real-world app might need a more robust solution.
        sanitized_text = re.sub(r'[<>/;"\']', '', text)
        
        # Truncate to the maximum length
        return sanitized_text[:max_length].strip()

    @staticmethod
    def validate_exercise_content(content_text: str):
        """
        Validate exercise content structure from a JSON string.
        Returns the parsed dictionary if valid, otherwise None.
        """
        try:
            content = json.loads(content_text)
        except json.JSONDecodeError:
            return None

        if not isinstance(content, dict):
            return None
        
        required_fields = ['questions']
        for field in required_fields:
            if field not in content:
                return None
        
        # Validate questions structure
        questions = content.get('questions', [])
        if not isinstance(questions, list) or not questions:
            return None
        
        for question in questions:
            if not isinstance(question, dict):
                return None
            # For now, we just require a 'text' field. This can be expanded.
            if 'text' not in question or not question['text']:
                return None
        
        return content 