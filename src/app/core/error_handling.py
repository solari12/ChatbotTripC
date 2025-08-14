#!/usr/bin/env python3
"""
Centralized error handling for TripC.AI Chatbot
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Base exception for workflow errors"""
    def __init__(self, message: str, error_code: str = "WORKFLOW_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        logger.error(f"WorkflowError [{error_code}]: {message}")


class ValidationError(WorkflowError):
    """Validation errors (platform, input validation)"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class AgentError(WorkflowError):
    """Agent-specific errors"""
    def __init__(self, message: str, agent_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, f"AGENT_ERROR_{agent_name.upper()}", details)
        self.agent_name = agent_name


class LLMError(WorkflowError):
    """LLM-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "LLM_ERROR", details)


class ServiceError(WorkflowError):
    """External service errors (TripC API, etc.)"""
    def __init__(self, message: str, service_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, f"SERVICE_ERROR_{service_name.upper()}", details)
        self.service_name = service_name


class ErrorHandler:
    """Centralized error handler"""
    
    @staticmethod
    def handle_workflow_error(error: WorkflowError, language: str = "vi") -> Dict[str, Any]:
        """Handle workflow errors and return user-friendly response"""
        
        # Log error with context
        logger.error(f"Handling workflow error: {error.error_code} - {error.message}")
        
        # Generate user-friendly message based on language
        if language == "vi":
            if isinstance(error, ValidationError):
                user_message = "Thông tin không hợp lệ. Vui lòng kiểm tra lại."
            elif isinstance(error, AgentError):
                user_message = "Có lỗi xảy ra khi xử lý yêu cầu. Vui lòng thử lại."
            elif isinstance(error, LLMError):
                user_message = "Hệ thống đang bận. Vui lòng thử lại sau."
            elif isinstance(error, ServiceError):
                user_message = "Dịch vụ tạm thời không khả dụng. Vui lòng thử lại sau."
            else:
                user_message = "Xin lỗi, đã xảy ra lỗi hệ thống. Vui lòng thử lại sau."
        else:
            if isinstance(error, ValidationError):
                user_message = "Invalid information. Please check and try again."
            elif isinstance(error, AgentError):
                user_message = "An error occurred while processing your request. Please try again."
            elif isinstance(error, LLMError):
                user_message = "System is busy. Please try again later."
            elif isinstance(error, ServiceError):
                user_message = "Service temporarily unavailable. Please try again later."
            else:
                user_message = "Sorry, a system error occurred. Please try again later."
        
        return {
            "type": "Error",
            "answerAI": user_message,
            "error_code": error.error_code,
            "suggestions": [
                {
                    "label": "Thử lại" if language == "vi" else "Try again",
                    "action": "retry",
                    "data": {}
                }
            ]
        }
    
    @staticmethod
    def handle_generic_error(error: Exception, language: str = "vi") -> Dict[str, Any]:
        """Handle generic exceptions"""
        logger.error(f"Handling generic error: {type(error).__name__} - {str(error)}")
        
        if language == "vi":
            user_message = "Xin lỗi, đã xảy ra lỗi không xác định. Vui lòng thử lại sau."
        else:
            user_message = "Sorry, an unknown error occurred. Please try again later."
        
        return {
            "type": "Error",
            "answerAI": user_message,
            "error_code": "UNKNOWN_ERROR",
            "suggestions": [
                {
                    "label": "Thử lại" if language == "vi" else "Try again",
                    "action": "retry",
                    "data": {}
                }
            ]
        }
    
    @staticmethod
    def create_fallback_response(language: str = "vi") -> Dict[str, Any]:
        """Create a fallback response when all else fails"""
        if language == "vi":
            user_message = "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."
        else:
            user_message = "Sorry, the system is experiencing issues. Please try again later."
        
        return {
            "type": "Error",
            "answerAI": user_message,
            "error_code": "FALLBACK_ERROR",
            "suggestions": [
                {
                    "label": "Thử lại" if language == "vi" else "Try again",
                    "action": "retry",
                    "data": {}
                }
            ]
        }
