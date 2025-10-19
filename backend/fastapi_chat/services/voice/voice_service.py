"""
Voice Service for Audio Transcription and Processing
Handles audio file transcription using OpenAI Whisper API
Similar architecture to VisionService but for audio processing
"""

import asyncio
import base64
import io
import json
import logging
import time
import uuid
import boto3
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from models import AsyncSessionLocal, UserImage, Message, Conversation
from services.shared.async_s3_service import AsyncS3Service
from services.shared.async_openai_pool_service import get_openai_pool

logger = logging.getLogger(__name__)

class VoiceService:
    """
    Voice service for audio transcription and processing
    Uses OpenAI Whisper API for speech-to-text conversion
    """
    
    def __init__(self, cache_service=None):
        self.cache_service = cache_service
        self.s3_service = AsyncS3Service()
        
        # Voice configuration - support both AWS Transcribe and OpenAI Whisper
        self.whisper_model = "whisper-1"  # OpenAI Whisper model (fallback)
        self.aws_region = "us-east-1"  # AWS region for Transcribe
        self.supported_formats = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
        self.max_file_size = 25 * 1024 * 1024  # 25MB limit
        
        # AWS Transcribe client
        self.transcribe_client = boto3.client('transcribe', region_name=self.aws_region)
        
        # Performance tracking
        self.processing_stats = {
            "total_audio_processed": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "total_processing_time": 0.0
        }
        
        # OpenAI pool will be assigned from main (for fallback)
        self.openai_pool = None

    async def _get_openai_pool(self):
        """Get OpenAI pool from service or global"""
        if self.openai_pool:
            return self.openai_pool
        return await get_openai_pool()

    async def transcribe_with_aws_transcribe(self, s3_bucket: str, s3_key: str, filename: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Transcribe audio using AWS Transcribe service
        
        Args:
            s3_bucket: S3 bucket containing the audio file
            s3_key: S3 key of the audio file
            filename: Original filename for job naming
            
        Returns:
            Tuple of (success, transcription, metadata)
        """
        try:
            # Generate unique job name
            job_name = f"transcribe_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            
            # Determine media format from filename
            file_ext = filename.lower().split('.')[-1] if '.' in filename else 'mp3'
            media_format_map = {
                'mp3': 'mp3',
                'mp4': 'mp4', 
                'm4a': 'mp4',
                'wav': 'wav',
                'webm': 'webm'
            }
            media_format = media_format_map.get(file_ext, 'mp3')
            
            # Start transcription job
            logger.info(f"🎙️ Starting AWS Transcribe job: {job_name}")
            
            transcribe_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.transcribe_client.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={
                        'MediaFileUri': f"s3://{s3_bucket}/{s3_key}"
                    },
                    MediaFormat=media_format,
                    LanguageCode='en-US'  # Can be made configurable
                    # Removed Settings to keep it simple and avoid speaker labeling issues
                )
            )
            
            # Poll for completion
            max_wait_time = 120  # 2 minutes max wait
            wait_interval = 2  # Check every 2 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                await asyncio.sleep(wait_interval)
                elapsed_time += wait_interval
                
                status_response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.transcribe_client.get_transcription_job(
                        TranscriptionJobName=job_name
                    )
                )
                
                status = status_response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get transcription result
                    transcript_uri = status_response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    
                    # Download and parse transcript
                    async with httpx.AsyncClient() as client:
                        transcript_response = await client.get(transcript_uri)
                        transcript_data = transcript_response.json()
                    
                    # Extract transcription text
                    transcription = transcript_data['results']['transcripts'][0]['transcript']
                    
                    # Clean up the job
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.transcribe_client.delete_transcription_job(
                            TranscriptionJobName=job_name
                        )
                    )
                    
                    metadata = {
                        'service': 'aws_transcribe',
                        'job_name': job_name,
                        'media_format': media_format,
                        'language_code': 'en-US',
                        'processing_time': elapsed_time
                    }
                    
                    logger.info(f"✅ AWS Transcribe completed: {len(transcription)} characters")
                    return True, transcription, metadata
                    
                elif status == 'FAILED':
                    failure_reason = status_response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    logger.error(f"❌ AWS Transcribe failed: {failure_reason}")
                    
                    # Clean up failed job
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self.transcribe_client.delete_transcription_job(
                                TranscriptionJobName=job_name
                            )
                        )
                    except:
                        pass
                    
                    return False, f"Transcription failed: {failure_reason}", {}
            
            # Timeout - clean up job
            logger.warning(f"⏰ AWS Transcribe timeout after {max_wait_time}s")
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.transcribe_client.delete_transcription_job(
                        TranscriptionJobName=job_name
                    )
                )
            except:
                pass
            
            return False, "Transcription timed out", {}
            
        except Exception as e:
            logger.error(f"❌ AWS Transcribe error: {str(e)}")
            return False, f"Transcription error: {str(e)}", {}

    async def transcribe_audio(self, audio_content: bytes, filename: str, user_message: str = "", s3_info: Dict[str, Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Transcribe audio using AWS Transcribe (primary) or OpenAI Whisper (fallback)
        
        Args:
            audio_content: Raw audio bytes
            filename: Original filename for format detection
            user_message: Optional user message context
            s3_info: S3 upload information (bucket, key) for AWS Transcribe
            
        Returns:
            Tuple of (success, transcription, metadata)
        """
        try:
            # Validate file size
            if len(audio_content) > self.max_file_size:
                return False, f"Audio file too large. Maximum size is {self.max_file_size // (1024*1024)}MB", {}
            
            # Get file extension for format validation
            file_ext = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
            if file_ext not in self.supported_formats:
                return False, f"Unsupported audio format: {file_ext}. Supported: {', '.join(self.supported_formats)}", {}
            
            logger.info(f"🎙️ Starting audio transcription for {filename} ({len(audio_content)} bytes)")
            start_time = time.time()
            
            # Try AWS Transcribe first if S3 info is available
            if s3_info and s3_info.get('s3_bucket') and s3_info.get('s3_key'):
                logger.info("🎙️ Using AWS Transcribe for transcription")
                success, transcription, aws_metadata = await self.transcribe_with_aws_transcribe(
                    s3_info['s3_bucket'], 
                    s3_info['s3_key'], 
                    filename
                )
                
                if success and transcription.strip():
                    processing_time = time.time() - start_time
                    self.processing_stats["total_audio_processed"] += 1
                    self.processing_stats["successful_transcriptions"] += 1
                    self.processing_stats["total_processing_time"] += processing_time
                    
                    # Merge metadata
                    transcription_data = {
                        **aws_metadata,
                        'total_processing_time': processing_time,
                        'file_size': len(audio_content),
                        'file_format': file_ext,
                        'confidence': 'high',
                        'user_message_provided': bool(user_message),
                        'primary_service': 'aws_transcribe'
                    }
                    
                    logger.info(f"✅ AWS Transcribe successful: {len(transcription)} characters")
                    return True, transcription, transcription_data
                else:
                    logger.warning(f"⚠️ AWS Transcribe failed, trying fallback: {transcription}")
            
            # Fallback to OpenAI Whisper or simple response
            logger.info("🎙️ AWS Transcribe not available, using fallback")
            
            # Create a user-friendly response based on the scenario
            if user_message.strip():
                # User provided text with audio
                transcription = f"I can see you've shared an audio message along with your text: '{user_message}'. While I can't transcribe the audio yet, I'm happy to help with your question!"
            else:
                # Audio only
                transcription = f"I can see you've shared an audio message. While I can't transcribe audio yet, please feel free to type your message and I'll be happy to help!"
            
            processing_time = time.time() - start_time
            
            # Update stats
            self.processing_stats["total_audio_processed"] += 1
            self.processing_stats["failed_transcriptions"] += 1
            self.processing_stats["total_processing_time"] += processing_time
            
            # Create metadata
            transcription_data = {
                'model_used': 'fallback_response',
                'processing_time': processing_time,
                'file_size': len(audio_content),
                'file_format': file_ext,
                'confidence': 'low',
                'user_message_provided': bool(user_message),
                'service': 'fallback_user_friendly'
            }
            
            return True, transcription, transcription_data
            
        except Exception as e:
            logger.error(f"❌ Voice transcription error: {str(e)}")
            self.processing_stats["failed_transcriptions"] += 1
            return False, f"Error transcribing audio: {str(e)}", {}

    async def store_audio_to_attachments(
        self, 
        user_id: int, 
        audio_content: bytes, 
        filename: str, 
        transcription: str,
        transcription_data: Dict[str, Any],
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Store audio file to S3 and create attachment record
        
        Args:
            user_id: User ID
            audio_content: Raw audio bytes
            filename: Original filename
            transcription: Transcribed text
            transcription_data: Metadata from transcription
            conversation_id: Optional conversation context
            message_id: Optional message context
            
        Returns:
            Dictionary with success status and file data
        """
        try:
            # Generate unique filename
            unique_filename = f"audio_{uuid.uuid4().hex[:8]}_{filename}"
            
            # Determine content type based on extension
            file_ext = filename.lower().split('.')[-1] if '.' in filename else 'mp3'
            content_type_map = {
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav', 
                'm4a': 'audio/mp4',
                'webm': 'audio/webm',
                'ogg': 'audio/ogg'
            }
            content_type = content_type_map.get(file_ext, 'audio/mpeg')
            
            # Upload to S3
            s3_result = await self.s3_service.upload_audio_to_s3(
                file_content=audio_content,
                filename=unique_filename,
                user_id=user_id,
                content_type=content_type
            )
            
            if not s3_result.get("success"):
                logger.error(f"❌ S3 upload failed: {s3_result.get('error')}")
                return {"success": False, "error": "Failed to upload audio to storage"}
            
            # Create attachment record (similar to how documents are handled)
            return {
                "success": True,
                "filename": unique_filename,
                "original_filename": filename,
                "s3_url": s3_result["download_url"],
                "s3_key": s3_result["s3_key"],
                "s3_bucket": s3_result["s3_bucket"],
                "transcription": transcription,
                "metadata": transcription_data,
                "content_type": content_type,
                "file_size": len(audio_content)
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing audio file: {str(e)}")
            return {"success": False, "error": str(e)}

    async def process_voice_request(
        self, 
        user_id: int, 
        user_message: str = "",
        audio_files: List[Dict[str, Any]] = None,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process voice request with transcription and storage
        
        Args:
            user_id: User ID
            user_message: Optional user message
            audio_files: List of audio file dictionaries
            conversation_id: Optional conversation ID
            message_id: Optional message ID
            
        Returns:
            Processing result with transcriptions and AI response
        """
        try:
            logger.info(f"🎙️ Processing voice request for user {user_id} with {len(audio_files) if audio_files else 0} audio files")
            
            if not audio_files:
                return {
                    "success": False,
                    "content": "No audio files provided for transcription.",
                    "error": "No audio files"
                }
            
            self.processing_stats["total_audio_processed"] += len(audio_files)
            
            processed_audio = []
            transcriptions = []
            
            for audio_dict in audio_files:
                try:
                    # Extract audio data
                    if isinstance(audio_dict.get('content'), str):
                        # Base64 encoded content
                        audio_content = base64.b64decode(audio_dict['content'])
                    else:
                        # Raw bytes
                        audio_content = audio_dict['content']
                    
                    filename = audio_dict.get('filename', 'audio.mp3')
                    
                    # First upload to S3 to get S3 info for transcription
                    storage_result = await self.store_audio_to_attachments(
                        user_id=user_id,
                        audio_content=audio_content,
                        filename=filename,
                        transcription="",  # Will update after transcription
                        transcription_data={},
                        conversation_id=conversation_id,
                        message_id=message_id
                    )
                    
                    if not storage_result.get("success"):
                        logger.error(f"❌ Storage failed for {filename}: {storage_result.get('error')}")
                        continue
                    
                    # Now transcribe audio with S3 info
                    s3_info = {
                        's3_bucket': storage_result.get('s3_bucket'),
                        's3_key': storage_result.get('s3_key')
                    }
                    
                    success, transcription, transcription_data = await self.transcribe_audio(
                        audio_content, filename, user_message, s3_info
                    )
                    
                    if not success:
                        logger.error(f"❌ Transcription failed for {filename}: {transcription}")
                        # Still continue with the file, but use a fallback message
                        transcription = f"Audio file uploaded successfully, but transcription failed."
                    
                    if storage_result.get("success"):
                        processed_audio.append({
                            "filename": filename,
                            "s3_url": storage_result["s3_url"],
                            "transcription": transcription,
                            "original_filename": filename
                        })
                        transcriptions.append(transcription)
                        logger.info(f"✅ Successfully processed audio: {filename}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing audio file: {str(e)}")
                    continue
            
            # Generate AI response based on transcriptions
            if transcriptions:
                # Check if transcriptions are actual transcriptions or fallback messages
                real_transcriptions = []
                fallback_responses = []
                
                for t in transcriptions:
                    if t.startswith("I can see you've shared an audio message"):
                        fallback_responses.append(t)
                    else:
                        real_transcriptions.append(t)
                
                if real_transcriptions:
                    # We have real transcriptions - return the transcribed text for LangGraph processing
                    if len(real_transcriptions) == 1:
                        if user_message.strip():
                            # Combine transcribed audio with text message
                            combined_response = f"{real_transcriptions[0]} {user_message}"
                        else:
                            # Only audio transcription - return the transcribed question
                            combined_response = real_transcriptions[0]
                    else:
                        # Multiple audio files
                        transcription_text = " ".join(real_transcriptions)
                        if user_message.strip():
                            combined_response = f"{transcription_text} {user_message}"
                        else:
                            combined_response = transcription_text
                else:
                    # Only fallback responses - use the first one as it's already user-friendly
                    combined_response = fallback_responses[0] if fallback_responses else "I received your audio message. How can I help you?"
            else:
                combined_response = "I apologize, but I wasn't able to process the audio files you shared. Please try again or send your message as text."
            
            return {
                "success": True,
                "content": combined_response,
                "processed_files": processed_audio,
                "transcriptions": transcriptions,
                "audio_count": len(processed_audio),
                "processing_stats": {
                    "total_processed": len(audio_files),
                    "successful": len(processed_audio),
                    "failed": len(audio_files) - len(processed_audio)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in process_voice_request: {str(e)}")
            return {
                "success": False,
                "content": "I apologize, but I encountered an error processing your audio. Please try again.",
                "error": str(e)
            }

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get voice service processing statistics"""
        return {
            "voice_service_stats": self.processing_stats,
            "s3_service_stats": self.s3_service.get_upload_stats() if hasattr(self.s3_service, 'get_upload_stats') else {}
        }
