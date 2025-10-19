"""
Document Upload API Routes
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Dict, Any
import logging

from middleware.auth import require_auth
from services.document_service import DocumentService

router = APIRouter()
logger = logging.getLogger(__name__)

# File size limit: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'txt',
    'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff'
}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: Optional[int] = Form(None),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Upload and process a document (ChatGPT-style pre-processing)
    
    Steps:
    1. Get or create conversation (if not provided)
    2. Upload to S3
    3. Extract text
    4. Chunk and store in Pinecone
    5. Return document metadata
    
    Frontend shows loading state during this process.
    """
    try:
        user_id = current_user["id"]
        
        # If no conversation_id provided (None or 0), get or create active conversation
        if not conversation_id or conversation_id == 0:
            from models import Conversation
            from models.base import AsyncSessionLocal
            from sqlalchemy import select, and_
            
            async with AsyncSessionLocal() as session:
                # Try to get active (non-archived) conversation
                result = await session.execute(
                    select(Conversation)
                    .where(and_(
                        Conversation.user_id == user_id,
                        Conversation.is_archived == False
                    ))
                    .order_by(Conversation.updated_at.desc())
                    .limit(1)
                )
                conversation = result.scalar_one_or_none()
                
                # If no active conversation, create one
                if not conversation:
                    from datetime import datetime
                    conversation = Conversation(
                        user_id=user_id,
                        title="New Chat",
                        is_archived=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(conversation)
                    await session.commit()
                    await session.refresh(conversation)
                    logger.info(f"✅ Created new conversation {conversation.id} for document upload")
                
                conversation_id = conversation.id
        
        logger.info(f"📎 Uploading document to conversation {conversation_id}")
        
        # Validate file extension
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '.{file_ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Process document
        document_service = DocumentService()
        result = await document_service.upload_and_process_document(
            user_id=user_id,
            conversation_id=conversation_id,
            file_content=file_content,
            filename=filename,
            content_type=file.content_type or 'application/octet-stream'
        )
        
        logger.info(f"Document uploaded successfully: {result['id']}")
        
        return {
            "success": True,
            "document": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/batch-upload")
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    conversation_id: int = Form(...),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Upload multiple documents at once
    Maximum 5 documents per request
    """
    try:
        user_id = current_user["id"]
        
        # Limit number of files
        if len(files) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 documents allowed per message"
            )
        
        document_service = DocumentService()
        results = []
        errors = []
        
        for file in files:
            try:
                # Validate
                filename = file.filename
                file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                
                if file_ext not in ALLOWED_EXTENSIONS:
                    errors.append({
                        "filename": filename,
                        "error": f"File type not allowed: .{file_ext}"
                    })
                    continue
                
                file_content = await file.read()
                file_size = len(file_content)
                
                if file_size > MAX_FILE_SIZE:
                    errors.append({
                        "filename": filename,
                        "error": f"File too large (max {MAX_FILE_SIZE / 1024 / 1024}MB)"
                    })
                    continue
                
                if file_size == 0:
                    errors.append({
                        "filename": filename,
                        "error": "File is empty"
                    })
                    continue
                
                # Process
                result = await document_service.upload_and_process_document(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    file_content=file_content,
                    filename=filename,
                    content_type=file.content_type or 'application/octet-stream'
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process {file.filename}: {e}")
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return {
            "success": len(results) > 0,
            "documents": results,
            "errors": errors if errors else None,
            "total": len(files),
            "successful": len(results),
            "failed": len(errors)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


@router.get("/status/{document_id}")
async def get_document_status(
    document_id: int,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get processing status of a document"""
    try:
        from sqlalchemy import text
        from models.base import AsyncSessionLocal
        
        user_id = current_user["id"]
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT id, filename, file_type, file_size, s3_url,
                           processing_status, error_message, chunk_count,
                           pinecone_vectors_stored, created_at
                    FROM ic_documents
                    WHERE id = :doc_id AND user_id = :user_id
                """),
                {"doc_id": document_id, "user_id": user_id}
            )
            row = result.first()
            
            if not row:
                raise HTTPException(status_code=404, detail="Document not found")
            
            return {
                "id": row[0],
                "filename": row[1],
                "file_type": row[2],
                "file_size": row[3],
                "s3_url": row[4],
                "status": row[5],
                "error": row[6],
                "chunk_count": row[7],
                "vectors_stored": row[8],
                "created_at": row[9].isoformat() if row[9] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Delete a document (soft delete)"""
    try:
        from sqlalchemy import text
        from models.base import AsyncSessionLocal
        from datetime import datetime
        
        user_id = current_user["id"]
        
        async with AsyncSessionLocal() as session:
            # Verify ownership
            result = await session.execute(
                text("SELECT user_id FROM ic_documents WHERE id = :doc_id"),
                {"doc_id": document_id}
            )
            row = result.first()
            
            if not row:
                raise HTTPException(status_code=404, detail="Document not found")
            
            if row[0] != user_id:
                raise HTTPException(status_code=403, detail="Not authorized")
            
            # Soft delete
            await session.execute(
                text("""
                    UPDATE ic_documents 
                    SET is_deleted = true, updated_at = :now
                    WHERE id = :doc_id
                """),
                {"doc_id": document_id, "now": datetime.utcnow()}
            )
            await session.commit()
        
        return {"success": True, "message": "Document deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))



