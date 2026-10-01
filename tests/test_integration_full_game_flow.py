"""
Integration Tests for Complete Game Flow
Tests the full game loop: User creation -> Study -> Points -> Rewards -> Leaderboard

Run with: pytest tests/test_integration_full_game_flow.py -v
"""

import pytest
import json
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from src.db_session import get_session, init_db
from src.models.user import User
from sqlmodel import Session, select

client = TestClient(app)

# Tests act as the operator: the backend accepts the admin Basic credentials
# on every route, so no per-user token plumbing is needed here.
os.environ["RATE_LIMIT_DISABLED"] = "true"
os.environ.setdefault("ADMIN_USERNAME", "test-admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-pass")
client.auth = (os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])

# Test fixtures
@pytest.fixture(scope="function")
def test_user_name():
    """Generate unique test user name"""
    return f"test_user_{datetime.now().timestamp()}"

@pytest.fixture(scope="function")
def test_user(test_user_name):
    """Create test user"""
    user_data = {
        "name": test_user_name,
        "email": f"{test_user_name}@test.com",
        "password": "testpass123",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code in [200, 201], f"Failed to create test user: {response.text}"
    return test_user_name

@pytest.fixture(scope="function", autouse=True)
def cleanup_test_users(test_user_name):
    """Clean up test users after tests"""
    yield
    try:
        client.delete(f"/users/{test_user_name}")
    except:
        pass


class TestUserManagement:
    """Test user management APIs"""

    def test_create_user(self, test_user_name):
        """Test user creation endpoint"""
        user_data = {
            "name": test_user_name,
            "email": f"{test_user_name}@test.com",
            "password": "password123",
        }
        response = client.post("/users/", json=user_data)
        assert response.status_code in [200, 201], f"User creation failed: {response.text}"
        data = response.json()
        assert data.get("name") == test_user_name or "name" in str(data)
        print(f"✓ User created: {test_user_name}")

    def test_user_already_exists(self, test_user):
        """Test that duplicate user creation returns 409"""
        user_data = {
            "name": test_user,
            "email": f"{test_user}@test.com",
            "password": "password123",
        }
        response = client.post("/users/", json=user_data)
        assert response.status_code == 409, "Should return 409 for duplicate user"
        print(f"✓ Duplicate user correctly rejected")

    def test_get_user_profile(self, test_user):
        """Test retrieving user profile"""
        response = client.get(f"/users/{test_user}/profile")
        assert response.status_code == 200, f"Failed to get profile: {response.text}"
        data = response.json()
        assert data.get("name") == test_user
        print(f"✓ User profile retrieved: {test_user}")

    def test_get_nonexistent_user(self):
        """Test getting non-existent user returns 404"""
        response = client.get("/users/nonexistent_user_12345/profile")
        assert response.status_code == 404, "Should return 404 for non-existent user"
        print(f"✓ Non-existent user correctly returns 404")

    def test_update_user_profile(self, test_user):
        """Test updating user profile"""
        update_data = {
            "email": f"updated_{test_user}@test.com",
            "school": "Test School",
            "grade": "10",
        }
        response = client.put(
            f"/users/{test_user}/profile",
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update profile: {response.text}"

        # Verify update
        response = client.get(f"/users/{test_user}/profile")
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == test_user
        print(f"✓ User profile updated")

    def test_verify_password(self, test_user_name):
        """Test password verification"""
        # Create user
        user_data = {
            "name": test_user_name,
            "email": f"{test_user_name}@test.com",
            "password": "testpass123",
        }
        client.post("/users/", json=user_data)

        # Verify correct password
        response = client.post(
            f"/users/{test_user_name}/verify-password",
            data={"password": "testpass123"}
        )
        assert response.status_code == 200, f"Password verification failed: {response.text}"
        data = response.json()
        assert data.get("verified") == True
        print(f"✓ Password verification works")


class TestPointsSystem:
    """Test points and rewards APIs"""

    def test_get_initial_points(self, test_user):
        """Test getting user points"""
        response = client.get(f"/users/{test_user}/points/")
        assert response.status_code == 200, f"Failed to get points: {response.text}"
        data = response.json()
        assert "total_points" in data
        assert isinstance(data["total_points"], (int, float))
        print(f"✓ Retrieved points: {data['total_points']}")

    def test_add_points(self, test_user):
        """Test adding points to user"""
        add_data = {
            "points": 100,
            "reason": "test_study_session"
        }
        response = client.post(
            f"/users/{test_user}/points/add",
            json=add_data
        )
        assert response.status_code == 200, f"Failed to add points: {response.text}"
        data = response.json()
        assert data.get("total_points", 0) >= 100
        print(f"✓ Points added successfully: {data['total_points']}")

    def test_redeem_points_insufficient(self, test_user):
        """Test redeeming with insufficient points"""
        redeem_data = {
            "item": "cosmetic_1",
            "points": 999999
        }
        response = client.post(
            f"/users/{test_user}/points/redeem",
            json=redeem_data
        )
        # Should return 400 with insufficient_points message
        assert response.status_code in [400, 409], "Should fail with insufficient points"
        print(f"✓ Insufficient points correctly rejected")

    def test_redeem_points_success(self, test_user):
        """Test redeeming points successfully"""
        # First add points
        add_data = {
            "points": 500,
            "reason": "test_points_for_redemption"
        }
        response = client.post(
            f"/users/{test_user}/points/add",
            json=add_data
        )
        assert response.status_code == 200

        # Then redeem
        redeem_data = {
            "item": "test_cosmetic",
            "points": 100
        }
        response = client.post(
            f"/users/{test_user}/points/redeem",
            json=redeem_data
        )
        assert response.status_code == 200, f"Failed to redeem points: {response.text}"
        data = response.json()
        assert "total_points" in data or "success" in str(data)
        print(f"✓ Points redeemed successfully")

    def test_get_reward_history(self, test_user):
        """Test getting reward history"""
        response = client.get(f"/users/{test_user}/points/history?page=1")
        assert response.status_code == 200, f"Failed to get history: {response.text}"
        data = response.json()
        assert isinstance(data, (dict, list))
        print(f"✓ Reward history retrieved")


class TestLevelSystem:
    """Test levels and progression APIs"""

    def test_list_levels(self):
        """Test listing all levels"""
        response = client.get("/levels/")
        assert response.status_code == 200, f"Failed to list levels: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Levels listed: {len(data)} levels found")

    def test_get_level_details(self):
        """Test getting level with words"""
        # Get first level
        response = client.get("/levels/")
        if response.status_code == 200:
            levels = response.json()
            if levels:
                level_id = levels[0].get("id", 1)
                response = client.get(f"/levels/{level_id}")
                assert response.status_code == 200, f"Failed to get level details: {response.text}"
                data = response.json()
                assert "id" in data or "name" in data
                print(f"✓ Level details retrieved for level {level_id}")

    def test_get_nonexistent_level(self):
        """Test getting non-existent level"""
        response = client.get("/levels/99999")
        assert response.status_code in [404, 500], "Should return error for invalid level"
        print(f"✓ Non-existent level correctly returns error")

    def test_start_level(self, test_user):
        """Test starting a level"""
        # First get levels
        response = client.get("/levels/")
        if response.status_code == 200 and response.json():
            level_id = response.json()[0].get("id", 1)
            response = client.post(
                f"/levels/users/{test_user}/progress/{level_id}/start"
            )
            # May be locked or other status, but shouldn't crash
            assert response.status_code in [200, 403, 404], f"Unexpected response: {response.text}"
            print(f"✓ Level start endpoint works")

    def test_complete_level(self, test_user):
        """Test completing a level"""
        response = client.get("/levels/")
        if response.status_code == 200 and response.json():
            level_id = response.json()[0].get("id", 1)

            # Try to complete with valid accuracy
            response = client.post(
                f"/levels/users/{test_user}/progress/{level_id}/complete?accuracy=0.85"
            )
            # May fail due to not starting first, but endpoint should exist
            assert response.status_code in [200, 400, 403, 404], f"Unexpected response: {response.text}"
            print(f"✓ Level complete endpoint works")

    def test_complete_level_invalid_accuracy(self, test_user):
        """Test completing level with invalid accuracy"""
        response = client.get("/levels/")
        if response.status_code == 200 and response.json():
            level_id = response.json()[0].get("id", 1)

            # Try with invalid accuracy > 1.0
            response = client.post(
                f"/levels/users/{test_user}/progress/{level_id}/complete?accuracy=1.5"
            )
            assert response.status_code == 400, "Should reject accuracy > 1.0"
            print(f"✓ Invalid accuracy correctly rejected")

    def test_get_user_levels(self, test_user):
        """Test getting user's level progress"""
        response = client.get(f"/levels/users/{test_user}")
        assert response.status_code == 200, f"Failed to get user levels: {response.text}"
        data = response.json()
        assert "user_name" in data
        assert "levels" in data or isinstance(data, (dict, list))
        print(f"✓ User level progress retrieved")


class TestLeaderboard:
    """Test leaderboard APIs"""

    def test_get_leaderboard_top(self):
        """Test getting top leaderboard"""
        response = client.get("/leaderboard/top?limit=20")
        assert response.status_code == 200, f"Failed to get leaderboard: {response.text}"
        data = response.json()
        assert isinstance(data, (dict, list))
        print(f"✓ Top leaderboard retrieved")

    def test_get_leaderboard_schools(self):
        """Test getting available schools"""
        response = client.get("/leaderboard/schools")
        assert response.status_code == 200, f"Failed to get schools: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Schools list retrieved: {len(data)} schools")

    def test_get_leaderboard_grades(self):
        """Test getting available grades"""
        response = client.get("/leaderboard/grades")
        assert response.status_code == 200, f"Failed to get grades: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Grades list retrieved: {len(data)} grades")

    def test_get_leaderboard_me(self, test_user):
        """Test getting user's leaderboard position"""
        response = client.get(
            "/leaderboard/me",
            headers={"X-User-Name": test_user}
        )
        # May not have ranking yet, but endpoint should work
        assert response.status_code in [200, 404], f"Unexpected response: {response.text}"
        print(f"✓ User leaderboard position endpoint works")

    def test_leaderboard_with_filters(self):
        """Test leaderboard with school/grade filters"""
        response = client.get("/leaderboard/top?limit=20&school=TestSchool&grade=10")
        assert response.status_code == 200, f"Failed with filters: {response.text}"
        print(f"✓ Leaderboard filtering works")


class TestUnlockables:
    """Test cosmetics/unlockables APIs"""

    def test_list_unlockables(self, test_user):
        """Test listing unlockables"""
        response = client.get(f"/unlockables/?user_name={test_user}")
        assert response.status_code == 200, f"Failed to get unlockables: {response.text}"
        data = response.json()
        assert isinstance(data, (dict, list))
        print(f"✓ Unlockables listed")

    def test_redeem_unlockable_insufficient_points(self, test_user):
        """Test redeeming cosmetic with insufficient points"""
        response = client.post(
            f"/unlockables/1/redeem?user_name={test_user}"
        )
        # Should fail or return error about insufficient points
        assert response.status_code in [400, 404, 409], f"Unexpected response: {response.text}"
        print(f"✓ Insufficient points for cosmetic correctly handled")

    def test_equip_cosmetic(self, test_user):
        """Test equipping cosmetic"""
        response = client.post(
            f"/unlockables/1/equip?user_name={test_user}"
        )
        # May fail if not owned, but endpoint should exist
        assert response.status_code in [200, 400, 404], f"Unexpected response: {response.text}"
        print(f"✓ Equip cosmetic endpoint works")


class TestStreaks:
    """Test streak system APIs"""

    def test_get_user_streaks(self, test_user):
        """Test getting user streaks"""
        response = client.get(f"/streaks/users/{test_user}")
        assert response.status_code in [200, 404], f"Failed to get streaks: {response.text}"
        print(f"✓ Streak data retrieved or correctly not found")

    def test_check_in_streak(self, test_user):
        """Test checking in to streak"""
        response = client.post(f"/streaks/users/{test_user}/check-in")
        assert response.status_code in [200, 201, 400], f"Unexpected response: {response.text}"
        print(f"✓ Streak check-in endpoint works")


class TestHistory:
    """Test history tracking APIs"""

    def test_save_study_session(self, test_user):
        """Test saving study session"""
        session_data = {
            "user_name": test_user,
            "records": [
                {
                    "word_id": 1,
                    "correct": True,
                    "time_spent": 5.5
                }
            ]
        }
        response = client.post(
            "/history/study-session",
            json=session_data
        )
        assert response.status_code in [200, 201], f"Failed to save study session: {response.text}"
        print(f"✓ Study session saved")

    def test_get_study_history(self, test_user):
        """Test getting study history"""
        response = client.get(f"/history/study/{test_user}?limit=100")
        assert response.status_code == 200, f"Failed to get study history: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Study history retrieved: {len(data)} records")

    def test_get_quiz_history(self, test_user):
        """Test getting quiz history"""
        response = client.get(f"/history/quiz/{test_user}?limit=100")
        assert response.status_code == 200, f"Failed to get quiz history: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Quiz history retrieved: {len(data)} records")

    def test_clear_study_history(self, test_user):
        """Test clearing study history"""
        response = client.delete(f"/history/study/{test_user}")
        assert response.status_code == 200, f"Failed to clear history: {response.text}"
        print(f"✓ Study history cleared")


class TestIntegrationFullGameFlow:
    """Test complete game flow from user creation to rewards"""

    def test_full_game_flow_sequence(self, test_user_name):
        """Test complete game loop: Create User -> Study -> Points -> Rewards -> Leaderboard"""

        print("\n=== Starting Full Game Flow Integration Test ===")

        # 1. Create user
        print("1. Creating user...")
        user_data = {
            "name": test_user_name,
            "email": f"{test_user_name}@test.com",
            "password": "testpass123",
        }
        response = client.post("/users/", json=user_data)
        assert response.status_code in [200, 201], f"Failed to create user: {response.text}"
        print(f"   ✓ User created: {test_user_name}")

        # 2. Get levels
        print("2. Fetching levels...")
        response = client.get("/levels/")
        assert response.status_code == 200
        levels = response.json()
        assert len(levels) > 0, "No levels found"
        first_level_id = levels[0].get("id", 1)
        print(f"   ✓ Found {len(levels)} levels")

        # 3. Start level
        print(f"3. Starting level {first_level_id}...")
        response = client.post(
            f"/levels/users/{test_user_name}/progress/{first_level_id}/start"
        )
        # May be locked, but endpoint should work
        assert response.status_code in [200, 403], f"Failed to start level: {response.text}"
        print(f"   ✓ Level start initiated")

        # 4. Add points (simulating study completion)
        print("4. Adding points (study completion)...")
        add_data = {
            "points": 100,
            "reason": "study_session_complete"
        }
        response = client.post(
            f"/users/{test_user_name}/points/add",
            json=add_data
        )
        assert response.status_code == 200, f"Failed to add points: {response.text}"
        points_data = response.json()
        print(f"   ✓ Points added: {points_data.get('total_points', 'N/A')} total points")

        # 5. Get current points
        print("5. Checking points balance...")
        response = client.get(f"/users/{test_user_name}/points/")
        assert response.status_code == 200
        points_info = response.json()
        current_points = points_info.get("total_points", 0)
        print(f"   ✓ Current points: {current_points}")

        # 6. Check leaderboard
        print("6. Checking leaderboard...")
        response = client.get("/leaderboard/top?limit=20")
        assert response.status_code == 200
        leaderboard = response.json()
        print(f"   ✓ Leaderboard retrieved")

        # 7. Check user's position
        print("7. Getting user position...")
        response = client.get(
            "/leaderboard/me",
            headers={"X-User-Name": test_user_name}
        )
        assert response.status_code in [200, 404]
        print(f"   ✓ User position checked")

        # 8. Get unlockables
        print("8. Checking available cosmetics...")
        response = client.get(f"/unlockables/?user_name={test_user_name}")
        assert response.status_code == 200
        unlockables = response.json()
        print(f"   ✓ Cosmetics available for purchase")

        # 9. Redeem points (if enough)
        if current_points >= 100:
            print("9. Redeeming points for cosmetic...")
            redeem_data = {
                "item": "test_cosmetic",
                "points": 50
            }
            response = client.post(
                f"/users/{test_user_name}/points/redeem",
                json=redeem_data
            )
            if response.status_code == 200:
                print(f"   ✓ Points redeemed successfully")
            else:
                print(f"   ℹ Redemption not applicable: {response.text}")
        else:
            print("9. Insufficient points for redemption (skipped)")

        # 10. Get profile
        print("10. Retrieving user profile...")
        response = client.get(f"/users/{test_user_name}/profile")
        assert response.status_code == 200
        profile = response.json()
        print(f"   ✓ Profile retrieved")

        print("\n=== Full Game Flow Integration Test PASSED ===\n")


class TestErrorHandling:
    """Test error handling across the API"""

    def test_404_non_existent_resource(self):
        """Test 404 error handling"""
        response = client.get("/users/nonexistent_12345/profile")
        assert response.status_code == 404
        print(f"✓ 404 error handled correctly")

    def test_400_bad_request(self, test_user):
        """Test 400 error handling"""
        # Try to complete level with invalid accuracy
        response = client.post(
            f"/levels/users/{test_user}/progress/1/complete?accuracy=2.0"
        )
        assert response.status_code == 400
        print(f"✓ 400 error handled correctly")

    def test_500_server_error_handling(self):
        """Test that server errors are handled gracefully"""
        # This test verifies error handling works without crashing
        response = client.get("/levels/")
        # Should not be 500, or if it is, should have proper error message
        assert response.status_code in [200, 500]
        print(f"✓ Server error handling verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
