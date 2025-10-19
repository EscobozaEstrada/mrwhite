"""
Streaming response service using Server-Sent Events (SSE)
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from config.settings import settings
from schemas.chat import StreamChunk

logger = logging.getLogger(__name__)


class StreamingService:
    """Service for streaming AI responses using SSE"""
    
    def __init__(self):
        """Initialize streaming service with Bedrock client"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.model_id = settings.BEDROCK_MODEL_ID
        self.max_tokens = settings.BEDROCK_MAX_TOKENS
        self.temperature = settings.BEDROCK_TEMPERATURE
        self.chunk_size = settings.STREAM_CHUNK_SIZE
    
    async def stream_chat_response(
        self,
        messages: list,
        system_prompt: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        tools: Optional[list] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from Bedrock Claude
        
        Args:
            messages: List of message dicts (role, content)
            system_prompt: System prompt for context
            metadata: Additional metadata to send
            tools: List of tool definitions for function calling
        
        Yields:
            SSE formatted strings with chunks
        """
        try:
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": messages
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            if tools:
                request_body["tools"] = tools
            
            # Invoke model with streaming
            response = self.bedrock_runtime.invoke_model_with_response_stream(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Send initial metadata
            if metadata:
                chunk = StreamChunk(
                    type="metadata",
                    content=None,
                    metadata=metadata,
                    error=None
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            # Stream tokens
            stream = response.get('body')
            full_content = ""
            tool_use_blocks = []
            
            if stream:
                for event in stream:
                    chunk_data = event.get('chunk')
                    if chunk_data:
                        chunk_json = json.loads(chunk_data.get('bytes').decode())
                        
                        # Handle different event types
                        if chunk_json.get('type') == 'content_block_start':
                            # Check if this is a tool_use block
                            content_block = chunk_json.get('content_block', {})
                            if content_block.get('type') == 'tool_use':
                                tool_use_blocks.append({
                                    'id': content_block.get('id'),
                                    'name': content_block.get('name'),
                                    'input': {}
                                })
                        
                        elif chunk_json.get('type') == 'content_block_delta':
                            delta = chunk_json.get('delta', {})
                            if delta.get('type') == 'text_delta':
                                text = delta.get('text', '')
                                full_content += text
                                
                                # Send token chunk
                                chunk = StreamChunk(
                                    type="token",
                                    content=text,
                                    metadata=None,
                                    error=None
                                )
                                yield f"data: {chunk.model_dump_json()}\n\n"
                            
                            elif delta.get('type') == 'input_json_delta':
                                # Accumulate tool input
                                if tool_use_blocks:
                                    partial_json = delta.get('partial_json', '')
                                    # Note: input will be complete in content_block_stop
                        
                        elif chunk_json.get('type') == 'content_block_stop':
                            # Tool use block is complete
                            if tool_use_blocks:
                                # The last tool in the list is now complete
                                pass
                        
                        elif chunk_json.get('type') == 'message_stop':
                            # Send completion metadata
                            stop_reason = chunk_json.get('stop_reason', 'end_turn')
                            chunk = StreamChunk(
                                type="done",
                                content=full_content,
                                metadata={
                                    "stop_reason": stop_reason,
                                    "total_tokens": len(full_content.split()),  # Rough estimate
                                    "tool_calls": tool_use_blocks if tool_use_blocks else None
                                },
                                error=None
                            )
                            yield f"data: {chunk.model_dump_json()}\n\n"
            
            logger.info(f"✅ Streaming completed, total content length: {len(full_content)}")
            
        except ClientError as e:
            error_msg = f"Bedrock streaming error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            chunk = StreamChunk(
                type="error",
                content=None,
                metadata=None,
                error=error_msg
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
            
        except Exception as e:
            error_msg = f"Streaming error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            chunk = StreamChunk(
                type="error",
                content=None,
                metadata=None,
                error=error_msg
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
    
    async def generate_non_streaming_response(
        self,
        messages: list,
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Generate non-streaming response (fallback)
        
        Args:
            messages: List of message dicts
            system_prompt: System prompt
        
        Returns:
            Response dict with content and metadata
        """
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": messages
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            content = ""
            for content_block in response_body.get('content', []):
                if content_block.get('type') == 'text':
                    content += content_block.get('text', '')
            
            usage = response_body.get('usage', {})
            
            return {
                "content": content,
                "tokens_used": usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
                "input_tokens": usage.get('input_tokens', 0),
                "output_tokens": usage.get('output_tokens', 0),
                "stop_reason": response_body.get('stop_reason', 'end_turn')
            }
            
        except Exception as e:
            logger.error(f"❌ Non-streaming generation failed: {str(e)}")
            raise
    
    def format_sse_message(self, data: Dict[str, Any]) -> str:
        """
        Format message as SSE
        
        Args:
            data: Data to send
        
        Returns:
            SSE formatted string
        """
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    async def stream_with_thinking(
        self,
        messages: list,
        system_prompt: str = "",
        thinking_message: str = "Thinking..."
    ) -> AsyncGenerator[str, None]:
        """
        Stream response with initial thinking indicator
        
        Args:
            messages: Message history
            system_prompt: System prompt
            thinking_message: Initial message to show
        
        Yields:
            SSE formatted chunks
        """
        # Send thinking indicator
        chunk = StreamChunk(
            type="token",
            content=thinking_message,
            metadata={"is_thinking": True},
            error=None
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        
        # Stream actual response
        async for sse_chunk in self.stream_chat_response(messages, system_prompt):
            yield sse_chunk






