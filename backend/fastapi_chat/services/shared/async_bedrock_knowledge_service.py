"""
AWS Bedrock Knowledge Bases Service for RAG Capabilities
Implements knowledge retrieval augmented generation using Bedrock KB
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AsyncBedrockKnowledgeService:
    """
    Async Bedrock Knowledge Bases service for RAG capabilities
    Integrates with your document corpus for intelligent retrieval
    """
    
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.knowledge_base_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
        self.data_source_id = os.getenv("BEDROCK_DATA_SOURCE_ID")
        self.s3_bucket = os.getenv("S3_KNOWLEDGE_BUCKET", "mr-white-knowledge-base")
        
        # Initialize Bedrock clients
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=self.aws_region)
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=self.aws_region)
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        
        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_documents_indexed": 0,
            "average_query_time": 0.0,
            "knowledge_base_ready": False
        }
        
        logger.info(f"✅ Bedrock Knowledge Base service initialized for region: {self.aws_region}")
    
    # ==================== KNOWLEDGE BASE MANAGEMENT ====================
    
    async def ensure_knowledge_base_exists(self) -> bool:
        """Ensure knowledge base and data source exist"""
        try:
            # Check if knowledge base exists
            # Early return if Knowledge Base is not configured
            if not os.getenv("BEDROCK_KB_ROLE_ARN") or not os.getenv("OPENSEARCH_COLLECTION_ARN"):
                logger.info("Knowledge base not configured - operating in standard mode")
                self.stats["knowledge_base_ready"] = False
                return False

            if not self.knowledge_base_id:
                self.knowledge_base_id = await self._create_knowledge_base()
            
            # Verify knowledge base status
            kb_status = await self._get_knowledge_base_status()
            if kb_status != 'ACTIVE':
                logger.warning(f"Knowledge base status: {kb_status}")
                return False
            
            # Get or create data source ID
            if not self.data_source_id:
                # First try to get existing data source ID
                try:
                    existing_sources = self.bedrock_agent.list_data_sources(knowledgeBaseId=self.knowledge_base_id)
                    for source in existing_sources.get('dataSourceSummaries', []):
                        if source['name'] == 'mr-white-s3-documents':
                            self.data_source_id = source['dataSourceId']
                            logger.info(f"✅ Found existing data source ID: {self.data_source_id}")
                            break
                except Exception as e:
                    logger.warning(f"Could not retrieve existing data sources: {e}")
                
                # If still no data source ID, create one
                if not self.data_source_id:
                    self.data_source_id = await self._create_data_source()
            
            # Ensure S3 bucket exists
            await self._ensure_s3_bucket_exists()
            
            self.stats["knowledge_base_ready"] = True
            logger.info("✅ Knowledge base and data source verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure knowledge base exists: {e}")
            self.stats["knowledge_base_ready"] = False
            return False
    
    async def _create_knowledge_base(self) -> str:
        """Create a new knowledge base"""
        try:
            # Create knowledge base
            response = self.bedrock_agent.create_knowledge_base(
                name="mr-white-dog-care-knowledge",
                description="Mr. White's comprehensive dog care and training knowledge base",
                roleArn=os.getenv("BEDROCK_KB_ROLE_ARN"),
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': f'arn:aws:bedrock:{self.aws_region}::foundation-model/{os.getenv("BEDROCK_TITAN_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")}',
                        'embeddingModelConfiguration': {
                            'bedrockEmbeddingModelConfiguration': {
                                'dimensions': 1536
                            }
                        }
                    }
                },
                storageConfiguration={
                    # Note: AWS Bedrock Knowledge Base uses OpenSearch Serverless as its backend
                    # This is separate from our application's vector storage (which uses Pinecone)
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': os.getenv("OPENSEARCH_COLLECTION_ARN"),
                        'vectorIndexName': 'mr-white-knowledge-index',
                        'fieldMapping': {
                            'vectorField': 'bedrock-knowledge-base-default-vector',
                            'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                            'metadataField': 'AMAZON_BEDROCK_METADATA'
                        }
                    }
                }
            )
            
            knowledge_base_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"✅ Created knowledge base: {knowledge_base_id}")
            
            # Wait for knowledge base to become active
            await self._wait_for_knowledge_base_ready(knowledge_base_id)
            
            return knowledge_base_id
            
        except ClientError as e:
            logger.error(f"❌ Failed to create knowledge base: {e}")
            raise
    
    async def _create_data_source(self) -> str:
        """Create data source for the knowledge base"""
        try:
            response = self.bedrock_agent.create_data_source(
                knowledgeBaseId=self.knowledge_base_id,
                name="mr-white-s3-documents",
                description="S3 data source for Mr. White's documents",
                dataSourceConfiguration={
                    'type': 'S3',
                    's3Configuration': {
                        'bucketArn': f'arn:aws:s3:::{self.s3_bucket}',
                        'inclusionPrefixes': ['documents/']  # AWS Bedrock only allows 1 prefix
                    }
                },
                vectorIngestionConfiguration={
                    'chunkingConfiguration': {
                        'chunkingStrategy': 'FIXED_SIZE',
                        'fixedSizeChunkingConfiguration': {
                            'maxTokens': 1000,
                            'overlapPercentage': 20
                        }
                    }
                }
            )
            
            data_source_id = response['dataSource']['dataSourceId']
            logger.info(f"✅ Created data source: {data_source_id}")
            return data_source_id
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConflictException':
                # DataSource already exists, extract ID from existing sources
                logger.info(f"✅ DataSource already exists, retrieving existing ID")
                try:
                    existing_sources = self.bedrock_agent.list_data_sources(knowledgeBaseId=self.knowledge_base_id)
                    for source in existing_sources.get('dataSourceSummaries', []):
                        if source['name'] == 'mr-white-s3-documents':
                            return source['dataSourceId']
                    logger.warning("⚠️ Could not find existing data source ID")
                    return None
                except Exception as list_e:
                    logger.error(f"❌ Failed to retrieve existing data source: {list_e}")
                    return None
            else:
                logger.error(f"❌ Failed to create data source: {e}")
                raise
    
    async def _ensure_s3_bucket_exists(self):
        """Ensure S3 bucket exists for knowledge base documents"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info(f"✅ S3 bucket {self.s3_bucket} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Create bucket
                self.s3_client.create_bucket(
                    Bucket=self.s3_bucket,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.aws_region
                    } if self.aws_region != 'us-east-1' else {}
                )
                logger.info(f"✅ Created S3 bucket: {self.s3_bucket}")
            else:
                raise
    
    async def _wait_for_knowledge_base_ready(self, knowledge_base_id: str, max_attempts: int = 30):
        """Wait for knowledge base to become ready"""
        for attempt in range(max_attempts):
            status = await self._get_knowledge_base_status(knowledge_base_id)
            if status == 'ACTIVE':
                return
            elif status == 'FAILED':
                raise Exception("Knowledge base creation failed")
            
            await asyncio.sleep(10)
        
        raise TimeoutError("Knowledge base did not become ready in time")
    
    async def _get_knowledge_base_status(self, knowledge_base_id: str = None) -> str:
        """Get knowledge base status"""
        try:
            kb_id = knowledge_base_id or self.knowledge_base_id
            response = self.bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
            return response['knowledgeBase']['status']
        except Exception as e:
            logger.error(f"❌ Failed to get knowledge base status: {e}")
            return 'UNKNOWN'
    
    # ==================== DOCUMENT MANAGEMENT ====================
    
    async def upload_document(
        self,
        file_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Upload a document to S3 for knowledge base ingestion"""
        try:
            # Upload to S3
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
            
            self.s3_client.upload_file(
                file_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"✅ Uploaded document to S3: {s3_key}")
            
            # Trigger ingestion job (only if knowledge base is properly configured)
            if self.data_source_id:
                await self._trigger_ingestion_job()
            
            self.stats["total_documents_indexed"] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload document {s3_key}: {e}")
            return False
    
    async def upload_document_content(
        self,
        content: str,
        s3_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Upload document content directly to S3"""
        try:
            # Upload content to S3
            extra_args = {'ContentType': 'text/plain'}
            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content.encode('utf-8'),
                **extra_args
            )
            
            logger.info(f"✅ Uploaded content to S3: {s3_key}")
            
            # Trigger ingestion job (only if knowledge base is properly configured)
            if self.data_source_id:
                await self._trigger_ingestion_job()
            
            self.stats["total_documents_indexed"] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload content {s3_key}: {e}")
            return False
    
    async def _trigger_ingestion_job(self):
        """Trigger ingestion job to update knowledge base"""
        try:
            # Check if we have a valid data source ID
            if not self.data_source_id:
                logger.warning("⚠️ No data source ID available - skipping ingestion job")
                return
                
            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"✅ Started ingestion job: {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger ingestion job: {e}")
    
    # ==================== KNOWLEDGE RETRIEVAL (RAG) ====================
    
    async def retrieve_knowledge(
        self,
        query: str,
        max_results: int = 5,
        user_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge for RAG"""
        try:
            if not self.knowledge_base_id:
                logger.debug("Knowledge base not configured")
                return []
            
            # Prepare retrieval request
            retrieval_query = {
                'text': query
            }
            
            # Add user context if available
            if user_context:
                retrieval_query['text'] += f" Context: {json.dumps(user_context)}"
            
            # Perform knowledge retrieval
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery=retrieval_query,
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'overrideSearchType': 'HYBRID'  # Use both semantic and text search
                    }
                }
            )
            
            # Process results
            knowledge_results = []
            for result in response['retrievalResults']:
                knowledge_results.append({
                    'content': result['content']['text'],
                    'score': result['score'],
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                })
            
            self.stats["successful_queries"] += 1
            logger.info(f"✅ Retrieved {len(knowledge_results)} knowledge items for query")
            return knowledge_results
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            logger.error(f"❌ Failed to retrieve knowledge: {e}")
            return []
    
    async def retrieve_and_generate(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        model_id: str = None
    ) -> Dict[str, Any]:
        """Retrieve knowledge and generate response (full RAG)"""
        # Use environment variable for model_id if not provided
        if model_id is None:
            model_id = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
            
        try:
            if not self.knowledge_base_id:
                logger.warning("Knowledge base not configured - falling back to main LLM only")
                return {"response": "", "sources": []}  # Graceful degradation
            
            # Prepare generation request
            input_data = {
                'text': query
            }
            
            if user_context:
                input_data['text'] += f" User context: {json.dumps(user_context)}"
            
            # Perform retrieve and generate
            response = self.bedrock_agent_runtime.retrieve_and_generate(
                input=input_data,
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.knowledge_base_id,
                        'modelArn': f'arn:aws:bedrock:{self.aws_region}::foundation-model/{model_id}',
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': 5,
                                'overrideSearchType': 'HYBRID'
                            }
                        }
                    }
                }
            )
            
            # Extract response and sources
            generated_response = response['output']['text']
            citations = response.get('citations', [])
            
            # Format sources
            sources = []
            for citation in citations:
                for reference in citation.get('retrievedReferences', []):
                    sources.append({
                        'content': reference['content']['text'][:200] + '...',
                        'location': reference.get('location', {}),
                        'metadata': reference.get('metadata', {})
                    })
            
            self.stats["successful_queries"] += 1
            logger.info("✅ Generated response with knowledge retrieval")
            
            return {
                "response": generated_response,
                "sources": sources,
                "session_id": response.get('sessionId')
            }
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            error_msg = str(e)
            
            # Provide specific guidance for common Bedrock errors
            if "403 Forbidden" in error_msg or "security_exception" in error_msg:
                logger.warning("Bedrock Knowledge Base: Access denied (403). Check AWS IAM permissions for Bedrock services. Falling back to main LLM.")
            elif "ValidationException" in error_msg:
                logger.warning("Bedrock Knowledge Base: Configuration invalid. Check agent/knowledge base IDs and settings. Falling back to main LLM.")
            elif "ResourceNotFoundException" in error_msg:
                logger.warning("Bedrock Knowledge Base: Resource not found. Verify knowledge base/agent exists in your AWS account. Falling back to main LLM.")
            else:
                logger.warning(f"Bedrock Knowledge Base: Temporarily unavailable ({error_msg[:100]}). Falling back to main LLM.")
            
            # Graceful degradation - let main LLM handle the query
            return {
                "response": "",  # Empty response - let the main LLM handle everything
                "sources": []
            }
    
    # ==================== PERFORMANCE & STATS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""
        return {
            **self.stats,
            "knowledge_base_id": self.knowledge_base_id,
            "data_source_id": self.data_source_id,
            "s3_bucket": self.s3_bucket,
            "region": self.aws_region
        }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_documents_indexed": 0,
            "average_query_time": 0.0,
            "knowledge_base_ready": False
        }