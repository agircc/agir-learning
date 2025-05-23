from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
import time

from src.completions.fast_completion import create_fast_completion
from src.chat.chat_with_learner import create_chat_session

router = APIRouter()

# Pydantic models for completion requests
class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = "agir-learner"
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7
    user_id: Optional[str] = None  # Optional user ID for personalized responses

class CompletionRequest(BaseModel):
    prompt: str
    model: Optional[str] = "agir-learner"
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7
    user_id: Optional[str] = None

@router.post("/", include_in_schema=True)
@router.post("", include_in_schema=False)  # Add support for path without slash
async def create_completion(request: CompletionRequest):
    """Create a text completion (similar to OpenAI's completions API)"""
    try:
        # Use a default user ID if none provided
        user_id = request.user_id or "00000000-0000-0000-0000-000000000000"
        
        # Track timing for performance monitoring
        start_time = time.time()
        
        # Use fast completion for better performance
        fast_completion = create_fast_completion(
            user_id=user_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not fast_completion:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize completion service"
            )
        
        # Generate completion with enhanced thinking process
        ai_response = fast_completion.complete(request.prompt)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Generate a unique completion ID
        completion_id = f"cmpl-{uuid.uuid4().hex[:20]}"
        
        # Return OpenAI-like response format with performance info
        response_data = {
            "id": completion_id,
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "text": ai_response,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": len(request.prompt.split()) + len(ai_response.split()),
                "processing_time_ms": round(processing_time * 1000, 2)
            }
        }
        
        return response_data
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating completion: {str(e)}"
        )

@router.post("/chat")
@router.post("/chat/", include_in_schema=False)  # Add support for path with slash
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (similar to OpenAI's chat completions API)"""
    try:
        # Use a default user ID if none provided
        user_id = request.user_id or "00000000-0000-0000-0000-000000000000"
        
        # Track timing for performance monitoring
        start_time = time.time()
        
        # Get the last user message
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in the conversation"
            )
        
        last_user_message = user_messages[-1].content
        
        # Use fast completion for better performance
        fast_completion = create_fast_completion(
            user_id=user_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not fast_completion:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize completion service"
            )
        
        # Generate completion with enhanced thinking process
        ai_response = fast_completion.complete(last_user_message)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Generate a unique completion ID
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:20]}"
        
        # Return OpenAI-like response format with performance info
        response_data = {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ai_response
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(ai_response.split()),
                "processing_time_ms": round(processing_time * 1000, 2)
            }
        }
        
        return response_data
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating chat completion: {str(e)}"
        )

@router.post("/simple")
@router.post("/simple/", include_in_schema=False)  # Add support for path with slash
async def create_simple_completion(request: CompletionRequest):
    """Create a simple text completion without CoT (Chain of Thought) analysis"""
    try:
        # Use a default user ID if none provided
        user_id = request.user_id or "00000000-0000-0000-0000-000000000000"
        
        # Track timing for performance monitoring
        start_time = time.time()
        
        # Use LearnerChatSession for simple completion
        chat_session = create_chat_session(
            user_id=user_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize chat session"
            )
        
        try:
            # Generate simple completion using chat method
            ai_response = chat_session.chat(request.prompt)
        finally:
            # Always close the session
            chat_session.close()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Generate a unique completion ID
        completion_id = f"cmpl-simple-{uuid.uuid4().hex[:20]}"
        
        # Return OpenAI-like response format with performance info
        response_data = {
            "id": completion_id,
            "object": "text_completion",
            "created": int(time.time()),
            "model": f"{request.model}-simple",
            "choices": [
                {
                    "text": ai_response,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": len(request.prompt.split()) + len(ai_response.split()),
                "processing_time_ms": round(processing_time * 1000, 2),
                "mode": "simple"
            }
        }
        
        return response_data
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating simple completion: {str(e)}"
        )

@router.post("/chat/simple")
@router.post("/chat/simple/", include_in_schema=False)  # Add support for path with slash
async def create_simple_chat_completion(request: ChatCompletionRequest):
    """Create a simple chat completion without CoT (Chain of Thought) analysis"""
    try:
        # Use a default user ID if none provided
        user_id = request.user_id or "00000000-0000-0000-0000-000000000000"
        
        # Track timing for performance monitoring
        start_time = time.time()
        
        # Get the last user message
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in the conversation"
            )
        
        last_user_message = user_messages[-1].content
        
        # Use LearnerChatSession for simple completion
        chat_session = create_chat_session(
            user_id=user_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize chat session"
            )
        
        try:
            # Generate simple completion using chat method
            ai_response = chat_session.chat(last_user_message)
        finally:
            # Always close the session
            chat_session.close()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Generate a unique completion ID
        completion_id = f"chatcmpl-simple-{uuid.uuid4().hex[:20]}"
        
        # Return OpenAI-like response format with performance info
        response_data = {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": f"{request.model}-simple",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ai_response
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(ai_response.split()),
                "processing_time_ms": round(processing_time * 1000, 2),
                "mode": "simple"
            }
        }
        
        return response_data
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating simple chat completion: {str(e)}"
        )

@router.post("/cache/clear")
async def clear_completion_cache():
    """Clear the completion memory cache"""
    try:
        from src.completions.fast_memory_retriever import clear_memory_cache
        clear_memory_cache()
        
        return {
            "message": "Completion memory cache cleared successfully",
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}"
        )

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        from src.completions.fast_memory_retriever import _retriever_cache
        from src.completions.fast_completion import _user_cache
        
        retriever_cache_size = len(_retriever_cache)
        user_cache_size = len(_user_cache)
        
        return {
            "retriever_cache_size": retriever_cache_size,
            "user_cache_size": user_cache_size,
            "retriever_cache_keys": list(_retriever_cache.keys()),
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache stats: {str(e)}"
        )

@router.get("/health")
async def completion_health_check():
    """Health check for completion service"""
    try:
        return {
            "status": "healthy",
            "service": "completions",
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        ) 