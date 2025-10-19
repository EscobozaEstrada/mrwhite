from flask import Blueprint, request, jsonify, g, make_response, current_app
from app.utils.jwt import decode_token
from app.services.conversation_service import ConversationService
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.middleware.usage_limits import check_conversation_usage
from app import db
from datetime import datetime, timezone

# Create blueprint
conversation_bp = Blueprint("conversation", __name__)

# Middleware to check authentication
@conversation_bp.before_request
def authenticate():
    # Skip authentication for OPTIONS requests
    if request.method == 'OPTIONS':
        return
    
    token = request.cookies.get('token')
    if not token:
        return jsonify({"message": "Unauthorized"}), 401
    
    try:
        user_data = decode_token(token)
        g.user_id = user_data.get('id')
    except:
        return jsonify({"message": "Invalid or expired token"}), 401

# Handler for OPTIONS requests
@conversation_bp.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", current_app.config['FRONTEND_URL'])
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# Get all conversations for the authenticated user
@conversation_bp.route("/user/<int:user_id>/conversations", methods=["GET"])
def get_conversations(user_id):
    # Ensure user can only access their own conversations
    if g.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    
    conversations = ConversationService.get_user_conversations(user_id)
    return jsonify(conversations)

# Create a new conversation
@conversation_bp.route("/conversations", methods=["POST"])
@check_conversation_usage
def create_conversation():
    """Create a new conversation"""
    data = request.get_json()
    
    if not data:
        return jsonify({"message": "No data provided"}), 400
    
    title = data.get('title', 'New Conversation')
    
    conversation = Conversation(
        user_id=g.user_id,
        title=title,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({
        "message": "Conversation created successfully",
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
    }), 201

# Get a specific conversation with its messages
@conversation_bp.route("/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    success, message, data = ConversationService.get_conversation_with_messages(conversation_id, g.user_id)
    
    if not success:
        status_code = 404 if 'not found' in message else 500
        return jsonify({"message": message}), status_code
    
    return jsonify(data)

# Update a conversation (e.g., change title)
@conversation_bp.route("/conversations/<int:conversation_id>", methods=["PUT"])
def update_conversation(conversation_id):
    data = request.json
    title = data.get('title')
    is_bookmarked = data.get('is_bookmarked')
    
    success, message, conversation_data = ConversationService.update_conversation(
        conversation_id, g.user_id, title, is_bookmarked
    )
    
    if not success:
        status_code = 404 if 'not found' in message else 500
        return jsonify({"message": message}), status_code
    
    return jsonify(conversation_data)

# Delete a conversation
@conversation_bp.route("/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    success, message = ConversationService.delete_conversation(conversation_id, g.user_id)
    
    if not success:
        status_code = 404 if 'not found' in message else 500
        return jsonify({"message": message}), status_code
    
    return jsonify({"message": message})

# Add a message to a conversation
@conversation_bp.route("/conversations/<int:conversation_id>/messages", methods=["POST"])
def add_message(conversation_id):
    data = request.json
    content = data.get('content', '')
    message_type = data.get('type', 'user')
    attachments = data.get('attachments', [])
    
    success, message, message_data = ConversationService.add_message(
        conversation_id, g.user_id, content, message_type, attachments
    )
    
    if not success:
        status_code = 404 if 'not found' in message else 500
        return jsonify({"message": message}), status_code
    
    return jsonify(message_data), 201

# Toggle bookmark status of a message
@conversation_bp.route("/messages/<int:message_id>/bookmark", methods=["POST"])
def toggle_bookmark(message_id):
    success, message, message_data = ConversationService.toggle_message_bookmark(message_id, g.user_id)
    
    if not success:
        status_code = 404 if 'not found' in message else 500
        return jsonify({"message": message}), status_code
    
    return jsonify(message_data)

# Toggle like/dislike status of a message
@conversation_bp.route("/messages/<int:message_id>/reaction", methods=["POST"])
def toggle_reaction(message_id):
    data = request.json
    reaction_type = data.get('type', '')
    
    success, message, message_data = ConversationService.toggle_message_reaction(
        message_id, g.user_id, reaction_type
    )
    
    if not success:
        status_code = 404 if 'not found' in message else 400
        return jsonify({"message": message}), status_code
    
    return jsonify(message_data)

# Get all bookmarked messages
@conversation_bp.route("/bookmarks", methods=["GET"])
def get_bookmarks():
    bookmarked_messages = ConversationService.get_bookmarked_messages(g.user_id)
    return jsonify(bookmarked_messages)

# Toggle bookmark status for a conversation
@conversation_bp.route("/conversations/<int:conversation_id>/bookmark", methods=["POST"])
def toggle_conversation_bookmark(conversation_id):
    # First get current conversation to toggle bookmark status
    success, _, data = ConversationService.get_conversation_with_messages(conversation_id, g.user_id)
    
    if not success:
        return jsonify({"message": "Conversation not found"}), 404
    
    current_bookmark_status = data['conversation'].get('is_bookmarked', False)
    new_bookmark_status = not current_bookmark_status
    
    success, message, conversation_data = ConversationService.update_conversation(
        conversation_id, g.user_id, is_bookmarked=new_bookmark_status
    )
    
    if not success:
        status_code = 404 if 'not found' in message else 500
        return jsonify({"message": message}), status_code
    
    return jsonify(conversation_data)

# Get all bookmarked conversations
@conversation_bp.route("/bookmarked-conversations", methods=["GET"])
def get_bookmarked_conversations():
    bookmarked_conversations = ConversationService.get_bookmarked_conversations(g.user_id)
    return jsonify(bookmarked_conversations)

# Clear cache for conversations
@conversation_bp.route("/clear-cache", methods=["POST"])
def clear_conversations_cache():
    """Clear cache for conversations"""
    try:
        from app.utils.cache import cache, invalidate_cache_pattern
        
        # Clear all conversation-related caches
        invalidate_cache_pattern("conversations:")
        invalidate_cache_pattern("user_conversations:")
        invalidate_cache_pattern("conversation_messages:")
        
        return jsonify({"message": "Cache cleared successfully", "status": "success"}), 200
    except Exception as e:
        current_app.logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({"message": f"Error clearing cache: {str(e)}", "status": "error"}), 500

# Delete all conversations for a user
@conversation_bp.route("/user/<int:user_id>/conversations", methods=["DELETE"])
def delete_all_conversations(user_id):
    # Ensure user can only delete their own conversations
    if g.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    
    success, message = ConversationService.delete_all_user_conversations(user_id)
    
    if not success:
        return jsonify({"message": message}), 500
    
    return jsonify({"message": message})