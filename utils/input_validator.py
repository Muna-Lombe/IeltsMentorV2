import json
import re

class InputValidator:
    @staticmethod
    def sanitize_text_input(text, max_length=1000):
        """Sanitize text input for database storage"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove potentially dangerous characters
        cleaned = re.sub(r'[<>"\\\']', '', text)
        # Limit length
        return cleaned[:max_length].strip()
        
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