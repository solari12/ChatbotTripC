# 🔄 Hướng dẫn sử dụng Endpoints mới

## 📋 Tổng quan

Chatbot system đã được cập nhật để hỗ trợ các endpoints mới từ TripC API dev server:

- **Nhà hàng thông thường**: `supplier_type_slug=am-thuc`
- **Hộ chiếu ẩm thực**: `/api/culinary-passport/suppliers`  
- **Khách sạn**: `supplier_type_slug=luu-tru`

---

## 🎯 Logic phân loại câu hỏi

### 1. Nhà hàng thông thường
**Endpoint**: `https://tripc-api.allyai.ai/api/services/restaurants?supplier_type_slug=am-thuc`

**Khi nào sử dụng**: Khi người dùng hỏi chung chung về dịch vụ ăn uống
```
- "Tìm nhà hàng ngon ở Đà Nẵng"
- "Quán ăn gần đây"
- "Nhà hàng hải sản"
- "Món ăn Việt Nam"
```

### 2. Hộ chiếu ẩm thực  
**Endpoint**: `https://tripc-api.allyai.ai/api/culinary-passport/suppliers`

**Khi nào sử dụng**: Khi người dùng yêu cầu riêng hộ chiếu ẩm thực
```
- "Nhà hàng trong hộ chiếu ẩm thực"
- "Culinary passport Đà Nẵng"
- "Hộ chiếu ẩm thực"
- "Đặc sản Đà Nẵng có seal"
```

### 3. Khách sạn
**Endpoint**: `https://tripc-api.allyai.ai/api/services/hotels?supplier_type_slug=luu-tru`

**Khi nào sử dụng**: Khi người dùng hỏi về lưu trú
```
- "Tìm khách sạn ở Đà Nẵng"
- "Nơi ở gần biển"
- "Resort cao cấp"
- "Đặt phòng khách sạn"
```

---

## 🔧 Cách hoạt động trong code

### 1. Service Agent Detection

```python
# Trong ServiceAgent._detect_service_type()
service_keywords = {
    "restaurant": ["nhà hàng", "quán ăn", "ẩm thực", ...],
    "culinary_passport": ["hộ chiếu ẩm thực", "culinary passport", ...],
    "hotel": ["khách sạn", "lưu trú", "accommodation", ...]
}
```

### 2. API Calls

```python
# Nhà hàng thông thường
if service_type == "restaurant":
    services = await self.tripc_client.get_restaurants(
        page=1, page_size=5, supplier_type_slug="am-thuc"
    )

# Hộ chiếu ẩm thực  
elif service_type == "culinary_passport":
    services = await self.tripc_client.get_culinary_passport_suppliers(
        page=1, page_size=100
    )
    services = services[:5]  # Limit to 5

# Khách sạn
elif service_type == "hotel":
    services = await self.tripc_client.get_hotels(
        page=1, page_size=100, supplier_type_slug="luu-tru"
    )
    services = services[:5]  # Limit to 5
```

### 3. Response Sources

```python
# Sources được tự động chọn dựa trên service_type
sources = self.tripc_client.get_service_sources(service_type)

# Kết quả:
# - restaurant: "TripC API - Nhà hàng Đà Nẵng"
# - culinary_passport: "Hộ chiếu ẩm thực Đà Nẵng"  
# - hotel: "TripC API - Khách sạn Đà Nẵng"
```

---

## 🏆 Đặc điểm Seal Image

Suppliers trong Hộ chiếu ẩm thực có `sealImageUrl` đặc biệt:

```json
{
  "id": 11,
  "name": "Nhà hàng ABC",
  "type": "culinary_passport",
  "imageUrl": "https://tripc-dev.s3.amazonaws.com/images/logo.jpg",
  "sealImageUrl": "https://tripc-dev.s3.amazonaws.com/images/culinary-passport-seal.png",
  "rating": 4.5,
  "city": "Đà Nẵng"
}
```

Frontend có thể sử dụng `sealImageUrl` để hiển thị badge đặc biệt cho nhà hàng trong hộ chiếu ẩm thực.

---

## 🧪 Testing

Chạy test script để kiểm tra tích hợp:

```bash
python test_new_endpoints.py
```

Test script sẽ:
- ✅ Test general restaurants API
- ✅ Test culinary passport suppliers API  
- ✅ Test hotels API
- ✅ Test Service Agent integration với các loại query khác nhau

---

## 📝 Examples

### Example 1: General Restaurant Query

**Input**: "Tìm nhà hàng ngon ở Đà Nẵng"

**Detected Type**: `restaurant`

**API Call**: `GET /api/services/restaurants?supplier_type_slug=am-thuc&page=1&page_size=5`

**Response**:
```json
{
  "type": "Service",
  "answerAI": "Dưới đây là những nhà hàng tuyệt vời tại Đà Nẵng...",
  "services": [...],
  "sources": [
    {
      "title": "TripC API - Nhà hàng Đà Nẵng",
      "url": "https://tripc-api.allyai.ai/api/services/restaurants?supplier_type_slug=am-thuc"
    }
  ]
}
```

### Example 2: Culinary Passport Query

**Input**: "Nhà hàng trong hộ chiếu ẩm thực Đà Nẵng"

**Detected Type**: `culinary_passport`

**API Call**: `GET /api/culinary-passport/suppliers?page=1&page_size=100`

**Response**:
```json
{
  "type": "Service", 
  "answerAI": "Dưới đây là những nhà hàng trong Hộ chiếu ẩm thực Đà Nẵng...",
  "services": [
    {
      "id": 11,
      "name": "Bông",
      "type": "culinary_passport",
      "sealImageUrl": "https://tripc-dev.s3.amazonaws.com/images/culinary-passport-seal.png",
      ...
    }
  ],
  "sources": [
    {
      "title": "Hộ chiếu ẩm thực Đà Nẵng",
      "url": "https://tripc-api.allyai.ai/api/culinary-passport/suppliers"
    }
  ]
}
```

### Example 3: Hotel Query

**Input**: "Tìm khách sạn ở Đà Nẵng"

**Detected Type**: `hotel`

**API Call**: `GET /api/services/hotels?supplier_type_slug=luu-tru&page=1&page_size=100`

**Response**:
```json
{
  "type": "Service",
  "answerAI": "Dưới đây là những khách sạn tuyệt vời tại Đà Nẵng...",
  "services": [...],
  "sources": [
    {
      "title": "TripC API - Khách sạn Đà Nẵng", 
      "url": "https://tripc-api.allyai.ai/api/services/hotels?supplier_type_slug=luu-tru"
    }
  ]
}
```

---

## ⚠️ Lưu ý quan trọng

1. **Không hỗ trợ spa, vũ trường**: Chỉ hỗ trợ restaurants, culinary passport, và hotels
2. **Authentication**: Tất cả API calls đều cần Bearer token
3. **Environment**: Sử dụng `tripc-api.allyai.ai` cho development
4. **Pagination**: 
   - Restaurants: page_size=5
   - Culinary passport: page_size=100 (limit 5 trong response)
   - Hotels: page_size=100 (limit 5 trong response)

---

## 🚀 Deployment

Sau khi test thành công, hệ thống đã sẵn sàng để:
- Phản hồi chính xác với các loại query khác nhau
- Hiển thị seal images cho culinary passport suppliers
- Tích hợp seamless với TripC API endpoints mới

Chatbot sẽ tự động phân loại câu hỏi và gọi đúng endpoint tương ứng!
