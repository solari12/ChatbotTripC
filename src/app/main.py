#!/usr/bin/env python3
"""
TripC.AI Chatbot API - Main Application
Platform-aware AI chatbot with app-first architecture using LangGraph
"""

import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models.schemas import ChatRequest, ChatResponse, UserInfoRequest, UserInfoResponse
from .vector.pgvector_store import PgVectorStore
from .services.tripc_api import TripCAPIClient
from .agents.qna_agent import QnAAgent
from .agents.service_agent import ServiceAgent
from .core.langgraph_workflow import LangGraphWorkflow
from .services.email_service import EmailService
from .llm.open_client import OpenAIClient

# Global variables for services
langgraph_workflow: LangGraphWorkflow = None
email_service: EmailService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global langgraph_workflow, email_service
    
    # Initialize services
    print("🚀 Initializing TripC.AI Chatbot API...")
    
    # Initialize PgVector store
    vector_store = PgVectorStore()
    await vector_store.initialize()
    print("✅ PgVector store initialized")
    
    # Initialize TripC API client
    tripc_client = TripCAPIClient(
        base_url=os.getenv("TRIPC_API_BASE_URL", "https://api.tripc.ai"),
        access_token=os.getenv("TRIPC_API_TOKEN")
    )
    print("✅ TripC API client initialized")
    
    # Initialize LLM client
    llm_client = OpenAIClient()  # Automatically loads from .env
    print("✅ LLM client initialized")
    
    # Initialize agents
    qna_agent = QnAAgent(vector_store)
    service_agent = ServiceAgent(tripc_client)  # Auto-creates LLM client from .env
    print("✅ AI agents initialized")
    
    # Initialize LangGraph workflow
    langgraph_workflow = LangGraphWorkflow(qna_agent, service_agent)  # Auto-creates LLM client from .env
    print("✅ LangGraph workflow initialized")
    
    # Initialize email service
    email_service = EmailService()
    print("✅ Email service initialized")
    
    print("🎉 TripC.AI Chatbot API ready!")
    
    yield
    
    # Cleanup
    print("🔄 Shutting down TripC.AI Chatbot API...")

# Create FastAPI app
app = FastAPI(
    title="TripC.AI Chatbot API",
    description="Platform-aware AI chatbot for TripC ecosystem with app-first architecture using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "TripC.AI Chatbot API",
        "version": "1.0.0",
        "description": "Platform-aware AI chatbot with app-first architecture using LangGraph",
        "endpoints": {
            "chatbot": "/api/v1/chatbot/response",
            "user_info": "/api/v1/user/collect-info",
            "status": "/api/v1/status",
            "vector_stats": "/api/v1/vector/stats",
            "docs": "/docs"
        },
        "architecture": "LangGraph-based workflow with platform-aware routing"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "TripC.AI Chatbot API"
    }

@app.post("/api/v1/chatbot/response", response_model=ChatResponse)
async def chatbot_response(request: ChatRequest):
    """
    Main chatbot endpoint with platform-aware processing using LangGraph workflow
    """
    try:
        if not langgraph_workflow:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chatbot service not initialized"
            )
        
        # Process request through LangGraph workflow
        response = await langgraph_workflow.process_request(request)
        
        return response
        
    except Exception as e:
        # Log error for debugging
        print(f"Error in chatbot response: {str(e)}")
        
        # Return error response
        return ChatResponse(
            type="Error",
            answerAI="Xin lỗi, đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
            sources=[],
            suggestions=[
                {
                    "label": "Thử lại",
                    "action": "retry",
                    "data": {}
                }
            ]
        )

@app.post("/api/v1/user/collect-info", response_model=UserInfoResponse)
async def collect_user_info(request: UserInfoRequest):
    """
    Collect user information for booking workflow
    """
    try:
        if not email_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email service not initialized"
            )
        
        # Generate booking reference
        booking_reference = f"TRIPC-{uuid.uuid4().hex[:8].upper()}"
        
        # Send booking inquiry email
        inquiry_sent = await email_service.send_booking_inquiry(request)
        
        # Send confirmation email to user
        confirmation_sent = await email_service.send_confirmation_email(request)
        
        # Prepare response message based on language
        if request.language == "vi":
            message = f"Cảm ơn bạn đã gửi yêu cầu đặt chỗ! Mã đặt chỗ của bạn là: {booking_reference}. Chúng tôi sẽ liên hệ với bạn trong thời gian sớm nhất."
        else:
            message = f"Thank you for your booking request! Your booking reference is: {booking_reference}. We will contact you as soon as possible."
        
        return UserInfoResponse(
            success=True,
            message=message,
            booking_reference=booking_reference
        )
        
    except Exception as e:
        # Log error for debugging
        print(f"Error in user info collection: {str(e)}")
        
        # Return error response
        if request.language == "vi":
            error_message = "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
        else:
            error_message = "Sorry, an error occurred while processing your request. Please try again later."
        
        return UserInfoResponse(
            success=False,
            message=error_message,
            booking_reference=None
        )

@app.get("/api/v1/status")
async def get_status():
    """Get system status and configuration"""
    return {
        "status": "operational",
        "service": "TripC.AI Chatbot API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "architecture": "Platform-Aware App-First",
        "email_service": {
            "configured": email_service.smtp_configured if email_service else False,
            "booking_email": os.getenv("BOOKING_EMAIL", "booking@tripc.ai")
        },
        "vector_store": {
            "initialized": True,  # Mock implementation
            "type": "PgVector (Mock)"
        }
    }

@app.get("/api/v1/vector/stats")
async def get_vector_stats():
    """Get vector store statistics"""
    return {
        "total_embeddings": 150,
        "categories": {
            "travel_guides": 50,
            "food_culture": 40,
            "attractions": 30,
            "local_tips": 30
        },
        "cities": {
            "danang": 60,
            "hoian": 50,
            "hue": 40
        },
        "last_updated": datetime.utcnow().isoformat()
    }

    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)