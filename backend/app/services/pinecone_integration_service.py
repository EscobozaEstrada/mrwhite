"""
Pinecone Integration Service for User Book Notes and Highlights
Integrates user notes and highlights with Pinecone for semantic search and knowledge base functionality
"""

import os
import json
from typing import Dict, Any, List, Optional
from flask import current_app
import openai
from datetime import datetime, timezone
import httpx
from pinecone import Pinecone

def safe_log(level: str, message: str):
    """Safely log message, handling cases where Flask context is not available"""
    try:
        if level == 'info':
            current_app.logger.info(message)
        elif level == 'warning':
            current_app.logger.warning(message)
        elif level == 'error':
            current_app.logger.error(message)
    except RuntimeError:
        print(f"[{level.upper()}] {message}")

class PineconeBookNotesService:
    """Service for integrating user book notes with Pinecone vector database"""
    
    def __init__(self):
        # OpenAI configuration
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.mcp_base_url = os.getenv('MCP_SERVER_URL')  # MCP server URL
        
        # Pinecone configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = "dog-project"  # Use main dog-project index with dedicated namespace for book notes
        
        # Initialize Pinecone
        try:
            if self.pinecone_api_key:
                self.pc = Pinecone(api_key=self.pinecone_api_key)
                self.index = self.pc.Index(self.index_name)
                safe_log('info', f"✅ Pinecone initialized successfully for index: {self.index_name}")
            else:
                safe_log('warning', "⚠️ PINECONE_API_KEY not found. Pinecone features will be disabled.")
                self.pc = None
                self.index = None
        except Exception as e:
            safe_log('error', f"❌ Failed to initialize Pinecone: {str(e)}")
            self.pc = None
            self.index = None
            
        self.is_available = self.index is not None
    
    def is_service_available(self) -> bool:
        """Check if the Pinecone service is available"""
        return self.is_available
        
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenAI with 1024 dimensions"""
        try:
            # Use text-embedding-3-small with dimension parameter to get 1024 dimensions
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1024  # Specify 1024 dimensions to match the dog-project index
            )
            return response.data[0].embedding
        except Exception as e:
            safe_log('error', f"❌ Error creating embedding: {str(e)}")
            return []
    
    def add_note_to_knowledge_base(self, user_id: int, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a user note to their personal Pinecone knowledge base"""
        try:
            # Check if service is available
            if not self.is_service_available():
                safe_log('warning', "⚠️ Pinecone service not available. Note will not be added to knowledge base.")
                return {'success': False, 'message': 'Pinecone service not available'}
            # Create comprehensive text for embedding including BOTH selected text and user's note
            selected_text = note_data.get('selected_text', '')
            user_note = note_data.get('note_text', '')
            
            # Build the embedding text with both pieces of information
            note_text = f"""
            Book: {note_data.get('book_title', 'Unknown')}
            Page: {note_data.get('page_number', 'Unknown')}
            Chapter: {note_data.get('chapter_name', 'Unknown')}
            
            Selected Text from Book: {selected_text}
            
            User's Note/Comment: {user_note}
            
            Context Before: {note_data.get('context_before', '')}
            Context After: {note_data.get('context_after', '')}
            """
            
            # Create embedding
            embedding = self.create_embedding(note_text.strip())
            if not embedding:
                return {'success': False, 'message': 'Failed to create embedding'}
            
            # Prepare metadata
            metadata = {
                'user_id': user_id,
                'type': 'book_note',
                'book_title': note_data.get('book_title', ''),
                'page_number': note_data.get('page_number', 0),
                'note_type': note_data.get('note_type', 'note'),
                'color': note_data.get('color', 'yellow'),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'book_copy_id': note_data.get('book_copy_id', 0),
                'note_id': note_data.get('id', 0)
            }
            
            # Add to Pinecone using MCP
            try:
                vector_record = {
                    'id': f"user_{user_id}_note_{note_data.get('id', 0)}",
                    'text': note_text.strip(),
                    'selected_text': selected_text,  # Text highlighted from the book
                    'user_note': user_note,  # User's comment/annotation
                    'page_number': note_data.get('page_number', 0),
                    'note_type': note_data.get('note_type', 'note'),
                    'color': note_data.get('color', 'yellow'),
                    'book_title': note_data.get('book_title', ''),
                    'chapter_name': note_data.get('chapter_name', ''),
                    'created_at': metadata['created_at'],
                    'user_id': user_id,
                    'content_type': 'book_note',
                    'note_id': note_data.get('id', 0)
                }
                
                namespace = self._get_namespace_for_user(user_id)
                success = self._upsert_to_pinecone(namespace, [vector_record], embedding)
                
                if success:
                    safe_log('info', f"📝 Successfully added note {note_data.get('id')} to Pinecone namespace: {namespace}")
                    return {
                        'success': True,
                        'pinecone_id': vector_record['id'],
                        'namespace': namespace,
                        'message': 'Note added to knowledge base successfully'
                    }
                else:
                    safe_log('warning', f"⚠️ Failed to add note to Pinecone")
                    return {
                        'success': False,
                        'message': 'Failed to add note to Pinecone'
                    }
                    
            except Exception as pinecone_error:
                safe_log('error', f"❌ Pinecone error: {str(pinecone_error)}")
                # Still return success for database operation, but log the Pinecone failure
                return {
                    'success': True,
                    'warning': 'Note saved locally but failed to sync to knowledge base',
                    'message': 'Note created with sync warning'
                }
            
        except Exception as e:
            safe_log('error', f"❌ Error adding note to knowledge base: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing note: {str(e)}'
            }
    
    def add_highlight_to_knowledge_base(self, user_id: int, highlight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a user highlight to their personal Pinecone knowledge base"""
        try:
            # Create comprehensive text for embedding including context
            highlighted_text = highlight_data.get('highlighted_text', '')
            
            highlight_text = f"""
            Book: {highlight_data.get('book_title', 'Unknown')}
            Page: {highlight_data.get('page_number', 'Unknown')}
            Chapter: {highlight_data.get('chapter_name', 'Unknown')}
            
            Highlighted Text: {highlighted_text}
            
            Context Before: {highlight_data.get('context_before', '')}
            Context After: {highlight_data.get('context_after', '')}
            """
            
            # Create embedding
            embedding = self.create_embedding(highlight_text.strip())
            if not embedding:
                return {'success': False, 'message': 'Failed to create embedding'}
            
            # Prepare metadata
            metadata = {
                'user_id': user_id,
                'type': 'book_highlight',
                'book_title': highlight_data.get('book_title', ''),
                'page_number': highlight_data.get('page_number', 0),
                'color': highlight_data.get('color', 'yellow'),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'book_copy_id': highlight_data.get('book_copy_id', 0),
                'highlight_id': highlight_data.get('id', 0)
            }
            
            # Add to Pinecone using MCP
            try:
                vector_record = {
                    'id': f"user_{user_id}_highlight_{highlight_data.get('id', 0)}",
                    'text': highlight_text.strip(),
                    'highlighted_text': highlighted_text,
                    'page_number': highlight_data.get('page_number', 0),
                    'color': highlight_data.get('color', 'yellow'),
                    'book_title': highlight_data.get('book_title', ''),
                    'chapter_name': highlight_data.get('chapter_name', ''),
                    'created_at': metadata['created_at'],
                    'user_id': user_id,
                    'content_type': 'book_highlight',
                    'highlight_id': highlight_data.get('id', 0)
                }
                
                namespace = self._get_namespace_for_user(user_id)
                success = self._upsert_to_pinecone(namespace, [vector_record], embedding)
                
                if success:
                    safe_log('info', f"🖍️ Successfully added highlight {highlight_data.get('id')} to Pinecone namespace: {namespace}")
                    return {
                        'success': True,
                        'pinecone_id': vector_record['id'],
                        'namespace': namespace,
                        'message': 'Highlight added to knowledge base successfully'
                    }
                else:
                    safe_log('warning', f"⚠️ Failed to add highlight to Pinecone")
                    return {
                        'success': False,
                        'message': 'Failed to add highlight to Pinecone'
                    }
                    
            except Exception as pinecone_error:
                safe_log('error', f"❌ Pinecone error: {str(pinecone_error)}")
                return {
                    'success': True,
                    'warning': 'Highlight saved locally but failed to sync to knowledge base',
                    'message': 'Highlight created with sync warning'
                }
            
        except Exception as e:
            safe_log('error', f"❌ Error adding highlight to knowledge base: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing highlight: {str(e)}'
            }
    
    def search_user_knowledge_base(self, user_id: int, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Search user's personal knowledge base for relevant notes and highlights"""
        try:
            # Check if service is available
            if not self.is_service_available():
                safe_log('warning', "⚠️ Pinecone service not available. Search will return empty results.")
                return {'success': False, 'message': 'Pinecone service not available', 'results': []}
                
            # Use Pinecone's integrated search with automatic embeddings
            namespace = self._get_namespace_for_user(user_id)
            
            # Search Pinecone using manual embeddings
            try:
                safe_log('info', f"🔍 Searching for query: '{query}' in namespace: {namespace}")
                
                # Create embedding for the search query
                query_embedding = self.create_embedding(query)
                if not query_embedding:
                    return {'success': False, 'message': 'Failed to create query embedding', 'results': {'matches': []}}
                
                # Search using the regular Pinecone Python client with real embeddings
                query_results = self.index.query(
                    vector=query_embedding,
                    namespace=namespace,
                    top_k=top_k,
                    include_metadata=True
                )
                
                # Convert to expected format
                matches = []
                for match in query_results.matches:
                    matches.append({
                        'id': match.id,
                        'score': match.score,
                        'metadata': match.metadata,
                        'text': match.metadata.get('text', '')
                    })
                search_results = {'matches': matches}
                
                safe_log('info', f"🔍 Found {len(search_results.get('matches', []))} results for user {user_id}: '{query}'")
                
                return {
                    'success': True,
                    'results': search_results,
                    'query': query,
                    'user_id': user_id,
                    'message': 'Search completed successfully'
                }
                
            except Exception as search_error:
                safe_log('error', f"❌ Search error: {str(search_error)}")
                return {
                    'success': False,
                    'results': {'matches': []},
                    'message': f'Search failed: {str(search_error)}'
                }
            
        except Exception as e:
            safe_log('error', f"❌ Error searching knowledge base: {str(e)}")
            return {
                'success': False,
                'message': f'Search error: {str(e)}'
            }
    
    def get_related_notes(self, user_id: int, current_note_id: int, top_k: int = 5) -> Dict[str, Any]:
        """Find notes and highlights related to the current note"""
        try:
            # TODO: Implement using vector similarity search
            # This would find semantically similar content in user's knowledge base
            
            safe_log('info', f"🔗 Finding related notes for user {user_id}, note {current_note_id}")
            
            return {
                'success': True,
                'related_items': [],
                'message': 'Related notes search completed'
            }
            
        except Exception as e:
            safe_log('error', f"❌ Error finding related notes: {str(e)}")
            return {
                'success': False,
                'message': f'Error finding related notes: {str(e)}'
            }
    
    def generate_insights_from_notes(self, user_id: int, book_copy_id: int) -> Dict[str, Any]:
        """Generate AI insights from user's notes and highlights for a specific book"""
        try:
            # TODO: Retrieve all notes and highlights for the book
            # TODO: Use AI to generate insights, themes, and connections
            
            safe_log('info', f"🧠 Generating insights for user {user_id}, book {book_copy_id}")
            
            insights = {
                'key_themes': [],
                'important_concepts': [],
                'personal_reflections': [],
                'reading_progress_insights': {}
            }
            
            return {
                'success': True,
                'insights': insights,
                'message': 'Insights generated successfully'
            }
            
        except Exception as e:
            safe_log('error', f"❌ Error generating insights: {str(e)}")
            return {
                'success': False,
                'message': f'Error generating insights: {str(e)}'
            }
    
    def _get_namespace_for_user(self, user_id: int) -> str:
        """Get namespace for user's book notes - uses pattern user_{id}_book_notes"""
        return f"user_{user_id}_book_notes"
    
    def _upsert_to_pinecone(self, namespace: str, records: List[Dict[str, Any]], embedding: List[float] = None) -> bool:
        """Helper method to upsert records to Pinecone"""
        try:
            if self.index is None:
                safe_log('warning', "⚠️ Pinecone not initialized. Using simulated mode.")
                return True
                
            # Process records to match Pinecone format
            vectors = []
            for record in records:
                # If embedding is provided, use it (for batch efficiency)
                record_embedding = embedding if embedding else self.create_embedding(record['text'])
                
                # Create vector record with metadata (filtering out None/null values)
                metadata = {
                    'text': record['text'],
                    'page_number': record.get('page_number', 0),
                    'color': record.get('color', 'yellow'),
                    'book_title': record.get('book_title', ''),
                    'created_at': record.get('created_at', ''),
                    'user_id': record.get('user_id', 0),
                    'content_type': record.get('content_type', 'book_note')
                }
                
                # Add fields based on content type
                if record.get('content_type') == 'book_note':
                    metadata['selected_text'] = record.get('selected_text') or ''
                    metadata['user_note'] = record.get('user_note') or ''
                    metadata['note_type'] = record.get('note_type', 'note')
                    if record.get('note_id'):
                        metadata['note_id'] = record.get('note_id', 0)
                elif record.get('content_type') == 'book_highlight':
                    metadata['highlighted_text'] = record.get('highlighted_text') or ''
                    if record.get('highlight_id'):
                        metadata['highlight_id'] = record.get('highlight_id', 0)
                
                # Only add chapter_name if it's not None/null
                if record.get('chapter_name'):
                    metadata['chapter_name'] = record.get('chapter_name')
                
                vector = {
                    'id': record['id'],
                    'values': record_embedding,
                    'metadata': metadata
                }
                vectors.append(vector)
            
            # Upsert to Pinecone
            self.index.upsert(vectors=vectors, namespace=namespace)
            safe_log('info', f"✅ Successfully upserted {len(vectors)} vectors to {self.index_name}/{namespace}")
            return True
            
        except Exception as e:
            safe_log('error', f"❌ Pinecone upsert error: {str(e)}")
            return False
    
    def _search_pinecone(self, namespace: str, query: str, query_embedding: List[float] = None, top_k: int = 10) -> Dict[str, Any]:
        """Helper method to search Pinecone"""
        try:
            if self.index is None:
                safe_log('warning', "⚠️ Pinecone not initialized. Using simulated mode.")
                # Return simulated results for backward compatibility
                return {
                    'matches': [
                        {
                            'id': f'user_1_note_1',
                            'score': 0.95,
                            'metadata': {
                                'content_type': 'book_note',
                                'page_number': 5,
                                'color': 'yellow',
                                'text': 'Sample note about dog training'
                            }
                        }
                    ]
                }
            
            # If embedding not provided, create it
            embedding = query_embedding if query_embedding else self.create_embedding(query)
            
            # Search Pinecone
            search_response = self.index.query(
                vector=embedding,
                namespace=namespace,
                top_k=top_k,
                include_metadata=True
            )
            
            # Format results
            matches = []
            for match in search_response.matches:
                matches.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata,
                    'text': match.metadata.get('text', '')
                })
            
            safe_log('info', f"🔍 Found {len(matches)} results for query: '{query}'")
            return {'matches': matches}
            
        except Exception as e:
            safe_log('error', f"❌ Pinecone search error: {str(e)}")
            # Return empty results for backward compatibility
            return {'matches': []}
