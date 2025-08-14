# 🔍 Keyword Analyzer Implementation

## 📋 Tổng quan

Đã implement thành công hệ thống phân tích từ khóa thông minh sử dụng LLM để cải thiện việc tìm kiếm nhà hàng trong TripC.AI Chatbot API.

## 🎯 Tính năng chính

### 1. **Phân tích từ khóa thông minh**
- Sử dụng LLM để trích xuất từ khóa từ câu hỏi người dùng
- Phân loại từ khóa theo 3 cấp độ:
  - **Danh từ riêng**: Tên địa điểm, tên món ăn cụ thể
  - **Tính từ**: Mô tả đặc điểm, phong cách, cảm giác
  - **Danh từ chung**: Loại món ăn, loại nhà hàng

### 2. **Tìm kiếm product_type_id phù hợp**
- Lấy tất cả product types từ API: `https://api.tripc.ai/api/services/product-type/all`
- Sử dụng LLM để match từ khóa với product_type_id
- Cache product types để tối ưu hiệu suất

### 3. **Tìm kiếm nhà hàng thông minh**
- Sử dụng product_type_id và province_id (4, 47 cho Đà Nẵng)
- Chỉ tìm kiếm với product_type_id, không có fallback
- API endpoint: `https://api.tripc.ai/api/services/restaurants?product_type_id=22&page=1&page_size=15`

## 🏗️ Kiến trúc

### Files đã tạo/cập nhật:

1. **`src/app/services/keyword_analyzer.py`** - Service chính
2. **`src/app/services/__init__.py`** - Import KeywordAnalyzer
3. **`src/app/main.py`** - Thêm endpoints mới
4. **`test_keyword_analyzer.py`** - Test script
5. **`demo_keyword_analyzer.py`** - Demo script
6. **`README.md`** - Cập nhật documentation

### API Endpoints mới:

1. **`POST /api/v1/keywords/analyze`**
   - Phân tích từ khóa từ câu hỏi người dùng
   - Trả về keywords và product_type_ids phù hợp

2. **`POST /api/v1/restaurants/search-with-analysis`**
   - Tìm kiếm nhà hàng với phân tích từ khóa
   - Kết hợp product_type_id và province_id

## 🔄 Workflow

```
1. User Query → 2. LLM Keyword Analysis → 3. Product Type Matching → 4. Restaurant Search
```

### Chi tiết từng bước:

1. **User Query**: Người dùng nhập câu hỏi
2. **LLM Keyword Analysis**: 
   - Phân tích từ khóa theo 3 cấp độ
   - Trích xuất thông tin quan trọng
3. **Product Type Matching**:
   - Lấy tất cả product types từ API
   - Sử dụng LLM để tìm product_type_id phù hợp
4. **Restaurant Search**:
   - Tìm kiếm với product_type_id và province_id
   - Không có fallback, chỉ dựa vào product_type_id

## 🧪 Testing

### Chạy test:
```bash
python test_keyword_analyzer.py
```

### Chạy demo:
```bash
python demo_keyword_analyzer.py
```

### Test cases:
- "Tôi muốn tìm nhà hàng hải sản ở Đà Nẵng"
- "Có nhà hàng buffet nào ngon không?"
- "Tìm quán cà phê view đẹp"
- "Nhà hàng chay ở đâu?"
- "Quán ăn vặt đường phố"

## 📊 Kết quả mong đợi

### Keyword Analysis:
```json
{
  "keywords": {
    "proper_nouns": ["Đà Nẵng"],
    "adjectives": [],
    "common_nouns": ["nhà hàng", "hải sản"]
  },
  "matching_product_type_ids": [22, 15],
  "province_ids": [4, 47]
}
```

### Restaurant Search:
- Tìm kiếm chính xác hơn với product_type_id
- Kết quả phù hợp với ý định người dùng
- Chỉ sử dụng product_type_id, không có fallback

## 🚀 Lợi ích

1. **Tìm kiếm chính xác hơn**: Sử dụng product_type_id thay vì chỉ keyword
2. **Hiểu ý định người dùng**: Phân tích từ khóa thông minh
3. **Tối ưu hiệu suất**: Cache product types
4. **Kết quả chất lượng cao**: Chỉ trả về kết quả phù hợp với product_type_id
5. **Mở rộng dễ dàng**: Có thể thêm các loại phân tích khác

## 🔧 Cấu hình

### Environment Variables:
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
TRIPC_API_BASE_URL=https://api.tripc.ai
TRIPC_API_TOKEN=your_tripc_token
```

### Province IDs cho Đà Nẵng:
- `4`: Đà Nẵng (cũ)
- `47`: Đà Nẵng (mới)

## 📈 Performance

- **Cache product types**: Chỉ load một lần khi khởi tạo
- **Async operations**: Sử dụng async/await cho API calls
- **Error handling**: Graceful error handling khi có lỗi
- **Logging**: Detailed logging cho debugging

## 🔮 Tương lai

1. **Thêm sentiment analysis**: Phân tích cảm xúc người dùng
2. **Context awareness**: Nhớ context của cuộc hội thoại
3. **Multi-language support**: Hỗ trợ nhiều ngôn ngữ
4. **Personalization**: Học sở thích người dùng
5. **A/B testing**: So sánh hiệu quả với phương pháp cũ
