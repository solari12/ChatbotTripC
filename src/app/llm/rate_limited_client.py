#!/usr/bin/env python3
"""
Rate-limited LLM client to prevent API limits and ensure service stability
"""

import asyncio
import time
from typing import Optional, Dict, Any
from collections import deque
import logging
from .open_client import OpenAIClient

logger = logging.getLogger(__name__)


class RateLimitedLLMClient:
    """Rate-limited wrapper around LLM client"""
    
    def __init__(self, llm_client: OpenAIClient, max_calls_per_minute: int = 60, max_calls_per_second: int = 10):
        self.llm_client = llm_client
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_second = max_calls_per_second
        
        # Track call times
        self.call_times = deque()
        self.last_call_time = 0
        
        # Cache for repeated requests
        self.response_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info(f"RateLimitedLLMClient initialized: {max_calls_per_minute}/min, {max_calls_per_second}/sec")
    
    async def generate_response(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate response with rate limiting"""
        try:
            # Check rate limits
            await self._check_rate_limits()
            
            # Check cache first
            cache_key = self._get_cache_key(prompt, kwargs)
            if cache_key in self.response_cache:
                cached_response, timestamp = self.response_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug("Returning cached LLM response")
                    return cached_response
                else:
                    # Remove expired cache entry
                    del self.response_cache[cache_key]
            
            # Make actual API call
            response = await self._make_api_call(prompt, **kwargs)
            
            # Cache successful response
            if response:
                self.response_cache[cache_key] = (response, time.time())
                # Limit cache size
                if len(self.response_cache) > 100:
                    # Remove oldest entry
                    oldest_key = next(iter(self.response_cache))
                    del self.response_cache[oldest_key]
            
            return response
            
        except Exception as e:
            logger.error(f"Error in rate-limited LLM call: {e}")
            return None
    
    def generate_response_sync(self, prompt: str, **kwargs) -> Optional[str]:
        """Sync version of generate_response for compatibility"""
        import asyncio
        try:
            # Run async version in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, just call the sync version directly
                return self._generate_response_sync(prompt, **kwargs)
            else:
                return loop.run_until_complete(self.generate_response(prompt, **kwargs))
        except RuntimeError:
            # No event loop, use sync version
            return self._generate_response_sync(prompt, **kwargs)
    
    def _generate_response_sync(self, prompt: str, **kwargs) -> Optional[str]:
        """Sync version that bypasses rate limiting for compatibility"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(prompt, kwargs)
            if cache_key in self.response_cache:
                cached_response, timestamp = self.response_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug("Returning cached LLM response")
                    return cached_response
                else:
                    # Remove expired cache entry
                    del self.response_cache[cache_key]
            
            # Make actual API call without rate limiting for sync calls
            response = self.llm_client.generate_response(prompt, **kwargs)
            
            # Cache successful response
            if response:
                self.response_cache[cache_key] = (response, time.time())
                # Limit cache size
                if len(self.response_cache) > 100:
                    # Remove oldest entry
                    oldest_key = next(iter(self.response_cache))
                    del self.response_cache[oldest_key]
            
            return response
            
        except Exception as e:
            logger.error(f"Error in sync LLM call: {e}")
            return None
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Remove old call times (older than 1 minute)
        while self.call_times and current_time - self.call_times[0] > 60:
            self.call_times.popleft()
        
        # Check per-minute limit
        if len(self.call_times) >= self.max_calls_per_minute:
            wait_time = 60 - (current_time - self.call_times[0])
            if wait_time > 0:
                logger.warning(f"Rate limit exceeded. Waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Check per-second limit
        if current_time - self.last_call_time < 1.0 / self.max_calls_per_second:
            wait_time = 1.0 / self.max_calls_per_second - (current_time - self.last_call_time)
            if wait_time > 0:
                logger.debug(f"Per-second rate limit. Waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
    
    async def _make_api_call(self, prompt: str, **kwargs) -> Optional[str]:
        """Make actual API call and track timing"""
        current_time = time.time()
        
        try:
            # Make the actual call - handle both sync and async
            if hasattr(self.llm_client, 'generate_response'):
                response = self.llm_client.generate_response(prompt, **kwargs)
            else:
                response = None
            
            # Track call time
            self.call_times.append(current_time)
            self.last_call_time = current_time
            
            logger.debug(f"LLM API call completed in {time.time() - current_time:.3f}s")
            return response
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            # Still track the attempt to prevent overwhelming the API
            self.call_times.append(current_time)
            self.last_call_time = current_time
            return None
    
    def _get_cache_key(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """Generate cache key for prompt and parameters"""
        # Create a hash of prompt and relevant kwargs
        import hashlib
        key_data = f"{prompt}:{kwargs.get('model', '')}:{kwargs.get('max_tokens', '')}:{kwargs.get('temperature', '')}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        current_time = time.time()
        
        # Clean old call times
        while self.call_times and current_time - self.call_times[0] > 60:
            self.call_times.popleft()
        
        return {
            "calls_last_minute": len(self.call_times),
            "max_calls_per_minute": self.max_calls_per_minute,
            "max_calls_per_second": self.max_calls_per_second,
            "cache_size": len(self.response_cache),
            "last_call_time": self.last_call_time,
            "time_since_last_call": current_time - self.last_call_time if self.last_call_time else None
        }
    
    def is_configured(self) -> bool:
        """Check if underlying LLM client is configured"""
        return self.llm_client.is_configured()
