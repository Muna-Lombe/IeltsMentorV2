import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TranslationSystem:
    _translations: Dict[str, Dict[str, Any]] = {}
    _fallback_language = "en"
    _supported_languages = ["en", "es"]

    @classmethod
    def load_translations(cls):
        """Loads all translation files."""
        for lang in cls._supported_languages:
            cls._load_translation_file(lang)

    @classmethod
    def _load_translation_file(cls, lang_code: str) -> None:
        """Loads a single translation file."""
        if lang_code not in cls._translations:
            try:
                # Build an absolute path to the locales directory
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(base_dir, 'locales', f'{lang_code}.json')
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    cls._translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translations for {lang_code}")
            except FileNotFoundError:
                logger.error(f"Translation file not found at {file_path}")
                cls._translations[lang_code] = {}
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON for {lang_code}")
                cls._translations[lang_code] = {}

    @classmethod
    def get_message(cls, category: str, key: str, lang_code: str, **kwargs) -> str:
        """Retrieves a translated message string."""
        if not cls._translations:
            cls.load_translations()

        message_template = cls._translations.get(lang_code, {}).get(category, {}).get(key)

        if not message_template and lang_code != cls._fallback_language:
            message_template = cls._translations.get(cls._fallback_language, {}).get(category, {}).get(key)
        
        if not message_template:
            logger.error(f"Message not found for {category}.{key} in any language")
            return f"[Missing translation: {category}.{key}]"
        
        try:
            return message_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format key {e} for message '{category}.{key}'")
            return message_template

    @classmethod
    def detect_language(cls, user_data: Dict[str, Any]) -> str:
        """Detects user's language, falling back to the default."""
        lang_code = user_data.get('language_code', '').split('-')[0]
        return lang_code if lang_code in cls._supported_languages else cls._fallback_language

    @classmethod
    def get_error_message(cls, error_type: str, language: str = 'en') -> str:
        """Gets a standardized error message."""
        return cls.get_message('errors', error_type, language)

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