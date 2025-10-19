"""
Document-related schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentUploadRequest(BaseModel):
    """Request schema for document upload"""
    conversation_id: int
    file_type: str = Field(..., description="File type: 'image', 'pdf', 'docx', 'txt'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 45,
                "file_type": "pdf"
            }
        }


class DocumentResponse(BaseModel):
    """Response schema for document"""
    id: int
    filename: str
    file_type: str
    file_size: Optional[int]
    s3_url: str
    created_at: str
    extracted_text: Optional[str] = None
    image_analysis: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123,
                "filename": "vet_report.pdf",
                "file_type": "pdf",
                "file_size": 2048576,
                "s3_url": "https://s3.amazonaws.com/bucket/file.pdf",
                "created_at": "2025-10-06T10:30:00Z"
            }
        }


class VetReportResponse(BaseModel):
    """Response schema for vet report"""
    id: int
    dog_profile_id: int
    report_name: str
    report_date: Optional[str]
    s3_url: str
    key_findings: Dict[str, Any]
    created_at: str
    
    class Config:
        from_attributes = True






