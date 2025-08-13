# 🔄 API Updates - January 2025

## 📋 Tóm tắt thay đổi

Dựa trên thông tin từ @Phụng Nguyễn, server tripc-api dev đã có những thay đổi quan trọng về API endpoints và cách lấy suppliers.

---

## 🆕 API Mới

### 1. Hộ chiếu ẩm thực Đà Nẵng
**Endpoint mới:**
```
GET /api/culinary-passport/suppliers
```

**Mục đích:** Lấy danh sách các suppliers nằm trong `supplier_collections.title="Hộ chiếu ẩm thực Đà Nẵng"`

**Request Example:**
```bash
curl --location 'https://tripc-api.allyai.ai/api/culinary-passport/suppliers?page=1&page_size=100' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoic2lnbmluIiwiaWQiOiI5MSIsImV4cCI6MTc1NTIzMDQ4OX0._-tMmdPo_z8kSoRIG6TeRf5yid51QydPc5Y2-Mk-uNQ' \
--data ''
```

**Đặc điểm:**
- ✅ Suppliers có `seal_image_url` đặc biệt để phân biệt
- ✅ Lọc theo `supplier_collections.title="Hộ chiếu ẩm thực Đà Nẵng"`
- ✅ Hỗ trợ pagination với `page` và `page_size`

---

## 🔄 API Cập nhật

### 2. Nhà hàng - Cập nhật endpoint
**Endpoint:** `GET /api/services/restaurants`

**Thay đổi:**
- ✅ Sử dụng `supplier_type_slug=am-thuc` để lọc nhà hàng
- ✅ Cập nhật request example với parameter mới

**Request Example mới:**
```bash
curl --location 'https://tripc-api.allyai.ai/api/services/restaurants?page=1&supplier_type_slug=am-thuc&page_size=5' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoic2lnbmluIiwiaWQiOiI5MSIsImV4cCI6MTc1NTIzMDQ4OX0._-tMmdPo_z8kSoRIG6TeRf5yid51QydPc5Y2-Mk-uNQ' \
--data ''
```

### 3. Khách sạn - Endpoint mới
**Endpoint mới:** `GET /api/services/hotels`

**Mục đích:** Lấy danh sách khách sạn

**Request Example:**
```bash
curl --location 'https://tripc-api.allyai.ai/api/services/hotels?page=1&page_size=100&supplier_type_slug=luu-tru' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoic2lnbmluIiwiaWQiOiI5MSIsImV4cCI6MTc1NTIzMDQ4OX0._-tMmdPo_z8kSoRIG6TeRf5yid51QydPc5Y2-Mk-uNQ' \
--data ''
```

**Đặc điểm:**
- ✅ Sử dụng `supplier_type_slug=luu-tru` để lọc khách sạn
- ✅ Hỗ trợ pagination
- ✅ Authentication với Bearer token

---

## 🔧 Authentication & Environment

### Development vs Production
- **Development:** `https://tripc-api.allyai.ai`
- **Production:** `https://api.tripc.ai`

### Authentication
- ✅ Tất cả API calls đều yêu cầu Bearer token
- ✅ JWT token format: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

---

## 📊 Response Format Updates

### Culinary Passport Suppliers
```json
{
    "status": true,
    "data": [
        {
            "id": 1,
            "name": "Nhà hàng A",
            "logo_url": "https://tripc-dev.s3.amazonaws.com/images/...",
            "rating": 4.5,
            "total_reviews": 120,
            "product_types": "Hải sản, Ẩm thực địa phương",
            "full_address": "123 Đường ABC, Quận XYZ, Đà Nẵng",
            "is_like": false,
            "cover_image_url": "https://tripc-dev.s3.amazonaws.com/images/...",
            "city": "Đà Nẵng",
            "lat": "16.0594",
            "long": "108.2498",
            "seal_image_url": "https://tripc-dev.s3.amazonaws.com/images/culinary-passport-seal.png"
        }
    ],
    "total": 50
}
```

**Đặc điểm quan trọng:**
- ✅ `seal_image_url` - URL hình ảnh seal đặc biệt cho Hộ chiếu ẩm thực
- ✅ Suppliers này có thể được phân biệt với suppliers thông thường

---

## 🎯 Impact trên Chatbot API

### Service Agent Updates
- ✅ **Culinary Passport Integration**: Service Agent có thể gợi ý suppliers từ Hộ chiếu ẩm thực
- ✅ **Seal Image Display**: Hiển thị seal_image_url cho suppliers đặc biệt
- ✅ **Enhanced Filtering**: Sử dụng supplier_type_slug để lọc chính xác

### Response Examples
```json
{
  "type": "Service",
  "answerAI": "Dưới đây là những nhà hàng trong Hộ chiếu ẩm thực Đà Nẵng:",
  "services": [
    {
      "id": 11,
      "name": "Bông",
      "type": "restaurant",
      "imageUrl": "https://tripc-dev.s3.amazonaws.com/images/...",
      "seal_image_url": "https://tripc-dev.s3.amazonaws.com/images/culinary-passport-seal.png",
      "rating": 0,
      "totalReviews": 0,
      "address": "500 Núi Thành, Hải Châu, Đà Nẵng",
      "city": "Đà Nẵng",
      "productTypes": "Trà sữa",
      "description": "Quán Bông có không gian thoáng mát, rộng rãi."
    }
  ],
  "sources": [
    {
      "title": "Hộ chiếu ẩm thực Đà Nẵng", 
      "url": "https://tripc-api.allyai.ai/api/culinary-passport/suppliers",
      "imageUrl": "https://cdn.tripc.ai/sources/culinary-passport.jpg"
    }
  ]
}
```

---

## 📝 Ghi chú Implementation

### 1. Backend Changes
- ✅ Cập nhật TripC API client để sử dụng endpoints mới
- ✅ Thêm support cho culinary passport suppliers
- ✅ Cập nhật service filtering logic

### 2. Frontend Changes
- ✅ Hiển thị seal_image_url cho suppliers đặc biệt
- ✅ Cập nhật UI để phân biệt suppliers từ Hộ chiếu ẩm thực

### 3. Documentation Updates
- ✅ Cập nhật `api_documentation.md` với endpoints mới
- ✅ Cập nhật `tripc_ai_chatbot_api.md` với integration examples
- ✅ Cập nhật `tripc_ai_chatbot_architecture.md` với flow mới

---

## 🚀 Next Steps

1. **Testing**: Test các endpoints mới với development environment
2. **Integration**: Cập nhật chatbot service để sử dụng API mới
3. **UI Updates**: Cập nhật frontend để hiển thị seal images
4. **Documentation**: Cập nhật user documentation nếu cần

---

## 📞 Contact

- **API Provider**: @Phụng Nguyễn
- **Development Domain**: `https://tripc-api.allyai.ai`
- **Production Domain**: `https://api.tripc.ai`
- **Documentation**: Đã cập nhật trong các file markdown
