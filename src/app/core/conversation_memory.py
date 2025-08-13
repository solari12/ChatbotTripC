from typing import List, Dict, Any, Optional
from collections import defaultdict


class ConversationMemory:
    """Lightweight in-memory conversation store for short-term context"""

    def __init__(self, max_turns: int = 8):
        self.history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.entities: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.max_turns = max_turns

    def add_turn(self, conversation_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
        self.history[conversation_id].append({"role": role, "content": content, "meta": meta or {}})
        if len(self.history[conversation_id]) > self.max_turns:
            self.history[conversation_id] = self.history[conversation_id][-self.max_turns:]

    def get_recent(self, conversation_id: str, k: int = 4) -> List[Dict[str, Any]]:
        return self.history.get(conversation_id, [])[-k:]

    def set_entities(self, conversation_id: str, data: Dict[str, Any]) -> None:
        self.entities[conversation_id].update(data)

    def get_entities(self, conversation_id: str) -> Dict[str, Any]:
        return self.entities.get(conversation_id, {})


