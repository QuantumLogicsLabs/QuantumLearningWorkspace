import json
import os
import sys

# Ensure Python looks in the current directory
sys.path.append(os.getcwd())

from quiz_generator.app.services.quiz_service import QuizService

def main():
    service = QuizService()

    print("\n--- AI Quiz Generator ---")
    
    # 1. Ask the user for the topic
    topic = input("Enter the topic you want a quiz on: ")
    
    # 2. Ask for the question type
    print("\nAvailable types: mcq, true_false, fill_blank, short_answer")
    q_type = input("Enter question type: ").lower()

    print(f"\nSearching database for '{topic}' and generating questions...")

    try:
        quiz = service.generate_quiz_from_topic(topic, q_type)
        
        if isinstance(quiz, dict) and "error" in quiz:
            print(f"\nResult: {quiz['error']}")
        else:
            print("\nGenerated Quiz:")
            print(json.dumps(quiz, indent=2))
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()