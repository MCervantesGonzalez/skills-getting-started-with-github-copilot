"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    
    # Clear and restore activities
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_has_correct_structure(self, client, reset_activities):
        """Test that activities have the correct data structure"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)
    
    def test_get_activities_returns_participant_list(self, client, reset_activities):
        """Test that activities include participant emails"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_adds_participant_to_list(self, client, reset_activities):
        """Test that signup adds participant to the activity participants list"""
        initial_count = len(activities["Programming Class"]["participants"])
        
        response = client.post(
            "/activities/Programming Class/signup",
            params={"email": "alice@mergington.edu"}
        )
        assert response.status_code == 200
        assert len(activities["Programming Class"]["participants"]) == initial_count + 1
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup to non-existent activity returns 404"""
        response = client.post(
            "/activities/Non Existent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_email_returns_400(self, client, reset_activities):
        """Test signing up with an email already registered returns 400"""
        # michael@mergington.edu is already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_same_email_different_activity(self, client, reset_activities):
        """Test that same email can sign up for different activities"""
        # michael@mergington.edu is in Chess Club, should be able to sign up for Programming Class
        response = client.post(
            "/activities/Programming Class/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        assert "michael@mergington.edu" in activities["Programming Class"]["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client, reset_activities):
        """Test successfully removing a participant from an activity"""
        response = client.delete(
            "/activities/Chess Club/participants/michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_remove_participant_reduces_count(self, client, reset_activities):
        """Test that removing participant reduces the participants list"""
        initial_count = len(activities["Gym Class"]["participants"])
        
        response = client.delete(
            "/activities/Gym Class/participants/john@mergington.edu"
        )
        assert response.status_code == 200
        assert len(activities["Gym Class"]["participants"]) == initial_count - 1
    
    def test_remove_participant_activity_not_found(self, client, reset_activities):
        """Test removing participant from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Non Existent Club/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_remove_participant_not_found(self, client, reset_activities):
        """Test removing non-existent participant returns 404"""
        response = client.delete(
            "/activities/Chess Club/participants/noone@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_remove_participant_idempotent_issue(self, client, reset_activities):
        """Test that removing the same participant twice fails on second attempt"""
        # First removal should succeed
        response1 = client.delete(
            "/activities/Chess Club/participants/daniel@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Second removal should fail
        response2 = client.delete(
            "/activities/Chess Club/participants/daniel@mergington.edu"
        )
        assert response2.status_code == 404


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_full_signup_and_removal_workflow(self, client, reset_activities):
        """Test complete workflow: signup, verify, then remove"""
        email = "testuser@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        get_response = client.get("/activities")
        data = get_response.json()
        assert email in data[activity]["participants"]
        
        # Remove
        remove_response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert remove_response.status_code == 200
        
        # Verify removal
        get_response = client.get("/activities")
        data = get_response.json()
        assert email not in data[activity]["participants"]
    
    def test_multiple_signups(self, client, reset_activities):
        """Test signing up multiple students for the same activity"""
        activity = "Gym Class"
        students = ["alice@mergington.edu", "bob@mergington.edu", "charlie@mergington.edu"]
        
        for student in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": student}
            )
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        data = response.json()
        for student in students:
            assert student in data[activity]["participants"]
        
        assert len(data[activity]["participants"]) == 5  # 2 original + 3 new
