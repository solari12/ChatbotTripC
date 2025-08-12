
# 🧠 TripC.AI Chatbot API Documentation (v1.0)

## 📚 Lịch sử phiên bản

| Phiên bản | Ngày cập nhật | Mô tả |
|-----------|----------------|-------|
| v1.0      | 2025-08-11     | **Giai đoạn 1 Release**: Platform-aware API, TripC API integration, QnA Agent với embedding data, Service Agent, CTA system, User booking collection |

## 📌 Mục tiêu

API này cung cấp chatbot AI cho các website du lịch trong hệ sinh thái TripC (ví dụ: [tripc.ai](https://tripc.ai)), hỗ trợ:

- **AI Agent QnA**: Trả lời câu hỏi người dùng dựa trên dữ liệu embedding từ file JSON với hình ảnh và nguồn trích dẫn được pre-indexed.
- **AI Agent Tư vấn dịch vụ**: Phân tích nhu cầu và đề xuất dịch vụ du lịch từ TripC API (nhà hàng, tour, vé tham quan).
- **Thu thập thông tin booking**: Thu thập thông tin người dùng khi có nhu cầu đặt dịch vụ.
- **CTA System**: Gợi ý tải app TripC trên web hoặc deeplink trong mobile app.
- **Integration Ready**: Tích hợp sẵn với TripC API và hỗ trợ embedding data sources với pre-indexed imageURL và sources.

---

## 🌐 API Base URL

```
https://chatbot-api.tripc.ai
```

---

## 📬 Endpoints

### 1. Main Chatbot Response

```
POST /api/v1/chatbot/response
```

### 2. User Information Collection (for Booking)

```
POST /api/v1/user/collect-info
```

---

## 📥 Request (Main Chatbot)

```json
{
  "message": "Buổi chiều ở Đà Nẵng nên đi đâu chơi?", // Bắt buộc – câu hỏi từ người dùng
  "conversationId": "conv123",                      // Tuỳ chọn – hệ thống sẽ tự tạo nếu không truyền
  "platform": "mobile_app",                        // Bắt buộc – nền tảng: "mobile_app" hoặc "web_browser"
  "device": "android",                              // Bắt buộc – thiết bị: "android", "ios", "desktop"
  "language": "vi"                                  // Bắt buộc – ngôn ngữ: "vi", "en"
}
```

### 📋 Platform & Device Parameters

#### Platform (Bắt buộc)
| Value | Description |
|-------|-------------|
| `mobile_app` | Từ TripC Mobile App (Android/iOS) |
| `web_browser` | Từ trình duyệt web (PC/Mobile Browser) |

#### Device (Bắt buộc)
| Value | Description | Compatible Platform |
|-------|-------------|-------------------|
| `android` | Thiết bị Android | `mobile_app`, `web_browser` |
| `ios` | Thiết bị iOS | `mobile_app`, `web_browser` |
| `desktop` | Máy tính để bàn | `web_browser` |

#### Language (Bắt buộc)
| Value | Description |
|-------|-------------|
| `vi` | Tiếng Việt |
| `en` | English |

### 🔧 Platform-specific Responses
- **Mobile App:** Response sẽ có deeplinks (`tripc://`) cho navigation
- **Web Browser:** Response sẽ có web URLs và CTA download app

---

## 📤 Response (Main Chatbot)

### ✅ QnA (Hỏi đáp du lịch địa phương)

```json
{
  "type": "QnA",
  "answerAI": "Buổi chiều ở Đà Nẵng bạn có thể dạo bãi biển Mỹ Khê, ngắm hoàng hôn tại bán đảo Sơn Trà hoặc ghé cầu Rồng khi lên đèn.",
  "sources": [
    {
      "title": "Du lịch Đà Nẵng - Hướng dẫn chi tiết",
      "url": "https://tripc.ai/danang-guide",
      "imageUrl": "https://cdn.tripc.ai/sources/danang-guide.jpg"
      // ✅ imageUrl và sources từ embedding data (pre-indexed)
    }
  ],
  "suggestions": [
    {
      "label": "Tìm nhà hàng gần đây",
      "detail": "Khám phá các nhà hàng nổi tiếng tại Đà Nẵng",
      "action": "show_services"
    },
    {
      "label": "Xem thêm địa điểm",
      "detail": "Gợi ý thêm các điểm tham quan khác",
      "action": "show_more_info"
    }
  ],
  "cta": {
    "device": "web",
    "label": "Tải app TripC để trải nghiệm tốt hơn",
    "url": "https://tripc.ai/mobileapp"
  }
}
```

### ✅ Service (Gợi ý dịch vụ du lịch)

```json
{
  "type": "Service",
  "answerAI": "Dưới đây là những nhà hàng hải sản tuyệt vời tại Đà Nẵng mà bạn có thể quan tâm:",
  "services": [
    {
      "id": 11,
      "name": "Bông",
      "type": "restaurant",
      "imageUrl": "https://tripc-dev.s3.amazonaws.com/images/17b6db06-278d-4504-a120-2bd6f4a9ed79/bông.jpg",
      "coverImageUrl": "https://tripc-dev.s3.amazonaws.com/images/c400faf6-9775-4b3b-8cb4-1997f5e5e67c/hinh-anh-trang-tri-spa-dep-2-2400x1500.jpg",
      "rating": 0,
      "totalReviews": 0,
      "address": "500 Núi Thành, Hải Châu, Đà Nẵng",
      "city": "Đà Nẵng",
      "productTypes": "Trà sữa",
      "priceRange": "$$",
      "description": "Quán Bông có không gian thoáng mát, rộng rãi. Chuyên phục vụ trà sữa, soda, rau câu và nhiều đồ uống hấp dẫn khác.",
      "workingHoursDisplay": "06:00-22:00",
      "amenities": ["Không gian thoáng mát", "Phục vụ chu đáo"],
      "location": {
        "lat": 16.0721,
        "lng": 108.2338
      }
    }
  ],
  "sources": [
    {
      "title": "TripC API - Nhà hàng Đà Nẵng",
      "url": "https://api.tripc.ai/services/restaurants",
      "imageUrl": "https://cdn.tripc.ai/sources/tripc-api.jpg"
      // ✅ Service sources từ TripC API metadata (not embedding)
    }
  ],
  "suggestions": [
    {
      "label": "Đặt bàn ngay",
      "action": "collect_user_info"
    },
    {
      "label": "Xem thêm nhà hàng",
      "action": "show_more_services"
    }
  ],
  "cta": {
    "device": "web",
    "label": "Tải app TripC để xem chi tiết",
    "url": "https://tripc.ai/mobileapp"
  }
}
```

---

## 📨 User Information Collection API

### Endpoint
```
POST /api/v1/user/collect-info
```

### Mục đích
Endpoint này được sử dụng khi người dùng muốn đặt dịch vụ sau khi tương tác với chatbot. Thường được gọi thông qua action `collect_user_info` trong suggestions.

### Request
```json
{
  "user_id": "user_123",           // Tuỳ chọn - ID người dùng từ session
  "name": "Nguyễn Văn A",          // Bắt buộc - Họ tên đầy đủ
  "email": "user@example.com",     // Bắt buộc - Email liên hệ
  "phone": "+84901234567",         // Bắt buộc - Số điện thoại
  "service_interest": "Nhà hàng hải sản",  // Tuỳ chọn - Dịch vụ quan tâm
  "message": "Muốn đặt bàn cho 4 người vào tối mai",  // Tuỳ chọn - Tin nhắn bổ sung
  "location": "Da Nang",           // Tuỳ chọn - Địa điểm
  "platform": "web_browser",       // Tuỳ chọn - Nền tảng gọi API
  "device": "android",             // Tuỳ chọn - Thiết bị
  "language": "vi"                 // Tuỳ chọn - Ngôn ngữ
}
```

### Response thành công
```json
{
  "status": "success",
  "message": "Thông tin của bạn đã được ghi nhận. Chúng tôi sẽ liên hệ lại trong thời gian sớm nhất.",
  "action": "info_collected"
}
```

### Response lỗi
```json
{
  "status": "error", 
  "message": "Có lỗi xảy ra. Vui lòng thử lại sau hoặc liên hệ hotline: 1900 1234",
  "action": "try_again"
}
```

### Email Workflow
Khi thông tin được thu thập thành công:

1. **Email đến booking@tripc.ai** - Chứa đầy đủ thông tin người dùng và yêu cầu
2. **Email xác nhận đến user** - Thông báo đã nhận được yêu cầu và sẽ liên hệ lại

> 📧 **Ghi chú**: Nếu chưa cấu hình SMTP credentials, hệ thống sẽ log thông tin thay vì gửi email thật.

---

## 🧭 CTA (Call-to-Action) System

### CTA Response Based on Platform & Device

#### 1. Web Browser Users (platform: "web_browser")
```json
{
  "device": "desktop",
  "label": "Tải app TripC để trải nghiệm tốt hơn",
  "url": "https://tripc.ai/mobileapp"
}
```

```json
{
  "device": "android", 
  "label": "Tải app TripC cho Android",
  "url": "https://play.google.com/store/apps/details?id=com.tripc.ai.app"
}
```

```json
{
  "device": "ios",
  "label": "Tải app TripC cho iOS", 
  "url": "https://apps.apple.com/vn/app/tripc-app/id6745506417"
}
```

#### 2. Mobile App Users (platform: "mobile_app")
```json
{
  "device": "android",
  "label": "Xem chi tiết trong app",
  "deeplink": "tripc://restaurant/11"
}
```

```json
{
  "device": "ios",
  "label": "Xem chi tiết trong app",
  "deeplink": "tripc://restaurant/11"
}
```

### CTA Logic Table

| Platform | Device | CTA Type | Action |
|----------|--------|----------|---------|
| `web_browser` | `desktop` | Download App | General app download page |
| `web_browser` | `android` | Download App | Google Play Store |
| `web_browser` | `ios` | Download App | App Store |
| `mobile_app` | `android` | Deeplink | Navigate within app |
| `mobile_app` | `ios` | Deeplink | Navigate within app |

---

## 🔧 Service Integration (TripC API)

### TripC API Base URL
```
https://api.tripc.ai
```

### Key TripC API Endpoints
- `GET /api/services/restaurants?page=1&page_size=10` - Lấy danh sách nhà hàng
- `GET /api/services/restaurants/{id}` - Chi tiết nhà hàng cụ thể

### API Authentication
```bash
Authorization: Bearer {access_token}
```

### 🚫 Service URL Policy
- **Services trong response:** KHÔNG có webURL hoặc deeplink individual
- **Chi tiết dịch vụ:** Chỉ accessible qua TripC App
- **CTA Purpose:** Hướng dẫn user tải app để xem chi tiết

---

## 📊 Data Sources & Attribution

### QnA Agent Sources (Embedding-based)
```json
{
  "sources": [
    {
      "title": "Du lịch Đà Nẵng - Hướng dẫn chi tiết",
      "url": "https://tripc.ai/danang-guide",
      "imageUrl": "https://cdn.tripc.ai/sources/guide.jpg"
      // ✅ Tất cả imageUrl và sources từ embedding data (pre-indexed)
    }
  ]
}
```

**Characteristics:**
- ✅ **Pre-indexed Content**: Tất cả imageURL và sources được embed sẵn trong PgVector
- ✅ **No Real-time APIs**: QnA không gọi external APIs cho sources/images  
- ✅ **Fast Response**: Vector similarity search trong pre-indexed data
- ✅ **Consistent Quality**: Curated content với verified sources

### Service Agent Sources (TripC API-based)
```json
{
  "sources": [
    {
      "title": "TripC API - Nhà hàng Đà Nẵng", 
      "url": "https://api.tripc.ai/services/restaurants",
      "imageUrl": "https://cdn.tripc.ai/sources/tripc-api.jpg"
      // ✅ Service sources từ TripC API metadata (real-time)
    }
  ]
}
```

**Characteristics:**
- ✅ **Real-time Data**: Fresh service data từ TripC ecosystem
- ✅ **API Integration**: Direct calls to `api.tripc.ai`
- ✅ **Service Images**: `logo_url`, `cover_image_url` từ S3 bucket
- ✅ **App-first Policy**: No individual service URLs

### 🔄 Data Source Strategy

#### QnA Flow: Embedding-first Approach
```
User Question → Vector Search → Pre-indexed Content + Sources + ImageURLs → Response
```
- **No External API Calls** for QnA sources
- **Fast Response Time** với vector similarity search
- **Consistent Data Quality** từ curated embedding content

#### Service Flow: Live API Approach  
```
Service Request → TripC API Call → Live Service Data + Metadata → Response
```
- **Real-time Service Data** từ TripC ecosystem
- **Fresh Information** về restaurants, availability, prices
- **Dynamic Sources** based on API metadata

Tối đa 5 địa điểm liên quan đến câu hỏi du lịch địa phương.

```json
"places": [
  {
    "name": "Bãi biển Mỹ Khê",
    "address": "Ngũ Hành Sơn, Đà Nẵng",
    "rating": 4.7,
    "location": { "lat": 16.0594, "lng": 108.2498 },
    "imageUrl": "https://cdn.tripc.ai/places/mykhe.jpg",
    "detailInfo": {
      "type": "Bãi biển",
      "description": "Bãi biển Mỹ Khê nổi tiếng với cát trắng mịn và nước biển trong xanh, thích hợp cho các hoạt động tắm biển và thể thao dưới nước.",
      "hours": "Cả ngày",
      "phone": "0236 789 123"
    }
  }
]
```

### 🔎 detailInfo (tuỳ chọn)

Thông tin chi tiết về địa điểm, bao gồm các trường cơ bản:

- `type`: Loại hình (nhà hàng, bãi biển, cầu biểu tượng...)
- `description`: Mô tả ngắn gọn
- `hours`: Giờ mở cửa
- `phone`: Số điện thoại
- `priceRange`: Mức giá (`$`, `$$`, `$$$`)
- `amenities`: Tiện ích (WiFi, bãi đậu xe...)

> **Ghi chú**: `detailInfo` chỉ hiển thị khi có dữ liệu từ hệ thống nội bộ.

---

##  Ví dụ mở rộng (v1.0)

### Ví dụ 1 – QnA: Câu hỏi du lịch địa phương (Web Browser)

**Request**:
```json
{
  "message": "Buổi chiều ở Đà Nẵng nên đi đâu chơi?",
  "conversationId": "conv_001",
  "platform": "web_browser",
  "device": "desktop",
  "language": "vi"
}
```

**Response**:
```json
{
  "type": "QnA", 
  "answerAI": "Buổi chiều ở Đà Nẵng bạn có thể dạo bãi biển Mỹ Khê, ngắm hoàng hôn tại bán đảo Sơn Trà hoặc ghé cầu Rồng khi lên đèn. Đây đều là những địa điểm nổi tiếng và thích hợp cho hoạt động buổi chiều.",
  "sources": [
    {
      "title": "Du lịch Đà Nẵng - Hướng dẫn chi tiết",
      "url": "https://tripc.ai/guides/danang-afternoon",
      "imageUrl": "https://cdn.tripc.ai/sources/danang-guide.jpg"
      // ✅ imageUrl và sources từ embedding data (pre-indexed)
    }
  ],
  "suggestions": [
    {
      "label": "Tìm nhà hàng gần đây",
      "action": "show_services"
    },
    {
      "label": "Xem thêm gợi ý",
      "action": "show_more_info"
    }
  ],
  "cta": {
    "device": "desktop",
    "label": "Tải app TripC để trải nghiệm tốt hơn",
    "url": "https://tripc.ai/mobileapp"
  }
}
```

---

### Ví dụ 2 – Service: Gợi ý nhà hàng (Mobile App)

**Request**:
```json
{
  "message": "Tôi muốn tìm nhà hàng hải sản ngon ở Đà Nẵng",
  "conversationId": "conv_002",
  "platform": "mobile_app",
  "device": "android",
  "language": "vi"
}
```

**Response**:
```json
{
  "type": "Service",
  "answerAI": "Dưới đây là những nhà hàng hải sản tuyệt vời tại Đà Nẵng mà bạn có thể tham khảo:",
  "services": [
    {
      "id": 11,
      "name": "Bông",
      "type": "restaurant",
      "imageUrl": "https://tripc-dev.s3.amazonaws.com/images/17b6db06-278d-4504-a120-2bd6f4a9ed79/bông.jpg",
      "coverImageUrl": "https://tripc-dev.s3.amazonaws.com/images/c400faf6-9775-4b3b-8cb4-1997f5e5e67c/hinh-anh-trang-tri-spa-dep-2-2400x1500.jpg",
      "rating": 0,
      "totalReviews": 0,
      "address": "500 Núi Thành, Hải Châu, Đà Nẵng",
      "city": "Đà Nẵng",
      "productTypes": "Trà sữa",
      "priceRange": "$$",
      "description": "Quán Bông có không gian thoáng mát, rộng rãi. Chuyên phục vụ trà sữa, soda, rau câu và nhiều đồ uống hấp dẫn khác.",
      "workingHoursDisplay": "06:00-22:00",
      "amenities": ["Không gian thoáng mát", "Phục vụ chu đáo"],
      "location": {
        "lat": 16.0721,
        "lng": 108.2338
      }
    },
    {
      "id": 25,
      "name": "Đồng Quê",
      "type": "restaurant", 
      "imageUrl": "https://tripc-dev.s3.amazonaws.com/images/c9684ad0-d413-40dd-8bfd-f7493dd7c60f/bánh xèo.jpg",
      "coverImageUrl": "https://tripc-dev.s3.amazonaws.com/images/fc4a2800-7c5e-4f1b-948e-42e470cdf3dc/mì quảng.png",
      "rating": 0,
      "totalReviews": 0,
      "address": "123 Đống Đa, Hải Châu, Đà Nẵng",
      "city": "Đà Nẵng",
      "productTypes": "Bún, Lẩu, Bánh xèo",
      "priceRange": "$$$",
      "description": "Nhà hàng đặc sản miền Trung với các món ăn truyền thống như bánh xèo, mì quảng.",
      "workingHoursDisplay": "10:00-22:00",
      "amenities": ["Đặc sản miền Trung", "Không gian truyền thống"],
      "location": {
        "lat": 16.0654,
        "lng": 108.2208
      }
    }
    }
  ],
  "sources": [
    {
      "title": "TripC API - Nhà hàng Đà Nẵng",
      "url": "https://api.tripc.ai/services/restaurants",
      "imageUrl": "https://cdn.tripc.ai/sources/tripc-restaurants.jpg"
      // ✅ Service sources từ TripC API metadata (real-time)
    }
  ],
  "suggestions": [
    {
      "label": "Đặt bàn ngay",
      "action": "collect_user_info"
    },
    {
      "label": "Xem thêm nhà hàng",
      "action": "show_more_services"
    }
  ],
  "cta": {
    "device": "android",
    "label": "Xem chi tiết trong app",
    "deeplink": "tripc://restaurant/11"
  }
}
```

---

### Ví dụ 3 – Complete Booking Workflow (v1.0)

**Bước 1 - User hỏi về dịch vụ (Web Browser):**
```json
{
  "message": "Tôi cần đặt nhà hàng cho 6 người tối nay",
  "conversationId": "conv_003",
  "platform": "web_browser",
  "device": "android",
  "language": "vi"
}
```

**Response với suggestion đặt chỗ:**
```json
{
  "type": "Service",
  "answerAI": "Tôi sẽ gợi ý một số nhà hàng phù hợp cho 6 người:",
  "services": [{...}],
  "suggestions": [
    {
      "label": "Đặt bàn ngay",
      "detail": "Để lại thông tin để nhận hỗ trợ đặt bàn",
      "action": "collect_user_info"
    }
  ]
}
```

**Bước 2 - User click "Đặt bàn ngay", frontend gọi collect-info:**
```json
{
  "name": "Nguyễn Văn A",
  "email": "nguyenvana@email.com",
  "phone": "+84901234567", 
  "service_interest": "Nhà hàng cho 6 người",
  "message": "Cần đặt bàn cho 6 người vào tối nay 19h"
}
```

**Response xác nhận:**
```json
{
  "status": "success",
  "message": "Thông tin của bạn đã được ghi nhận. Chúng tôi sẽ liên hệ lại trong thời gian sớm nhất.",
  "action": "info_collected"
}
```

**Bước 3 - Automatic Email System:**
- ✉️ Email đến `booking@tripc.ai` với thông tin đầy đủ
- ✉️ Email xác nhận đến user về việc đã nhận yêu cầu

> 🎯 **Giai đoạn 1 Workflow**: Chat → Service suggestion → User info collection → Email booking system

---

## 🎉 Version 1.0 Features Summary

### ✅ **Completed Features (Giai đoạn 1)**

#### Epic 1: UI Web App Chat (tripc.ai)
- 🌐 **Web Chat Interface**: Đầy đủ giao diện chat với AI responses, suggestions, và CTA
- 📱 **Responsive Design**: Tương thích với desktop và mobile browsers
- 🔗 **App Download CTA**: Gợi ý tải app TripC khi dùng trên web

#### Epic 2: UI Mobile App Chat (TripC Mobile App)  
- 📲 **Mobile Integration Ready**: Hỗ trợ deeplinks cho tích hợp vào app
- 🔗 **Deeplink Navigation**: `tripc://service/{id}` cho navigation trong app

#### Epic 3: AI Agent QnA
- 🧠 **Embedding-based QnA**: Trả lời dựa trên dữ liệu đã embedding trong PgVector
- 🖼️ **Pre-indexed Sources**: imageURL và sources được embed sẵn trong knowledge base (không gọi external APIs)
- 📚 **Source Transparency**: Hiển thị nguồn gốc từ embedding data với pre-indexed metadata
- 🔍 **Vector Search**: Similarity search trong pre-indexed content với attached sources

#### Epic 4: AI Agent Tư vấn dịch vụ
- 🍽️ **TripC API Integration**: Lấy dữ liệu nhà hàng từ API TripC
- 🏨 **Service Recommendations**: Gợi ý dịch vụ phù hợp với nhu cầu
- 📝 **Booking Collection**: Thu thập thông tin booking qua `/api/v1/user/collect-info`

#### Epic 5: CTA System
- 🌐 **Web CTA**: Download app button cho web users
- 📱 **Mobile Deeplinks**: Navigation links cho mobile app users

### 🔄 **Backend Implementation**

#### Core Endpoints
- ✅ `POST /api/v1/chatbot/response` - Main chat endpoint
- ✅ `POST /api/v1/user/collect-info` - User booking information collection

#### Data Integration
- ✅ **TripC API**: Integration với restaurant APIs cho Service responses
- ✅ **Embedding Data**: JSON-based knowledge base với pre-indexed sources và imageURLs cho QnA responses
- ✅ **Email System**: Automated booking notifications
- 🔍 **Source Separation**: QnA sources từ embedding data, Service sources từ TripC API metadata

#### Response Types
- ✅ **QnA Type**: AI answers với sources và suggestions
- ✅ **Service Type**: Service listings với TripC data integration

---

## 🚀 **Giai đoạn 2 (Future Roadmap)**

- 🗓️ **AI Agent Gợi ý hoạt động**: Lịch trình và activity recommendations
- 🔄 **Chat Synchronization**: Đồng bộ giữa web và mobile
- 🌍 **Multi-language Support**: Hỗ trợ thêm ngôn ngữ
- 📖 **Chat History**: Lưu và xem lại lịch sử chat

---

## 📧 **Contact & Support**

- **API Base URL**: `https://chatbot-api.tripc.ai`
- **Booking Email**: `booking@tripc.ai`
- **API Version**: v1.0 (Platform-aware)

---

