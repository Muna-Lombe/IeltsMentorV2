import os
import logging
import json # For potential JSON parsing if AI returns it
from openai import OpenAI, OpenAIError # Import the OpenAI library and OpenAIError
from dotenv import load_dotenv
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(
            api_key=self.api_key,
            base_url='https://open-ai-proxy-hub-munalombe01.replit.app/api/proxy/v1'
        )

    def speech_to_text(self, audio_file_path: str, prompt: str = "") -> str:
        """
        Transcribes audio to text using OpenAI's Whisper model.
        It handles various audio formats by converting them to MP3.

        Args:
            audio_file_path: The path to the audio file.
            prompt: Optional context to guide the transcription.

        Returns:
            The transcribed text as a string.
        """
        try:
            # Convert audio to MP3 format to ensure compatibility with Whisper
            file_extension = os.path.splitext(audio_file_path)[1].lower()
            if file_extension != ".mp3":
                audio = AudioSegment.from_file(audio_file_path)
                mp3_path = audio_file_path.replace(file_extension, ".mp3")
                audio.export(mp3_path, format="mp3")
                audio_file_path = mp3_path

            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    prompt=prompt
                )
            return transcript.text
        except FileNotFoundError:
            logger.error(f"Audio file not found at: {audio_file_path}")
            raise
        except Exception as e:
            logger.error(f"An error occurred during speech-to-text conversion: {e}")
            raise

    def generate_speaking_feedback(self, transcript: str, part_number: int, question: str) -> dict:
        """
        Generates structured feedback for an IELTS speaking response.
        
        Args:
            transcript: The transcribed text of the user's response.
            part_number: The part of the IELTS speaking test (1, 2, or 3).
            question: The question the user was answering.
        
        Returns:
            A dictionary containing structured feedback.
        """
        criteria_descriptions = {
            1: "Part 1 focuses on introductions and familiar topics.",
            2: "Part 2 is a long turn where the candidate speaks for 1-2 minutes on a given topic.",
            3: "Part 3 involves a discussion on more abstract issues and concepts related to the Part 2 topic."
        }
        
        system_message = f"""
You are an expert IELTS speaking examiner. Your task is to provide constructive feedback on a student's response.
The student was answering the following question for IELTS Speaking Part {part_number}: "{question}"
Context for this part: {criteria_descriptions.get(part_number, "General speaking practice.")}

Please analyze the following transcript of the student's response:
---
{transcript}
---

Provide your feedback in a structured JSON format with the following keys:
- "strengths": [A list of 1-2 specific strengths of the response.]
- "areas_for_improvement": [A list of 1-2 specific and actionable areas for improvement.]
- "vocabulary_feedback": "A brief, constructive comment on the use of vocabulary (range, precision)."
- "grammar_feedback": "A brief, constructive comment on grammar accuracy and range."
- "fluency_feedback": "A brief, constructive comment on fluency and coherence."
- "pronunciation_feedback": "A brief comment on pronunciation based on the clarity and flow of the text. Acknowledge that you cannot hear the actual voice but can infer based on the transcription."
- "tips_for_next": "One specific, actionable tip for the student to focus on next time."
- "estimated_band": A float representing the estimated band score for this specific response, from 6.0 to 9.0.
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            feedback = json.loads(response.choices[0].message.content)
            return feedback
        except OpenAIError as e:
            logger.error(f"OpenAI API error during speaking feedback generation: {e}")
            raise
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse JSON feedback from OpenAI: {e}")
            raise

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