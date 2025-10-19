"""
AWS Bedrock-Only AI Client Pool Service
Pure AWS implementation with no fallback services
Optimized for AWS Bedrock Claude models
"""

import asyncio
import time
import json
import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import threading

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AsyncAIClientPool:
    """
    AWS Bedrock-Only AI Client Pool
    Pure AWS implementation with no fallback services - optimized for Bedrock Claude models
    """
    
    def __init__(self, pool_size: int = 10, timeout: float = 60.0, max_concurrent: int = 8):
        self.pool_size = pool_size
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.total_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        self.lock = asyncio.Lock()
        
        # Context7 optimization: Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Performance tracking (Context7 best practice)
        self.performance_metrics = {
            'ttft_times': [],
            'total_times': [],
            'token_rates': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # AWS Bedrock Configuration - PURE AWS ONLY
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock_client = None
        
        # Bedrock Model Configuration - Read from environment variables
        self.primary_model = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.fast_model = os.getenv("BEDROCK_CLAUDE_FAST_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")  # Fast model for simple queries
        
        # Model mapping for compatibility - Use environment variables
        self.model_mapping = {
            "gpt-4": self.primary_model,
            "gpt-4-turbo": self.primary_model, 
            "gpt-3.5-turbo": self.fast_model,
            "gpt-4o": self.primary_model,
            "gpt-4o-mini": self.fast_model,
            "claude-3-sonnet": self.primary_model,
            "claude-3-haiku": self.fast_model
        }
        
        # AWS Bedrock Statistics
        self.bedrock_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "model_usage": {},
            "average_response_time": 0.0
        }
        
        self._initialized = False
        logger.info(f"🤖 AWS Bedrok-Only AI Client Pool initialized - Region: {self.aws_region}")
    
    async def initialize(self):
        """Initialize the AWS Bedrock client"""
        if self._initialized:
            return
        
        try:
            # Initialize AWS Bedrock client
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.aws_region
            )
            
            # Test connection
            await self._test_bedrock_connection()
            
            self._initialized = True
            logger.info("✅ AWS Bedrock client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS Bedrock client: {e}")
            raise RuntimeError(f"AWS Bedrock initialization failed: {e}")
    
    async def _test_bedrock_connection(self):
        """Test AWS Bedrock connection"""
        try:
            # Simple test message
            test_messages = [{"role": "user", "content": "Test connection"}]
            await self._bedrock_chat_completion(
                test_messages, 
                "claude-3-haiku",  # Use model name, not direct ID
                0.1, 
                10  # Very short response for testing
            )
            logger.info("✅ AWS Bedrock connection test successful")
        except Exception as e:
            logger.error(f"❌ AWS Bedrock connection test failed: {e}")
            raise

    @asynccontextmanager
    async def get_client(self):
        """Context manager for getting Bedrock client (pure AWS)"""
        if not self._initialized:
            await self.initialize()
        
        if not self.bedrock_client:
            raise RuntimeError("AWS Bedrock client not available")
        
        yield self.bedrock_client

    async def parallel_chat_completions(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Context7 optimization: Process multiple chat requests in parallel
        Based on AWS samples: concurrent.futures.ThreadPoolExecutor pattern
        """
        max_concurrent = max_concurrent or self.max_concurrent
        
        async def process_single_request(request):
            async with self.semaphore:
                return await self.chat_completion(**request)
        
        # Execute all requests concurrently
        tasks = [process_single_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and return results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel request {i} failed: {result}")
                processed_results.append({
                    'error': True,
                    'message': str(result),
                    'choices': []
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pure AWS Bedrock chat completion - no fallbacks
        Maps common model names to Bedrock models
        """
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        if not self.bedrock_client:
            raise RuntimeError("AWS Bedrock client not initialized")
        
        try:
            # Context7 optimization: Use standard bedrock chat completion
            result = await self._bedrock_chat_completion(
                messages, model, temperature, max_tokens, **kwargs
            )
            
            response_time = time.time() - start_time
            await self._update_bedrock_stats(response_time, True, model)
            
            # Track performance metrics (Context7 best practice)
            if 'ttft' in result:
                self.performance_metrics['ttft_times'].append(result['ttft'])
            self.performance_metrics['total_times'].append(response_time)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            await self._update_bedrock_stats(response_time, False, model)
            logger.error(f"❌ AWS Bedrock request failed: {e}")
            raise RuntimeError(f"AWS Bedrock chat completion failed: {e}")

    async def _bedrock_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute chat completion using AWS Bedrock Claude models"""
        
        # Map model name to Bedrock model ID
        bedrock_model = self.model_mapping.get(model, self.primary_model)
        
        # Convert messages to Claude format
        claude_messages = []
        system_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or 4000,
            "temperature": temperature,
            "messages": claude_messages
        }
        
        if system_message:
            request_body["system"] = system_message
        
        try:
            # Make request to Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=bedrock_model,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            
            # Convert to OpenAI-compatible format
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response_body["content"][0]["text"]
                    },
                    "finish_reason": response_body.get("stop_reason", "stop")
                }],
                "usage": {
                    "prompt_tokens": response_body.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": response_body.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": (
                        response_body.get("usage", {}).get("input_tokens", 0) + 
                        response_body.get("usage", {}).get("output_tokens", 0)
                    )
                },
                "model": bedrock_model,
                "aws_region": self.aws_region,
                "service": "bedrock"
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"❌ AWS Bedrock ClientError [{error_code}]: {error_message}")
            raise RuntimeError(f"AWS Bedrock error [{error_code}]: {error_message}")
        except Exception as e:
            logger.error(f"❌ AWS Bedrock unexpected error: {e}")
            raise RuntimeError(f"AWS Bedrock request failed: {e}")

    async def _update_bedrock_stats(self, response_time: float, success: bool, model: str):
        """Update AWS Bedrock usage statistics"""
        async with self.lock:
            self.bedrock_stats["total_requests"] += 1
            self.bedrock_stats["total_response_time"] += response_time
            
            if success:
                self.bedrock_stats["successful_requests"] += 1
            else:
                self.bedrock_stats["failed_requests"] += 1
            
            # Track model usage
            bedrock_model = self.model_mapping.get(model, model)
            if bedrock_model not in self.bedrock_stats["model_usage"]:
                self.bedrock_stats["model_usage"][bedrock_model] = 0
            self.bedrock_stats["model_usage"][bedrock_model] += 1
            
            # Calculate average response time
            if self.bedrock_stats["total_requests"] > 0:
                self.bedrock_stats["average_response_time"] = (
                    self.bedrock_stats["total_response_time"] / 
                    self.bedrock_stats["total_requests"]
                )

    async def embeddings(
        self,
        input_text: str,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings using AWS Bedrock Titan Embeddings
        Pure AWS implementation - no external APIs
        """
        # Use environment variable for embedding model if not provided
        if model is None:
            model = os.getenv("BEDROCK_TITAN_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
            
        if not self._initialized:
            await self.initialize()
        
        if not self.bedrock_client:
            raise RuntimeError("AWS Bedrock client not initialized")
        
        try:
            request_body = {
                "inputText": input_text
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response["body"].read())
            
            return {
                "data": [{
                    "embedding": response_body["embedding"],
                    "index": 0
                }],
                "usage": {
                    "prompt_tokens": len(input_text.split()),
                    "total_tokens": len(input_text.split())
                },
                "model": model,
                "service": "bedrock-embeddings"
            }
            
        except Exception as e:
            logger.error(f"❌ AWS Bedrock embeddings failed: {e}")
            raise RuntimeError(f"AWS Bedrock embeddings failed: {e}")

    async def batch_chat_completions(
        self,
        batch_requests: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """Execute multiple chat completions concurrently on AWS Bedrock"""
        
        async def process_single_request(request):
            try:
                return await self.chat_completion(**request)
            except Exception as e:
                logger.error(f"❌ Batch request failed: {e}")
                return {
                    "error": str(e),
                    "success": False,
                    "service": "bedrock"
                }
        
        # Process requests with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_request(request):
            async with semaphore:
                return await process_single_request(request)
        
        results = await asyncio.gather(
            *[bounded_request(req) for req in batch_requests],
            return_exceptions=True
        )
        
        return results

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get comprehensive AWS Bedrock usage statistics"""
        async with self.lock:
            total_requests = self.bedrock_stats["total_requests"]
            successful_requests = self.bedrock_stats["successful_requests"]
            
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "service": "aws-bedrock-only",
                "region": self.aws_region,
                "initialized": self._initialized,
                "statistics": {
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "failed_requests": self.bedrock_stats["failed_requests"],
                    "success_rate_percent": round(success_rate, 2),
                    "average_response_time": round(self.bedrock_stats["average_response_time"], 3),
                    "total_response_time": round(self.bedrock_stats["total_response_time"], 3)
                },
                "model_usage": self.bedrock_stats["model_usage"],
                "available_models": list(self.model_mapping.values()),
                "fallback_services": "none"  # Pure AWS implementation
            }

    async def reset_stats(self):
        """Reset all statistics"""
        async with self.lock:
            self.bedrock_stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_response_time": 0.0,
                "model_usage": {},
                "average_response_time": 0.0
            }
            logger.info("📊 AWS Bedrock statistics reset")

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Context7 optimization: Get comprehensive performance metrics
        """
        try:
            import numpy as np
            
            ttft_times = self.performance_metrics.get('ttft_times', [])
            total_times = self.performance_metrics.get('total_times', [])
            
            metrics = {
                'total_requests': self.total_requests,
                'failed_requests': self.failed_requests,
                'success_rate': (self.total_requests - self.failed_requests) / max(self.total_requests, 1),
                'cache_hit_rate': self.performance_metrics['cache_hits'] / max(
                    self.performance_metrics['cache_hits'] + self.performance_metrics['cache_misses'], 1
                ),
                'cache_hits': self.performance_metrics['cache_hits'],
                'cache_misses': self.performance_metrics['cache_misses']
            }
            
            if ttft_times:
                metrics.update({
                    'ttft_mean': np.mean(ttft_times),
                    'ttft_p90': np.percentile(ttft_times, 90),
                    'ttft_p50': np.percentile(ttft_times, 50)
                })
            
            if total_times:
                metrics.update({
                    'response_time_mean': np.mean(total_times),
                    'response_time_p90': np.percentile(total_times, 90),
                    'response_time_p50': np.percentile(total_times, 50)
                })
            
            return metrics
        except ImportError:
            # Fallback without numpy
            return {
                'total_requests': self.total_requests,
                'failed_requests': self.failed_requests,
                'cache_hits': self.performance_metrics.get('cache_hits', 0),
                'cache_misses': self.performance_metrics.get('cache_misses', 0)
            }

    async def batch_chat_completions(
        self,
        prompts: List[str],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Context7 optimization: Batch processing for similar requests
        Based on AWS samples batch processing patterns
        """
        # Convert prompts to request format
        requests = []
        for prompt in prompts:
            requests.append({
                'messages': [{'role': 'user', 'content': prompt}],
                'model': model,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'use_cache': use_cache
            })
        
        # Process in parallel
        return await self.parallel_chat_completions(requests)

    async def close(self):
        """Clean up resources and thread pool"""
        # Clean up thread pool if it exists
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
        
        # AWS Bedrock client doesn't need explicit closing
        self._initialized = False
        logger.info("🔒 AWS Bedrock-Only AI Client Pool closed")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for AWS Bedrock service"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Test with a simple request
            start_time = time.time()
            test_result = await self.chat_completion(
                messages=[{"role": "user", "content": "Health check"}],
                model="claude-3-haiku",
                temperature=0.1,
                max_tokens=10
            )
            response_time = time.time() - start_time
            
            return {
                "service": "aws-bedrock-only",
                "status": "healthy",
                "region": self.aws_region,
                "response_time": round(response_time, 3),
                "test_successful": True,
                "available_models": len(self.model_mapping),
                "initialized": self._initialized
            }
            
        except Exception as e:
            return {
                "service": "aws-bedrock-only",
                "status": "unhealthy",
                "error": str(e),
                "region": self.aws_region,
                "initialized": self._initialized
            }

# Global instance management
_global_ai_pool: Optional[AsyncAIClientPool] = None

async def get_openai_pool(pool_size: int = 5) -> AsyncAIClientPool:
    """Get global AWS Bedrock-only AI client pool"""
    global _global_ai_pool
    
    if _global_ai_pool is None:
        _global_ai_pool = AsyncAIClientPool(pool_size=pool_size)
        await _global_ai_pool.initialize()
        logger.info("🌐 Global AWS Bedrock-Only AI pool created")
    
    return _global_ai_pool

async def close_global_openai_pool():
    """Close global AI client pool"""
    global _global_ai_pool
    
    if _global_ai_pool:
        await _global_ai_pool.close()
        _global_ai_pool = None
        logger.info("🔒 Global AWS Bedrock-Only AI pool closed")