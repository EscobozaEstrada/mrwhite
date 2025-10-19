"""
Document Prompts - Specialized prompts for document processing and analysis
Contains all document-related prompts and analysis templates
"""

from typing import Dict, Any, Optional, List

class DocumentPrompts:
    """
    Centralized prompt management for document service
    """
    
    DOCUMENT_ANALYSIS_SYSTEM_PROMPT = """You are Dr. White's Document Analysis Assistant, specialized in analyzing and extracting insights from various types of documents related to dog care, training, health, and pet ownership.

Key capabilities:
1. Analyze and summarize document content accurately
2. Extract key information, dates, and action items
3. Identify important health information, training instructions, or legal requirements
4. Provide clear, structured analysis in easy-to-understand format
5. Flag important warnings, deadlines, or critical information
6. Maintain context awareness for pet-related documents

Always provide thorough, accurate analysis while highlighting the most important and actionable information for pet owners."""

    DOCUMENT_QA_SYSTEM_PROMPT = """You are Dr. White's Document Q&A Assistant. You answer questions based strictly on the provided document content.

Guidelines:
1. Answer questions based ONLY on the provided document content
2. If information isn't in the documents, clearly state this
3. Provide specific references to the source documents when possible
4. Maintain accuracy - don't infer beyond what's explicitly stated
5. For health-related documents, emphasize consulting professionals when appropriate
6. Structure answers clearly with relevant document excerpts as support

Always be precise and cite your sources from the provided documents."""

    def get_document_summary_prompt(self, text_content: str, filename: str) -> str:
        """Get prompt for document summarization"""
        return f"""Analyze and summarize this document:

Document: {filename}
Content Length: {len(text_content)} characters

Document Content:
{text_content[:3000]}{'...' if len(text_content) > 3000 else ''}

Please provide a comprehensive summary including:
1. Main topic and purpose of the document
2. Key information and important points
3. Any dates, deadlines, or time-sensitive information
4. Action items or instructions (if any)
5. Important warnings or considerations

Keep the summary concise but comprehensive (200-300 words).

Summary:"""

    def get_general_document_analysis_prompt(
        self, 
        document_text: str, 
        filename: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get prompt for general document analysis"""
        context_info = ""
        if context:
            context_info = f"\nContext: {context.get('description', 'General document analysis')}"
        
        return f"""Analyze this document comprehensively:

Document: {filename}{context_info}
Content: {document_text[:4000]}{'...' if len(document_text) > 4000 else ''}

Provide detailed analysis covering:
1. Document type and primary purpose
2. Key topics and main themes
3. Important information and highlights
4. Critical dates, deadlines, or time-sensitive items
5. Action items or next steps (if applicable)
6. Potential concerns or important considerations
7. Overall assessment and recommendations

Structure your response with clear headings and bullet points for easy reading.

Analysis:"""

    def get_health_document_analysis_prompt(
        self, 
        document_text: str, 
        filename: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get prompt for health/medical document analysis"""
        pet_info = ""
        if context and context.get("pet_info"):
            pet_info = f"\nPet Information: {context['pet_info']}"
        
        return f"""Analyze this health/medical document for pet care:

Medical Document: {filename}{pet_info}
Content: {document_text[:4000]}{'...' if len(document_text) > 4000 else ''}

Provide medical document analysis focusing on:
1. Type of medical document (vet records, test results, prescriptions, etc.)
2. Pet health information and medical history
3. Diagnoses, conditions, or health concerns mentioned
4. Medications, treatments, or prescribed care
5. Important dates (visit dates, medication schedules, follow-up appointments)
6. Critical health alerts or warnings
7. Veterinary recommendations and care instructions
8. Any concerning symptoms or conditions requiring attention

⚠️ Important: Always recommend consulting with a veterinarian for medical interpretation and decisions.

Medical Analysis:"""

    def get_training_document_analysis_prompt(
        self, 
        document_text: str, 
        filename: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get prompt for training document analysis"""
        return f"""Analyze this dog training document:

Training Document: {filename}
Content: {document_text[:4000]}{'...' if len(document_text) > 4000 else ''}

Provide training analysis covering:
1. Training methodology or approach described
2. Specific commands, techniques, or exercises
3. Training schedule or progression plan
4. Behavioral issues being addressed
5. Equipment or tools mentioned
6. Safety considerations and precautions
7. Expected outcomes and timeline
8. Tips for consistency and success
9. Common mistakes to avoid

Focus on practical, actionable training guidance that pet owners can follow safely.

Training Analysis:"""

    def get_legal_document_analysis_prompt(
        self, 
        document_text: str, 
        filename: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get prompt for legal document analysis"""
        return f"""Analyze this legal document related to pet ownership:

Legal Document: {filename}
Content: {document_text[:4000]}{'...' if len(document_text) > 4000 else ''}

Provide legal analysis focusing on:
1. Type of legal document (contract, agreement, policy, regulations, etc.)
2. Key legal obligations and responsibilities
3. Important terms and conditions
4. Rights and protections provided
5. Critical deadlines or compliance requirements
6. Potential legal implications or consequences
7. Required actions or documentation
8. Important clauses or restrictions

⚠️ Legal Notice: This analysis is for informational purposes only. Consult with a qualified attorney for legal advice.

Legal Analysis:"""

    def build_document_qa_prompt(
        self, 
        question: str, 
        document_context: List[Dict[str, Any]]
    ) -> str:
        """Build Q&A prompt based on document context"""
        context_text = ""
        
        for i, doc in enumerate(document_context):
            filename = doc.get("metadata", {}).get("filename", f"Document {i+1}")
            content = doc.get("content", "")
            context_text += f"\n--- {filename} ---\n{content}\n"
        
        return f"""Based on the following documents, please answer this question:

Question: {question}

Document Context:
{context_text}

Instructions:
1. Answer based ONLY on the information provided in the documents above
2. If the answer isn't in the documents, clearly state "This information is not available in the provided documents"
3. Quote specific parts of the documents to support your answer
4. If multiple documents contain relevant information, reference them clearly
5. For health-related questions, remind users to consult their veterinarian

Answer:"""

    def get_document_comparison_prompt(
        self, 
        documents: List[Dict[str, Any]], 
        comparison_aspect: str = "general"
    ) -> str:
        """Get prompt for comparing multiple documents"""
        doc_summaries = ""
        
        for i, doc in enumerate(documents):
            filename = doc.get("filename", f"Document {i+1}")
            content = doc.get("content", "")[:1000]  # First 1000 chars
            doc_summaries += f"\n--- Document {i+1}: {filename} ---\n{content}...\n"
        
        return f"""Compare these documents focusing on {comparison_aspect}:

{doc_summaries}

Provide a comprehensive comparison including:
1. Similarities between the documents
2. Key differences and unique information
3. Conflicting information (if any)
4. Complementary information that works together
5. Overall assessment and recommendations
6. Which document is most relevant for specific use cases

Comparison Analysis:"""

    def get_document_extraction_prompt(
        self, 
        document_text: str, 
        extraction_type: str
    ) -> str:
        """Get prompt for extracting specific information from documents"""
        if extraction_type == "dates":
            return f"""Extract all dates and time-sensitive information from this document:

{document_text[:3000]}

Find and list:
1. Specific dates (appointments, deadlines, etc.)
2. Date ranges or periods
3. Recurring schedules or intervals
4. Expiration dates or validity periods
5. Time-sensitive actions or requirements

Format each item with the date and its context/purpose.

Extracted Dates:"""
        
        elif extraction_type == "contacts":
            return f"""Extract all contact information from this document:

{document_text[:3000]}

Find and list:
1. Names of people, veterinarians, or businesses
2. Phone numbers
3. Email addresses
4. Physical addresses
5. Website URLs
6. Professional titles or specializations

Format as a structured list with clear labels.

Extracted Contacts:"""
        
        elif extraction_type == "medications":
            return f"""Extract all medication and treatment information from this document:

{document_text[:3000]}

Find and list:
1. Medication names and dosages
2. Administration instructions
3. Frequency and duration
4. Side effects or warnings
5. Treatment protocols
6. Prescription information

Format as a clear, organized list with dosage and instruction details.

Extracted Medications:"""
        
        else:
            return f"""Extract key information from this document focusing on {extraction_type}:

{document_text[:3000]}

Please identify and extract all relevant information related to {extraction_type}, organizing it in a clear, structured format.

Extracted Information:"""

    def get_document_translation_prompt(self, document_text: str, target_language: str = "simple_english") -> str:
        """Get prompt for translating complex documents to simpler language"""
        return f"""Translate this document into {target_language} while preserving all important information:

Original Document:
{document_text[:3000]}

Please rewrite this document to be:
1. Easy to understand for pet owners
2. Clear and concise
3. Free of unnecessary jargon
4. Well-organized with clear sections
5. Focused on actionable information

Maintain all critical details while making it more accessible.

Simplified Version:"""

    def get_document_validation_prompt(self, document_text: str, document_type: str) -> str:
        """Get prompt for validating document completeness and accuracy"""
        return f"""Validate this {document_type} document for completeness and potential issues:

Document Content:
{document_text[:3000]}

Please check for:
1. Missing information typical for this document type
2. Inconsistencies or contradictions
3. Unclear or ambiguous language
4. Missing critical details or requirements
5. Potential errors or concerns
6. Completeness assessment

Provide recommendations for improvement or clarification.

Validation Report:"""