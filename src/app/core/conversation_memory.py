from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MemoryManager:
    """Centralized memory manager to prevent entity conflicts and overwrites"""
    
    def __init__(self, memory: 'ConversationMemory'):
        self.memory = memory
        self.update_log = defaultdict(list)
    
    def update_entities(self, conversation_id: str, updates: Dict[str, Any], source: str) -> None:
        """Update entities intelligently, preventing overwrites and logging changes"""
        try:
            current_entities = self.memory.get_entities(conversation_id)
            
            # Log the update attempt
            self.update_log[conversation_id].append({
                "source": source,
                "updates": updates.copy(),
                "timestamp": self._get_timestamp()
            })
            
            # Merge updates intelligently
            merged_entities = self._merge_entities(current_entities, updates, source)
            
            # Update memory
            self.memory.set_entities(conversation_id, merged_entities)
            
            logger.debug(f"Memory updated by {source}: {updates}")
            
        except Exception as e:
            logger.error(f"Error updating entities: {e}")
    
    def _merge_entities(self, current: Dict[str, Any], updates: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Merge entities intelligently, preventing overwrites of important data"""
        merged = current.copy()
        
        for key, value in updates.items():
            if value is None:
                continue
                
            # Special handling for different entity types
            if key in ["user_name", "user_email", "user_phone"]:
                # User info - only update if current is empty or different
                if not merged.get(key) or merged[key] != value:
                    merged[key] = value
                    logger.debug(f"Updated user info {key} by {source}")
                    
            elif key in ["current_place", "last_mentioned_place"]:
                # Place info - update and maintain history
                if key == "current_place":
                    # Move current to last_mentioned if different
                    if merged.get("current_place") and merged["current_place"] != value:
                        merged["last_mentioned_place"] = merged["current_place"]
                merged[key] = value
                logger.debug(f"Updated place info {key} by {source}")
                
            elif key in ["current_topic", "last_subject"]:
                # Topic info - update and maintain history
                if key == "current_topic":
                    # Move current to last_subject if different
                    if merged.get("current_topic") and merged["current_topic"] != value:
                        merged["last_subject"] = merged["current_topic"]
                merged[key] = value
                logger.debug(f"Updated topic info {key} by {source}")
                
            elif key == "booking":
                # Booking state - merge carefully
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    # Merge booking states
                    merged[key].update(value)
                else:
                    merged[key] = value
                logger.debug(f"Updated booking state by {source}")
                
            else:
                # Default behavior - update if not None
                merged[key] = value
                logger.debug(f"Updated entity {key} by {source}")
        
        return merged
    
    def get_entities(self, conversation_id: str) -> Dict[str, Any]:
        """Get entities with logging"""
        entities = self.memory.get_entities(conversation_id)
        logger.debug(f"Retrieved entities for {conversation_id}: {list(entities.keys())}")
        return entities
    
    def get_update_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get update history for debugging"""
        return self.update_log.get(conversation_id, [])
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging"""
        return datetime.utcnow().isoformat()


class ConversationMemory:
    """Enhanced conversation memory with user session management and cleanup"""

    def __init__(self, max_turns: int = 50, session_timeout_hours: int = 24):
        self.history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.entities: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.session_info: Dict[str, Dict[str, Any]] = defaultdict(dict)  # Track session metadata
        self.max_turns = max_turns
        self.session_timeout_hours = session_timeout_hours
        self.memory_manager = MemoryManager(self)

    def add_turn(self, conversation_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Add a conversation turn with session tracking"""
        # Update session info
        if conversation_id not in self.session_info:
            self.session_info[conversation_id] = {
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "turn_count": 0,
                "user_identifier": meta.get("user_identifier") if meta else None
            }
        else:
            self.session_info[conversation_id]["last_activity"] = datetime.utcnow()
            self.session_info[conversation_id]["turn_count"] += 1
        
        # Add turn to history
        turn_data = {
            "role": role, 
            "content": content, 
            "meta": meta or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.history[conversation_id].append(turn_data)
        
        # Limit history size
        if len(self.history[conversation_id]) > self.max_turns:
            self.history[conversation_id] = self.history[conversation_id][-self.max_turns:]
        
        logger.debug(f"Added turn to {conversation_id}: {role} ({len(content)} chars)")

    def get_recent(self, conversation_id: str, k: int = 4) -> List[Dict[str, Any]]:
        """Get recent conversation turns"""
        # Clean up expired sessions first
        self._cleanup_expired_sessions()
        
        return self.history.get(conversation_id, [])[-k:]

    def set_entities(self, conversation_id: str, data: Dict[str, Any]) -> None:
        """Set entities for conversation with session tracking"""
        self.entities[conversation_id].update(data)
        
        # Update session info
        if conversation_id in self.session_info:
            self.session_info[conversation_id]["last_activity"] = datetime.utcnow()

    def get_entities(self, conversation_id: str) -> Dict[str, Any]:
        """Get entities for conversation"""
        # Clean up expired sessions first
        self._cleanup_expired_sessions()
        
        return self.entities.get(conversation_id, {})
    
    def update_entities_safe(self, conversation_id: str, updates: Dict[str, Any], source: str) -> None:
        """Safe entity update using MemoryManager"""
        self.memory_manager.update_entities(conversation_id, updates, source)
    
    def get_session_info(self, conversation_id: str) -> Dict[str, Any]:
        """Get session information"""
        return self.session_info.get(conversation_id, {})
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active conversation IDs"""
        self._cleanup_expired_sessions()
        return list(self.session_info.keys())
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions to prevent memory leaks"""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for conv_id, session_data in self.session_info.items():
            last_activity = session_data.get("last_activity")
            if last_activity and isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            
            if last_activity and (current_time - last_activity) > timedelta(hours=self.session_timeout_hours):
                expired_sessions.append(conv_id)
        
        # Remove expired sessions
        for conv_id in expired_sessions:
            del self.history[conv_id]
            del self.entities[conv_id]
            del self.session_info[conv_id]
            logger.info(f"Cleaned up expired session: {conv_id}")
    
    def clear_session(self, conversation_id: str) -> None:
        """Clear a specific session"""
        if conversation_id in self.history:
            del self.history[conversation_id]
        if conversation_id in self.entities:
            del self.entities[conversation_id]
        if conversation_id in self.session_info:
            del self.session_info[conversation_id]
        logger.info(f"Cleared session: {conversation_id}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        self._cleanup_expired_sessions()
        
        return {
            "total_sessions": len(self.session_info),
            "total_history_entries": sum(len(history) for history in self.history.values()),
            "total_entities": sum(len(entities) for entities in self.entities.values()),
            "oldest_session": min(
                (session.get("created_at") for session in self.session_info.values() if session.get("created_at")),
                default=None
            ),
            "newest_session": max(
                (session.get("last_activity") for session in self.session_info.values() if session.get("last_activity")),
                default=None
            )
        }


