# IELTS Preparation Bot - Database Seeding Guide

## Overview

This guide provides comprehensive instructions for seeding the IELTS Preparation Bot database with authentic educational content. The seed data is organized across multiple formats and sources, each serving specific educational purposes.

## Data Sources and Structure

### Primary Data Directory (`data/`)

#### 1. Vocabulary Data
**Files**: `vocabulary.json`, `practice/education.json`, `practice/vocabulary.json`

**Structure**:
```json
{
  "word": "ubiquitous",
  "definition": "present, appearing, or found everywhere",
  "part_of_speech": "adjective",
  "example": "Mobile phones are now ubiquitous in modern society.",
  "ielts_relevance": "Useful for Task 2 essays about technology or social changes",
  "cefr_level": "C1"
}
```

**Database Target**: `vocabulary` table or practice content JSON
**Seeding Process**:
```python
def seed_vocabulary_data():
    """Seed vocabulary data from JSON files"""
    with open('data/vocabulary.json', 'r') as f:
        vocab_data = json.load(f)
    
    for entry in vocab_data:
        vocab_item = {
            'word': entry['word'],
            'definition': entry['definition'],
            'part_of_speech': entry['part_of_speech'],
            'example': entry['example'],
            'cefr_level': entry['cefr_level'],
            'ielts_relevance': entry.get('ielts_relevance', ''),
            'category': 'general'
        }
        # Insert into practice content or create vocabulary records
```

#### 2. Grammar Practice Data
**File**: `grammar.json`

**Structure**:
```json
{
  "question": "She _____ in this company for five years before she resigned.",
  "options": ["has worked", "had worked", "worked", "was working"],
  "correct_option": 1,
  "explanation": "Past perfect explanation...",
  "grammar_concept": "Past Perfect Tense"
}
```

**Database Target**: `TeacherExercise` content field
**Seeding Process**:
```python
def seed_grammar_exercises():
    """Create grammar exercises from JSON data"""
    with open('data/grammar.json', 'r') as f:
        grammar_data = json.load(f)
    
    for item in grammar_data:
        exercise_content = {
            'type': 'multiple_choice',
            'question': item['question'],
            'options': item['options'],
            'correct_answer': item['correct_option'],
            'explanation': item['explanation'],
            'grammar_concept': item['grammar_concept']
        }
        
        exercise = TeacherExercise(
            title=f"Grammar: {item['grammar_concept']}",
            description=f"Practice exercise for {item['grammar_concept']}",
            exercise_type='grammar',
            content=exercise_content,
            difficulty='medium',
            creator_id=1,  # System-generated exercises
            is_published=True
        )
        db.session.add(exercise)
```

#### 3. Speaking Practice Data
**File**: `speaking.json`

**Structure**:
```json
{
  "part": 1,
  "questions": [
    "Can you tell me something about your hometown?",
    "What kind of accommodation do you live in?"
  ],
  "time_to_speak": "1-2 minutes"
}
```

**Database Target**: `TeacherExercise` content field
**Seeding Process**:
```python
def seed_speaking_exercises():
    """Create speaking exercises from structured data"""
    with open('data/speaking.json', 'r') as f:
        speaking_data = json.load(f)
    
    for section in speaking_data:
        if section['part'] == 1:
            # Part 1 - Personal questions
            content = {
                'type': 'speaking_part1',
                'questions': section['questions'],
                'time_limit': section['time_to_speak'],
                'instructions': 'Answer these questions about yourself'
            }
        elif section['part'] == 2:
            # Part 2 - Cue card
            content = {
                'type': 'speaking_part2',
                'cue_card': section['cue_card'],
                'follow_up_questions': section.get('follow_up_questions', []),
                'preparation_time': section['time_to_prepare'],
                'speaking_time': section['time_to_speak']
            }
        
        exercise = TeacherExercise(
            title=f"Speaking Part {section['part']} Practice",
            description=f"IELTS Speaking Part {section['part']} exercise",
            exercise_type='speaking',
            content=content,
            difficulty='medium',
            creator_id=1,
            is_published=True
        )
        db.session.add(exercise)
```

#### 4. Listening Practice Data
**File**: `listening.json`

**Structure**:
```json
{
  "transcript": "Good morning everyone! Today, I'm going to talk about...",
  "questions": [
    {
      "question": "What percentage of Copenhagen residents cycle to work?",
      "answer": "62%"
    }
  ]
}
```

**Database Target**: `TeacherExercise` content field with audio references
**Seeding Process**:
```python
def seed_listening_exercises():
    """Create listening exercises with transcripts and questions"""
    with open('data/listening.json', 'r') as f:
        listening_data = json.load(f)
    
    for idx, item in enumerate(listening_data):
        content = {
            'type': 'listening_comprehension',
            'transcript': item['transcript'],
            'questions': item['questions'],
            'audio_file': f"listening_audio_{idx}.mp3",  # Reference to audio file
            'instructions': 'Listen to the audio and answer the questions'
        }
        
        exercise = TeacherExercise(
            title=f"Listening Practice {idx + 1}",
            description="IELTS Listening comprehension exercise",
            exercise_type='listening',
            content=content,
            difficulty='medium',
            creator_id=1,
            is_published=True
        )
        db.session.add(exercise)
```

### Cue Cards Directory (`data/cue_cards/`)

#### Speaking Cue Cards
**Files**: `001-city.md`, `002-gift.md`, etc.

**Structure**: Markdown format with Part 2 and Part 3 content
```markdown
### PART 2
**Describe a city where you'd like to stay for a short time.**
- **What city is**
- **Who you will go there with**
- **What you will do there**
- **Why you will stay there only for a short time**

#### what city is:
Hmm, well, I would like to go to a city with a cooler temperature...

### PART 3
#### 1. Why is noise pollution worse in tourism cities?
Well, actually, I don't have precise information...
```

**Database Target**: `TeacherExercise` content field
**Seeding Process**:
```python
def seed_cue_cards():
    """Process markdown cue cards into database exercises"""
    import os
    import re
    
    cue_cards_dir = 'data/cue_cards'
    for filename in os.listdir(cue_cards_dir):
        if filename.endswith('.md'):
            with open(os.path.join(cue_cards_dir, filename), 'r') as f:
                content = f.read()
            
            # Parse markdown content
            parts = content.split('### PART')
            if len(parts) >= 3:  # Has Part 2 and Part 3
                part2_content = parts[1].replace('2\n', '').strip()
                part3_content = parts[2].replace('3\n', '').strip()
                
                # Extract cue card prompt
                cue_card_match = re.search(r'\*\*(.*?)\*\*', part2_content)
                cue_card_prompt = cue_card_match.group(1) if cue_card_match else ""
                
                # Extract bullet points
                bullet_points = re.findall(r'- \*\*(.*?)\*\*', part2_content)
                
                # Extract Part 3 questions
                part3_questions = re.findall(r'#### \d+\. (.*?)\n', part3_content)
                
                exercise_content = {
                    'type': 'speaking_cue_card',
                    'prompt': cue_card_prompt,
                    'bullet_points': bullet_points,
                    'part3_questions': part3_questions,
                    'sample_response': part2_content,
                    'part3_sample_responses': part3_content
                }
                
                # Extract topic from filename
                topic = filename.replace('.md', '').split('-', 1)[1] if '-' in filename else filename.replace('.md', '')
                
                exercise = TeacherExercise(
                    title=f"Speaking Cue Card: {topic.title()}",
                    description=f"IELTS Speaking Part 2 cue card about {topic}",
                    exercise_type='speaking',
                    content=exercise_content,
                    difficulty='medium',
                    creator_id=1,
                    is_published=True
                )
                db.session.add(exercise)
```

### CSV Data Sources (`attached_assets/`)

#### 1. IELTS Writing Vocabulary
**File**: `IeltsWritingVocab.csv`

**Structure**:
```csv
Category,Word,Example Sentence
Increase,Increase,The sales figures exhibited a consistent increase over three months.
Increase,Rise,Stock prices experienced a significant rise during the first quarter.
```

**Database Target**: Vocabulary practice content
**Seeding Process**:
```python
def seed_writing_vocabulary():
    """Process IELTS writing vocabulary from CSV"""
    import csv
    
    with open('attached_assets/IeltsWritingVocab.csv', 'r') as f:
        reader = csv.DictReader(f)
        categories = {}
        
        for row in reader:
            category = row['Category']
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                'word': row['Word'],
                'example': row['Example Sentence'],
                'category': category.lower()
            })
    
    # Create exercises by category
    for category, words in categories.items():
        content = {
            'type': 'vocabulary_category',
            'category': category,
            'words': words,
            'exercise_type': 'writing_vocabulary'
        }
        
        exercise = TeacherExercise(
            title=f"Writing Vocabulary: {category}",
            description=f"Essential vocabulary for IELTS Writing - {category}",
            exercise_type='vocabulary',
            content=content,
            difficulty='intermediate',
            creator_id=1,
            is_published=True
        )
        db.session.add(exercise)
```

#### 2. PET Vocabulary List
**File**: `84669-pet-vocabulary-list.csv`

**Database Target**: Foundation vocabulary for lower-level students
**Seeding Process**:
```python
def seed_pet_vocabulary():
    """Process Cambridge PET vocabulary list"""
    # Skip header rows and process actual vocabulary
    # Structure depends on actual CSV format after headers
    pass
```

### Audio Files
**Files**: `Cambridge_IELTS17_Test1_Audio*.mp3`

**Database Target**: Audio content references in listening exercises
**Seeding Process**:
```python
def seed_audio_references():
    """Create references to audio files for listening exercises"""
    import os
    
    audio_dir = 'attached_assets'
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    
    for idx, audio_file in enumerate(audio_files):
        # Create listening exercise referencing this audio
        content = {
            'type': 'listening_test',
            'audio_file': audio_file,
            'instructions': 'Listen to the audio and complete the tasks',
            'test_number': idx + 1
        }
        
        exercise = TeacherExercise(
            title=f"Cambridge IELTS Listening Test {idx + 1}",
            description="Official Cambridge IELTS listening practice",
            exercise_type='listening',
            content=content,
            difficulty='authentic',
            creator_id=1,
            is_published=True
        )
        db.session.add(exercise)
```

## Complete Seeding Script

### Main Seeding Function
```python
def seed_database():
    """Complete database seeding from all data sources"""
    print("Starting database seeding process...")
    
    try:
        # Create system user for generated content
        system_user = User(
            user_id=999999999,  # Special system user ID
            first_name="System",
            last_name="Generated",
            username="system_bot",
            is_admin=True,
            is_botmaster=True
        )
        db.session.add(system_user)
        db.session.commit()
        
        # Seed vocabulary data
        print("Seeding vocabulary data...")
        seed_vocabulary_data()
        seed_writing_vocabulary()
        
        # Seed grammar exercises
        print("Seeding grammar exercises...")
        seed_grammar_exercises()
        
        # Seed speaking exercises
        print("Seeding speaking exercises...")
        seed_speaking_exercises()
        seed_cue_cards()
        
        # Seed listening exercises
        print("Seeding listening exercises...")
        seed_listening_exercises()
        seed_audio_references()
        
        # Commit all changes
        db.session.commit()
        print("Database seeding completed successfully!")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during seeding: {e}")
        raise

if __name__ == "__main__":
    from app import app
    with app.app_context():
        seed_database()
```

## Data Validation and Quality Assurance

### Pre-Seeding Validation
```python
def validate_data_integrity():
    """Validate data files before seeding"""
    validations = []
    
    # Check JSON files are valid
    json_files = ['vocabulary.json', 'grammar.json', 'speaking.json', 'listening.json']
    for file in json_files:
        try:
            with open(f'data/{file}', 'r') as f:
                json.load(f)
            validations.append(f"✓ {file} is valid JSON")
        except Exception as e:
            validations.append(f"✗ {file} is invalid: {e}")
    
    # Check required fields in vocabulary data
    with open('data/vocabulary.json', 'r') as f:
        vocab_data = json.load(f)
    
    required_vocab_fields = ['word', 'definition', 'part_of_speech', 'example']
    for idx, entry in enumerate(vocab_data[:5]):  # Check first 5 entries
        missing_fields = [field for field in required_vocab_fields if field not in entry]
        if missing_fields:
            validations.append(f"✗ Vocabulary entry {idx} missing: {missing_fields}")
        else:
            validations.append(f"✓ Vocabulary entry {idx} complete")
    
    return validations
```

### Post-Seeding Verification
```python
def verify_seeded_data():
    """Verify data was seeded correctly"""
    # Check exercise counts by type
    exercise_counts = db.session.query(
        TeacherExercise.exercise_type,
        func.count(TeacherExercise.id)
    ).group_by(TeacherExercise.exercise_type).all()
    
    print("Seeded exercise counts:")
    for exercise_type, count in exercise_counts:
        print(f"  {exercise_type}: {count}")
    
    # Check for content integrity
    sample_exercise = TeacherExercise.query.filter_by(exercise_type='grammar').first()
    if sample_exercise:
        content = sample_exercise.get_content()
        required_fields = ['question', 'options', 'correct_answer']
        missing = [field for field in required_fields if field not in content]
        if missing:
            print(f"Warning: Grammar exercise missing fields: {missing}")
        else:
            print("✓ Grammar exercise content structure valid")
```

## Usage Instructions

### Running the Seeding Process
```bash
# Ensure database is set up
python migrations.py

# Run seeding script
python seed_database.py

# Verify seeding results
python -c "from seed_database import verify_seeded_data; verify_seeded_data()"
```

### Updating Seed Data
1. **Add New Content**: Place new JSON/CSV files in appropriate directories
2. **Update Seeding Functions**: Modify seeding functions to handle new formats
3. **Test Locally**: Validate new data before production seeding
4. **Run Incremental Seeding**: Add logic to avoid duplicating existing content

This seeding guide ensures all authentic educational content is properly structured and imported into the database for use by the IELTS Preparation Bot.