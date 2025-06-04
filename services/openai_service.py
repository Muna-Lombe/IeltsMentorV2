import os
import logging
import json # For potential JSON parsing if AI returns it
from openai import OpenAI # Import the OpenAI library
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        load_dotenv() # Load environment variables from .env
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            raise ValueError("OPENAI_API_KEY is not set. Please set it in your .env file.")
        
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            # Depending on how critical this is, you might want to raise the error
            # or allow the service to be created but in a non-functional state.
            self.client = None # Ensure client is None if initialization fails
            raise # Re-raise the exception to signal a critical failure

    def generate_explanation(self, query: str, context: str = None, language: str = "en") -> str | None:
        """
        Generates an AI-powered explanation for a given query, optionally with context.
        (Rule 5, project_rules.md - GPT-4o, JSON responses if applicable, context management)
        
        Args:
            query (str): The concept or question to explain.
            context (str, optional): Additional context for the explanation.
            language (str, optional): The desired language for the explanation.
        
        Returns:
            str | None: The AI-generated explanation, or None if an error occurs.
        """
        if not self.client:
            logger.error("OpenAI client not initialized. Cannot generate explanation.")
            return None
        
        logger.info(f"Generating explanation for query: '{query}' in language: {language} using gpt-4o")
        system_prompt = f"You are an expert IELTS tutor. Explain the following concept clearly and concisely in {language}. If the query seems to ask for structured data (like a list or steps), try to format your response as a JSON object with a clear top-level key (e.g., \"explanation_steps\"). Otherwise, provide a natural language text explanation."
        user_content = f"Concept to explain: \"{query}\""
        if context:
            user_content += f"\nAdditional context: \"{context}\""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", # As per Rule 5, project_rules.md
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
                # Consider adding temperature, max_tokens if needed
            )
            explanation = response.choices[0].message.content
            logger.debug(f"OpenAI explanation raw response: {explanation}")
            return explanation.strip()
        except Exception as e:
            logger.error(f"OpenAI API call failed for explanation query '{query}': {e}")
            return None

    def generate_definition(self, word: str, language: str = "en") -> str | None:
        """
        Generates a definition for a given word, including usage examples.
        
        Args:
            word (str): The word to define.
            language (str, optional): The desired language for the definition.
            
        Returns:
            str | None: The AI-generated definition, or None if an error occurs.
        """
        if not self.client:
            logger.error("OpenAI client not initialized. Cannot generate definition.")
            return None

        logger.info(f"Generating definition for word: '{word}' in language: {language} using gpt-4o")
        system_prompt = f"You are an IELTS vocabulary assistant. For the given word, provide a comprehensive definition in {language}. Include:
1. Part of speech.
2. Clear definition(s).
3. An example sentence relevant to IELTS contexts if possible.
4. Common synonyms, if any."
        user_content = f"Word to define: \"{word}\""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )
            definition_text = response.choices[0].message.content
            logger.debug(f"OpenAI definition raw response for '{word}': {definition_text}")
            return definition_text.strip()
        except Exception as e:
            logger.error(f"OpenAI API call failed for definition of '{word}': {e}")
            return None

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