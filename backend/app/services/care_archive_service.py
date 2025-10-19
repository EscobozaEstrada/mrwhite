from typing import Dict, List, Optional, Tuple, Any
import os
import uuid
from datetime import datetime, timezone
from werkzeug.datastructures import FileStorage
from flask import current_app
from sqlalchemy import and_, or_, desc

from app import db
from app.models.care_record import CareRecord, Document, KnowledgeBase
from app.models.user import User
from app.services.ai_service import AIService
from app.utils.s3_handler import upload_file_to_s3, delete_file_from_s3
from app.utils.file_handler import extract_and_store, get_user_namespace
from langchain_pinecone import PineconeVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document as LangchainDocument


class CareArchiveService:
    """Service for managing user care archives and knowledge bases"""
    
    def __init__(self):
        self.ai_service = AIService()
    
    @staticmethod
    def create_care_record(user_id: int, title: str, category: str, 
                          date_occurred: datetime, description: str = None,
                          metadata: Dict = None, reminder_date: datetime = None) -> Tuple[bool, str, Optional[CareRecord]]:
        """Create a new care record"""
        try:
            care_record = CareRecord(
                user_id=user_id,
                title=title,
                category=category,
                date_occurred=date_occurred,
                description=description,
                meta_data=metadata or {},
                reminder_date=reminder_date
            )
            
            db.session.add(care_record)
            db.session.commit()
            
            # Store care record in knowledge base for semantic search
            success, message = CareArchiveService._store_care_record_in_knowledge_base(care_record)
            if not success:
                current_app.logger.warning(f"Failed to store care record in knowledge base: {message}")
            
            return True, "Care record created successfully", care_record
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating care record: {str(e)}")
            return False, f"Error creating care record: {str(e)}", None
    
    @staticmethod
    def upload_and_process_document(file: FileStorage, user_id: int, 
                                  care_record_id: int = None) -> Tuple[bool, str, Optional[Document]]:
        """Upload and process a document, linking it to a care record if provided"""
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Upload to S3
            try:
                s3_key = f"users/{user_id}/documents/{unique_filename}"
                success, message, s3_url = upload_file_to_s3(file, s3_key, file.content_type)
                
                if not success:
                    return False, "Failed to upload file to S3", None
            except Exception as e:
                return False, f"S3 upload error: {str(e)}", None
            
            # Create document record
            document = Document(
                user_id=user_id,
                care_record_id=care_record_id,
                filename=unique_filename,
                original_filename=file.filename,
                file_type=CareArchiveService._get_file_type(file.filename),
                file_size=len(file.read()),
                s3_url=s3_url,
                s3_key=s3_key,
                processing_status='pending'
            )
            
            # Reset file pointer
            file.seek(0)
            
            db.session.add(document)
            db.session.commit()
            
            # Process document asynchronously (in a real implementation, use Celery or similar)
            success, message = CareArchiveService._process_document_content(document, file)
            
            return True, "Document uploaded successfully", document
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error uploading document: {str(e)}")
            return False, f"Error uploading document: {str(e)}", None
    
    @staticmethod
    def _process_document_content(document: Document, file: FileStorage) -> Tuple[bool, str]:
        """Process document content and add to knowledge base"""
        try:
            document.processing_status = 'processing'
            db.session.commit()
            
            # Extract text and create embeddings
            if document.file_type in ['pdf', 'txt', 'doc', 'docx']:
                success, message, s3_url = extract_and_store(file, document.user_id)
                
                if success:
                    # Generate content summary using AI
                    summary = CareArchiveService._generate_content_summary(file, document)
                    
                    document.content_summary = summary
                    document.is_processed = True
                    document.processing_status = 'completed'
                    
                    # Update knowledge base statistics
                    CareArchiveService._update_knowledge_base_stats(document.user_id)
                else:
                    document.processing_status = 'failed'
                    current_app.logger.error(f"Failed to process document {document.id}: {message}")
            
            db.session.commit()
            return True, "Document processed successfully"
            
        except Exception as e:
            document.processing_status = 'failed'
            db.session.commit()
            current_app.logger.error(f"Error processing document content: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def _generate_content_summary(file: FileStorage, document: Document) -> str:
        """Generate AI summary of document content"""
        try:
            # This is a simplified version - in production, you'd want more sophisticated text extraction
            file_content = ""
            if document.file_type == 'txt':
                file_content = file.read().decode('utf-8')
            
            if file_content:
                ai_service = AIService()
                prompt = f"""
                Please provide a concise summary of this document content, focusing on:
                1. Key medical/care information
                2. Important dates and events
                3. Any action items or reminders
                
                Content: {file_content[:2000]}...
                """
                
                summary = ai_service.generate_response(prompt)
                return summary[:500]  # Limit summary length
            
            return "Content summary not available"
            
        except Exception as e:
            current_app.logger.error(f"Error generating content summary: {str(e)}")
            return "Summary generation failed"
    
    @staticmethod
    def _get_file_type(filename: str) -> str:
        """Determine file type from filename"""
        extension = os.path.splitext(filename)[1].lower()
        
        if extension in ['.pdf']:
            return 'pdf'
        elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return 'image'
        elif extension in ['.txt']:
            return 'txt'
        elif extension in ['.doc', '.docx']:
            return 'doc'
        else:
            return 'other'
    
    @staticmethod
    def _update_knowledge_base_stats(user_id: int):
        """Update knowledge base statistics"""
        try:
            kb = KnowledgeBase.query.filter_by(user_id=user_id).first()
            
            if not kb:
                # Create knowledge base entry if it doesn't exist
                namespace = get_user_namespace(user_id)
                kb = KnowledgeBase(
                    user_id=user_id,
                    pinecone_namespace=namespace,
                    vector_count=0
                )
                db.session.add(kb)
            
            # Update statistics
            kb.vector_count = Document.query.filter_by(user_id=user_id, is_processed=True).count()
            kb.last_updated = datetime.now(timezone.utc)
            
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error updating knowledge base stats: {str(e)}")
    
    @staticmethod
    def get_user_care_timeline(user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's care timeline with records and documents"""
        try:
            care_records = (CareRecord.query
                          .filter_by(user_id=user_id, is_active=True)
                          .order_by(desc(CareRecord.date_occurred))
                          .limit(limit)
                          .all())
            
            timeline = []
            for record in care_records:
                timeline.append({
                    'type': 'care_record',
                    'data': record.to_dict(),
                    'date': record.date_occurred
                })
            
            # Add standalone documents
            standalone_docs = (Document.query
                             .filter_by(user_id=user_id, care_record_id=None)
                             .order_by(desc(Document.created_at))
                             .limit(limit // 2)
                             .all())
            
            for doc in standalone_docs:
                timeline.append({
                    'type': 'document',
                    'data': doc.to_dict(),
                    'date': doc.created_at
                })
            
            # Sort timeline by date
            timeline.sort(key=lambda x: x['date'], reverse=True)
            
            return timeline[:limit]
            
        except Exception as e:
            current_app.logger.error(f"Error getting care timeline: {str(e)}")
            return []
    
    @staticmethod
    def get_care_records_by_category(user_id: int, category: str) -> List[CareRecord]:
        """Get care records filtered by category"""
        try:
            return (CareRecord.query
                   .filter_by(user_id=user_id, category=category, is_active=True)
                   .order_by(desc(CareRecord.date_occurred))
                   .all())
        except Exception as e:
            current_app.logger.error(f"Error getting care records by category: {str(e)}")
            return []
    
    @staticmethod
    def search_user_archive(user_id: int, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search user's archive using AI, vector similarity, and common knowledge base"""
        try:
            ai_service = AIService()
            
            # Step 1: Search common knowledge base for general information
            common_knowledge_results = []
            try:
                from app.services.common_knowledge_service import get_common_knowledge_service
                common_knowledge_service = get_common_knowledge_service()
                
                if common_knowledge_service.is_service_available():
                    current_app.logger.info("Searching common knowledge base for general information")
                    success, ck_results = common_knowledge_service.search_common_knowledge(
                        query, top_k=3, min_relevance_score=0.6
                    )
                    
                    if success and ck_results:
                        common_knowledge_results = ck_results
                        current_app.logger.info(f"Found {len(ck_results)} relevant results from common knowledge base")
            except Exception as e:
                current_app.logger.warning(f"Error searching common knowledge base: {str(e)}")
            
            # Step 2: Search in vector database (documents)
            success, doc_results = ai_service.search_user_documents(query, user_id, top_k=limit)
            
            # Step 3: Enhanced semantic search including care records from knowledge base
            semantic_care_records = CareArchiveService._search_care_records_semantic(user_id, query, limit)
            
            # Step 4: Search in care records (text-based fallback)
            care_results = (CareRecord.query
                           .filter(
                               and_(
                                   CareRecord.user_id == user_id,
                                   CareRecord.is_active == True,
                                   or_(
                                       CareRecord.title.ilike(f'%{query}%'),
                                       CareRecord.description.ilike(f'%{query}%')
                                   )
                               )
                           )
                           .order_by(desc(CareRecord.date_occurred))
                           .limit(limit)
                           .all())
            
            # Combine semantic and text-based results, removing duplicates
            all_care_records = semantic_care_records.copy()
            existing_ids = {record.get('id') for record in semantic_care_records}
            
            for record in care_results:
                if record.id not in existing_ids:
                    all_care_records.append(record.to_dict())
            
            # Handle document search results
            documents = doc_results if success else []
            
            # Return enhanced results with common knowledge
            return {
                'documents': documents,
                'care_records': all_care_records[:limit],  # Limit final results
                'common_knowledge': common_knowledge_results,
                'total_found': len(documents) + len(all_care_records) + len(common_knowledge_results),
                'common_knowledge_available': bool(common_knowledge_results)
            }
        except Exception as e:
            current_app.logger.error(f"Error searching user archive: {str(e)}")
            return {
                'documents': [],
                'care_records': [],
                'common_knowledge': [],
                'total_found': 0,
                'common_knowledge_available': False
            }
    
    @staticmethod
    def search_care_records(user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search care records for a user with a semantic query"""
        try:
            # First try semantic search if available
            try:
                results = CareArchiveService._search_care_records_semantic(user_id, query, limit)
                if results:
                    return results
            except Exception as e:
                current_app.logger.warning(f"Semantic search failed, falling back to basic search: {str(e)}")
            
            # Fall back to basic keyword search
            care_records = CareRecord.query.filter(
                CareRecord.user_id == user_id,
                or_(
                    CareRecord.title.ilike(f"%{query}%"),
                    CareRecord.description.ilike(f"%{query}%")
                )
            ).order_by(desc(CareRecord.date_occurred)).limit(limit).all()
            
            # Format results
            results = []
            for record in care_records:
                results.append({
                    'id': record.id,
                    'title': record.title,
                    'category': record.category,
                    'date_occurred': record.date_occurred.isoformat() if record.date_occurred else None,
                    'content': record.description or "",
                    'metadata': record.meta_data
                })
                
            return results
            
        except Exception as e:
            current_app.logger.error(f"Error searching care records: {str(e)}")
            return []
    
    @staticmethod
    def _search_care_records_semantic(user_id: int, query: str, limit: int = 5) -> List[Dict]:
        """Search care records using semantic similarity in Pinecone"""
        try:
            from app.utils.file_handler import get_user_namespace
            from langchain_pinecone import PineconeVectorStore
            from langchain_openai.embeddings import OpenAIEmbeddings
            import os
            
            embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
            namespace = get_user_namespace(user_id)
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            if not index_name:
                return []
            
            # Search for care records in knowledge base
            vectorstore = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Search with filter for care records only
            docs = vectorstore.similarity_search(
                query,
                k=limit,
                filter={"record_type": "care_record"}
            )
            
            # Convert back to care record format
            care_records = []
            for doc in docs:
                metadata = doc.metadata
                record_id = metadata.get('record_id')
                
                if record_id:
                    # Fetch full record from database
                    care_record = CareRecord.query.filter_by(
                        id=int(record_id),
                        user_id=user_id,
                        is_active=True
                    ).first()
                    
                    if care_record:
                        care_records.append(care_record.to_dict())
            
            return care_records
            
        except Exception as e:
            current_app.logger.error(f"Error in semantic care record search: {str(e)}")
            return []
    
    @staticmethod
    def get_upcoming_reminders(user_id: int, days_ahead: int = 30) -> List[CareRecord]:
        """Get upcoming care reminders"""
        try:
            cutoff_date = datetime.now(timezone.utc) + timezone.timedelta(days=days_ahead)
            
            return (CareRecord.query
                   .filter(
                       and_(
                           CareRecord.user_id == user_id,
                           CareRecord.is_active == True,
                           CareRecord.reminder_date <= cutoff_date,
                           CareRecord.reminder_date >= datetime.now(timezone.utc)
                       )
                   )
                   .order_by(CareRecord.reminder_date)
                   .all())
                   
        except Exception as e:
            current_app.logger.error(f"Error getting upcoming reminders: {str(e)}")
            return []
    
    @staticmethod
    def delete_document(user_id: int, document_id: int) -> Tuple[bool, str]:
        """Delete a document and its associated data"""
        try:
            document = Document.query.filter_by(id=document_id, user_id=user_id).first()
            
            if not document:
                return False, "Document not found"
            
            # Delete from S3
            try:
                delete_file_from_s3(document.s3_key)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete S3 file: {str(e)}")
            
            # Delete from database
            db.session.delete(document)
            db.session.commit()
            
            # Update knowledge base stats
            CareArchiveService._update_knowledge_base_stats(user_id)
            
            return True, "Document deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting document: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def get_document(document_id: int) -> Optional[Document]:
        """Get a document by ID"""
        try:
            document = Document.query.get(document_id)
            return document
        except Exception as e:
            current_app.logger.error(f"Error getting document: {str(e)}")
            return None
    
    @staticmethod
    def get_knowledge_base_stats(user_id: int) -> Dict[str, Any]:
        """Get knowledge base statistics for user"""
        try:
            kb = KnowledgeBase.query.filter_by(user_id=user_id).first()
            
            if not kb:
                return {
                    'total_documents': 0,
                    'total_care_records': 0,
                    'processed_documents': 0,
                    'last_updated': None,
                    'categories': {}
                }
            
            # Get detailed statistics
            total_docs = Document.query.filter_by(user_id=user_id).count()
            processed_docs = Document.query.filter_by(user_id=user_id, is_processed=True).count()
            total_care_records = CareRecord.query.filter_by(user_id=user_id, is_active=True).count()
            
            # Get category breakdown
            category_counts = db.session.query(
                CareRecord.category,
                db.func.count(CareRecord.id)
            ).filter_by(user_id=user_id, is_active=True).group_by(CareRecord.category).all()
            
            categories = {category: count for category, count in category_counts}
            
            return {
                'total_documents': total_docs,
                'total_care_records': total_care_records,
                'processed_documents': processed_docs,
                'last_updated': kb.last_updated.isoformat() if kb.last_updated else None,
                'categories': categories
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting knowledge base stats: {str(e)}")
            return {} 
    
    @staticmethod
    def _store_care_record_in_knowledge_base(care_record: CareRecord) -> Tuple[bool, str]:
        """Store care record content in Pinecone for semantic search"""
        try:
            # Create rich content for embedding
            content_parts = [
                f"Title: {care_record.title}",
                f"Category: {care_record.category}",
                f"Date: {care_record.date_occurred.strftime('%Y-%m-%d')}"
            ]
            
            if care_record.description:
                content_parts.append(f"Description: {care_record.description}")
            
            if care_record.meta_data:
                metadata_text = ", ".join([f"{k}: {v}" for k, v in care_record.meta_data.items() if v])
                if metadata_text:
                    content_parts.append(f"Additional Info: {metadata_text}")
            
            content = "\n".join(content_parts)
            
            # Create document for embedding
            doc = LangchainDocument(
                page_content=content,
                metadata={
                    "source": f"care_record_{care_record.id}",
                    "record_id": str(care_record.id),
                    "category": care_record.category,
                    "date_occurred": care_record.date_occurred.isoformat(),
                    "user_id": str(care_record.user_id),
                    "record_type": "care_record",
                    "health_category": CareArchiveService._map_to_health_category(care_record.category),
                    "content_type": "structured_record",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Store in Pinecone
            embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
            namespace = get_user_namespace(care_record.user_id)
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            vectorstore = PineconeVectorStore.from_documents(
                documents=[doc],
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            
            current_app.logger.info(f"Successfully stored care record {care_record.id} in knowledge base")
            return True, "Care record stored in knowledge base successfully"
            
        except Exception as e:
            current_app.logger.error(f"Error storing care record in knowledge base: {str(e)}")
            return False, f"Error storing care record: {str(e)}"
    
    @staticmethod
    def _map_to_health_category(category: str) -> str:
        """Map care record category to health categories for better retrieval"""
        health_mapping = {
            'vaccination': 'vaccination',
            'vet_visit': 'vet_visits',
            'medication': 'medication',
            'diet': 'nutrition',
            'exercise': 'general_care',
            'behavior': 'behavior',
            'grooming': 'general_care',
            'training': 'behavior',
            'milestone': 'general_care'
        }
        return health_mapping.get(category, 'general_care')

    @staticmethod
    def backfill_care_records_to_knowledge_base(user_id: int = None) -> Tuple[bool, str, Dict[str, int]]:
        """Backfill existing care records to knowledge base"""
        try:
            stats = {"total_processed": 0, "successful": 0, "failed": 0, "skipped": 0}
            
            # Get care records to process
            query = CareRecord.query.filter_by(is_active=True)
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            care_records = query.all()
            
            current_app.logger.info(f"Starting backfill for {len(care_records)} care records")
            
            for record in care_records:
                stats["total_processed"] += 1
                
                try:
                    # Check if already exists in knowledge base
                    if CareArchiveService._care_record_exists_in_knowledge_base(record):
                        stats["skipped"] += 1
                        continue
                    
                    # Store in knowledge base
                    success, message = CareArchiveService._store_care_record_in_knowledge_base(record)
                    
                    if success:
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1
                        current_app.logger.warning(f"Failed to store record {record.id}: {message}")
                        
                except Exception as e:
                    stats["failed"] += 1
                    current_app.logger.error(f"Error processing record {record.id}: {str(e)}")
            
            message = f"Backfill completed: {stats['successful']} successful, {stats['failed']} failed, {stats['skipped']} skipped"
            current_app.logger.info(message)
            
            return True, message, stats
            
        except Exception as e:
            current_app.logger.error(f"Error in backfill process: {str(e)}")
            return False, f"Backfill failed: {str(e)}", {"total_processed": 0, "successful": 0, "failed": 0, "skipped": 0}

    @staticmethod
    def _care_record_exists_in_knowledge_base(care_record: CareRecord) -> bool:
        """Check if care record already exists in knowledge base"""
        try:
            from app.utils.file_handler import get_user_namespace
            from langchain_pinecone import PineconeVectorStore
            from langchain_openai.embeddings import OpenAIEmbeddings
            import os
            
            embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
            namespace = get_user_namespace(care_record.user_id)
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            if not index_name:
                return False
            
            vectorstore = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Search for existing record
            docs = vectorstore.similarity_search(
                care_record.title,
                k=1,
                filter={
                    "record_type": "care_record",
                    "record_id": str(care_record.id)
                }
            )
            
            return len(docs) > 0
            
        except Exception as e:
            current_app.logger.error(f"Error checking if care record exists in knowledge base: {str(e)}")
            return False 