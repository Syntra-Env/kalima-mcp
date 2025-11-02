from collections import Counter
import sqlite3

FILE_PATH = "C:\\lab\\QuranNLP\\quran-clean.txt"

def create_letter_mapping():
    """Create a bidirectional mapping between Arabic letters and numbers."""
    # Common Arabic letters (add more if needed)
    arabic_letters = 'ابتثجحخدذرزسشصضطظعغفقكلمنهويء'
    # Create number-to-letter and letter-to-number mappings
    number_to_letter = {i+1: letter for i, letter in enumerate(arabic_letters)}
    letter_to_number = {letter: i+1 for i, letter in enumerate(arabic_letters)}
    return number_to_letter, letter_to_number

def process_text(text, letter_to_number):
    """Convert text to numbered representation."""
    numbered_text = []
    for char in text:
        if char in letter_to_number:
            numbered_text.append(f"{char}({letter_to_number[char]})")
        else:
            numbered_text.append(char)
    return ' '.join(numbered_text)

def analyze_patterns(text, letter_to_number, pattern_length=3):
    """Analyze text for common letter patterns of specified length."""
    patterns = []
    # Convert text to number pattern
    numbers = [letter_to_number.get(char, 0) for char in text]
    numbers = [str(num) for num in numbers]
    
    # Create patterns of specified length
    for i in range(len(numbers) - pattern_length + 1):
        pattern = '-'.join(numbers[i:i + pattern_length])
        if '0' not in pattern:  # Only include patterns of Arabic letters
            patterns.append(pattern)
    
    return patterns

def print_common_patterns(patterns, number_to_letter, n=10):
    """Print the n most common patterns with their letter representations."""
    pattern_counts = Counter(patterns)
    print(f"\nTop {n} most common {len(patterns[0].split('-'))}-letter patterns:")
    print("-" * 50)
    for pattern, count in pattern_counts.most_common(n):
        # Convert number pattern back to letters
        letters = [number_to_letter[int(num)] for num in pattern.split('-')]
        arabic_pattern = ''.join(letters)
        number_pattern = pattern
        print(f"Pattern: {arabic_pattern:<10} Numbers: {number_pattern:<15} Occurrences: {count:>5}")

def create_database():
    """Create a SQLite database for storing patterns."""
    conn = sqlite3.connect('quran_patterns.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY,
            arabic_pattern TEXT NOT NULL,
            number_pattern TEXT NOT NULL,
            occurrences INTEGER NOT NULL,
            pattern_length INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    return conn

def store_patterns(conn, patterns, number_to_letter):
    """Store patterns in the database."""
    cursor = conn.cursor()
    # Clear existing patterns
    cursor.execute('DELETE FROM patterns')
    
    pattern_counts = Counter(patterns)
    for pattern, count in pattern_counts.most_common():
        letters = [number_to_letter[int(num)] for num in pattern.split('-')]
        arabic_pattern = ''.join(letters)
        pattern_length = len(letters)
        
        cursor.execute('''
            INSERT INTO patterns (arabic_pattern, number_pattern, occurrences, pattern_length)
            VALUES (?, ?, ?, ?)
        ''', (arabic_pattern, pattern, count, pattern_length))
    
    conn.commit()

if __name__ == '__main__':
    file_path = FILE_PATH
    
    # Create letter mappings
    number_to_letter, letter_to_number = create_letter_mapping()
    
    try:
        # Initialize database
        with create_database() as conn:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                # Analyze patterns in the entire text at once
                all_patterns = analyze_patterns(text, letter_to_number)
            
            store_patterns(conn, all_patterns, number_to_letter)
            print_common_patterns(all_patterns, number_to_letter, n=20)
    
    except Exception as e:
        print(f"An error occurred: {e}")
    except IOError as e:
        print(e)
