import os
import logging
import json # For potential JSON parsing if AI returns it
from openai import OpenAI, OpenAIError # Import the OpenAI library and OpenAIError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)

    def generate_explanation(self, query: str, context: str, language: str = 'en') -> str:
        """
        Generates an AI-powered explanation for an IELTS concept.
        
        Args:
            query: The specific concept to explain (e.g., "present perfect").
            context: The broader context (e.g., "grammar").
            language: The target language for the explanation.
            
        Returns:
            A string containing the explanation.
        """
        try:
            prompt = (
                f"You are an expert IELTS tutor. Explain the concept of '{query}' "
                f"in the context of '{context}' for an IELTS student. "
                f"Provide clear examples. The explanation should be in {language}."
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # As per project rules
                messages=[
                    {"role": "system", "content": "You are a helpful IELTS preparation assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            logger.error(f"OpenAI API error during explanation generation: {e}")
            raise  # Re-raise to be caught by safe_handler

    def generate_definition(self, word: str, language: str = 'en') -> str:
        """
        Generates a definition for a word, including examples.
        
        Args:
            word: The word to define.
            language: The target language for the definition.
            
        Returns:
            A string containing the definition, part of speech, and examples.
        """
        try:
            prompt = (
                f"You are an expert IELTS tutor. Provide a clear definition for the word '{word}'. "
                f"Include its part of speech, and at least two example sentences relevant to the IELTS exam. "
                f"The response should be in {language}."
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful IELTS preparation assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            logger.error(f"OpenAI API error during definition generation: {e}")
            raise

# Example usage (for testing this file directly)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) # Ensure root logger is configured for stream output
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

    print("\n--- OpenAIService Test with Live API Calls ---")
    # THIS WILL MAKE ACTUAL API CALLS IF OPENAI_API_KEY IS SET AND VALID
    # ENSURE YOU HAVE CREDITS AND ARE OKAY WITH THE COST.
    try:
        service = OpenAIService()
        if service.client:
            print("OpenAIService initialized.")
            
            expl_query = "the main difference between 'affect' and 'effect' in academic writing"
            print(f"\nTesting generate_explanation for: '{expl_query}'...")
            explanation = service.generate_explanation(expl_query, context="common grammar errors for IELTS students", language="en")
            if explanation:
                print(f"-> Explanation Received:\n{explanation}")
            else:
                print("-> Failed to get explanation.")

            def_word = "ubiquitous"
            print(f"\nTesting generate_definition for: '{def_word}'...")
            definition = service.generate_definition(def_word, language="en")
            if definition:
                print(f"-> Definition Received:\n{definition}")
            else:
                print("-> Failed to get definition.")
            
            def_word_es = "perseverancia"
            print(f"\nTesting generate_definition for: '{def_word_es}' in Spanish...")
            definition_es = service.generate_definition(def_word_es, language="es")
            if definition_es:
                print(f"-> Definición Recibida:\n{definition_es}")
            else:
                print("-> No se pudo obtener la definición.")

        else:
            print("OpenAIService client could not be initialized. Check API key and logs.")
            
    except ValueError as ve:
        print(f"ERROR: Configuration issue (likely API key missing or invalid in .env): {ve}")
    except Exception as e:
        print(f"An unexpected error occurred during OpenAIService live test: {e}")
    print("--- End of Live Test ---") 