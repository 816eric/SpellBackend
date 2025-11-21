"""Test script for history tracking endpoints"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_study_session():
    """Test saving study session history"""
    print("\n=== Testing Study Session ===")
    
    # Test data
    study_data = {
        "user_name": "test_user",
        "records": [
            {"word": "apple", "difficulty": 5},
            {"word": "banana", "difficulty": 3},
            {"word": "cherry", "difficulty": 1},
        ]
    }
    
    # Save study session
    response = requests.post(
        f"{BASE_URL}/history/study-session",
        json=study_data
    )
    
    print(f"Save Study Session - Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Get study history
    response = requests.get(f"{BASE_URL}/history/study/test_user")
    print(f"\nGet Study History - Status: {response.status_code}")
    history = response.json()
    print(f"Retrieved {len(history)} records")
    if history:
        print(f"Sample record: {json.dumps(history[0], indent=2)}")

def test_quiz_session():
    """Test saving quiz session history"""
    print("\n=== Testing Quiz Session ===")
    
    # Test data
    quiz_data = {
        "user_name": "test_user",
        "records": [
            {"word": "apple", "is_correct": True},
            {"word": "banana", "is_correct": True},
            {"word": "cherry", "is_correct": False},
            {"word": "date", "is_correct": True},
        ]
    }
    
    # Save quiz session
    response = requests.post(
        f"{BASE_URL}/history/quiz-session",
        json=quiz_data
    )
    
    print(f"Save Quiz Session - Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Get quiz history
    response = requests.get(f"{BASE_URL}/history/quiz/test_user")
    print(f"\nGet Quiz History - Status: {response.status_code}")
    history = response.json()
    print(f"Retrieved {len(history)} records")
    if history:
        print(f"Sample record: {json.dumps(history[0], indent=2)}")

def test_multiple_sessions():
    """Test saving multiple sessions"""
    print("\n=== Testing Multiple Sessions ===")
    
    # Session 1
    study_data1 = {
        "user_name": "test_user",
        "records": [
            {"word": "test1", "difficulty": 5},
            {"word": "test2", "difficulty": 3},
        ]
    }
    requests.post(f"{BASE_URL}/history/study-session", json=study_data1)
    
    # Session 2
    study_data2 = {
        "user_name": "test_user",
        "records": [
            {"word": "test3", "difficulty": 1},
            {"word": "test4", "difficulty": 5},
        ]
    }
    requests.post(f"{BASE_URL}/history/study-session", json=study_data2)
    
    # Get all records
    response = requests.get(f"{BASE_URL}/history/study/test_user?limit=10")
    history = response.json()
    print(f"Total study records after 2 sessions: {len(history)}")
    
    # Show stats
    difficulties = [r['difficulty'] for r in history]
    print(f"Difficulty distribution: {difficulties}")

if __name__ == "__main__":
    print("History Tracking API Test")
    print("=" * 50)
    
    try:
        test_study_session()
        test_quiz_session()
        test_multiple_sessions()
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
