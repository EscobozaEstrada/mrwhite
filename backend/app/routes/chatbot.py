from flask import Blueprint, request, jsonify, g, make_response, current_app
from app.utils.openai_helper import get_mr_white_response
from app.utils.personalization_helper import get_personalized_mr_white_response
from app.utils.file_handler import extract_and_store, query_user_docs, store_chat_message, query_chat_history
from app.utils.langgraph_helper_enhanced import process_with_enhanced_graph
from app import db
from app.models.conversation import Conversation
from app.models.message import Message, Attachment
from app.models.user import User
from app.utils.jwt import decode_token
from app.middleware.usage_limits import check_chat_usage, check_document_usage, check_conversation_usage
from app.middleware.credit_middleware import require_chat_credits
from app.services.enhanced_chat_service import EnhancedChatService
from datetime import datetime, timezone
import os
from werkzeug.utils import secure_filename
from langchain_openai import ChatOpenAI
import json
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# === Custom tools === #
from tools.previous import previous
from tools.storage import storage
from tools.summarizer import summarize
from tools.emailer import emailer

# Remove the hardcoded API key and use environment variable
llm = ChatOpenAI(
    model="gpt-4", 
    temperature=0
)

# Initialize enhanced chat service
enhanced_chat_service = EnhancedChatService()

# === Agent with tool usage === #
tool_objs = [
    Tool.from_function(
        func=previous, 
        name="get_previous_message",
        description="Gets relevant previous messages based on the user's query. IMPORTANT: Pass the full user query to search for relevant history."
    ),
    Tool.from_function(
        func=storage,
        name="store_file",
        description="Stores files, images, PDFs, or Google Drive links in the database. Use this when the user mentions uploading or sharing files or links."
    ),
    Tool.from_function(
        func=summarize,
        name="summarize_files",
        description="Summarizes the user's uploaded files based on their query. Use this when the user asks for summaries or information about their files."
    ),
    Tool.from_function(
        func=emailer,
        name="email_files",
        description="Emails the user's files to them. Use this when the user asks to send files to their email address."
    ),
]

agent = initialize_agent(
    tools=tool_objs,
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True,
    agent_kwargs={
        "system_message": """You are a helpful assistant that can use tools to answer user questions.

When using the 'previous' tool to get relevant past messages, always pass the user's ENTIRE query as the input parameter.
DO NOT just pass a single word like 'user' or '1' - this will not return useful results.
The full context of the query is needed to find semantically relevant past messages.

When the user uploads files or mentions files being uploaded, ALWAYS use the 'store_file' tool to handle this.
Look for keywords like 'upload', 'file', 'document', 'image', 'photo', 'pdf', 'drive link', etc.
If the user is talking about files they've shared or want to upload, use the store_file tool.

When the user asks about information in their uploaded files or wants a summary, ALWAYS use the 'summarize_files' tool.
Look for phrases like "summarize my files", "what's in my documents", "tell me about the files I uploaded", etc.
Pass their specific query to the tool to get targeted information from their files.

When the user asks for files to be sent to them via email, ALWAYS use the 'email_files' tool.
Look for phrases like "email me", "send to my email", "send me the files", etc.
If the user doesn't specify which files they want, ask them for clarification and then use the tool with their response."""
    }
)

chat_bp = Blueprint("chat", __name__)

# Set up file uploads directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@chat_bp.before_request
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
        g.user_email = user_data.get('email')
    except:
        return jsonify({"message": "Invalid or expired token"}), 401

@chat_bp.route("/chat", methods=["OPTIONS"])
def handle_options():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", current_app.config['FRONTEND_URL'])
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

@chat_bp.route("/chat", methods=["POST"])
@require_chat_credits
@check_document_usage  # For file uploads
def chat():
    # Get form data
    user_message = request.form.get("message", "")
    context = request.form.get("context", "chat")  # Default to "chat" if not specified
    conversation_id = request.form.get("conversationId")
    files = request.files.getlist("attachments")
    
    print(f"Received request with message: '{user_message}', context: {context}, files: {len(files)}")
    
    # Check for dog name in message and update user profile if found
    try:
        from app.utils.personalization_helper import detect_dog_name_in_message, update_user_dog_name
        dog_name = detect_dog_name_in_message(user_message)
        if dog_name:
            current_app.logger.info(f"🐕 Detected dog name in message: {dog_name}")
            update_user_dog_name(g.user_id, dog_name)
    except Exception as e:
        current_app.logger.error(f"Error processing dog name: {str(e)}")
    
    # Process uploaded files
    processed_files = []
    file_processing_results = []
    processed_documents = []  # Track only document files
    all_files_processed_successfully = True  # Flag to track if all files were processed successfully
    
    # Ensure user_id is set in Flask g object for services that need it
    from flask import g
    g.user_id = g.user_id  # This ensures g.user_id is already set from the authenticate function
    
    # Get file descriptions if provided
    file_descriptions = {}
    if request.form.get("fileDescriptions"):
        try:
            file_descriptions = json.loads(request.form.get("fileDescriptions"))
            print(f"📝 Received file descriptions: {file_descriptions}")
        except Exception as e:
            print(f"❌ Failed to parse fileDescriptions JSON: {str(e)}")
            print(f"Raw fileDescriptions: {request.form.get('fileDescriptions')}")
    
    # For backward compatibility
    if request.form.get("imageDescriptions") and not file_descriptions:
        try:
            file_descriptions = json.loads(request.form.get("imageDescriptions"))
            print(f"📝 Using legacy imageDescriptions: {file_descriptions}")
        except Exception as e:
            print(f"❌ Failed to parse imageDescriptions JSON: {str(e)}")
    
    # Get or create conversation
    if not conversation_id:
        # Create a new conversation with a default title based on the first message
        title = user_message[:50] + "..." if len(user_message) > 50 else user_message
        conversation = Conversation(user_id=g.user_id, title=title)
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id
    else:
        # Verify the conversation exists and belongs to the user
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            return jsonify({"message": "Conversation not found"}), 404
        
        # Security check: Make sure the conversation belongs to the current user
        if conversation.user_id != g.user_id:
            return jsonify({"message": "You don't have permission to access this conversation"}), 403
        
        # Update the conversation's timestamp
        conversation.updated_at = datetime.now(timezone.utc)
    
    # Set the current user ID in environment variable for tools to access
    os.environ["CURRENT_USER_ID"] = str(g.user_id)
    
    # Save user message FIRST (before processing files)
    user_msg = Message(
        conversation_id=conversation_id,
        content=user_message,
        type="user"
    )
    db.session.add(user_msg)
    db.session.flush()  # Flush to get the message ID for file processing

    # NOW process uploaded files with the correct message_id
    if files:
        print(f"Processing {len(files)} uploaded files")
        
        for file in files:
            if file.filename:
                print(f"Processing file: {file.filename}, type: {file.content_type}")
                if file.content_type.startswith('image/'):
                    # Process image with OpenAI Vision API
                    try:
                        print(f"🖼️ Processing image file: {file.filename}")
                        # First try to get description from fileDescriptions
                        user_description = None
                        if file.filename in file_descriptions:
                            user_description = file_descriptions[file.filename]
                            print(f"👤 Found description for {file.filename} in fileDescriptions: {user_description[:50]}...")
                        else:
                            # Try to find a matching key (filename might have been modified)
                            for key in file_descriptions.keys():
                                if key in file.filename or file.filename in key:
                                    user_description = file_descriptions[key]
                                    print(f"👤 Found partial match description for {file.filename} using key {key}: {user_description[:50]}...")
                                    break
                        
                        # If no specific description was provided for this image but user provided a message,
                        # use the user's message as the description
                        if user_description is None and user_message and len(files) == 1:
                            user_description = user_message
                            print(f"👤 Using user message as description: {user_description[:50]}...")
                        
                        # Log the final decision
                        if user_description is None:
                            print(f"⚠️ No description found for {file.filename}, will use empty description")
                        
                        # Set user_id in Flask g object for ImageService
                        from flask import g
                        g.user_id = g.user_id  # Ensure user_id is set
                        print(f"🔑 Setting g.user_id = {g.user_id} for image processing")
                        
                        # Process image file
                        print(f"🔄 Calling extract_and_store for image: {file.filename}")
                        result = extract_and_store(file, g.user_id, conversation_id, None, user_description)
                        print(f"✅ extract_and_store result for image: {result}")
                        processed_files.append(result)
                        
                        # If successful, add to context
                        if result.get('success'):
                            print(f"✅ Image processed successfully: {result}")
                            # Add image context to the message
                            image_context = f"\n[Image: {file.filename}"
                            if user_description:
                                image_context += f" - {user_description}"
                            image_context += "]"
                            
                            user_message += image_context
                        else:
                            print(f"❌ Image processing failed: {result}")
                            all_files_processed_successfully = False
                            
                    except Exception as e:
                        print(f"❌ Error processing image {file.filename}: {str(e)}")
                        import traceback
                        print(f"❌ Image processing error traceback: {traceback.format_exc()}")
                        all_files_processed_successfully = False
                
                elif file.content_type.startswith('audio/'):
                    # Process audio file
                    try:
                        # First try to get description from fileDescriptions
                        user_description = None
                        if file.filename in file_descriptions:
                            user_description = file_descriptions[file.filename]
                            print(f"👤 Found description for audio {file.filename} in fileDescriptions: {user_description[:50]}...")
                        else:
                            # Try to find a matching key (filename might have been modified)
                            for key in file_descriptions.keys():
                                if key in file.filename or file.filename in key:
                                    user_description = file_descriptions[key]
                                    print(f"👤 Found partial match description for audio {file.filename} using key {key}: {user_description[:50]}...")
                                    break
                        
                        # If no specific description was provided for this audio but user provided a message,
                        # use the user's message as the description
                        if user_description is None and user_message and len(files) == 1:
                            user_description = user_message
                            print(f"👤 Using user message as description: {user_description[:50]}...")
                        
                        # Log the final decision
                        if user_description is None:
                            print(f"⚠️ No description found for {file.filename}, will use empty description")
                        
                        # Use the new audio handler to process and upload to S3
                        from app.utils.audio_handler import process_audio_file
                        result = process_audio_file(file, g.user_id, user_description)
                        
                        if not result.get('success'):
                            print(f"❌ Error processing audio {file.filename}: {result.get('error')}")
                            all_files_processed_successfully = False
                            continue
                        
                        # Add the file info to processed files
                        processed_files.append(result)
                        
                        # Log the audio file processing
                        print(f"🎵 Processed audio file: {result['filename']}, URL: {result['url']}")
                        
                        # Create an attachment for the message
                        attachment = Attachment(
                            message_id=user_msg.id,
                            type='audio',
                            url=result['url'],
                            name=result['name']
                        )
                        db.session.add(attachment)
                        
                        # Add voice message to the user message for context
                        # But don't add it to processed_documents to avoid document processing response
                        if user_description:
                            voice_context = f"\n[Voice Message: {user_description}]"
                            # If this is the only content, replace user_message entirely
                            if not user_message.strip():
                                user_message = user_description
                            # Otherwise, append it as context
                            else:
                                user_message += voice_context
                        
                    except Exception as e:
                        print(f"❌ Error processing audio {file.filename}: {str(e)}")
                        all_files_processed_successfully = False
                
                else:
                    # Process document file
                    try:
                        # Store the document in vector DB
                        result = extract_and_store(file, g.user_id, conversation_id)
                        processed_files.append(result)
                        processed_documents.append(result.get('filename', file.filename))
                        
                        if not result.get('success'):
                            all_files_processed_successfully = False
                    except Exception as e:
                        print(f"❌ Error processing document {file.filename}: {str(e)}")
                        all_files_processed_successfully = False
    
    # If file processing failed and this was a file upload request, return an error
    if files and context == "file_upload" and not all_files_processed_successfully:
        return jsonify({
            "message": "Error processing files",
            "details": file_processing_results
        }), 500

    print(f"Processed files: {processed_files}")
    
    # Save attachments if any
    for attachment_data in processed_files:
        # Debug log what we're saving
        print(f"💾 Saving attachment: {attachment_data}")
        
        # Ensure image files have the correct type
        attachment_type = attachment_data.get('type', 'file')
        
        # Force 'image' type for image files based on multiple criteria
        if (attachment_data.get('file_type', '').startswith('image/') or 
            attachment_data.get('url', '').lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) or
            'image' in attachment_data.get('file_type', '').lower()):
            attachment_type = 'image'
            print(f"🖼️ Setting attachment type to 'image' for {attachment_data.get('name', '')}")
            
        attachment = Attachment(
            message_id=user_msg.id,
            type=attachment_type,
            url=attachment_data.get('url', ''),
            name=attachment_data.get('name', '')
        )
        db.session.add(attachment)
        print(f"✅ Added attachment to database: type={attachment_type}, name={attachment_data.get('name', '')}")
        
    # Create a variable to hold the storage tool response
    storage_response = None
        
    # If files were uploaded, directly call the storage tool
    if files and len(processed_files) > 0:
        # Check if we have any document files (not images or audio)
        has_documents = any(
            (not attachment.get('type') in ['image', 'audio']) and 
            (not attachment.get('file_type', '').startswith('image/')) and
            (not attachment.get('file_type', '').startswith('audio/'))
            for attachment in processed_files
        )
        
        if has_documents and processed_documents:
            # Prepare a descriptive message about the files for the storage tool
            file_info = ""
            if processed_documents:
                file_info += f"Documents: {', '.join(processed_documents)}. "
            
            # Add attachment details for non-image, non-audio files
            for attachment in processed_files:
                if attachment.get('type') not in ['image', 'audio']:
                    file_info += f"{attachment.get('type', 'file')}: {attachment.get('name', 'unnamed')}. "
            
            print(f"Calling storage tool directly with file_info: {file_info}")
            
            # Call the storage tool directly only for documents
            try:
                storage_response = storage(file_info)
                print(f"Storage tool response: {storage_response}")
            except Exception as e:
                print(f"Error calling storage tool: {str(e)}")
                storage_response = f"I received your files, but encountered an error while processing them: {str(e)}"
    
    # Store user message in Pinecone
    store_result, store_message = store_chat_message(
        user_id=g.user_id, 
        message_content=user_message, 
        message_id=user_msg.id, 
        message_type="user", 
        conversation_id=conversation_id
    )
    
    if not store_result:
        print(f"Warning: Failed to store user message in Pinecone: {store_message}")
    
    # 🤖 AI AGENT FLOW: Check for reminder requests FIRST
    try:
        # Create service instance for reminder detection
        
        # Check if this is a reminder request (simplified check for now)
        reminder_keywords = ['remind', 'reminder', 'schedule', 'appointment', 'medication', 'vaccine']
        is_reminder_request = any(keyword in user_message.lower() for keyword in reminder_keywords)
        
        if is_reminder_request:
            current_app.logger.info("🤖 AI Agent detected potential reminder request in regular chat")
            
            # Use enhanced chat service which will handle the reminder appropriately
            try:
                success, ai_reply, context_info = enhanced_chat_service.generate_contextual_response(
                    user_id=g.user_id,
                    message=user_message,
                    conversation_id=conversation_id,
                    thread_id=conversation.thread_id if conversation else None
                )
                
                if success:
                    current_app.logger.info("✅ Enhanced chat service handled reminder request")
                    
                    # Skip to the end and save the response
                    ai_msg = Message(
                        conversation_id=conversation_id,
                        content=ai_reply,
                        type="ai"
                    )
                    db.session.add(ai_msg)
                    
                    # Store AI response in Pinecone
                    store_result, store_message = store_chat_message(
                        user_id=g.user_id,
                        message_content=ai_reply,
                        message_id=ai_msg.id,
                        message_type="ai",
                        conversation_id=conversation_id
                    )
                    
                    db.session.commit()
                    
                    return jsonify({
                        "message": ai_reply,
                        "conversation_id": conversation_id,
                        "context_info": context_info
                    })
                
            except Exception as e:
                current_app.logger.error(f"Enhanced chat service failed for reminder: {str(e)}")
                # Continue to regular processing
        
    except Exception as e:
        current_app.logger.error(f"Error in reminder detection: {str(e)}")
        # Continue to regular chat processing

    # Get AI response
    try:
        # Get the user's email for document sending
        user = User.query.filter_by(id=g.user_id).first()
        user_email = user.email if user else "unknown@example.com"
        
        # Get conversation history for context (moved this up to make it available for all paths)
        conversation_messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
        conversation_history = [
            {
                'content': msg.content,
                'type': msg.type
            } for msg in conversation_messages[:-1]  # Exclude the current message
        ]
        
        # 🖼️ PRIORITY: Handle image uploads with AI analysis
        if files and any(f.content_type.startswith('image/') for f in files if hasattr(f, 'content_type') and f.filename):
            # Build image analysis response
            image_analyses = []
            for attachment in processed_files:
                if attachment.get('type') == 'image' and attachment.get('description'):
                    image_analyses.append(f"📸 **{attachment.get('name')}**: {attachment.get('description')}")
                # Also check for images without explicit type field
                elif 'image' in attachment.get('file_type', '').lower() and attachment.get('description'):
                    image_analyses.append(f"📸 **{attachment.get('name')}**: {attachment.get('description')}")
            
            if image_analyses:
                # Create a comprehensive response with AI analysis
                if user_message and user_message.strip():
                    # User provided a message with the image
                    ai_reply = f"I can see you've uploaded an image! Here's what I found:\n\n{chr(10).join(image_analyses)}\n\n{user_message}"
                    
                    # Get additional context-aware response
                    try:
                        enhanced_message = f"User uploaded an image and said: '{user_message}'. Image analysis: {chr(10).join(image_analyses)}"
                        context_response = get_personalized_mr_white_response(enhanced_message, "image_upload", conversation_history, g.user_id)
                        ai_reply = context_response
                    except Exception as e:
                        print(f"Error getting context response for image: {e}")
                        # Fall back to basic response
                        ai_reply = f"I can see your image! Here's what I found:\n\n{chr(10).join(image_analyses)}\n\nHow can I help you with this image?"
                else:
                    # No user message, just image upload
                    ai_reply = f"I can see you've uploaded an image! Here's what I found:\n\n{chr(10).join(image_analyses)}\n\nWhat would you like to know about this image?"
            else:
                # Check if any image files were processed successfully
                has_images = any(
                    attachment.get('type') == 'image' or 'image' in attachment.get('file_type', '').lower()
                    for attachment in processed_files
                )
                
                if has_images:
                    # Images were processed but no analyses were found
                    ai_reply = "I can see you've uploaded an image. What would you like to know about it?"
                else:
                    # Image processing failed, use storage response as fallback
                    ai_reply = storage_response if storage_response else "I received your image, but I'm having trouble analyzing it right now. Please try again or let me know if you need help!"
        
        # 📄 Handle document uploads with enhanced processing
        elif files and context == "file_upload":
            # Check if we only have audio files (voice messages)
            only_audio_files = all(
                file.content_type.startswith('audio/') 
                for file in files if hasattr(file, 'content_type') and file.content_type
            )
            
            # If we only have audio files, treat them as regular messages
            if only_audio_files:
                current_app.logger.info("🎤 Processing voice message as regular chat")
                # Make sure user_message is not empty when processing voice messages
                if not user_message.strip():
                    # Find any transcriptions from the file descriptions
                    audio_descriptions = []
                    for file in files:
                        if hasattr(file, 'filename') and file.filename in file_descriptions:
                            audio_descriptions.append(file_descriptions[file.filename])
                    
                    # Use the first transcription as the message if available
                    if audio_descriptions:
                        user_message = audio_descriptions[0]
                        current_app.logger.info(f"📝 Using transcription as message: {user_message[:50]}...")
                
                # Use Enhanced Chat Service for voice message response
                try:
                    success, ai_reply, context_info = enhanced_chat_service.generate_contextual_response(
                        user_id=g.user_id,
                        message=user_message,
                        conversation_id=conversation_id,
                        thread_id=conversation.thread_id if conversation else None
                    )
                    
                    if not success:
                        # Fallback to regular response
                        ai_reply = get_personalized_mr_white_response(user_message, context, conversation_history, g.user_id)
                except Exception as e:
                    current_app.logger.error(f"Error processing voice message: {str(e)}")
                    ai_reply = get_personalized_mr_white_response(user_message, context, conversation_history, g.user_id)
            else:
                # Create comprehensive document processing response
                file_message = "✅ **Document Processing Complete!**\n\n"
                
                if processed_documents:
                    doc_list = ", ".join(processed_documents)
                    file_message += f"📄 **Processed Documents:** {doc_list}\n\n"
                    
                    # Register document upload with conversation context manager
                    try:
                        from app.utils.conversation_context_manager import get_context_manager
                        context_manager = get_context_manager()
                        
                        # Create document metadata
                        document_metadata = {}
                        for attachment in processed_files:
                            if attachment.get('type') == 'document':
                                doc_name = attachment.get('name', 'Unknown')
                                document_metadata[doc_name] = {
                                    'url': attachment.get('url', ''),
                                    'type': attachment.get('file_type', ''),
                                    'summary': attachment.get('summary', ''),
                                    'key_insights': attachment.get('key_insights', []),
                                    'upload_time': datetime.now(timezone.utc).isoformat()
                                }
                        
                        # Register the document upload
                        context_manager.register_document_upload(
                            user_id=g.user_id,
                            conversation_id=conversation_id,
                            document_names=processed_documents,
                            document_metadata=document_metadata
                        )
                        
                        current_app.logger.info(f"✅ Registered document upload with context manager: {processed_documents}")
                    except Exception as e:
                        current_app.logger.error(f"❌ Error registering document upload with context manager: {str(e)}")
                
                # Add detailed processing results
                if file_processing_results:
                    file_message += "📊 **Processing Results:**\n"
                    for result in file_processing_results:
                        file_message += f"• {result}\n"
                    file_message += "\n"
                
                # Add document details from processed files
                for attachment in processed_files:
                    if attachment.get('type') == 'document':
                        file_message += f"📋 **{attachment.get('name')}**\n"
                        if attachment.get('summary'):
                            file_message += f"📝 Summary: {attachment.get('summary')}\n"
                        if attachment.get('key_insights'):
                            insights = attachment.get('key_insights', [])
                            if insights:
                                file_message += f"💡 Key Insights: {', '.join(insights[:3])}\n"
                        if attachment.get('quality_score'):
                            score = attachment.get('quality_score', 0.0)
                            file_message += f"⭐ Quality Score: {score:.1f}/10\n"
                        file_message += "\n"
                
                file_message += "🔍 **Your documents have been:**\n"
                file_message += "• Analyzed with advanced AI processing\n"
                file_message += "• Added to your personal knowledge base\n"
                file_message += "• Made searchable for future conversations\n"
                file_message += "• Stored securely in the cloud\n\n"
                file_message += "💬 You can now ask me questions about these documents in future conversations!"
                
                # For document uploads, provide direct response without going through chat AI
                ai_reply = file_message
        
        # 💬 Regular chat without files
        else:
            # 🚀 Use Enhanced Chat Service for comprehensive AI response
            try:
                current_app.logger.info("🔥 Using Enhanced Chat Service for regular chat")
                
                # Generate enhanced response with document and context awareness
                success, ai_reply, context_info = enhanced_chat_service.generate_contextual_response(
                    user_id=g.user_id,
                    message=user_message,
                    conversation_id=conversation_id,
                    thread_id=conversation.thread_id if conversation else None
                )
                
                if success:
                    current_app.logger.info(f"✅ Enhanced response generated: {context_info.get('service_used', 'unknown')}")
                    
                    # Add context information to response if available
                    if context_info.get('document_context_added'):
                        ai_reply += f"\n\n📄 *Referenced from: {context_info.get('referenced_document', 'your documents')}*"
                    
                else:
                    # Fallback to LangGraph
                    raise Exception("Enhanced chat service failed")
                
            except Exception as e:
                current_app.logger.error(f"Error with Enhanced Chat Service: {str(e)}")
                # Fallback to LangGraph
                try:
                    current_app.logger.info("🔄 Falling back to LangGraph processing")
                    ai_reply = process_with_enhanced_graph(
                        user_id=g.user_id, 
                        user_email=user_email, 
                        conversation_id=conversation_id,
                        query=user_message, 
                        conversation_history=conversation_history
                    )
                except Exception as e2:
                    current_app.logger.error(f"Error with enhanced LangGraph: {str(e2)}")
                    # Final fallback to regular response
                    current_app.logger.info("🔄 Final fallback to regular response")
                    ai_reply = get_personalized_mr_white_response(user_message, context, conversation_history, g.user_id)
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error generating AI response: {str(e)}"}), 500
    
    # Save AI response
    ai_msg = Message(
        conversation_id=conversation_id,
        content=ai_reply,
        type="ai"
    )
    db.session.add(ai_msg)
    
    # Store AI response in Pinecone
    store_result, store_message = store_chat_message(
        user_id=g.user_id, 
        message_content=ai_reply, 
        message_id=ai_msg.id, 
        message_type="ai", 
        conversation_id=conversation_id
    )
    
    if not store_result:
        print(f"Warning: Failed to store AI response in Pinecone: {store_message}")
    
    # Update conversation title if it's the first message
    if conversation.title == "New Conversation" and len(user_message) > 0:
        conversation.title = user_message[:50] + "..." if len(user_message) > 50 else user_message
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error saving conversation: {str(e)}"}), 500

    # Return the response in the expected format
    return jsonify({
        "response": ai_reply,  # Changed from "message" back to "response" to match expected format
        "conversationId": conversation_id,
        "userMessageId": user_msg.id,
        "aiMessageId": ai_msg.id
    })