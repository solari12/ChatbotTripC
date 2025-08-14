# 🔧 Session Management Fix - Giải quyết vấn đề tin nhắn lộn xộn

## 🚨 Vấn đề ban đầu

Khi có 2 người cùng chat với bot, tin nhắn bị lộn xộn vì:

1. **ConversationId mặc định**: Khi không có `conversationId`, hệ thống dùng `"default"`
2. **Không phân biệt user**: Không có cơ chế phân biệt user thực sự
3. **In-memory storage**: Conversation memory không persistent, dễ bị conflict

## ✅ Giải pháp đã implement

### 1. User Session Management

```python
# Tạo unique user identifier
def generate_user_identifier(request: Request) -> str:
    # Ưu tiên X-User-ID header
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user_{user_id}"
    
    # Fallback: IP + User-Agent hash
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "unknown")
    identifier = f"{client_ip}_{user_agent}"
    return f"session_{hashlib.md5(identifier.encode()).hexdigest()[:12]}"

# Tạo conversation ID unique cho mỗi user
def get_or_create_conversation_id(user_identifier: str) -> str:
    if user_identifier not in user_sessions:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        conversation_id = f"{user_identifier}_{timestamp}_{uuid.uuid4().hex[:8]}"
        user_sessions[user_identifier] = conversation_id
    return user_sessions[user_identifier]
```

### 2. Enhanced Conversation Memory

```python
class ConversationMemory:
    def __init__(self, max_turns: int = 20, session_timeout_hours: int = 24):
        self.history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.entities: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.session_info: Dict[str, Dict[str, Any]] = defaultdict(dict)  # NEW
        self.session_timeout_hours = session_timeout_hours  # NEW
    
    def add_turn(self, conversation_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None):
        # Track session metadata
        if conversation_id not in self.session_info:
            self.session_info[conversation_id] = {
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "turn_count": 0,
                "user_identifier": meta.get("user_identifier") if meta else None
            }
        
        # Add turn with timestamp
        turn_data = {
            "role": role, 
            "content": content, 
            "meta": meta or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.history[conversation_id].append(turn_data)
    
    def _cleanup_expired_sessions(self):
        # Tự động xóa session cũ để tránh memory leak
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for conv_id, session_data in self.session_info.items():
            last_activity = session_data.get("last_activity")
            if last_activity and (current_time - last_activity) > timedelta(hours=self.session_timeout_hours):
                expired_sessions.append(conv_id)
        
        for conv_id in expired_sessions:
            del self.history[conv_id]
            del self.entities[conv_id]
            del self.session_info[conv_id]
```

### 3. API Endpoint Enhancement

```python
@app.post("/api/v1/chatbot/response", response_model=ChatResponse)
async def chatbot_response(request: ChatRequest, http_request: Request):
    # Generate user identifier
    user_identifier = generate_user_identifier(http_request)
    
    # Auto-create conversation ID if not provided
    if not request.conversationId:
        conversation_id = get_or_create_conversation_id(user_identifier)
        request_dict = request.dict()
        request_dict["conversationId"] = conversation_id
        request = ChatRequest(**request_dict)
        print(f"🆔 [SESSION] Assigned conversation ID: {conversation_id} to user: {user_identifier}")
    
    # Process request
    response = await ai_orchestrator.process_request(request)
    return response
```

## 🆕 New API Endpoints

### Session Statistics
```bash
GET /api/v1/session/stats
```

Response:
```json
{
  "total_user_sessions": 5,
  "user_sessions": ["user_123", "session_abc123", ...],
  "memory_stats": {
    "total_sessions": 5,
    "total_history_entries": 25,
    "total_entities": 15,
    "oldest_session": "2024-01-15T10:30:00",
    "newest_session": "2024-01-15T15:45:00"
  }
}
```

### Clear Specific Session
```bash
DELETE /api/v1/session/{conversation_id}
```

### Clear All Sessions (Admin)
```bash
POST /api/v1/session/clear-all
```

## 🧪 Testing

Chạy test script để verify fix:

```bash
python test_session_management.py
```

Test cases:
1. **Two users with same conversation ID** - Vẫn hoạt động nhưng có warning
2. **Two users without conversation ID** - Auto-generate unique IDs
3. **Conversation continuity** - User nhớ context
4. **Session statistics** - Monitor session usage

## 📊 Conversation ID Format

### Auto-generated format:
```
{user_type}_{user_id}_{timestamp}_{random}
```

Examples:
- `user_12345_20240115_143022_a1b2c3d4`
- `session_abc123_20240115_143023_e5f6g7h8`

### Manual format:
```
{any_custom_string}
```

## 🔒 Security Considerations

1. **User validation**: Kiểm tra conversation ID có thuộc user không
2. **Session timeout**: Tự động xóa session cũ (24h)
3. **Memory limits**: Giới hạn số turn per conversation (20)
4. **IP tracking**: Log IP để debug nếu cần

## 🚀 Benefits

✅ **No more message mixing** - Mỗi user có conversation riêng  
✅ **Automatic session management** - Không cần manual conversation ID  
✅ **Memory cleanup** - Tự động xóa session cũ  
✅ **Session monitoring** - API để check session stats  
✅ **Backward compatibility** - Vẫn support manual conversation ID  
✅ **User identification** - Support custom user headers  

## 🔄 Migration

**Existing code không cần thay đổi** - hệ thống tự động:
- Tạo conversation ID nếu chưa có
- Maintain backward compatibility
- Auto-cleanup old sessions

**Optional improvements**:
- Thêm `X-User-ID` header cho better user tracking
- Sử dụng session stats API để monitor
- Clear sessions định kỳ nếu cần

