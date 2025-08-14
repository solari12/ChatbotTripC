# Language Enrichment Logic

## Tổng quan
Tính năng làm giàu ngôn ngữ được thêm vào workflow để làm cho `answerAI` tự nhiên hơn, thân thiện hơn mà không thay đổi ý nghĩa cốt lõi.

## Logic phân loại

### 1. **Được làm giàu (Enriched)**
- **Service responses**: Tìm kiếm nhà hàng, khách sạn, tour
- **Booking responses**: Đặt bàn, đặt phòng, xác nhận booking
- **QnA từ booking agent**: Câu hỏi từ booking flow (không có sources)

### 2. **KHÔNG được làm giàu (Skipped)**
- **QnA embedding responses**: Câu trả lời từ QnAAgent (có sources từ vector search)

## Cách phân biệt

```python
# QnA từ QnAAgent (embedding-based) - KHÔNG làm giàu
{
    "type": "QnA",
    "answerAI": "Bảo tàng Chăm mở cửa từ 7:00-17:00",
    "sources": [  # ← Có sources = embedding-based
        {"title": "Bảo tàng Chăm", "url": "..."}
    ]
}

# QnA từ booking agent - ĐƯỢC làm giàu  
{
    "type": "QnA",
    "answerAI": "Bạn muốn đặt bàn cho mấy người?",
    "sources": []  # ← Không có sources = từ booking agent
}
```

## Ví dụ làm giàu

### Service Response
```
Gốc: "Tìm thấy 5 nhà hàng hải sản tại Đà Nẵng"
Làm giàu: "Tôi đã tìm thấy 5 nhà hàng hải sản tuyệt vời tại Đà Nẵng cho bạn"
```

### Booking Response  
```
Gốc: "Đặt bàn thành công cho 4 người vào 19:00"
Làm giàu: "Tuyệt vời! Việc đặt bàn của bạn cho 4 người vào 19:00 đã được xác nhận thành công"
```

### QnA từ Booking Agent
```
Gốc: "Bạn muốn đặt bàn cho mấy người?"
Làm giàu: "Bạn có thể cho mình biết bạn muốn đặt bàn cho mấy người không?"
```

## Cấu hình LLM

- **Temperature**: 0.3 (thấp để đảm bảo tính nhất quán)
- **Max tokens**: 200 (đủ để làm giàu mà không quá dài)
- **Language**: Hỗ trợ tiếng Việt và tiếng Anh

## Workflow Integration

```
validate_platform → classify_intent → rewrite_to_standalone → 
route_to_agent → add_cta → enrich_language → format_response
```

Node `enrich_language` được thêm vào trước `format_response` để làm giàu ngôn ngữ cuối cùng.

## Fallback Strategy

- Nếu LLM không khả dụng → Giữ nguyên answerAI gốc
- Nếu enrichment thất bại → Giữ nguyên answerAI gốc  
- Nếu response rỗng → Giữ nguyên answerAI gốc

## Logging

```
🎨 [LANGUAGE ENRICHMENT] Enriching Service response
✅ [LANGUAGE ENRICHMENT] Successfully enriched response
⏭️ [LANGUAGE ENRICHMENT] Skipping QnA embedding response (has sources)
⚠️ [LANGUAGE ENRICHMENT] Error enriching language: ..., keeping original
```
