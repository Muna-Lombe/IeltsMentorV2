import json
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en"
TRANSLATIONS_DIR = "data/translations"

class TranslationSystem:
    def __init__(self, translations_dir: str = TRANSLATIONS_DIR):
        self.translations = {}
        self.translations_dir = translations_dir
        self._load_translations()

    def _load_translations(self):
        """Loads all .json translation files from the specified directory."""
        if not os.path.exists(self.translations_dir):
            logger.warning(f"Translations directory not found: {self.translations_dir}. Creating it.")
            os.makedirs(self.translations_dir, exist_ok=True)
            # Create a dummy en.json to avoid errors if it's the first run
            dummy_en_content = {
                "greetings": {
                    "hello": "Hello, {name}!"
                },
                "errors": {
                    "translation_not_found": "Translation not found for key: {key}"
                }
            }
            try:
                with open(os.path.join(self.translations_dir, "en.json"), 'w', encoding='utf-8') as f:
                    json.dump(dummy_en_content, f, ensure_ascii=False, indent=4)
                logger.info(f"Created dummy en.json in {self.translations_dir}")
            except IOError as e:
                logger.error(f"Could not create dummy en.json: {e}")
                return # Stop if we can't even create a dummy file

        for filename in os.listdir(self.translations_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]  # Remove .json
                filepath = os.path.join(self.translations_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translations for language: {lang_code} from {filename}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from {filepath}: {e}")
                except Exception as e:
                    logger.error(f"Error loading translation file {filepath}: {e}")
        if not self.translations:
            logger.warning("No translation files were loaded. The system will use fallback messages.")

    def get_message(self, category: str, key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """Retrieves a localized message with dynamic content insertion."""
        lang_to_try = language if language in self.translations else DEFAULT_LANGUAGE

        if lang_to_try not in self.translations:
            # This case means even English (DEFAULT_LANGUAGE) is not loaded.
            logger.error(f"Default language '{DEFAULT_LANGUAGE}' not found in translations. Key: {category}.{key}")
            return f"Critical Error: Default translations missing. Key: {category}.{key}"

        translation_category = self.translations[lang_to_try].get(category)
        if not translation_category:
            # Category not found in the tried language, try fallback language if not already tried
            if lang_to_try != DEFAULT_LANGUAGE and DEFAULT_LANGUAGE in self.translations:
                logger.warning(f"Category '{category}' not found for language '{lang_to_try}'. Falling back to '{DEFAULT_LANGUAGE}'.")
                translation_category = self.translations[DEFAULT_LANGUAGE].get(category)
            
            if not translation_category:
                logger.error(f"Category '{category}' not found even in default language '{DEFAULT_LANGUAGE}' for key '{key}'.")
                # Fallback to a generic error message from the default language if possible
                return self._get_fallback_error_message(key)

        message_template = translation_category.get(key)
        if not message_template:
            # Key not found in the category, try fallback language if not already tried
            if lang_to_try != DEFAULT_LANGUAGE and DEFAULT_LANGUAGE in self.translations:
                logger.warning(f"Key '{key}' in category '{category}' not found for lang '{lang_to_try}'. Falling back to '{DEFAULT_LANGUAGE}'.")
                default_translation_category = self.translations[DEFAULT_LANGUAGE].get(category)
                if default_translation_category:
                    message_template = default_translation_category.get(key)
            
            if not message_template:
                logger.error(f"Key '{key}' in category '{category}' not found even in default language '{DEFAULT_LANGUAGE}'.")
                return self._get_fallback_error_message(key)
        
        try:
            return message_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing placeholder '{e}' for message key '{category}.{key}' in language '{lang_to_try}'. Template: '{message_template}'")
            # Return the template itself or a more specific error
            return f"Formatting error for key {category}.{key} (missing placeholder: {e})"
        except Exception as e:
            logger.error(f"Error formatting message for key '{category}.{key}': {e}. Template: '{message_template}'")
            return message_template # Return unformatted template on other errors

    def _get_fallback_error_message(self, key: str) -> str:
        """Provides a standardized fallback message if a key is entirely missing."""
        if DEFAULT_LANGUAGE in self.translations and \
           'errors' in self.translations[DEFAULT_LANGUAGE] and \
           'translation_not_found' in self.translations[DEFAULT_LANGUAGE]['errors']:
            try:
                return self.translations[DEFAULT_LANGUAGE]['errors']['translation_not_found'].format(key=key)
            except KeyError:
                 return f"[Translation not found for key: {key} AND error message format failed]"
        return f"[Translation not found for key: {key}] (and default error msg missing)"

# Global instance (or manage through dependency injection in Flask app)
# For simplicity here, a global instance that can be imported.
ts = TranslationSystem()

def get_message(category: str, key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Convenience function to access the global TranslationSystem instance."""
    return ts.get_message(category, key, language, **kwargs)

# Example usage (for testing this file directly)
if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler()) # Show logs in console for testing
    logger.setLevel(logging.INFO)
    
    print("--- Translation System Test ---")
    # ts will load from data/translations/en.json (dummy created if not exists)
    
    print(f"Translations loaded: {ts.translations.keys()}")
    
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
    es_path = os.path.join(TRANSLATIONS_DIR, "es.json")
    try:
        with open(es_path, 'w', encoding='utf-8') as f_es:
            json.dump(spanish_translations, f_es, ensure_ascii=False, indent=4)
        print(f"Created dummy es.json at {es_path}")
        ts._load_translations() # Reload to pick up es.json
        print(f"Translations reloaded: {ts.translations.keys()}")
        message_hello_es_direct = get_message("greetings", "hello", "es", name=name)
        print(f"Spanish ('es') Hello (direct): {message_hello_es_direct}")
    except Exception as e:
        print(f"Could not create or load dummy es.json for testing: {e}")

    print("--- End of Test ---") 