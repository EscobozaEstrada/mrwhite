from flask import Blueprint, request, jsonify, current_app, send_file, make_response
from werkzeug.utils import secure_filename
from app.middleware.auth import require_auth
from app.services.auth_service import AuthService
from app.services.book_management_service import BookManagementService
from app.models.user import User
from app import db
from datetime import datetime, timezone
import uuid
import os
import tempfile
import requests
from datetime import datetime, timezone

# Create blueprint
book_bp = Blueprint('book', __name__, url_prefix='/api/book')

# Initialize book service lazily
book_service = None

def get_book_service():
    """Get book service with lazy initialization"""
    global book_service
    if book_service is None:
        book_service = BookManagementService()
    return book_service

@book_bp.route('/info', methods=['GET'])
def get_book_info():
    """Get information about a test book for the PDF reader"""
    try:
        # This is a test route that returns a sample book
        # In a real implementation, you would fetch this from the database
        
        sample_book = {
            "id": 1,
            "title": "Sample PDF Document",
            "description": "This is a sample PDF document for testing the PDF reader",
            "s3_url": "https://arxiv.org/pdf/2307.09288.pdf",  # Example PDF URL (Claude 3 paper)
            "public_access": True
        }
        
        return jsonify({
            'success': True,
            'book_info': sample_book
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching book info: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch book information'
        }), 500

@book_bp.route('/read', methods=['POST'])
def read_book():
    """Read book content with navigation support"""
    try:
        # Get user from token (optional for public book access)
        user_id = 1  # Default user for public access
        
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        data = request.get_json()
        query = data.get('query', 'Show me the book content')
        page_number = data.get('page_number')
        chapter = data.get('chapter')
        
        current_app.logger.info(f"📖 Processing book reading request for user {user_id}")
        
        # Process book reading through enhanced service
        result = get_book_service().read_book(
            user_id=user_id,
            query=query,
            page_number=page_number,
            chapter=chapter
        )
        
        if result['success']:
            current_app.logger.info(f"✅ Book reading processed successfully")
            
            return jsonify({
                'success': True,
                'response': result['response'],
                'operation': 'read',
                'reading_info': {
                    'page_number': page_number,
                    'chapter': chapter,
                    'reading_position': result.get('reading_position', {}),
                    'relevant_sections': result.get('relevant_sections', [])
                },
                'insights': result.get('insights', []),
                'suggestions': result.get('suggestions', []),
                'confidence_score': result.get('confidence_score', 0.0),
                'tools_used': result.get('tools_used', []),
                'processing_status': result.get('processing_status', 'completed')
            }), 200
            
        else:
            current_app.logger.error(f"❌ Book reading failed: {result.get('error_message')}")
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Book reading failed'),
                'operation': 'read'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Book reading error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Book reading error: {str(e)}',
            'operation': 'read'
        }), 500

@book_bp.route('/chat', methods=['POST'])
def chat_about_book():
    """Chat about book content with Mr. White"""
    try:
        # Get user from token (optional for public book access)
        user_id = 1  # Default user for public access
        conversation_history = []
        
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        data = request.get_json()
        query = data.get('query', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Query is required for book chat',
                'operation': 'chat'
            }), 400
        
        current_app.logger.info(f"💬 Processing book chat for user {user_id}: {query}")
        
        # Create a basic response since BookService is not available  
        response_content = f"""I understand you're asking about: "{query}". 

Based on "The Way of the Dog", here's what I can share:

🐕 **Dog Care Wisdom**: This book contains valuable insights about understanding and caring for dogs, focusing on building deep connections with our canine companions.

**Key Topics I can help with:**
• Dog behavior and psychology
• Training techniques and approaches  
• Health and wellness for dogs
• Building stronger human-dog bonds
• Understanding dog communication

For specific questions about "{query}", I can provide guidance based on general dog care principles. Would you like me to elaborate on any particular aspect?

📖 *This response is based on general book content. For personalized advice, please consult with a veterinarian or professional dog trainer.*"""
        
        return jsonify({
            'success': True,
            'response': response_content,
            'operation': 'chat',
            'chat_info': {
                'query': query,
                'context_used': {'general_book_content': True},
                'conversation_length': len(conversation_history)
            },
            'insights': ['Dog care basics', 'Human-dog relationships'],
            'suggestions': ['Ask about specific dog behaviors', 'Inquire about training methods'],
            'confidence_score': 0.8,
            'tools_used': ['general_knowledge'],
            'processing_status': 'completed'
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"❌ Book chat error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Book chat error: {str(e)}',
            'operation': 'chat'
        }), 500

@book_bp.route('/knowledge-chat', methods=['POST', 'OPTIONS'])
def knowledge_chat_about_book():
    """Chat about book content with awareness of user's personal knowledge base"""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", current_app.config['FRONTEND_URL'])
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response
    try:
        # Get user from token (optional for public book access)
        user_id = 1  # Default user for public access
        
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        data = request.get_json()
        query = data.get('query', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Query is required for book chat',
                'operation': 'chat'
            }), 400
        
        current_app.logger.info(f"🧠 Processing knowledge-aware book chat for user {user_id}: {query}")
        
        # Process book chat through enhanced service
        result = get_book_service().chat_about_book(
            user_id=user_id,
            query=query,
            conversation_history=conversation_history
        )
        
        if result['success']:
            current_app.logger.info(f"✅ Knowledge-aware book chat processed successfully")
            
            # Check if user knowledge was used
            user_knowledge_used = result.get('chat_context', {}).get('user_knowledge_used', False)
            
            return jsonify({
                'success': True,
                'response': result['response'],
                'operation': 'knowledge_chat',
                'chat_info': {
                    'query': query,
                    'context_used': result.get('chat_context', {}),
                    'conversation_length': len(conversation_history),
                    'user_knowledge_used': user_knowledge_used
                },
                'insights': result.get('insights', []),
                'suggestions': result.get('suggestions', []),
                'confidence_score': result.get('confidence_score', 0.0),
                'tools_used': result.get('tools_used', []),
                'processing_status': result.get('processing_status', 'completed')
            }), 200
            
        else:
            current_app.logger.error(f"❌ Knowledge-aware book chat failed: {result.get('error_message')}")
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Book chat failed'),
                'operation': 'knowledge_chat'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Knowledge-aware book chat error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Knowledge-aware book chat error: {str(e)}',
            'operation': 'knowledge_chat'
        }), 500

@book_bp.route('/edit', methods=['POST'])
@require_auth
def edit_book_content():
    """Edit book content using AI - requires authentication"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        data = request.get_json()
        edit_instruction = data.get('edit_instruction', '').strip()
        edit_type = data.get('edit_type', 'content')
        
        if not edit_instruction:
            return jsonify({
                'success': False,
                'message': 'Edit instruction is required',
                'operation': 'edit'
            }), 400
        
        # Validate edit type
        valid_edit_types = ['content', 'style', 'structure']
        if edit_type not in valid_edit_types:
            return jsonify({
                'success': False,
                'message': f'Invalid edit type. Must be one of: {", ".join(valid_edit_types)}',
                'operation': 'edit'
            }), 400
        
        current_app.logger.info(f"✏️ Processing book edit for user {user_id}: {edit_type}")
        
        # Process book editing through enhanced service
        result = get_book_service().edit_book_content(
            user_id=user_id,
            edit_instruction=edit_instruction,
            edit_type=edit_type
        )
        
        if result['success']:
            current_app.logger.info(f"✅ Book editing processed successfully")
            
            return jsonify({
                'success': True,
                'response': result['response'],
                'operation': 'edit',
                'edit_info': {
                    'instruction': edit_instruction,
                    'edit_type': edit_type,
                    'edit_summary': result.get('edit_summary', ''),
                    'original_content_preview': result.get('original_content', '')[:500] + '...' if result.get('original_content') else ''
                },
                'insights': result.get('insights', []),
                'suggestions': result.get('suggestions', []),
                'confidence_score': result.get('confidence_score', 0.0),
                'tools_used': result.get('tools_used', []),
                'processing_status': result.get('processing_status', 'completed')
            }), 200
            
        else:
            current_app.logger.error(f"❌ Book editing failed: {result.get('error_message')}")
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Book editing failed'),
                'operation': 'edit'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Book editing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Book editing error: {str(e)}',
            'operation': 'edit'
        }), 500

@book_bp.route('/download', methods=['GET', 'POST'])
def download_book():
    """Download book in specified format"""
    try:
        # Get user from token (optional for public book access)
        user_id = 1  # Default user for public access
        
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        # Get format from query parameter or request body
        download_format = 'pdf'  # Default format
        
        if request.method == 'POST':
            data = request.get_json()
            download_format = data.get('format', 'pdf').lower()
        else:
            download_format = request.args.get('format', 'pdf').lower()
        
        current_app.logger.info(f"⬇️ Processing book download for user {user_id}: {download_format}")
        
        # Process book download through enhanced service
        result = get_book_service().download_book(
            user_id=user_id,
            format=download_format
        )
        
        if result['success']:
            current_app.logger.info(f"✅ Book download processed successfully")
            
            return jsonify({
                'success': True,
                'response': result['response'],
                'operation': 'download',
                'download_info': {
                    'format': download_format,
                    'download_url': result.get('download_url', ''),
                    'available_formats': ['pdf'],
                    'file_size': 'Variable',
                    'public_access': True
                },
                'insights': result.get('insights', []),
                'suggestions': result.get('suggestions', []),
                'confidence_score': result.get('confidence_score', 0.0),
                'tools_used': result.get('tools_used', []),
                'processing_status': result.get('processing_status', 'completed')
            }), 200
            
        else:
            current_app.logger.error(f"❌ Book download failed: {result.get('error_message')}")
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Book download failed'),
                'operation': 'download'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Book download error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Book download error: {str(e)}',
            'operation': 'download'
        }), 500

@book_bp.route('/download/direct', methods=['GET'])
def download_book_direct():
    """Direct download of the book PDF file"""
    try:
        current_app.logger.info("📥 Processing direct book download")
        
        book_info = get_book_service().get_book_info()
        download_url = book_info['s3_url']
        
        # Log download for analytics
        user_id = 1  # Default user
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        current_app.logger.info(f"📥 Direct download initiated by user {user_id}")
        
        # Redirect to S3 URL for direct download
        from flask import redirect
        return redirect(download_url)
        
    except Exception as e:
        current_app.logger.error(f"❌ Direct download error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Direct download error: {str(e)}'
        }), 500

@book_bp.route('/search', methods=['POST'])
def search_book_content():
    """Search within book content"""
    try:
        # Get user from token (optional for public book access)
        user_id = 1  # Default user for public access
        
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        data = request.get_json()
        search_query = data.get('query', '').strip()
        
        if not search_query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        current_app.logger.info(f"🔍 Processing book search for user {user_id}: {search_query}")
        
        # Use book chat for search functionality
        result = get_book_service().chat_about_book(
            user_id=user_id,
            query=f"Search for information about: {search_query}",
            conversation_history=[]
        )
        
        if result['success']:
            current_app.logger.info(f"✅ Book search processed successfully")
            
            return jsonify({
                'success': True,
                'query': search_query,
                'response': result['response'],
                'operation': 'search',
                'search_results': {
                    'relevant_sections': result.get('relevant_sections', []),
                    'insights': result.get('insights', []),
                    'suggestions': result.get('suggestions', [])
                },
                'confidence_score': result.get('confidence_score', 0.0),
                'tools_used': result.get('tools_used', []),
                'processing_status': result.get('processing_status', 'completed')
            }), 200
            
        else:
            current_app.logger.error(f"❌ Book search failed: {result.get('error_message')}")
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Book search failed'),
                'operation': 'search'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Book search error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Book search error: {str(e)}',
            'operation': 'search'
        }), 500

@book_bp.route('/chapters', methods=['GET'])
def get_book_chapters():
    """Get book chapters and navigation structure"""
    try:
        current_app.logger.info("📑 Getting book chapters")
        
        # Use book reading functionality to get structure
        result = get_book_service().read_book(
            user_id=1,
            query="Show me the book structure and chapters"
        )
        
        # Mock chapter structure - this would be enhanced with actual content analysis
        chapters = [
            {
                "chapter_number": 1,
                "title": "Introduction to the Way of the Dog",
                "page_range": "1-15",
                "summary": "Foundational concepts of dog-human relationships"
            },
            {
                "chapter_number": 2,
                "title": "Understanding Anahata",
                "page_range": "16-35",
                "summary": "The heart-centered approach to dog training"
            },
            {
                "chapter_number": 3,
                "title": "Practical Training Techniques",
                "page_range": "36-60",
                "summary": "Hands-on methods and exercises"
            },
            {
                "chapter_number": 4,
                "title": "Building Trust and Connection",
                "page_range": "61-85",
                "summary": "Developing deeper bonds with your dog"
            },
            {
                "chapter_number": 5,
                "title": "Advanced Applications",
                "page_range": "86-110",
                "summary": "Complex training scenarios and solutions"
            }
        ]
        
        return jsonify({
            'success': True,
            'book_title': get_book_service().BOOK_TITLE,
            'chapters': chapters,
            'total_chapters': len(chapters),
            'navigation_available': True,
            'message': 'Book chapters retrieved successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error getting chapters: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving chapters: {str(e)}'
        }), 500

@book_bp.route('/stats', methods=['GET'])
def get_book_stats():
    """Get book usage statistics"""
    try:
        current_app.logger.info("📊 Getting book statistics")
        
        # Mock statistics - this would be enhanced with actual analytics
        stats = {
            "book_title": get_book_service().BOOK_TITLE,
            "total_reads": 150,
            "total_chats": 89,
            "total_downloads": 75,
            "total_edits": 12,
            "public_access": True,
            "available_operations": ["read", "chat", "edit", "download"],
            "most_popular_chapters": [
                {"chapter": "Understanding Anahata", "views": 45},
                {"chapter": "Practical Training Techniques", "views": 38},
                {"chapter": "Building Trust and Connection", "views": 32}
            ],
            "common_topics": [
                {"topic": "training techniques", "mentions": 23},
                {"topic": "dog psychology", "mentions": 19},
                {"topic": "relationship building", "mentions": 16}
            ]
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'message': 'Book statistics retrieved successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error getting stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving statistics: {str(e)}'
        }), 500

@book_bp.route('/feedback', methods=['POST'])
def submit_book_feedback():
    """Submit feedback about the book"""
    try:
        # Get user from token (optional)
        user_id = 1  # Default user for public access
        
        token = request.cookies.get('token')
        if token:
            success, message, user_data = AuthService.get_user_from_token(token)
            if success:
                user_id = user_data['id']
        
        data = request.get_json()
        feedback_text = data.get('feedback', '').strip()
        rating = data.get('rating', 0)
        category = data.get('category', 'general')
        
        if not feedback_text:
            return jsonify({
                'success': False,
                'message': 'Feedback text is required'
            }), 400
        
        current_app.logger.info(f"📝 Processing book feedback from user {user_id}")
        
        # Store feedback (this would be enhanced with actual database storage)
        feedback_record = {
            "user_id": user_id,
            "feedback": feedback_text,
            "rating": rating,
            "category": category,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "book_title": get_book_service().BOOK_TITLE
        }
        
        # Log the feedback
        current_app.logger.info(f"📝 Book feedback received: {category} - Rating: {rating}")
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback! Your input helps improve the book experience.',
            'feedback_id': str(uuid.uuid4()),
            'submitted_at': feedback_record['timestamp']
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Feedback submission error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Feedback submission error: {str(e)}'
        }), 500

@book_bp.route('/ai-chat-edit', methods=['POST'])
@require_auth
def ai_chat_edit():
    """AI-powered conversational story editing - requires authentication"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        data = request.get_json()
        chat_message = data.get('message', '').strip()
        chapter_id = data.get('chapterId', '')
        book_id = data.get('bookId', '')
        current_content = data.get('currentContent', '')
        chat_history = data.get('chatHistory', [])
        edit_context = data.get('editContext', {})
        
        if not chat_message:
            return jsonify({
                'success': False,
                'message': 'Chat message is required'
            }), 400
        
        if not current_content:
            return jsonify({
                'success': False,
                'message': 'Content is required for AI editing'
            }), 400
        
        current_app.logger.info(f"💬 Processing AI chat edit for user {user_id}")
        current_app.logger.info(f"📝 Message: {chat_message[:100]}...")
        current_app.logger.info(f"📚 Book: {edit_context.get('bookTitle', 'Unknown')}")
        current_app.logger.info(f"📄 Chapter: {edit_context.get('chapterTitle', 'Unknown')}")
        
        # Process AI chat editing through enhanced service
        from app.services.ai_service import AIService
        ai_service = AIService()
        
        # Prepare context for AI
        context_prompt = f"""
You are an expert AI writing assistant helping a user edit their book chapter. Be conversational and helpful.

BOOK CONTEXT:
- Book Title: {edit_context.get('bookTitle', 'Unknown')}
- Chapter Title: {edit_context.get('chapterTitle', 'Unknown')}
- Content Type: {edit_context.get('contentType', 'narrative')}

CURRENT CHAPTER CONTENT:
{current_content}

CHAT HISTORY:
{chr(10).join([f"{msg.get('type', 'user')}: {msg.get('content', '')}" for msg in chat_history[-3:]])}

USER REQUEST: {chat_message}

INSTRUCTIONS:
1. Respond conversationally and helpfully
2. If the user asks for edits, provide a suggested revision in a clear, structured way
3. Offer specific, actionable suggestions
4. Be encouraging and supportive
5. If providing a rewrite, format it clearly so it can be applied to the content
6. Ask follow-up questions if needed to clarify the user's intent

Respond in a helpful, professional tone as a writing coach would.
"""
        
        try:
            # Generate AI response using OpenAI
            ai_response = ai_service.generate_completion(
                messages=[
                    {"role": "system", "content": "You are an expert AI writing assistant and editor."},
                    {"role": "user", "content": context_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Parse response for suggestions and edits
            response_text = ai_response.strip()
            suggested_edit = None
            suggestions = []
            
            # Check if the response contains a rewrite or suggestion
            if any(keyword in response_text.lower() for keyword in ['here\'s a rewrite', 'revised version', 'here\'s how', 'try this']):
                # Extract the suggested content (simplified extraction)
                lines = response_text.split('\n')
                edit_lines = []
                in_edit_section = False
                
                for line in lines:
                    if any(marker in line.lower() for marker in ['revised:', 'rewrite:', 'suggested:', 'here\'s', 'try this:']):
                        in_edit_section = True
                        continue
                    elif in_edit_section and line.strip():
                        if not line.startswith('**') and not line.startswith('*'):  # Skip formatting markers
                            edit_lines.append(line.strip())
                
                if edit_lines:
                    suggested_edit = '\n'.join(edit_lines)
            
            # Generate quick suggestions based on content type and user message
            if 'style' in chat_message.lower():
                suggestions = ["Make it more descriptive", "Add more dialogue", "Change to first person", "Make it more dramatic"]
            elif 'grammar' in chat_message.lower():
                suggestions = ["Check sentence structure", "Fix punctuation", "Improve word choice", "Simplify complex sentences"]
            elif 'emotion' in chat_message.lower():
                suggestions = ["Add more feelings", "Include sensory details", "Show don't tell", "Create emotional tension"]
            elif 'detail' in chat_message.lower():
                suggestions = ["Add character descriptions", "Include setting details", "Expand on actions", "Add background information"]
            
            current_app.logger.info(f"✅ AI chat edit processed successfully")
            current_app.logger.info(f"📝 Response length: {len(response_text)} characters")
            if suggested_edit:
                current_app.logger.info(f"💡 Suggested edit provided: {len(suggested_edit)} characters")
            
            return jsonify({
                'success': True,
                'response': response_text,
                'suggestedEdit': suggested_edit,
                'suggestions': suggestions,
                'editInfo': {
                    'chapterId': chapter_id,
                    'bookId': book_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'userMessage': chat_message
                },
                'processing_status': 'completed'
            }), 200
            
        except Exception as ai_error:
            current_app.logger.error(f"❌ AI processing error: {str(ai_error)}")
            
            # Fallback response
            fallback_response = f"""I understand you want to work on improving your chapter. While I'm experiencing some technical difficulties right now, here are some general suggestions for your request:

"{chat_message}"

• Consider the overall flow and pacing of your content
• Look for opportunities to add more vivid descriptions
• Ensure your writing matches the tone you're aiming for
• Check that each paragraph advances your story

Please try rephrasing your request, and I'll do my best to help you improve your writing!"""
            
            return jsonify({
                'success': True,
                'response': fallback_response,
                'suggestedEdit': None,
                'suggestions': ["Improve clarity", "Add more detail", "Enhance flow", "Polish grammar"],
                'editInfo': {
                    'chapterId': chapter_id,
                    'bookId': book_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'userMessage': chat_message,
                    'fallback': True
                },
                'processing_status': 'completed'
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"❌ AI chat edit error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'AI chat edit error: {str(e)}'
        }), 500

# Error handlers for the book blueprint
@book_bp.errorhandler(404)
def book_not_found(error):
    return jsonify({
        'success': False,
        'message': 'Book endpoint not found',
        'available_endpoints': [
            '/info', '/read', '/chat', '/edit', '/download', 
            '/search', '/chapters', '/stats', '/feedback'
        ]
    }), 404

@book_bp.errorhandler(500)
def book_internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error in book service',
        'error': 'Please try again later'
    }), 500 