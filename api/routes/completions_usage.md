# Completions API Usage Guide

This standalone completions API provides fast text generation functionality based on FAISS with OpenAI API compatibility.

## 📚 API Endpoints

### 1. Text Completion
```
POST /api/completions/
```

**Request Body:**
```json
{
  "prompt": "Explain the concept of machine learning",
  "model": "agir-learner",
  "max_tokens": 150,
  "temperature": 0.7,
  "user_id": "your-user-id"
}
```

**Response:**
```json
{
  "id": "cmpl-abc123...",
  "object": "text_completion",
  "created": 1677652288,
  "model": "agir-learner",
  "choices": [
    {
      "text": "Machine learning is a branch of artificial intelligence...",
      "index": 0,
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 45,
    "total_tokens": 57
  }
}
```

### 2. Chat Completion
```
POST /api/completions/chat
```

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello, please introduce yourself"}
  ],
  "model": "agir-learner",
  "max_tokens": 150,
  "temperature": 0.7,
  "user_id": "your-user-id"
}
```

**Response:**
```json
{
  "id": "chatcmpl-xyz789...",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "agir-learner",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I am an AGIR learning assistant..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 25,
    "total_tokens": 33
  }
}
```

### 3. Cache Management

#### Clear Cache
```
POST /api/completions/cache/clear
```

**Response:**
```json
{
  "message": "Completion memory cache cleared successfully",
  "timestamp": 1677652288
}
```

#### Get Cache Statistics
```
GET /api/completions/cache/stats
```

**Response:**
```json
{
  "retriever_cache_size": 5,
  "user_cache_size": 10,
  "retriever_cache_keys": ["user1:model1", "user2:model1"],
  "timestamp": 1677652288
}
```

#### Health Check
```
GET /api/completions/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "completions",
  "timestamp": 1677652288
}
```

## 🚀 Performance Advantages

1. **FAISS Vector Index**: Pre-loads user memories into in-memory FAISS index
2. **Multi-level Caching**: Smart caching for user information and memory retrievers
3. **No Conversation History**: Focuses on single completions, reducing memory usage
4. **Fast Response**: 2-5x speed improvement for subsequent requests

## 📝 Usage Examples

### cURL Examples
```bash
# Text completion
curl -X POST "http://localhost:8000/api/completions/" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "Explain machine learning",
  "temperature": 0.7,
  "max_tokens": 150,
  "user_id": "your-user-id"
}'

# Chat completion
curl -X POST "http://localhost:8000/api/completions/chat" \
-H "Content-Type: application/json" \
-d '{
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.5,
  "max_tokens": 100
}'

# Check cache status
curl "http://localhost:8000/api/completions/cache/stats"
```

### Python Examples
```python
import requests

# Text completion
response = requests.post(
    "http://localhost:8000/api/completions/",
    json={
        "prompt": "Explain machine learning",
        "temperature": 0.7,
        "max_tokens": 150,
        "user_id": "your-user-id"
    }
)
print(response.json())

# Chat completion
response = requests.post(
    "http://localhost:8000/api/completions/chat",
    json={
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.5,
        "max_tokens": 100,
        "user_id": "your-user-id"
    }
)
print(response.json())
```

### JavaScript/Node.js Examples
```javascript
// Text completion
const response = await fetch('http://localhost:8000/api/completions/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'Explain machine learning',
    temperature: 0.7,
    max_tokens: 150,
    user_id: 'your-user-id'
  })
});

const result = await response.json();
console.log(result);
```

## ⚙️ Parameter Description

- **prompt/messages**: Input text or conversation messages
- **model**: Model name (default: "agir-learner")
- **temperature**: Generation temperature 0.0-2.0 (default: 0.7)
- **max_tokens**: Maximum number of tokens to generate (default: 150)
- **user_id**: User ID for personalized responses (optional)

## 🔧 Advanced Configuration

### Custom User Context
When providing a `user_id`, the system will:
1. Load the user's personal memories from the database
2. Create a FAISS vector index for fast similarity search
3. Use relevant memories to provide contextual responses

### Performance Tuning
- **First Request**: Slower (builds FAISS index)
- **Subsequent Requests**: Much faster (uses cached index)
- **Memory Usage**: Scales with number of unique users and their memory count
- **Cache Limits**: 50 memory retrievers, 100 user records by default

### Error Handling
The API provides detailed error messages for:
- Invalid user IDs
- Missing LLM model configurations
- Memory loading failures
- Service initialization errors 