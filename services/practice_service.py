import json
import os
import logging
import random

logger = logging.getLogger(__name__)

READING_MCQ_FILE = "data/reading_mcq.json"

class PracticeService:
    def __init__(self):
        self.reading_mcq_data = self._load_reading_mcq_data()

    def _load_reading_mcq_data(self) -> list:
        """Loads reading MCQ data from the JSON file."""
        try:
            if os.path.exists(READING_MCQ_FILE):
                with open(READING_MCQ_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Successfully loaded {len(data)} reading MCQ sets from {READING_MCQ_FILE}")
                    return data
            else:
                logger.warning(f"Reading MCQ data file not found: {READING_MCQ_FILE}. Returning empty list.")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {READING_MCQ_FILE}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading reading MCQ data from {READING_MCQ_FILE}: {e}")
            return []

    def get_reading_mcq_set(self, set_id: str = None) -> dict | None:
        """Gets a specific reading MCQ set by ID, or a random one if ID is not provided."""
        if not self.reading_mcq_data:
            logger.warning("No reading MCQ data loaded to select a set from.")
            return None
        
        if set_id:
            for mcq_set in self.reading_mcq_data:
                if mcq_set.get("id") == set_id:
                    return mcq_set
            logger.warning(f"Reading MCQ set with id '{set_id}' not found.")
            return None # Or raise an error
        else:
            # Return a random set if no ID is specified
            return random.choice(self.reading_mcq_data)

# Example usage (for testing this file directly)
if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler()) # Show logs in console for testing
    logger.setLevel(logging.INFO)
    
    service = PracticeService()
    if service.reading_mcq_data:
        print("\n--- PracticeService Test ---")
        first_set = service.get_reading_mcq_set(set_id="reading_set_1")
        if first_set:
            print(f"Got set by ID: {first_set['id']}")
            print(f"Passage: {first_set['passage'][:50]}...")
            print(f"Number of questions: {len(first_set['questions'])}")
        
        random_set = service.get_reading_mcq_set()
        if random_set:
            print(f"Got random set: {random_set['id']}")
        print("--- End of Test ---")
    else:
        print("PracticeService Test: No data loaded, check logs.") 