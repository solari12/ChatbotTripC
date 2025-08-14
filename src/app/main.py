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

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models.schemas import ChatRequest, ChatResponse, UserInfoRequest, UserInfoResponse
from .vector.pgvector_store import PgVectorStore
from .services.tripc_api import TripCAPIClient
from .services.keyword_analyzer import KeywordAnalyzer
from .agents.qna_agent import QnAAgent
from .agents.service_agent import ServiceAgent
from .agents.ai_orchestrator import AIAgentOrchestrator
from .services.email_service import EmailService
from .llm.open_client import OpenAIClient
from .llm.rate_limited_client import RateLimitedLLMClient

# Global variables for services
ai_orchestrator: AIAgentOrchestrator = None
email_service: EmailService = None
keyword_analyzer: KeywordAnalyzer = None

# User session management
user_sessions: Dict[str, str] = {}  # user_identifier -> conversation_id

def generate_user_identifier(request: Request) -> str:
    """Generate unique user identifier based on request"""
    # Try to get user identifier from headers or request
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user_{user_id}"
    
    # Fallback to IP + User-Agent for web users
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Create a hash-like identifier
    import hashlib
    identifier = f"{client_ip}_{user_agent}"
    return f"session_{hashlib.md5(identifier.encode()).hexdigest()[:12]}"

def get_or_create_conversation_id(user_identifier: str) -> str:
    """Get existing conversation ID or create new one for user"""
    if user_identifier not in user_sessions:
        # Create new conversation ID with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        conversation_id = f"{user_identifier}_{timestamp}_{uuid.uuid4().hex[:8]}"
        user_sessions[user_identifier] = conversation_id
        print(f"🆕 [SESSION] Created new conversation: {conversation_id} for user: {user_identifier}")
    else:
        conversation_id = user_sessions[user_identifier]
        print(f"🔄 [SESSION] Using existing conversation: {conversation_id} for user: {user_identifier}")
    
    return conversation_id

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ai_orchestrator, email_service, keyword_analyzer
    
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
    base_llm_client = OpenAIClient()  # Automatically loads from .env
    llm_client = RateLimitedLLMClient(base_llm_client)
    print("✅ LLM client initialized with rate limiting")
    
    # Initialize email service (needed for conversational booking)
    email_service = EmailService()
    print("✅ Email service initialized")

    # Initialize agents
    qna_agent = QnAAgent(vector_store, llm_client)  # Pass rate-limited client
    service_agent = ServiceAgent(tripc_client, llm_client)  # Pass rate-limited client
    print("✅ AI agents initialized")
    
    # Initialize AI Agent Orchestrator (LangGraph-based) with EmailService
    ai_orchestrator = AIAgentOrchestrator(qna_agent, service_agent, llm_client, email_service)  # Pass rate-limited client
    print("✅ AI Agent Orchestrator (LangGraph-based) initialized")
    
    # Initialize Keyword Analyzer
    keyword_analyzer = KeywordAnalyzer(llm_client, tripc_client)
    print("✅ Keyword Analyzer initialized")
    
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
async def chatbot_response(request: ChatRequest, http_request: Request):
    """
    Main chatbot endpoint with platform-aware processing using LangGraph workflow
    """
    try:
        if not ai_orchestrator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chatbot service not initialized"
            )
        
        # Generate user identifier and conversation ID
        user_identifier = generate_user_identifier(http_request)
        
        # If no conversationId provided, create one
        if not request.conversationId:
            conversation_id = get_or_create_conversation_id(user_identifier)
            # Create new request with conversation ID
            request_dict = request.dict()
            request_dict["conversationId"] = conversation_id
            request = ChatRequest(**request_dict)
            print(f"🆔 [SESSION] Assigned conversation ID: {conversation_id} to user: {user_identifier}")
        else:
            # User provided conversationId - validate it belongs to them
            conversation_id = request.conversationId
            if user_identifier in user_sessions and user_sessions[user_identifier] != conversation_id:
                print(f"⚠️ [SESSION] User {user_identifier} trying to use different conversation ID: {conversation_id}")
                # For security, we could reject this, but for now just log it
        
        # Process request through AI Agent Orchestrator (LangGraph-based)
        response = await ai_orchestrator.process_request(request)
        
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
        if getattr(request.language, "value", request.language) == "vi":
            message = f"Thông tin của bạn đã được ghi nhận. Mã tham chiếu: {booking_reference}. Chúng tôi sẽ liên hệ lại trong thời gian sớm nhất."
        else:
            message = f"Your information has been recorded. Reference: {booking_reference}. We will contact you as soon as possible."
        
        return UserInfoResponse(
            status="success",
            message=message,
            action="info_collected",
            booking_reference=booking_reference,
            success=True
        )
        
    except Exception as e:
        # Log error for debugging
        print(f"Error in user info collection: {str(e)}")
        
        # Return error response
        if getattr(request.language, "value", request.language) == "vi":
            error_message = "Có lỗi xảy ra. Vui lòng thử lại sau hoặc liên hệ hotline: 1900 1234"
        else:
            error_message = "An error occurred. Please try again later or contact our hotline."
        
        return UserInfoResponse(
            status="error",
            message=error_message,
            action="try_again",
            booking_reference=None,
            success=False
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

@app.post("/api/v1/restaurants/search-with-analysis")
async def search_restaurants_with_analysis(request: Dict[str, Any]):
    """
    Tìm kiếm nhà hàng với phân tích từ khóa và product_type_id
    """
    try:
        if not keyword_analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keyword analyzer service not initialized"
            )
        
        user_query = request.get("query", "")
        page = request.get("page", 1)
        page_size = request.get("page_size", 15)
        
        if not user_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )
        
        # Sử dụng KeywordAnalyzer để tìm kiếm
        result = await keyword_analyzer.search_restaurants_with_analysis(
            user_query=user_query,
            page=page,
            page_size=page_size
        )
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in restaurant search with analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/keywords/analyze")
async def analyze_keywords(request: Dict[str, Any]):
    """
    Phân tích từ khóa từ câu hỏi người dùng
    """
    try:
        if not keyword_analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keyword analyzer service not initialized"
            )
        
        user_query = request.get("query", "")
        
        if not user_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )
        
        # Phân tích từ khóa
        analysis_result = await keyword_analyzer.process_user_query(user_query)
        
        return {
            "status": "success",
            "data": analysis_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in keyword analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/keywords/debug")
async def debug_keywords(request: Dict[str, Any]):
    """
    Debug từ khóa và product type matching
    """
    try:
        if not keyword_analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keyword analyzer service not initialized"
            )
        
        user_query = request.get("query", "")
        
        if not user_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )
        
        # Debug matching
        debug_result = await keyword_analyzer.debug_matching(user_query)
        
        return {
            "status": "success",
            "data": debug_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in keyword debug: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/v1/test/province-ids")
async def test_province_ids():
    """
    Test các province_id để tìm province_id đúng cho Đà Nẵng
    """
    try:
        if not keyword_analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keyword analyzer service not initialized"
            )
        
        # Test province IDs
        test_result = await keyword_analyzer.test_province_ids()
        
        return {
            "status": "success",
            "data": test_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in province ID test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/v1/session/stats")
async def session_stats():
    """Get conversation session statistics"""
    try:
        if not ai_orchestrator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI orchestrator not initialized"
            )
        
        # Get memory stats
        memory_stats = ai_orchestrator.memory.get_session_stats()
        
        # Get user session info
        session_info = {
            "total_user_sessions": len(user_sessions),
            "user_sessions": list(user_sessions.keys()),
            "memory_stats": memory_stats
        }
        
        return session_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting session stats: {str(e)}"
        )

@app.delete("/api/v1/session/{conversation_id}")
async def clear_session(conversation_id: str):
    """Clear a specific conversation session"""
    try:
        if not ai_orchestrator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI orchestrator not initialized"
            )
        
        # Clear from memory
        ai_orchestrator.memory.clear_session(conversation_id)
        
        # Remove from user sessions if exists
        for user_id, conv_id in list(user_sessions.items()):
            if conv_id == conversation_id:
                del user_sessions[user_id]
                break
        
        return {"status": "success", "message": f"Session {conversation_id} cleared"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing session: {str(e)}"
        )

@app.post("/api/v1/session/clear-all")
async def clear_all_sessions():
    """Clear all conversation sessions (admin only)"""
    try:
        if not ai_orchestrator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI orchestrator not initialized"
            )
        
        # Clear all sessions from memory
        active_sessions = ai_orchestrator.memory.get_active_sessions()
        for conv_id in active_sessions:
            ai_orchestrator.memory.clear_session(conv_id)
        
        # Clear user sessions
        user_sessions.clear()
        
        return {
            "status": "success", 
            "message": f"Cleared {len(active_sessions)} sessions",
            "cleared_sessions": len(active_sessions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing all sessions: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)