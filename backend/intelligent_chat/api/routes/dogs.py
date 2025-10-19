"""
Dog Profile API Routes for Intelligent Chat
CRUD operations for ic_dog_profiles table
"""
import logging
import json
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from datetime import datetime

from models.base import get_db
from middleware.auth import require_auth
from schemas.dog_profile import (
    DogProfileCreate,
    DogProfileUpdate,
    DogProfileResponse,
    DogProfileListResponse,
    DogProfileDeleteResponse
)
from services.s3_service import s3_service
from services.vision_service import vision_service
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dogs", tags=["Dog Profiles"])


class ImageUploadRequest(BaseModel):
    """Request schema for image upload with dog context"""
    image_data: str  # base64 encoded image
    dog_name: str
    breed: str | None = None
    age: int | None = None
    gender: str | None = None
    color: str | None = None


class ImageUploadResponse(BaseModel):
    """Response schema for image upload"""
    image_url: str
    image_description: str


class VetReportUploadRequest(BaseModel):
    """Request schema for vet report upload"""
    dog_id: int
    file_data: str
    filename: str
    content_type: str


class VetReportUploadResponse(BaseModel):
    """Response schema for vet report upload"""
    s3_url: str
    status: str
    document_id: int


@router.post("", response_model=DogProfileResponse, status_code=201)
async def create_dog_profile(
    dog_data: DogProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Create a new dog profile in ic_dog_profiles table
    """
    try:
        user_id = current_user["id"]
        
        # Prepare data
        dog_dict = dog_data.model_dump(exclude_unset=True)
        
        # Convert JSONB field to JSON string
        if "comprehensive_profile" in dog_dict and dog_dict["comprehensive_profile"]:
            dog_dict["comprehensive_profile"] = json.dumps(dog_dict["comprehensive_profile"])
        else:
            dog_dict["comprehensive_profile"] = '{}'
        
        # Insert into ic_dog_profiles
        insert_query = text("""
            INSERT INTO ic_dog_profiles 
            (user_id, name, breed, age, date_of_birth, weight, gender, color, 
             image_url, image_description, comprehensive_profile, created_at, updated_at)
            VALUES 
            (:user_id, :name, :breed, :age, :date_of_birth, :weight, :gender, :color,
             :image_url, :image_description, :comprehensive_profile, :created_at, :updated_at)
            RETURNING id, user_id, name, breed, age, date_of_birth, weight, gender, color,
                      image_url, image_description, comprehensive_profile, created_at, updated_at
        """)
        
        params = {
            "user_id": user_id,
            "name": dog_dict.get("name"),
            "breed": dog_dict.get("breed"),
            "age": dog_dict.get("age"),
            "date_of_birth": dog_dict.get("date_of_birth"),
            "weight": dog_dict.get("weight"),
            "gender": dog_dict.get("gender"),
            "color": dog_dict.get("color"),
            "image_url": dog_dict.get("image_url"),
            "image_description": dog_dict.get("image_description"),
            "comprehensive_profile": dog_dict.get("comprehensive_profile"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.execute(insert_query, params)
        await db.commit()
        
        row = result.fetchone()
        
        # Parse JSONB back to dict
        comprehensive_profile = row[11]
        if isinstance(comprehensive_profile, str):
            comprehensive_profile = json.loads(comprehensive_profile)
        
        response_data = {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "breed": row[3],
            "age": row[4],
            "date_of_birth": row[5],
            "weight": float(row[6]) if row[6] else None,
            "gender": row[7],
            "color": row[8],
            "image_url": row[9],
            "image_description": row[10],
            "comprehensive_profile": comprehensive_profile,
            "created_at": row[12],
            "updated_at": row[13]
        }
        
        logger.info(f"✅ Created dog profile: {response_data['name']} for user {user_id}")
        return DogProfileResponse(**response_data)
        
    except Exception as e:
        logger.error(f"❌ Create dog profile failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create dog profile: {str(e)}")


@router.get("", response_model=DogProfileListResponse)
async def list_dog_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get all dog profiles for the current user from ic_dog_profiles
    """
    try:
        user_id = current_user["id"]
        
        query = text("""
            SELECT id, user_id, name, breed, age, date_of_birth, weight, gender, color,
                   image_url, image_description, comprehensive_profile, created_at, updated_at
            FROM ic_dog_profiles
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        dogs = []
        for row in rows:
            # Parse JSONB
            comprehensive_profile = row[11]
            if isinstance(comprehensive_profile, str):
                comprehensive_profile = json.loads(comprehensive_profile)
            
            dog = {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "breed": row[3],
                "age": row[4],
                "date_of_birth": row[5],
                "weight": float(row[6]) if row[6] else None,
                "gender": row[7],
                "color": row[8],
                "image_url": row[9],
                "image_description": row[10],
                "comprehensive_profile": comprehensive_profile,
                "created_at": row[12],
                "updated_at": row[13]
            }
            dogs.append(DogProfileResponse(**dog))
        
        logger.info(f"✅ Retrieved {len(dogs)} dog profiles for user {user_id}")
        return DogProfileListResponse(dogs=dogs)
        
    except Exception as e:
        logger.error(f"❌ List dog profiles failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dog profiles: {str(e)}")


@router.get("/{dog_id}", response_model=DogProfileResponse)
async def get_dog_profile(
    dog_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get a specific dog profile by ID
    """
    try:
        user_id = current_user["id"]
        
        query = text("""
            SELECT id, user_id, name, breed, age, date_of_birth, weight, gender, color,
                   image_url, image_description, comprehensive_profile, created_at, updated_at
            FROM ic_dog_profiles
            WHERE id = :dog_id AND user_id = :user_id
        """)
        
        result = await db.execute(query, {"dog_id": dog_id, "user_id": user_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Dog profile not found")
        
        # Parse JSONB
        comprehensive_profile = row[11]
        if isinstance(comprehensive_profile, str):
            comprehensive_profile = json.loads(comprehensive_profile)
        
        dog = {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "breed": row[3],
            "age": row[4],
            "date_of_birth": row[5],
            "weight": float(row[6]) if row[6] else None,
            "gender": row[7],
            "color": row[8],
            "image_url": row[9],
            "image_description": row[10],
            "comprehensive_profile": comprehensive_profile,
            "created_at": row[12],
            "updated_at": row[13]
        }
        
        logger.info(f"✅ Retrieved dog profile {dog_id} for user {user_id}")
        return DogProfileResponse(**dog)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get dog profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dog profile: {str(e)}")


@router.put("/{dog_id}", response_model=DogProfileResponse)
async def update_dog_profile(
    dog_id: int,
    dog_data: DogProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Update a dog profile
    """
    try:
        user_id = current_user["id"]
        
        # Verify ownership
        check_query = text("SELECT id FROM ic_dog_profiles WHERE id = :dog_id AND user_id = :user_id")
        result = await db.execute(check_query, {"dog_id": dog_id, "user_id": user_id})
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Dog profile not found")
        
        # Prepare update data
        update_dict = dog_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Convert JSONB to JSON string
        if "comprehensive_profile" in update_dict and update_dict["comprehensive_profile"]:
            update_dict["comprehensive_profile"] = json.dumps(update_dict["comprehensive_profile"])
        
        # Build UPDATE query
        set_clauses = [f"{col} = :{col}" for col in update_dict.keys()]
        set_clauses.append("updated_at = :updated_at")
        
        update_query = text(f"""
            UPDATE ic_dog_profiles 
            SET {', '.join(set_clauses)}
            WHERE id = :dog_id AND user_id = :user_id
            RETURNING id, user_id, name, breed, age, date_of_birth, weight, gender, color,
                      image_url, image_description, comprehensive_profile, created_at, updated_at
        """)
        
        update_dict["updated_at"] = datetime.utcnow()
        update_dict["dog_id"] = dog_id
        update_dict["user_id"] = user_id
        
        result = await db.execute(update_query, update_dict)
        await db.commit()
        
        row = result.fetchone()
        
        # Parse JSONB
        comprehensive_profile = row[11]
        if isinstance(comprehensive_profile, str):
            comprehensive_profile = json.loads(comprehensive_profile)
        
        dog = {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "breed": row[3],
            "age": row[4],
            "date_of_birth": row[5],
            "weight": float(row[6]) if row[6] else None,
            "gender": row[7],
            "color": row[8],
            "image_url": row[9],
            "image_description": row[10],
            "comprehensive_profile": comprehensive_profile,
            "created_at": row[12],
            "updated_at": row[13]
        }
        
        logger.info(f"✅ Updated dog profile {dog_id} for user {user_id}")
        return DogProfileResponse(**dog)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update dog profile failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update dog profile: {str(e)}")


@router.delete("/{dog_id}", status_code=200)
async def delete_dog_profile(
    dog_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Delete a dog profile and inject context message to inform chatbot
    
    This automatically adds a system message to the conversation so the chatbot
    knows the dog has been removed, without requiring the user to clear their chat.
    """
    try:
        user_id = current_user["id"]
        
        # First, get the dog name for the context message
        dog_query = text("SELECT name FROM ic_dog_profiles WHERE id = :dog_id AND user_id = :user_id")
        dog_result = await db.execute(dog_query, {"dog_id": dog_id, "user_id": user_id})
        dog_row = dog_result.fetchone()
        
        if not dog_row:
            raise HTTPException(status_code=404, detail="Dog profile not found")
        
        dog_name = dog_row[0]
        
        # Delete the dog profile
        delete_query = text("""
            DELETE FROM ic_dog_profiles 
            WHERE id = :dog_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = await db.execute(delete_query, {"dog_id": dog_id, "user_id": user_id})
        
        # Get active conversation (not archived)
        from models.conversation import Conversation
        conv_result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.is_archived == False)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        conversation = conv_result.scalar_one_or_none()
        
        # If there's an active conversation, inject a system context message
        if conversation:
            from models.conversation import Message
            from datetime import datetime
            
            context_message = f"[SYSTEM NOTE: {dog_name}'s profile has been deleted by the user. Do not reference {dog_name} in future responses unless the user specifically asks about past memories with {dog_name}.]"
            
            system_msg = Message(
                conversation_id=conversation.id,
                user_id=user_id,  # Required field!
                role="system",
                content=context_message,
                created_at=datetime.utcnow(),
                is_deleted=False
            )
            db.add(system_msg)
            
            logger.info(f"✅ Injected context message about {dog_name} deletion into conversation {conversation.id}")
        
        await db.commit()
        
        logger.info(f"✅ Deleted dog profile {dog_id} ({dog_name}) for user {user_id}")
        
        return DogProfileDeleteResponse(
            success=True, 
            message=f"{dog_name}'s profile has been deleted successfully.",
            dog_name=dog_name,
            clear_chat_recommended=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete dog profile failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete dog profile: {str(e)}")


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_dog_image(
    request: ImageUploadRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Upload dog image to S3 and generate Claude Vision description
    
    This endpoint:
    1. Uploads the image to S3
    2. Calls Claude Vision to analyze the image with dog context
    3. Returns both the S3 URL and personalized description
    """
    try:
        user_id = current_user["id"]
        
        logger.info(f"📸 Processing image upload for {request.dog_name}...")
        
        # 1. Upload image to S3
        s3_url, clean_image_data = await s3_service.upload_dog_image(
            image_data=request.image_data,
            user_id=user_id,
            dog_name=request.dog_name
        )
        
        # 2. Generate personalized description with Claude Vision
        dog_context = {
            "name": request.dog_name,
            "breed": request.breed,
            "age": request.age,
            "gender": request.gender,
            "color": request.color
        }
        
        image_description = await vision_service.analyze_dog_image(
            image_data=clean_image_data,
            dog_context=dog_context
        )
        
        logger.info(f"✅ Image processed successfully for {request.dog_name}")
        
        return ImageUploadResponse(
            image_url=s3_url,
            image_description=image_description
        )
        
    except Exception as e:
        logger.error(f"❌ Image upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@router.post("/upload-vet-report", response_model=VetReportUploadResponse)
async def upload_vet_report(
    request: VetReportUploadRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Upload vet report for a dog profile
    
    This endpoint:
    1. Uploads the file to S3
    2. Extracts text from PDF/DOC/DOCX/TXT/images
    3. Stores in Pinecone user_docs namespace with dog_id metadata
    4. Returns S3 URL for reference
    """
    try:
        user_id = current_user["id"]
        
        logger.info(f"📋 Processing vet report for dog {request.dog_id}...")
        
        import base64
        
        file_content = base64.b64decode(request.file_data.split(',')[1] if ',' in request.file_data else request.file_data)
        
        document_service = DocumentService()
        
        result = await document_service.upload_and_process_document(
            user_id=user_id,
            conversation_id=None,
            file_content=file_content,
            filename=request.filename,
            content_type=request.content_type,
            dog_profile_id=request.dog_id
        )
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        logger.info(f"✅ Vet report processed successfully for dog {request.dog_id}")
        
        return VetReportUploadResponse(
            s3_url=result["s3_url"],
            status=result["status"],
            document_id=result["id"]
        )
        
    except Exception as e:
        logger.error(f"❌ Vet report upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process vet report: {str(e)}")