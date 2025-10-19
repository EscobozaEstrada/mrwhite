from flask import Blueprint, request, jsonify, g, make_response, current_app
from app.utils.openai_helper import get_mr_white_response
from app.utils.file_handler import extract_and_store, query_user_docs, store_chat_message, query_chat_history
from app.utils.langgraph_helper_enhanced import process_with_enhanced_graph
from app import db
from app.models.conversation import Conversation
from app.models.message import Message, Attachment
from app.models.user import User
from app.utils.jwt import decode_token
from app.middleware.usage_limits import check_chat_usage, check_document_usage, check_conversation_usage
from app.middleware.credit_middleware import require_chat_credits
from datetime import datetime, timezone
import os
from werkzeug.utils import secure_filename
from langchain_openai import ChatOpenAI
from flask import Flask, request, jsonify
from flask_cors import CORS

from langchain_openai import ChatOpenAI
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
    
    # Process uploaded files
    processed_files = []
    file_processing_results = []
    processed_documents = []  # Track only document files
    all_files_processed_successfully = True  # Flag to track if all files were processed successfully
    
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
                # Check if it's an image or a document
                if file.content_type.startswith('image/'):
                    print(f"Handling image file: {file.filename}")
                    # Use the new ImageService for comprehensive image processing
                    try:
                        from app.services.image_service import image_service
                        
                        success, message, image_data = image_service.process_image_upload(
                            file=file,
                            user_id=g.user_id,
                            conversation_id=conversation_id,
                            message_id=user_msg.id  # NOW we have the correct message_id
                        )
                        
                        if success:
                            processed_files.append({
                                'type': 'image',
                                'name': image_data['original_filename'],
                                'url': image_data['url'],
                                'description': image_data['description'],
                                'image_id': image_data['id'],
                                'metadata': image_data['metadata']
                            })
                            
                            # Add AI description to file processing results for user feedback
                            file_processing_results.append(
                                f"✅ Image '{image_data['original_filename']}' analyzed: {image_data['description'][:100]}..."
                            )
                            
                            print(f"Successfully processed image with OpenAI analysis: {image_data['description'][:50]}...")
                        else:
                            # Don't fail completely - treat as warning for image processing
                            print(f"Image processing failed: {message}")
                            file_processing_results.append(f"⚠️  Image '{file.filename}': {message}")
                            
                            # Still add to processed files as a basic file attachment
                            processed_files.append({
                                'type': 'image',
                                'name': file.filename,
                                'url': f"/uploads/{file.filename}",  # Fallback URL
                                'description': f"Image upload failed: {message}",
                                'image_id': None,
                                'metadata': {}
                            })
                            
                    except Exception as e:
                        # Log the error but don't fail the entire request
                        print(f"Exception in image processing: {str(e)}")
                        file_processing_results.append(f"⚠️  Image '{file.filename}': Processing error")
                        
                        # Still add to processed files as a basic file attachment
                        processed_files.append({
                            'type': 'image',
                            'name': file.filename,
                            'url': f"/uploads/{file.filename}",  # Fallback URL
                            'description': f"Image processing encountered an error",
                            'image_id': None,
                            'metadata': {}
                        })
                else:
                    print(f"Handling document file: {file.filename}")
                    # For documents (PDF, TXT), process and store in Pinecone
                    try:
                        success, message, s3_url = extract_and_store(file, g.user_id)
                        print(f"Document processing result: success={success}, message={message}, url={s3_url}")
                        file_processing_results.append(message)
                        
                        if success:
                            processed_files.append({
                                'type': 'file',
                                'name': file.filename,
                                'url': s3_url if s3_url else f"/uploads/{file.filename}"
                            })
                            processed_documents.append(file.filename)
                        else:
                            all_files_processed_successfully = False
                            print(f"Failed to process document: {file.filename}")
                    except Exception as e:
                        all_files_processed_successfully = False
                        error_msg = f"Error processing {file.filename}: {str(e)}"
                        print(error_msg)
                        file_processing_results.append(error_msg)
    
    # If file processing failed and this was a file upload request, return an error
    if files and context == "file_upload" and not all_files_processed_successfully:
        return jsonify({
            "message": "Error processing files",
            "details": file_processing_results
        }), 500

    print(f"Processed files: {processed_files}")
    
    # Save attachments if any
    for attachment_data in processed_files:
        attachment = Attachment(
            message_id=user_msg.id,
            type=attachment_data.get('type', 'file'),
            url=attachment_data.get('url', ''),
            name=attachment_data.get('name', '')
        )
        db.session.add(attachment)
        
    # Create a variable to hold the storage tool response
    storage_response = None
        
    # If files were uploaded, directly call the storage tool
    if files and len(processed_files) > 0:
        # Prepare a descriptive message about the files for the storage tool
        file_info = ""
        if processed_documents:
            file_info += f"Documents: {', '.join(processed_documents)}. "
        
        # Add attachment details
        for attachment in processed_files:
            file_info += f"{attachment.get('type', 'file')}: {attachment.get('name', 'unnamed')}. "
        
        print(f"Calling storage tool directly with file_info: {file_info}")
        
        # Call the storage tool directly
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
        from app.services.enhanced_chat_service import EnhancedChatService
        
        # Create service instance for reminder detection
        enhanced_service = EnhancedChatService()
        
        # Check if this is a reminder request
        if enhanced_service._is_reminder_request(user_message):
            current_app.logger.info("🤖 AI Agent detected reminder request in regular chat")
            
            # Extract reminder details
            reminder_details = enhanced_service._extract_reminder_details_ai(user_message, g.user_id)
            
            if reminder_details.get("is_reminder_request", False) and reminder_details.get("confidence", 0) > 0.3:
                current_app.logger.info(f"🎯 AI Agent extracted reminder: {reminder_details}")
                
                # Create the reminder
                success, create_message, reminder_info = enhanced_service._create_health_reminder(g.user_id, reminder_details)
                
                if success:
                    # Generate confirmation response
                    ai_reply = enhanced_service._generate_reminder_confirmation_response(
                        reminder_details, reminder_info, user_message
                    )
                    
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
                    
                    # Commit changes
                    db.session.commit()
                    
                    current_app.logger.info(f"✅ AI Agent successfully created reminder via regular chat")
                    
                    return jsonify({
                        "response": ai_reply,
                        "conversationId": conversation_id,
                        "userMessageId": user_msg.id,
                        "aiMessageId": ai_msg.id,
                        "ai_agent_action": "reminder_created",
                        "reminder_info": reminder_info
                    })
                else:
                    # Failed to create reminder, but still respond helpfully
                    ai_reply = f"I understand you'd like me to remind you about {reminder_details.get('title', 'that task')}. I had a small issue setting up the reminder automatically, but I can still help you with pet care advice! You can also create reminders manually in your Reminders page."
                    
                    # Save AI response
                    ai_msg = Message(
                        conversation_id=conversation_id,
                        content=ai_reply,
                        type="ai"
                    )
                    db.session.add(ai_msg)
                    db.session.commit()
                    
                    return jsonify({
                        "response": ai_reply,
                        "conversationId": conversation_id,
                        "userMessageId": user_msg.id,
                        "aiMessageId": ai_msg.id,
                        "ai_agent_action": "reminder_failed",
                        "error": create_message
                    })
    except Exception as e:
        current_app.logger.error(f"Error in AI agent flow: {str(e)}")
        # Continue with regular chat flow
        pass

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
        if files and any(f.content_type.startswith('image/') for f in files if f.filename):
            # Build image analysis response
            image_analyses = []
            for attachment in processed_files:
                if attachment.get('type') == 'image' and attachment.get('description'):
                    image_analyses.append(f"📸 **{attachment.get('name')}**: {attachment.get('description')}")
            
            if image_analyses:
                # Create a comprehensive response with AI analysis
                if user_message and user_message.strip():
                    # User provided a message with the image
                    ai_reply = f"I can see you've uploaded an image! Here's what I found:\n\n{chr(10).join(image_analyses)}\n\n{user_message}"
                    
                    # Get additional context-aware response
                    try:
                        enhanced_message = f"User uploaded an image and said: '{user_message}'. Image analysis: {chr(10).join(image_analyses)}"
                        context_response = get_mr_white_response(enhanced_message, "image_upload", conversation_history)
                        ai_reply = context_response
                    except Exception as e:
                        print(f"Error getting context response for image: {e}")
                        # Fall back to basic response
                        ai_reply = f"I can see your image! Here's what I found:\n\n{chr(10).join(image_analyses)}\n\nHow can I help you with this image?"
                else:
                    # No user message, just image upload
                    ai_reply = f"I can see you've uploaded an image! Here's what I found:\n\n{chr(10).join(image_analyses)}\n\nWhat would you like to know about this image?"
            else:
                # Image processing failed, use storage response as fallback
                ai_reply = storage_response if storage_response else "I received your image, but I'm having trouble analyzing it right now. Please try again or let me know if you need help!"
        
        # 📄 Handle document uploads 
        elif files and context == "file_upload":
            # Create a clear message about processed documents
            file_message = ""
            if processed_documents:
                doc_list = ", ".join(processed_documents)
                file_message = f"I've uploaded {len(processed_documents)} document(s): {doc_list}. These have been successfully added to your knowledge base. You can now ask questions about them."
            
            # Enhance the message with file processing results
            enhanced_message = f"{user_message}\n\n{file_message}"
            
            # Log the enhanced message for debugging
            print(f"Enhanced message for file upload: {enhanced_message}")
                
            ai_reply = get_mr_white_response(enhanced_message, context, conversation_history)
        
        # 💬 Regular chat without files
        else:
            # 🚀 NEW: Use EnhancedChatService with common knowledge integration for ALL regular chat
            try:
                current_app.logger.info("🔥 Using EnhancedChatService with common knowledge integration for regular chat")
                
                # Create enhanced chat service instance
                enhanced_service = EnhancedChatService()
                
                # Build context for enhanced service
                context_data = {
                    'conversation_history': [{
                        'content': msg['content'],
                        'type': msg['type'],
                        'is_current_conversation': True
                    } for msg in conversation_history]
                }
                
                # Generate enhanced response with common knowledge
                ai_reply = enhanced_service._generate_health_response(user_message, context_data, g.user_id)
                
                current_app.logger.info(f"✅ Enhanced response generated with common knowledge integration")
                
            except Exception as e:
                current_app.logger.error(f"Error with EnhancedChatService: {str(e)}")
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
                    ai_reply = get_mr_white_response(user_message, context, conversation_history)
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

    return jsonify({
        "response": ai_reply,
        "conversationId": conversation_id,
        "userMessageId": user_msg.id,
        "aiMessageId": ai_msg.id
    })