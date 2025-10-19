import os
import uuid
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Literal
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Document processing libraries
import PyPDF2
import fitz  # PyMuPDF for better PDF handling
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangchainDocument
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    CSVLoader
)

# LangGraph and LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import TypedDict

# Flask and internal imports
from flask import current_app
from app import db
from app.models.care_record import Document, KnowledgeBase
from app.models.user import User
from app.utils.s3_handler import upload_file_to_s3, get_s3_url
from app.utils.file_handler import store_document_vectors, query_user_docs

# Enhanced state for document processing with Context7 patterns
class DocumentProcessingState(MessagesState):
    """Enhanced state for document processing workflow following Context7 best practices"""
    user_id: int
    document_id: Optional[int]
    file_path: str
    file_type: str
    original_filename: str
    
    # Document content and analysis
    extracted_text: str
    document_summary: str
    detailed_analysis: Dict[str, Any]
    key_insights: List[str]
    document_classification: str
    
    # Pet-specific information
    pet_information: Dict[str, Any]
    health_information: Dict[str, Any]
    care_instructions: List[str]
    
    # Processing metadata
    processing_status: str
    processing_metrics: Dict[str, Any]
    quality_score: float
    error_message: Optional[str]
    
    # Storage and retrieval
    s3_url: Optional[str]
    s3_key: Optional[str]
    vector_stored: bool
    chunks_created: int
    
    # Agent communication
    agent_notes: Dict[str, Any]
    workflow_trace: List[str]


class EnhancedDocumentProcessingService:
    """Enhanced document processing service with Context7 LangGraph patterns"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            chunk_size=1000
        )
        self.chat_model = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            max_tokens=3000
        )
        self.checkpointer = MemorySaver()
        self.graph = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._initialize_processing_graph()
    
    def _initialize_processing_graph(self):
        """Initialize the document processing LangGraph workflow with Context7 patterns"""
        try:
            self._build_processing_graph()
            # Use Flask logger if available, otherwise use Python logging
            try:
                current_app.logger.info("✅ Enhanced document processing graph initialized successfully")
            except RuntimeError:
                logging.info("✅ Enhanced document processing graph initialized successfully")
        except Exception as e:
            # Use Flask logger if available, otherwise use Python logging
            try:
                current_app.logger.error(f"❌ Error initializing enhanced document processing graph: {str(e)}")
            except RuntimeError:
                logging.error(f"❌ Error initializing enhanced document processing graph: {str(e)}")
            raise
    
    def _build_processing_graph(self):
        """Build the enhanced LangGraph state graph for document processing"""
        
        builder = StateGraph(DocumentProcessingState)
        
        # Add specialized processing agents
        builder.add_node("document_extractor", self._document_extractor_agent)
        builder.add_node("content_analyzer", self._content_analyzer_agent)
        builder.add_node("pet_specialist", self._pet_specialist_agent)
        builder.add_node("health_analyzer", self._health_analyzer_agent)
        builder.add_node("insights_generator", self._insights_generator_agent)
        builder.add_node("vector_processor", self._vector_processor_agent)
        builder.add_node("metadata_enricher", self._metadata_enricher_agent)
        builder.add_node("quality_validator", self._quality_validator_agent)
        builder.add_node("storage_manager", self._storage_manager_agent)
        
        # Define the processing flow with Context7 patterns
        builder.add_edge(START, "document_extractor")
        builder.add_edge("document_extractor", "content_analyzer")
        builder.add_edge("content_analyzer", "pet_specialist")
        builder.add_edge("pet_specialist", "health_analyzer")
        builder.add_edge("health_analyzer", "insights_generator")
        builder.add_edge("insights_generator", "vector_processor")
        builder.add_edge("vector_processor", "metadata_enricher")
        builder.add_edge("metadata_enricher", "quality_validator")
        builder.add_edge("quality_validator", "storage_manager")
        builder.add_edge("storage_manager", END)
        
        # Compile the graph with checkpointing
        self.graph = builder.compile(checkpointer=self.checkpointer)
    
    def _document_extractor_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to extract text and basic information from documents"""
        
        try:
            current_app.logger.info(f"🔍 Document Extractor Agent processing: {state['original_filename']}")
            
            file_path = state['file_path']
            file_type = state['file_type']
            
            # Extract text based on file type with enhanced methods
            if file_type.lower() == 'pdf':
                extracted_text = self._extract_pdf_text_enhanced(file_path)
            elif file_type.lower() in ['txt', 'text']:
                extracted_text = self._extract_text_file(file_path)
            elif file_type.lower() in ['doc', 'docx']:
                extracted_text = self._extract_word_document(file_path)
            elif file_type.lower() == 'csv':
                extracted_text = self._extract_csv_content(file_path)
            else:
                extracted_text = self._extract_fallback(file_path)
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ValueError(f"Failed to extract meaningful text from {file_type} file")
            
            # Enhanced processing metrics
            processing_metrics = {
                'text_length': len(extracted_text),
                'word_count': len(extracted_text.split()),
                'extraction_method': f'enhanced_{file_type}_extraction',
                'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Document Extractor: Extracted {len(extracted_text)} characters")
            
            current_app.logger.info(f"✅ Text extracted: {len(extracted_text)} characters")
            
            return {
                **state,
                "extracted_text": extracted_text,
                "processing_status": "text_extracted",
                "processing_metrics": processing_metrics,
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Document extraction failed: {str(e)}")
            return {
                **state,
                "processing_status": "extraction_failed",
                "error_message": str(e)
            }
    
    def _content_analyzer_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to analyze document content comprehensively"""
        
        try:
            current_app.logger.info("🔍 Content Analyzer Agent processing")
            
            extracted_text = state['extracted_text']
            
            # Truncate for analysis if too long
            text_for_analysis = extracted_text[:8000] if len(extracted_text) > 8000 else extracted_text
            
            # Comprehensive AI-powered content analysis
            analysis_prompt = f"""
            You are an expert document analyzer capable of processing any type of document.
            
            Analyze this document comprehensively and provide:
            1. A detailed summary (4-6 sentences)
            2. Document type classification (e.g., contract, medical record, legal document, vet report, training manual, NDA, agreement, etc.)
            3. Key information extracted (medical, legal, business, technical, etc.)
            4. Important dates and timelines
            5. Pet information (if any - names, breeds, ages, etc.)
            6. Instructions or recommendations (if any)
            7. Urgency level assessment
            8. Key topics and themes
            9. Actionable insights
            10. Document quality assessment
            
            For ANY type of document, extract relevant information based on its content and purpose.
            If it's not pet-related, that's perfectly fine - analyze it appropriately.
            
            Document Content:
            {text_for_analysis}
            
            Please respond in valid JSON format:
            {{
                "detailed_summary": "Comprehensive summary here",
                "document_type": "Specific document type (e.g., NDA, contract, medical_record, etc.)",
                "key_information": ["Key point 1", "Key point 2"],
                "important_dates": ["Date 1 with context", "Date 2 with context"],
                "pet_information": {{"names": [], "breeds": [], "ages": [], "details": "None if not pet-related"}},
                "instructions_recommendations": ["Instruction 1", "Instruction 2"],
                "urgency_level": "low|medium|high",
                "key_topics": ["Topic 1", "Topic 2", "Topic 3"],
                "actionable_insights": ["Insight 1", "Insight 2"],
                "document_quality": "excellent|good|fair|poor",
                "confidence_score": 0.95
            }}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a professional document analyzer. Always respond with valid JSON."),
                HumanMessage(content=analysis_prompt)
            ])
            
            try:
                analysis_result = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback analysis
                analysis_result = {
                    "detailed_summary": "Document analysis completed",
                    "document_type": "general_document",
                    "key_information": [],
                    "important_dates": [],
                    "pet_information": {"names": [], "breeds": [], "ages": [], "details": "None"},
                    "instructions_recommendations": [],
                    "urgency_level": "low",
                    "key_topics": [],
                    "actionable_insights": [],
                    "document_quality": "good",
                    "confidence_score": 0.7
                }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Content Analyzer: Analyzed {analysis_result['document_type']} document")
            
            current_app.logger.info(f"✅ Content analysis completed: {analysis_result['document_type']}")
            
            return {
                **state,
                "document_summary": analysis_result['detailed_summary'],
                "document_classification": analysis_result['document_type'],
                "detailed_analysis": analysis_result,
                "processing_status": "content_analyzed",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Content analysis failed: {str(e)}")
            return {
                **state,
                "processing_status": "analysis_failed",
                "error_message": str(e)
            }
    
    def _pet_specialist_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Specialized agent for pet-specific information extraction"""
        
        try:
            current_app.logger.info("🐕 Pet Specialist Agent processing")
            
            extracted_text = state['extracted_text']
            detailed_analysis = state.get('detailed_analysis', {})
            
            # Pet-specific analysis
            pet_prompt = f"""
            You are a veterinary expert specializing in pet information extraction.
            
            Extract and analyze all pet-related information from this document:
            
            Document: {extracted_text[:4000]}
            
            Previous Analysis: {json.dumps(detailed_analysis.get('pet_information', {}), indent=2)}
            
            Provide detailed pet information in JSON format:
            {{
                "pets": [
                    {{
                        "name": "Pet name",
                        "breed": "Breed",
                        "species": "dog|cat|bird|etc",
                        "age": "Age or age range",
                        "weight": "Weight if mentioned",
                        "gender": "male|female|unknown",
                        "color": "Color/markings",
                        "medical_conditions": ["Condition 1", "Condition 2"],
                        "medications": ["Med 1", "Med 2"],
                        "vaccination_status": "up-to-date|needs-update|unknown",
                        "behavioral_notes": "Behavioral information"
                    }}
                ],
                "owner_information": {{
                    "name": "Owner name if mentioned",
                    "contact": "Contact info if mentioned",
                    "relationship": "owner|caregiver|etc"
                }},
                "veterinary_info": {{
                    "clinic_name": "Clinic name",
                    "veterinarian": "Vet name",
                    "contact": "Clinic contact"
                }},
                "key_recommendations": ["Recommendation 1", "Recommendation 2"]
            }}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a veterinary expert. Always respond with valid JSON."),
                HumanMessage(content=pet_prompt)
            ])
            
            try:
                pet_information = json.loads(response.content)
            except json.JSONDecodeError:
                pet_information = {
                    "pets": [],
                    "owner_information": {},
                    "veterinary_info": {},
                    "key_recommendations": []
                }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Pet Specialist: Identified {len(pet_information.get('pets', []))} pets")
            
            current_app.logger.info(f"✅ Pet information extracted: {len(pet_information.get('pets', []))} pets")
            
            return {
                **state,
                "pet_information": pet_information,
                "processing_status": "pet_analyzed",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Pet specialist analysis failed: {str(e)}")
            return {
                **state,
                "processing_status": "pet_analysis_failed",
                "error_message": str(e)
            }
    
    def _health_analyzer_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Specialized agent for health information analysis"""
        
        try:
            current_app.logger.info("🏥 Health Analyzer Agent processing")
            
            extracted_text = state['extracted_text']
            pet_information = state.get('pet_information', {})
            
            # Health-specific analysis
            health_prompt = f"""
            You are a veterinary health expert specializing in medical document analysis.
            
            Analyze this document for health-related information:
            
            Document: {extracted_text[:4000]}
            Pet Context: {json.dumps(pet_information, indent=2)}
            
            Extract comprehensive health information in JSON format:
            {{
                "medical_conditions": [
                    {{
                        "condition": "Condition name",
                        "severity": "mild|moderate|severe",
                        "status": "active|resolved|chronic",
                        "description": "Detailed description",
                        "treatment": "Treatment approach"
                    }}
                ],
                "medications": [
                    {{
                        "name": "Medication name",
                        "dosage": "Dosage",
                        "frequency": "How often",
                        "duration": "How long",
                        "purpose": "What it's for"
                    }}
                ],
                "procedures": [
                    {{
                        "procedure": "Procedure name",
                        "date": "Date if mentioned",
                        "outcome": "Result",
                        "notes": "Additional notes"
                    }}
                ],
                "vital_signs": {{
                    "temperature": "Temperature if mentioned",
                    "weight": "Weight",
                    "heart_rate": "Heart rate",
                    "other": "Other vitals"
                }},
                "follow_up_care": [
                    {{
                        "action": "What needs to be done",
                        "timeline": "When",
                        "importance": "high|medium|low"
                    }}
                ],
                "health_recommendations": ["Recommendation 1", "Recommendation 2"],
                "emergency_indicators": ["Emergency sign 1", "Emergency sign 2"]
            }}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a veterinary health expert. Always respond with valid JSON."),
                HumanMessage(content=health_prompt)
            ])
            
            try:
                health_information = json.loads(response.content)
            except json.JSONDecodeError:
                health_information = {
                    "medical_conditions": [],
                    "medications": [],
                    "procedures": [],
                    "vital_signs": {},
                    "follow_up_care": [],
                    "health_recommendations": [],
                    "emergency_indicators": []
                }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Health Analyzer: Found {len(health_information.get('medical_conditions', []))} conditions")
            
            current_app.logger.info(f"✅ Health information extracted: {len(health_information.get('medical_conditions', []))} conditions")
            
            return {
                **state,
                "health_information": health_information,
                "processing_status": "health_analyzed",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Health analyzer failed: {str(e)}")
            return {
                **state,
                "processing_status": "health_analysis_failed",
                "error_message": str(e)
            }
    
    def _insights_generator_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to generate actionable insights and care instructions"""
        
        try:
            current_app.logger.info("💡 Insights Generator Agent processing")
            
            detailed_analysis = state.get('detailed_analysis', {})
            pet_information = state.get('pet_information', {})
            health_information = state.get('health_information', {})
            
            # Generate comprehensive insights
            insights_prompt = f"""
            You are a veterinary consultant providing actionable insights and care instructions.
            
            Based on the following analysis, generate comprehensive insights:
            
            Document Analysis: {json.dumps(detailed_analysis, indent=2)}
            Pet Information: {json.dumps(pet_information, indent=2)}
            Health Information: {json.dumps(health_information, indent=2)}
            
            Generate insights in JSON format:
            {{
                "key_insights": [
                    "Insight 1 with specific details",
                    "Insight 2 with actionable advice",
                    "Insight 3 with timeline"
                ],
                "care_instructions": [
                    {{
                        "instruction": "Specific care instruction",
                        "frequency": "How often",
                        "importance": "high|medium|low",
                        "category": "feeding|exercise|medication|grooming|etc"
                    }}
                ],
                "recommendations": [
                    {{
                        "recommendation": "Specific recommendation",
                        "reason": "Why this is important",
                        "timeline": "When to implement",
                        "priority": "high|medium|low"
                    }}
                ],
                "alerts": [
                    {{
                        "alert": "Important alert",
                        "urgency": "immediate|urgent|monitor",
                        "action": "What to do"
                    }}
                ],
                "next_steps": [
                    "Next step 1",
                    "Next step 2"
                ]
            }}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a veterinary consultant. Always respond with valid JSON."),
                HumanMessage(content=insights_prompt)
            ])
            
            try:
                insights = json.loads(response.content)
            except json.JSONDecodeError:
                insights = {
                    "key_insights": [],
                    "care_instructions": [],
                    "recommendations": [],
                    "alerts": [],
                    "next_steps": []
                }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Insights Generator: Generated {len(insights.get('key_insights', []))} insights")
            
            current_app.logger.info(f"✅ Insights generated: {len(insights.get('key_insights', []))} insights")
            
            return {
                **state,
                "key_insights": insights.get('key_insights', []),
                "care_instructions": insights.get('care_instructions', []),
                "processing_status": "insights_generated",
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "insights": insights
                },
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Insights generation failed: {str(e)}")
            return {
                **state,
                "processing_status": "insights_failed",
                "error_message": str(e)
            }
    
    def _vector_processor_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to process and store document vectors"""
        
        try:
            current_app.logger.info("🔍 Vector Processor Agent processing")
            
            extracted_text = state['extracted_text']
            user_id = state['user_id']
            original_filename = state['original_filename']
            
            # Create enhanced metadata for vector storage
            metadata = {
                "user_id": user_id,
                "filename": original_filename,
                "document_type": state.get('document_classification', 'unknown'),
                "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                "pet_names": [pet.get('name', '') for pet in state.get('pet_information', {}).get('pets', [])],
                "health_conditions": [condition.get('condition', '') for condition in state.get('health_information', {}).get('medical_conditions', [])],
                "document_quality": state.get('detailed_analysis', {}).get('document_quality', 'good'),
                "key_topics": state.get('detailed_analysis', {}).get('key_topics', [])
            }
            
            # Enhanced text chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
            )
            
            chunks = text_splitter.split_text(extracted_text)
            
            # Store document vectors with enhanced metadata
            success = store_document_vectors(
                user_id=user_id,
                filename=original_filename,
                chunks=chunks,
                metadata=metadata
            )
            
            if success:
                workflow_trace = state.get('workflow_trace', [])
                workflow_trace.append(f"✅ Vector Processor: Stored {len(chunks)} chunks")
                
                current_app.logger.info(f"✅ Vector processing completed: {len(chunks)} chunks stored")
                
                return {
                    **state,
                    "vector_stored": True,
                    "chunks_created": len(chunks),
                    "processing_status": "vectors_stored",
                    "workflow_trace": workflow_trace
                }
            else:
                raise Exception("Failed to store document vectors")
                
        except Exception as e:
            current_app.logger.error(f"❌ Vector processing failed: {str(e)}")
            return {
                **state,
                "vector_stored": False,
                "processing_status": "vector_failed",
                "error_message": str(e)
            }
    
    def _metadata_enricher_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to enrich document metadata"""
        
        try:
            current_app.logger.info("📊 Metadata Enricher Agent processing")
            
            # Compile comprehensive metadata
            enriched_metadata = {
                "processing_summary": {
                    "status": state.get('processing_status', 'unknown'),
                    "workflow_trace": state.get('workflow_trace', []),
                    "processing_time": datetime.now(timezone.utc).isoformat()
                },
                "document_details": {
                    "type": state.get('document_classification', 'unknown'),
                    "summary": state.get('document_summary', ''),
                    "quality_assessment": state.get('detailed_analysis', {}).get('document_quality', 'good'),
                    "confidence_score": state.get('detailed_analysis', {}).get('confidence_score', 0.7)
                },
                "content_analysis": {
                    "text_length": len(state.get('extracted_text', '')),
                    "chunks_created": state.get('chunks_created', 0),
                    "key_topics": state.get('detailed_analysis', {}).get('key_topics', []),
                    "insights_count": len(state.get('key_insights', []))
                },
                "pet_data": {
                    "pets_identified": len(state.get('pet_information', {}).get('pets', [])),
                    "health_conditions": len(state.get('health_information', {}).get('medical_conditions', [])),
                    "medications": len(state.get('health_information', {}).get('medications', [])),
                    "care_instructions": len(state.get('care_instructions', []))
                },
                "storage_info": {
                    "vector_stored": state.get('vector_stored', False),
                    "s3_url": state.get('s3_url', ''),
                    "s3_key": state.get('s3_key', '')
                }
            }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("✅ Metadata Enricher: Compiled comprehensive metadata")
            
            current_app.logger.info("✅ Metadata enrichment completed")
            
            return {
                **state,
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "enriched_metadata": enriched_metadata
                },
                "processing_status": "metadata_enriched",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Metadata enrichment failed: {str(e)}")
            return {
                **state,
                "processing_status": "metadata_failed",
                "error_message": str(e)
            }
    
    def _quality_validator_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to validate processing quality and assign quality scores"""
        
        try:
            current_app.logger.info("✅ Quality Validator Agent processing")
            
            # Quality validation criteria
            quality_checks = {
                "text_extraction": len(state.get('extracted_text', '')) > 50,
                "content_analysis": bool(state.get('document_summary', '')),
                "vector_storage": state.get('vector_stored', False),
                "metadata_presence": bool(state.get('agent_notes', {})),
                "workflow_completion": 'metadata_enriched' in state.get('processing_status', ''),
                "error_free": not state.get('error_message', '')
            }
            
            # Calculate quality score
            passed_checks = sum(quality_checks.values())
            total_checks = len(quality_checks)
            quality_score = passed_checks / total_checks
            
            # Determine final status
            if quality_score >= 0.8:
                final_status = "completed"
            elif quality_score >= 0.6:
                final_status = "completed_with_warnings"
            else:
                final_status = "completed_with_errors"
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Quality Validator: Quality score {quality_score:.2f}")
            
            current_app.logger.info(f"✅ Quality validation completed: {quality_score:.2f} score")
            
            return {
                **state,
                "quality_score": quality_score,
                "processing_status": final_status,
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "quality_checks": quality_checks
                },
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Quality validation failed: {str(e)}")
            return {
                **state,
                "quality_score": 0.0,
                "processing_status": "validation_failed",
                "error_message": str(e)
            }
    
    def _storage_manager_agent(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Agent to manage final document storage and database updates"""
        
        try:
            current_app.logger.info("💾 Storage Manager Agent processing")
            
            document_id = state.get('document_id')
            
            if document_id:
                # Update existing document record
                document = Document.query.get(document_id)
                if document:
                    document.extracted_text = state.get('extracted_text', '')
                    document.content_summary = state.get('document_summary', '')
                    document.is_processed = True
                    document.processing_status = state.get('processing_status', 'completed')
                    
                    # Update metadata with all processing results
                    document.meta_data = {
                        **document.meta_data,
                        "processing_results": state.get('agent_notes', {}),
                        "quality_score": state.get('quality_score', 0.0),
                        "workflow_trace": state.get('workflow_trace', []),
                        "pet_information": state.get('pet_information', {}),
                        "health_information": state.get('health_information', {}),
                        "key_insights": state.get('key_insights', []),
                        "care_instructions": state.get('care_instructions', [])
                    }
                    
                    db.session.commit()
                    
                    workflow_trace = state.get('workflow_trace', [])
                    workflow_trace.append("✅ Storage Manager: Database updated successfully")
                    
                    current_app.logger.info(f"✅ Document {document_id} updated in database")
                    
                    return {
                        **state,
                        "processing_status": "storage_completed",
                        "workflow_trace": workflow_trace
                    }
            
            # If no document_id, this might be a direct processing call
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("✅ Storage Manager: Processing completed")
            
            return {
                **state,
                "processing_status": "storage_completed",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Storage management failed: {str(e)}")
            return {
                **state,
                "processing_status": "storage_failed",
                "error_message": str(e)
            }
    
    # Enhanced text extraction methods
    def _extract_pdf_text_enhanced(self, file_path: str) -> str:
        """Enhanced PDF text extraction using multiple methods"""
        try:
            # Try PyMuPDF first (better formatting)
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            if len(text.strip()) > 100:
                return text
            
            # Fallback to PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            
            return text
            
        except Exception as e:
            current_app.logger.error(f"PDF extraction failed: {str(e)}")
            return ""
    
    def _extract_text_file(self, file_path: str) -> str:
        """Extract text from text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            current_app.logger.error(f"Text file extraction failed: {str(e)}")
            return ""
    
    def _extract_word_document(self, file_path: str) -> str:
        """Extract text from Word documents"""
        try:
            loader = UnstructuredWordDocumentLoader(file_path)
            documents = loader.load()
            return " ".join([doc.page_content for doc in documents])
        except Exception as e:
            current_app.logger.error(f"Word document extraction failed: {str(e)}")
            return ""
    
    def _extract_csv_content(self, file_path: str) -> str:
        """Extract and format CSV content"""
        try:
            loader = CSVLoader(file_path)
            documents = loader.load()
            return " ".join([doc.page_content for doc in documents])
        except Exception as e:
            current_app.logger.error(f"CSV extraction failed: {str(e)}")
            return ""
    
    def _extract_fallback(self, file_path: str) -> str:
        """Fallback extraction method"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except Exception as e:
            current_app.logger.error(f"Fallback extraction failed: {str(e)}")
            return ""
    
    # Main processing method
    async def process_document(self, user_id: int, file_path: str, original_filename: str, 
                             document_id: Optional[int] = None) -> Dict[str, Any]:
        """Main method to process a document through the enhanced LangGraph workflow"""
        
        try:
            current_app.logger.info(f"🚀 Starting enhanced document processing for: {original_filename}")
            
            # Determine file type
            file_extension = Path(original_filename).suffix.lower()[1:]
            
            # Initial state
            initial_state = {
                "messages": [HumanMessage(content=f"Process document: {original_filename}")],
                "user_id": user_id,
                "document_id": document_id,
                "file_path": file_path,
                "file_type": file_extension,
                "original_filename": original_filename,
                "extracted_text": "",
                "document_summary": "",
                "detailed_analysis": {},
                "key_insights": [],
                "document_classification": "",
                "pet_information": {},
                "health_information": {},
                "care_instructions": [],
                "processing_status": "started",
                "processing_metrics": {
                    'start_time': datetime.now(timezone.utc).isoformat(),
                    'file_type': file_extension,
                    'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                },
                "quality_score": 0.0,
                "error_message": None,
                "s3_url": None,
                "s3_key": None,
                "vector_stored": False,
                "chunks_created": 0,
                "agent_notes": {},
                "workflow_trace": []
            }
            
            # Run the processing workflow
            config = {"thread_id": str(uuid.uuid4())}
            
            # Process through the enhanced graph
            final_state = None
            for state in self.graph.stream(initial_state, config):
                final_state = state
                current_app.logger.info(f"Processing step completed: {list(state.keys())}")
            
            if final_state:
                # Extract final processing results
                processing_result = {
                    'success': final_state.get('processing_status', '').startswith('completed') or final_state.get('processing_status') == 'storage_completed',
                    'extracted_text': final_state.get('extracted_text', ''),
                    'document_summary': final_state.get('document_summary', ''),
                    'document_classification': final_state.get('document_classification', ''),
                    'detailed_analysis': final_state.get('detailed_analysis', {}),
                    'pet_information': final_state.get('pet_information', {}),
                    'health_information': final_state.get('health_information', {}),
                    'key_insights': final_state.get('key_insights', []),
                    'care_instructions': final_state.get('care_instructions', []),
                    'processing_status': final_state.get('processing_status', 'completed'),
                    'quality_score': final_state.get('quality_score', 0.0),
                    'vector_stored': final_state.get('vector_stored', False),
                    'chunks_created': final_state.get('chunks_created', 0),
                    'workflow_trace': final_state.get('workflow_trace', []),
                    'metadata': final_state.get('agent_notes', {}),
                    'error_message': final_state.get('error_message')
                }
                
                # Update processing metrics
                processing_metrics = final_state.get('processing_metrics', {})
                processing_metrics['end_time'] = datetime.now(timezone.utc).isoformat()
                processing_metrics['total_duration'] = 'calculated'
                processing_result['processing_metrics'] = processing_metrics
                
                current_app.logger.info(f"✅ Enhanced document processing completed: {processing_result['success']}")
                
                return processing_result
            
            else:
                raise Exception("No final state received from processing workflow")
                
        except Exception as e:
            current_app.logger.error(f"❌ Enhanced document processing failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'processing_status': 'failed',
                'quality_score': 0.0
            }
    
    def upload_and_process_document(self, user_id: int, file_obj, original_filename: str) -> Dict[str, Any]:
        """Upload document to S3 and process it through the enhanced AI workflow"""
        
        try:
            current_app.logger.info(f"📤 Uploading and processing document: {original_filename}")
            
            # Save file temporarily
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{original_filename}")
            
            try:
                # Save uploaded file
                file_obj.save(temp_file_path)
                
                # Get file metadata
                file_size = os.path.getsize(temp_file_path)
                file_type = Path(original_filename).suffix.lower()[1:]
                
                # Upload to S3
                s3_key = f"documents/{user_id}/{uuid.uuid4()}_{original_filename}"
                success, message, s3_url = upload_file_to_s3(temp_file_path, s3_key)
                
                if not success:
                    raise Exception("Failed to upload document to S3")
                
                # Create document record in database
                document = Document(
                    user_id=user_id,
                    filename=f"{uuid.uuid4()}_{original_filename}",
                    original_filename=original_filename,
                    file_type=file_type,
                    file_size=file_size,
                    s3_url=s3_url,
                    s3_key=s3_key,
                    processing_status='processing',
                    meta_data={
                        'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                        'enhanced_processing': True
                    }
                )
                
                db.session.add(document)
                db.session.commit()
                
                # Process document through enhanced AI workflow
                processing_result = asyncio.run(self.process_document(
                    user_id=user_id,
                    file_path=temp_file_path,
                    original_filename=original_filename,
                    document_id=document.id
                ))
                
                # Update document record with processing results
                document.extracted_text = processing_result.get('extracted_text', '')
                document.content_summary = processing_result.get('document_summary', '')
                document.processing_status = processing_result.get('processing_status', 'completed')
                document.is_processed = processing_result.get('success', False)
                document.meta_data.update(processing_result.get('metadata', {}))
                
                db.session.commit()
                
                current_app.logger.info(f"✅ Enhanced document uploaded and processed successfully: {document.id}")
                
                return {
                    'success': True,
                    'document_id': document.id,
                    'document': document.to_dict(),
                    'processing_result': processing_result,
                    's3_url': s3_url
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            current_app.logger.error(f"❌ Enhanced document upload and processing failed: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error_message': str(e)
            } 