"""
Baseline chatbot without tools or reasoning loop.
Used to demonstrate limitations of standard LLM for structured queries.
"""

from typing import Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
import time


class BaselineChatbot:
    """Simple chatbot that uses LLM directly without tools or reasoning loop.
    
    This baseline demonstrates the limitations of a standard LLM:
    - No access to actual student data
    - Will hallucinate when asked about specific student points
    - Cannot correct itself or access data to verify claims
    - Single-shot response, no multi-step reasoning
    """
    
    SYSTEM_PROMPT = """You are a helpful educational assistant. 
Answer questions about students and their academic performance based on your knowledge.
Be helpful and provide specific information when asked."""
    
    def __init__(self, llm_provider: LLMProvider):
        """Initialize baseline chatbot with an LLM provider.
        
        Args:
            llm_provider: An LLMProvider instance (OpenAI, Gemini, or Local)
        """
        self.llm = llm_provider
        self.conversation_history = []
    
    def answer(self, user_input: str) -> str:
        """Generate a response to user input using only the LLM.
        
        No tools, no data validation, pure language model output.
        This allows hallucinations to occur naturally.
        
        Args:
            user_input: The user's question
        
        Returns:
            The LLM's response
        """
        # Log baseline request start
        logger.log_event("BASELINE_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "provider": self.llm.__class__.__name__
        })
        
        start_time = time.time()
        
        # Build conversation prompt
        messages = self.conversation_history + [user_input]
        conversation_text = "\n".join(messages)
        
        try:
            # Single LLM call - no tool use, no verification
            response = self.llm.generate(
                prompt=conversation_text,
                system_prompt=self.SYSTEM_PROMPT
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            answer_text = response.get("content", "")
            
            # Track metrics
            usage = response.get("usage", {})
            tracker.track_request(
                provider=response.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=usage,
                latency_ms=latency_ms
            )
            
            # Update conversation history
            self.conversation_history.append(user_input)
            self.conversation_history.append(answer_text)
            
            # Log the response
            logger.log_event("BASELINE_RESPONSE", {
                "input": user_input,
                "response": answer_text,
                "model": self.llm.model_name,
                "provider": response.get("provider"),
                "tokens_prompt": usage.get("prompt_tokens"),
                "tokens_completion": usage.get("completion_tokens"),
                "latency_ms": latency_ms,
                "success": True
            })
            
            return answer_text
        
        except Exception as e:
            # Log error
            latency_ms = int((time.time() - start_time) * 1000)
            logger.log_event("BASELINE_RESPONSE", {
                "input": user_input,
                "response": None,
                "model": self.llm.model_name,
                "provider": self.llm.__class__.__name__,
                "error": str(e),
                "latency_ms": latency_ms,
                "success": False
            })
            
            return f"Error generating response: {str(e)}"
    
    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
