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

    def generate_speaking_question(self, part_number: int, topic: str = None) -> dict:
        """
        Generates a question for a specific part of the IELTS speaking test.

        Args:
            part_number: The part of the IELTS speaking test (1, 2, or 3).
            topic: An optional topic for Part 2 or 3.

        Returns:
            A dictionary containing the question and topic, e.g., 
            {'topic': 'A hobby you enjoy', 'question': 'Describe a hobby...'}.
        """
        part_prompts = {
            1: "Generate a common IELTS Speaking Part 1 question. It should be about a familiar topic like home, family, work, studies, or interests.",
            2: "Generate an IELTS Speaking Part 2 cue card. Provide a main topic and 3-4 bullet points of things the student should talk about. The topic should be about a personal experience.",
            3: f"Generate a thought-provoking IELTS Speaking Part 3 discussion question. It should be related to the topic of '{topic if topic else 'hobbies and free time'}' and require abstract thinking."
        }

        if part_number not in part_prompts:
            raise ValueError("Invalid part number for speaking question.")

        system_message = f"""
You are an expert IELTS examiner creating questions for a practice test.
Your task is to generate a question for IELTS Speaking Part {part_number}.

{part_prompts[part_number]}

Return the response as a JSON object with the following keys:
- "topic": A very short, descriptive title for the question topic (e.g., "Hometown", "A memorable trip").
- "question": The full question or cue card text to be presented to the student.
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.9, # Higher temperature for more varied questions
            )
            question_data = json.loads(response.choices[0].message.content)
            return question_data
        except OpenAIError as e:
            logger.error(f"OpenAI API error during question generation: {e}")
            raise
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse JSON question from OpenAI: {e}")
            raise

    def generate_writing_task(self, task_type: int) -> dict:
        """
        Generates a task for IELTS Writing.

        Args:
            task_type: The type of writing task (1 or 2).

        Returns:
            A dictionary containing the task details.
        """
        task_prompts = {
            1: "Generate a detailed IELTS Writing Task 1 prompt. The prompt should describe a chart, graph, table, or diagram. The student needs to summarize the information by selecting and reporting the main features, and make comparisons where relevant.",
            2: "Generate a standard IELTS Writing Task 2 essay question. The question should present a point of view, argument, or problem, and ask the student to write an essay in response."
        }
        if task_type not in task_prompts:
            raise ValueError("Invalid task type for writing question.")

        system_message = f"""
You are an expert IELTS examiner creating a practice test.
Your task is to generate a prompt for IELTS Writing Task {task_type}.

{task_prompts[task_type]}

Return the response as a JSON object with the following keys:
- "task_type": The integer {task_type}.
- "question": The full task prompt to be presented to the student.
- "image_url": For Task 1, an optional URL to an image of the chart or graph. For Task 2, this should be null.
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_message}],
                response_format={"type": "json_object"},
                temperature=0.8,
            )
            task_data = json.loads(response.choices[0].message.content)
            return task_data
        except OpenAIError as e:
            logger.error(f"OpenAI API error during writing task generation: {e}")
            raise
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse JSON writing task from OpenAI: {e}")
            raise

    def provide_writing_feedback(self, essay_text: str, task_type: int, question: str) -> dict:
        """
        Generates structured feedback for an IELTS writing response.

        Args:
            essay_text: The user's written response.
            task_type: The writing task type (1 or 2).
            question: The question the user was answering.

        Returns:
            A dictionary containing structured feedback.
        """
        system_message = f"""
You are an expert IELTS writing examiner. Your task is to provide constructive feedback on a student's essay for IELTS Writing Task {task_type}.
The student was responding to the following prompt: "{question}"

Please analyze the following essay:
---
{essay_text}
---

Provide your feedback in a structured JSON format with the following keys:
- "strengths": [A list of 1-2 specific strengths of the essay.]
- "areas_for_improvement": [A list of 1-2 specific and actionable areas for improvement.]
- "task_achievement": "A brief comment on how well the writer addressed the task requirements.",
- "coherence_cohesion": "A brief comment on the organization, paragraphing, and linking of ideas.",
- "lexical_resource": "A brief comment on the range and accuracy of the vocabulary used.",
- "grammatical_range_accuracy": "A brief comment on the range and accuracy of grammar.",
- "estimated_band": A float representing the estimated band score for this essay, from 6.0 to 9.0.
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_message}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            feedback = json.loads(response.choices[0].message.content)
            return feedback
        except OpenAIError as e:
            logger.error(f"OpenAI API error during writing feedback generation: {e}")
            raise
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse JSON writing feedback from OpenAI: {e}")
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