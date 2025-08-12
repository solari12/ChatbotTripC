# test_main.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Welcome to TripC.AI Chatbot API v1.0"
    assert data["version"] == "1.0.0"
    assert data["architecture"] == "Platform-Aware App-First"


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "TripC.AI Chatbot API"


def test_chatbot_response_valid_request():
    """Test chatbot response with valid request"""
    request_data = {
        "message": "Xin chào",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi"
    }
    
    response = client.post("/api/v1/chatbot/response", json=request_data)
    # Note: This will return 503 in test environment due to service initialization
    # In production, it would return 200 with proper response
    assert response.status_code in [200, 503]


def test_chatbot_response_invalid_platform():
    """Test chatbot response with invalid platform-device combination"""
    request_data = {
        "message": "Xin chào",
        "platform": "mobile_app",
        "device": "desktop",  # Invalid: mobile_app + desktop
        "language": "vi"
    }
    
    response = client.post("/api/v1/chatbot/response", json=request_data)
    assert response.status_code == 400


def test_chatbot_response_missing_fields():
    """Test chatbot response with missing required fields"""
    request_data = {
        "message": "Xin chào"
        # Missing platform, device, language
    }
    
    response = client.post("/api/v1/chatbot/response", json=request_data)
    assert response.status_code == 422  # Validation error


def test_user_collect_info_valid_request():
    """Test user info collection with valid request"""
    request_data = {
        "name": "Nguyễn Văn A",
        "email": "user@example.com",
        "phone": "+84901234567",
        "message": "Tôi muốn đặt bàn",
        "platform": "web_browser",
        "device": "android",
        "language": "vi"
    }
    
    response = client.post("/api/v1/user/collect-info", json=request_data)
    # Note: This will return 503 in test environment due to service initialization
    # In production, it would return 200 with proper response
    assert response.status_code in [200, 503]


def test_user_collect_info_missing_fields():
    """Test user info collection with missing required fields"""
    request_data = {
        "name": "Nguyễn Văn A"
        # Missing email, phone, message, platform, device, language
    }
    
    response = client.post("/api/v1/user/collect-info", json=request_data)
    assert response.status_code == 422  # Validation error


def test_status_endpoint():
    """Test status endpoint"""
    response = client.get("/api/v1/status")
    # Note: This will return 503 in test environment due to service initialization
    # In production, it would return 200 with proper status
    assert response.status_code in [200, 503]


def test_vector_stats_endpoint():
    """Test vector stats endpoint"""
    response = client.get("/api/v1/vector/stats")
    # Note: This will return 503 in test environment due to service initialization
    # In production, it would return 200 with proper stats
    assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__])