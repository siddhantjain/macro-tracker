# Photo-Based Food Logging - Setup & Testing Guide

## ✅ Implementation Complete

The photo-based food logging feature is now implemented in macro-tracker!

### Components Implemented

1. **Vision Analyzer** (`src/vision_analyzer.py`)
   - Parses vision model responses into structured food items
   - Queue-based system for Neo to process vision requests
   - Handles timeouts and errors gracefully

2. **Nutrition Lookup** (`src/nutrition_lookup.py`)
   - USDA API integration for nutrition data
   - Web search fallback (optional, requires `requests`)
   - Unit conversion (grams, ounces, cups, etc.)
   - Confidence scoring

3. **API Endpoint** (`src/server.py`)
   - `POST /api/food/analyze` accepts multipart/form-data
   - Handles image uploads
   - Orchestrates vision → nutrition → response flow
   - CORS support for iOS app

4. **Vision Queue Processor** (`scripts/process_vision_queue.py`)
   - Monitors `data/vision_queue/` for new requests
   - Neo uses image tool to analyze photos
   - Writes responses for API to consume

## 🚀 Usage

### Start the Server

```bash
cd ~/clawd/macro-tracker
python3 -m src.server
# Server running on http://0.0.0.0:4001
```

### Process Vision Requests (Neo handles this automatically)

When a photo is uploaded to `/api/food/analyze`:
1. Image saved to temp file
2. Vision request written to `data/vision_queue/request_{uuid}.json`
3. Neo monitors the queue and processes with image tool
4. Response written to `data/vision_queue/response_{uuid}.json`
5. API reads response, looks up nutrition, returns JSON

### Test with curl

```bash
# With a real food photo
curl -X POST http://localhost:4001/api/food/analyze \
  -F "image=@path/to/food_photo.jpg" \
  | python3 -m json.tool
```

### Expected Response Format

```json
{
  "items": [
    {
      "name": "scrambled eggs",
      "quantity": 2,
      "unit": "eggs",
      "quantity_g": 100,
      "calories": 140,
      "protein_g": 12,
      "carbs_g": 2,
      "fat_g": 10,
      "source": "usda",
      "confidence": "high",
      "usda_fdc_id": 123456
    }
  ],
  "total": {
    "calories": 140,
    "protein_g": 12,
    "carbs_g": 2,
    "fat_g": 12
  },
  "raw_vision_response": "1. Scrambled eggs: 2 eggs"
}
```

## 🧪 Testing

### Unit Tests

```bash
# Test vision parser
python3 tests/test_vision_parser_simple.py

# Test API flow (mock)
python3 tests/test_api_endpoint.py
```

### Integration Test with Real Photo

1. **Find a food photo** (or take one with your phone)
2. **Start server:** `python3 -m src.server`
3. **Send request:**
   ```bash
   curl -X POST http://localhost:4001/api/food/analyze \
     -F "image=@my_meal.jpg"
   ```
4. **Neo will process the vision queue** when request comes in
5. **Response returned** with food items + nutrition

## 📱 iOS App Integration

### Swift Example

```swift
func analyzeFoodPhoto(image: UIImage) async throws -> FoodAnalysisResponse {
    let url = URL(string: "http://mac-mini:4001/api/food/analyze")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    // Create multipart form data
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", 
                     forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    let imageData = image.jpegData(compressionQuality: 0.8)!
    
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
    body.append(imageData)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(FoodAnalysisResponse.self, from: data)
}
```

### Models

```swift
struct FoodAnalysisResponse: Codable {
    let items: [FoodItem]
    let total: NutritionTotal
}

struct FoodItem: Codable {
    let name: String
    let quantity: Double
    let unit: String
    let quantity_g: Double
    let calories: Double
    let protein_g: Double
    let carbs_g: Double
    let fat_g: Double
    let source: String
    let confidence: String
}

struct NutritionTotal: Codable {
    let calories: Double
    let protein_g: Double
    let carbs_g: Double
    let fat_g: Double
}
```

## 🔍 How Neo Processes Vision Requests

When Neo monitors the vision queue, it:

1. **Detects new request file:** `data/vision_queue/request_{uuid}.json`
2. **Reads request:**
   ```json
   {
     "request_id": "abc123",
     "image_path": "/tmp/food_photo.jpg",
     "prompt": "Identify all food items...",
     "timestamp": "2026-02-08T10:00:00"
   }
   ```
3. **Uses image tool:** Analyzes image with the prompt
4. **Writes response:**
   ```json
   {
     "request_id": "abc123",
     "response": "1. Scrambled eggs: 2 eggs\n2. Toast: 2 slices",
     "timestamp": "2026-02-08T10:00:05"
   }
   ```
5. **API reads response:** Parses food items and looks up nutrition

## 📊 Architecture Diagram

```
┌─────────────┐
│  iOS App    │ (Take photo)
└──────┬──────┘
       │ POST /api/food/analyze
       ▼
┌─────────────────────────────┐
│  macro-tracker HTTP Server  │
│  (src/server.py)            │
└──────┬─────────────┬────────┘
       │             │
       ▼             │
┌─────────────┐     │
│  Save temp  │     │
│  image      │     │
└──────┬──────┘     │
       │             │
       ▼             │
┌─────────────────────────────┐
│  Vision Analyzer            │
│  Write request to queue     │
│  data/vision_queue/req.json │
└──────┬──────────────────────┘
       │
       │ (Neo monitors queue)
       ▼
┌─────────────────────────────┐
│  Neo (OpenClaw Agent)       │
│  - Detects request          │
│  - Uses image tool          │
│  - Writes response          │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Vision Analyzer            │
│  Read response from queue   │
│  Parse food items           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Nutrition Lookup           │
│  - Query USDA API           │
│  - Fallback to web search   │
│  - Scale to quantities      │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Return JSON Response       │
│  - items[]                  │
│  - total{}                  │
└─────────────────────────────┘
```

## 🎯 Success Criteria

- ✅ POST /api/food/analyze endpoint implemented
- ✅ Accepts multipart/form-data image uploads
- ✅ Vision analysis integration (queue-based)
- ✅ Nutrition lookup (USDA + web fallback)
- ✅ Returns structured JSON response
- ✅ Documentation complete
- ✅ Unit tests passing
- ⏳ Integration test with real food photo (requires Neo monitoring)

## 🐛 Known Issues & Future Improvements

1. **Vision Queue Polling:** Currently uses file-based queue with polling. Could improve with:
   - WebSocket for real-time push
   - Redis/message queue for production
   - Direct OpenClaw API integration

2. **Unit Conversion:** Some uncommon units may not convert accurately. Can improve:
   - Expand USDA portion mapping
   - Add more fallback conversions
   - Learn user's typical portion sizes

3. **Indian Food Support:** USDA database has limited Indian foods. Can improve:
   - Add custom Indian food database
   - Better web search patterns for Indian dishes
   - Manual nutrition entry option

4. **Error Handling:** Can improve:
   - Retry logic for failed vision requests
   - Better error messages for users
   - Partial results if some items fail

## 📚 References

- [Feature Design Doc](~/clawd/neo-ios-app/wiki/FEATURE_PHOTO_FOOD_LOGGING.md)
- [README API Documentation](README.md#-photo-based-food-logging)
- [USDA FoodData Central API](https://fdc.nal.usda.gov/)
- [Serper API (web search)](https://serper.dev/)
