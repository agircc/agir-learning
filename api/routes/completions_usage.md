# Enhanced Completions API Usage Guide

This standalone completions API provides intelligent text generation with **enhanced thinking chain** functionality for higher quality responses.

## 🧠 Enhanced Thinking Chain Process

The system now employs a 3-step thinking process for better responses:

1. **Knowledge Analysis**: Identifies what professional knowledge domains are needed
2. **Enhanced Memory Search**: Searches memories using both original prompt and knowledge analysis
3. **Comprehensive Response**: Generates expert-level responses with contextual knowledge

This approach significantly improves response quality and relevance.

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
    "total_tokens": 57,
    "processing_time_ms": 3250.5
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
    "total_tokens": 33,
    "processing_time_ms": 2890.2
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

1. **Enhanced Thinking Chain**: 3-step analysis process for higher quality responses
2. **FAISS Vector Index**: Pre-loads user memories into in-memory FAISS index
3. **Smart Memory Search**: Dual search strategy using prompt + knowledge analysis
4. **Multi-level Caching**: Smart caching for user information and memory retrievers
5. **Performance Monitoring**: Built-in timing metrics for optimization

## ⚡ Performance Characteristics

| Metric | First Request | Subsequent Requests |
|--------|---------------|-------------------|
| Knowledge Analysis | ~500-1000ms | ~300-600ms |
| Memory Loading | ~500ms-2s | Cached (0ms) |
| Enhanced Search | ~20-100ms | ~10-50ms |
| LLM Generation | ~1-5s | ~1-5s |
| **Total Time** | ~2-8s | ~1.5-6s |

## 🧪 Testing and Benchmarking

Run the enhanced testing script:

```bash
cd src/completions
python test_enhanced_completion.py --user-id your-user-id --output results.json
```

This provides detailed quality metrics:
- **Domain Relevance**: How well the response matches expected knowledge areas
- **Response Depth**: Comprehensive coverage of the topic
- **Structured Thinking**: Evidence of logical analysis and reasoning
- **Professional Language**: Use of appropriate terminology and expertise

## 📝 Usage Examples

### cURL Examples
```bash
# Text completion with enhanced thinking
curl -X POST "http://localhost:8000/api/completions/" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "How can I optimize database performance for large datasets?",
  "temperature": 0.7,
  "max_tokens": 200,
  "user_id": "your-user-id"
}'

# Chat completion with professional analysis
curl -X POST "http://localhost:8000/api/completions/chat" \
-H "Content-Type: application/json" \
-d '{
  "messages": [{"role": "user", "content": "What are the best practices for team leadership in remote environments?"}],
  "temperature": 0.5,
  "max_tokens": 200
}'
```

### Python Examples
```python
import requests

# Enhanced completion request
response = requests.post(
    "http://localhost:8000/api/completions/",
    json={
        "prompt": "Explain machine learning algorithms and their practical applications",
        "temperature": 0.7,
        "max_tokens": 200,
        "user_id": "your-user-id"
    }
)
result = response.json()

print("Response:", result["choices"][0]["text"])
print("Processing time:", result["usage"]["processing_time_ms"], "ms")
print("Quality indicators: domain knowledge, structured analysis, practical examples")
```

### JavaScript/Node.js Examples
```javascript
// Enhanced completion with quality monitoring
const response = await fetch('http://localhost:8000/api/completions/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'What strategies work best for customer retention in SaaS businesses?',
    temperature: 0.7,
    max_tokens: 200,
    user_id: 'your-user-id'
  })
});

const result = await response.json();
console.log('Enhanced response:', result.choices[0].text);
console.log('Performance:', result.usage.processing_time_ms + 'ms');
```

## ⚙️ Parameter Description

- **prompt/messages**: Input text or conversation messages
- **model**: Model name (default: "agir-learner")  
- **temperature**: Generation temperature 0.0-2.0 (default: 0.7)
- **max_tokens**: Maximum number of tokens to generate (default: 150)
- **user_id**: User ID for personalized responses (optional)

## 🔧 Advanced Configuration

### Enhanced Context Processing
When providing a `user_id`, the system will:
1. **Analyze knowledge requirements** for the specific prompt
2. **Load user's personal memories** from the database
3. **Create FAISS vector index** for fast similarity search
4. **Search using dual strategy**: prompt + knowledge analysis
5. **Generate expert-level response** with comprehensive context

### Quality Optimization Tips
- **Use descriptive prompts**: More context leads to better knowledge analysis
- **Provide user_id**: Enables personalized memory-based responses
- **Set appropriate max_tokens**: 150-300 for comprehensive responses
- **Use moderate temperature**: 0.5-0.7 for balanced creativity and accuracy

### Performance Tuning
- **First Request**: Slower (builds knowledge analysis + FAISS index)
- **Subsequent Requests**: Faster (uses cached analysis patterns)
- **Memory Usage**: Scales with number of unique users and their memory count
- **Cache Limits**: 50 memory retrievers, 100 user records by default

### Response Quality Indicators
High-quality responses will include:
- **Domain-specific terminology** and concepts
- **Structured thinking** with logical flow
- **Practical examples** and actionable insights
- **Professional expertise** demonstration
- **Comprehensive coverage** of the topic

### Error Handling
The API provides detailed error messages for:
- Invalid user IDs
- Missing LLM model configurations
- Memory loading failures
- Knowledge analysis timeout
- Service initialization errors 