import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TranslationSystem:
    _translations: Dict[str, Dict[str, str]] = {}
    _default_language = 'en'
    _supported_languages = ['en', 'es']  # Add more languages as needed

    @classmethod
    def initialize(cls) -> None:
        """Initialize the translation system by loading all translation files."""
        try:
            # Load translations from JSON files in the data/translations directory
            translations_dir = os.path.join('data', 'translations')
            if not os.path.exists(translations_dir):
                os.makedirs(translations_dir)
                logger.info(f"Created translations directory at {translations_dir}")

            for lang in cls._supported_languages:
                file_path = os.path.join(translations_dir, f'{lang}.json')
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cls._translations[lang] = json.load(f)
                    logger.info(f"Loaded translations for {lang}")
                else:
                    logger.warning(f"Translation file not found for {lang}: {file_path}")
                    # Create empty translation file if it doesn't exist
                    cls._translations[lang] = {}
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({}, f, indent=2, ensure_ascii=False)
                    logger.info(f"Created empty translation file for {lang}")

        except Exception as e:
            logger.error(f"Error initializing translation system: {e}")
            raise

    @classmethod
    def get_message(cls, category: str, key: str, language: str = 'en', **kwargs) -> str:
        """
        Get a translated message with optional variable substitution.
        
        Args:
            category: The category of the message (e.g., 'practice', 'error')
            key: The specific message key
            language: The target language code
            **kwargs: Variables to substitute in the message
            
        Returns:
            The translated message with variables substituted
        """
        if not cls._translations:
            cls.initialize()

        # Ensure language is supported, fall back to default if not
        if language not in cls._supported_languages:
            logger.warning(f"Unsupported language {language}, falling back to {cls._default_language}")
            language = cls._default_language

        try:
            # Get the message from translations
            message = cls._translations[language].get(category, {}).get(key)
            
            # If message not found in requested language, try default language
            if not message and language != cls._default_language:
                message = cls._translations[cls._default_language].get(category, {}).get(key)
                logger.warning(f"Message not found for {category}.{key} in {language}, using {cls._default_language}")

            # If still not found, return a fallback message
            if not message:
                logger.error(f"Message not found for {category}.{key} in any language")
                return f"[Missing translation: {category}.{key}]"

            # Substitute variables in the message
            try:
                return message.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing variable in translation {category}.{key}: {e}")
                return message

        except Exception as e:
            logger.error(f"Error getting translation for {category}.{key}: {e}")
            return f"[Translation error: {category}.{key}]"

    @classmethod
    def detect_language(cls, user_data: Dict[str, Any]) -> str:
        """
        Detect user's preferred language from Telegram user data.
        
        Args:
            user_data: Dictionary containing user information from Telegram
            
        Returns:
            The detected language code or default language if not supported
        """
        try:
            # Try to get language from user's Telegram settings
            language_code = user_data.get('language_code', '').lower()
            
            # Check if the detected language is supported
            if language_code in cls._supported_languages:
                return language_code
                
            # If language code is not supported, return default
            logger.info(f"Unsupported language code {language_code}, using default {cls._default_language}")
            return cls._default_language

        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return cls._default_language

    @classmethod
    def get_error_message(cls, error_type: str, language: str = 'en') -> str:
        """
        Get a standardized error message.
        
        Args:
            error_type: The type of error (e.g., 'permission_denied', 'invalid_input')
            language: The target language code
            
        Returns:
            The translated error message
        """
        return cls.get_message('error', error_type, language)

# Global instance (or manage through dependency injection in Flask app)
# For simplicity here, a global instance that can be imported.
ts = TranslationSystem()

def get_message(category: str, key: str, language: str = 'en', **kwargs) -> str:
    """Convenience function to access the global TranslationSystem instance."""
    return ts.get_message(category, key, language, **kwargs)

# Example usage (for testing this file directly)
if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler()) # Show logs in console for testing
    logger.setLevel(logging.INFO)
    
    print("--- Translation System Test ---")
    # ts will load from data/translations/en.json (dummy created if not exists)
    
    print(f"Translations loaded: {ts._translations.keys()}")
    
    # Test existing key from dummy en.json
    name = "User"
    message_hello_en = get_message("greetings", "hello", "en", name=name)
    print(f"English ('en') Hello: {message_hello_en}")

    message_hello_es_fallback = get_message("greetings", "hello", "es", name=name)
    print(f"Spanish ('es') Hello (fallback to en): {message_hello_es_fallback}")

    # Test non-existing key
    message_non_existent = get_message("greetings", "non_existent_key", "en")
    print(f"Non-existent key (en): {message_non_existent}")

    message_non_existent_es = get_message("greetings", "non_existent_key", "es")
    print(f"Non-existent key (es, fallback): {message_non_existent_es}")

    # Test placeholder error
    message_placeholder_missing = get_message("greetings", "hello", "en") # Missing 'name' kwarg
    print(f"Placeholder missing (en): {message_placeholder_missing}")

    # Create a dummy es.json for further testing
    spanish_translations = {
        "greetings": {
            "hello": "Hola, {name}!"
        },
        "user": {
            "welcome_new": "Bienvenido, {name}! Nos alegra tenerte.",
            "welcome_back": "Bienvenido de nuevo, {name}!"
        }
    }
    es_path = os.path.join('data', 'translations', 'es.json')
    try:
        with open(es_path, 'w', encoding='utf-8') as f_es:
            json.dump(spanish_translations, f_es, ensure_ascii=False, indent=4)
        print(f"Created dummy es.json at {es_path}")
        ts._load_translations() # Reload to pick up es.json
        print(f"Translations reloaded: {ts._translations.keys()}")
        message_hello_es_direct = get_message("greetings", "hello", "es", name=name)
        print(f"Spanish ('es') Hello (direct): {message_hello_es_direct}")
    except Exception as e:
        print(f"Could not create or load dummy es.json for testing: {e}")

    print("--- End of Test ---") 