"""
Token estimation utilities for manual token tracking when Azure usage is unavailable.
Uses tiktoken for accurate GPT-style token counting.
"""

import tiktoken
from typing import List, Dict, Any, Union


class TokenEstimator:
    """Handles token counting for messages and text content"""
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        Initialize tokenizer with model-specific encoding
        
        Args:
            model_name: Model name for encoding selection
        """
        try:
            # Try to get encoding for specific model
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base encoding (used by GPT-4, GPT-3.5-turbo)
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        self.model_name = model_name
        print(f"🔤 TokenEstimator initialized with encoding for {model_name}")
    
    def count_text_tokens(self, text: str) -> int:
        """
        Count tokens in a text string
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not text or not isinstance(text, str):
            return 0
        
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            print(f"⚠️ Error counting tokens for text: {e}")
            # Fallback: rough estimation (4 chars per token)
            return len(text) // 4
    
    def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """
        Count tokens for a single message
        
        Args:
            message: Message dict with 'role' and 'content'
            
        Returns:
            Number of tokens including role overhead
        """
        if not message:
            return 0
        
        role = message.get('role', '')
        content = message.get('content', '')
        
        # Handle content that might be a list (for image messages)
        if isinstance(content, list):
            text_content = ""
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_content += item.get('text', '')
                # Note: We're not counting image tokens here - would need separate handling
        else:
            text_content = str(content) if content else ""
        
        # Count tokens for content
        content_tokens = self.count_text_tokens(text_content)
        
        # Add overhead for message structure and role
        # Based on OpenAI's token counting guide:
        # Each message has overhead: <|start|>{role}<|separator|>{content}<|end|>
        role_tokens = self.count_text_tokens(role)
        message_overhead = 4  # Rough estimate for message formatting tokens
        
        total_tokens = content_tokens + role_tokens + message_overhead
        
        return total_tokens
    
    def count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Count tokens for a list of messages
        
        Args:
            messages: List of message dicts
            
        Returns:
            Total number of tokens for all messages
        """
        if not messages:
            return 0
        
        total_tokens = 0
        
        for message in messages:
            total_tokens += self.count_message_tokens(message)
        
        # Add overhead for conversation structure
        conversation_overhead = 2  # Rough estimate for conversation formatting
        
        return total_tokens + conversation_overhead
    
    def estimate_completion_tokens(self, response_text: str) -> int:
        """
        Estimate tokens in assistant response
        
        Args:
            response_text: The assistant's response text
            
        Returns:
            Estimated number of completion tokens
        """
        return self.count_text_tokens(response_text)


# Global tokenizer instance - can be reused across the application
_global_tokenizer = None


def get_tokenizer(model_name: str = "gpt-4") -> TokenEstimator:
    """
    Get or create a global tokenizer instance
    
    Args:
        model_name: Model name for encoding selection
        
    Returns:
        TokenEstimator instance
    """
    global _global_tokenizer
    
    if _global_tokenizer is None or _global_tokenizer.model_name != model_name:
        _global_tokenizer = TokenEstimator(model_name)
    
    return _global_tokenizer


def count_message_tokens(message: Dict[str, Any], model_name: str = "gpt-4") -> int:
    """
    Convenience function to count tokens in a single message
    
    Args:
        message: Message dict with 'role' and 'content'
        model_name: Model name for encoding selection
        
    Returns:
        Number of tokens
    """
    tokenizer = get_tokenizer(model_name)
    return tokenizer.count_message_tokens(message)


def count_messages_tokens(messages: List[Dict[str, Any]], model_name: str = "gpt-4") -> int:
    """
    Convenience function to count tokens in multiple messages
    
    Args:
        messages: List of message dicts
        model_name: Model name for encoding selection
        
    Returns:
        Total number of tokens
    """
    tokenizer = get_tokenizer(model_name)
    return tokenizer.count_messages_tokens(messages)


if __name__ == "__main__":
    # Test the tokenizer
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you for asking! How can I help you today?"}
    ]
    
    tokenizer = TokenEstimator()
    
    for i, msg in enumerate(test_messages):
        tokens = tokenizer.count_message_tokens(msg)
        print(f"Message {i+1} ({msg['role']}): {tokens} tokens")
    
    total_tokens = tokenizer.count_messages_tokens(test_messages)
    print(f"Total conversation: {total_tokens} tokens")