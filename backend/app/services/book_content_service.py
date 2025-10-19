#!/usr/bin/env python3
"""
Book Content Service - Handle DOCX processing and content management
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app
from docx import Document
from docx.shared import Inches
from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.table import Table, _Cell
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

from app import db
from app.models.user import User

logger = logging.getLogger(__name__)


class BookContentService:
    """Service for processing and managing book content from DOCX files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_docx_file(self, file_path: str, book_title: str, user_id: int) -> Dict[str, Any]:
        """
        Process a DOCX file and extract structured content
        
        Args:
            file_path: Path to the DOCX file
            book_title: Title of the book
            user_id: ID of the user processing the book
            
        Returns:
            Dictionary containing processed book content
        """
        try:
            self.logger.info(f"📖 Processing DOCX file: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"DOCX file not found: {file_path}")
            
            # Load the document
            doc = Document(file_path)
            
            # Extract content structure
            content_structure = self._extract_content_structure(doc)
            
            # Process chapters/sections
            chapters = self._process_chapters(content_structure)
            
            # Extract metadata
            metadata = self._extract_metadata(doc, book_title)
            
            # Create book data structure
            book_data = {
                'title': book_title,
                'content_type': 'docx_processed',
                'total_pages': len(chapters),
                'total_chapters': len(chapters),
                'chapters': chapters,
                'metadata': metadata,
                'processing_info': {
                    'processed_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': user_id,
                    'source_file': file_path,
                    'total_paragraphs': sum(len(ch.get('paragraphs', [])) for ch in chapters),
                    'total_words': sum(ch.get('word_count', 0) for ch in chapters)
                }
            }
            
            self.logger.info(f"✅ Successfully processed DOCX: {len(chapters)} chapters extracted")
            
            return {
                'success': True,
                'book_data': book_data,
                'message': f'Successfully processed {book_title}'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error processing DOCX file: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing DOCX file: {str(e)}',
                'error': str(e)
            }
    
    def _extract_content_structure(self, doc: DocxDocument) -> List[Dict[str, Any]]:
        """Extract the basic content structure from the document"""
        
        content_blocks = []
        current_block = {
            'type': 'section',
            'elements': []
        }
        
        for element in doc.element.body:
            if isinstance(element, CT_P):
                # It's a paragraph
                paragraph = Paragraph(element, doc)
                para_data = self._process_paragraph(paragraph)
                current_block['elements'].append(para_data)
                
            elif isinstance(element, CT_Tbl):
                # It's a table
                table = Table(element, doc)
                table_data = self._process_table(table)
                current_block['elements'].append(table_data)
        
        if current_block['elements']:
            content_blocks.append(current_block)
        
        return content_blocks
    
    def _process_paragraph(self, paragraph: Paragraph) -> Dict[str, Any]:
        """Process a single paragraph and extract its content and formatting"""
        
        # Determine if this is a heading
        heading_level = self._get_heading_level(paragraph)
        
        # Extract text and formatting
        runs_data = []
        full_text = ""
        
        for run in paragraph.runs:
            run_data = {
                'text': run.text,
                'bold': run.bold,
                'italic': run.italic,
                'underline': run.underline,
                'font_size': run.font.size.pt if run.font.size else None,
                'font_name': run.font.name,
                'color': self._get_color_hex(run.font.color) if run.font.color else None
            }
            runs_data.append(run_data)
            full_text += run.text
        
        # Generate HTML representation
        html_content = self._generate_paragraph_html(paragraph, runs_data, heading_level)
        
        return {
            'type': 'paragraph',
            'heading_level': heading_level,
            'text': full_text.strip(),
            'html': html_content,
            'runs': runs_data,
            'alignment': str(paragraph.alignment) if paragraph.alignment else 'left',
            'word_count': len(full_text.split()) if full_text.strip() else 0,
            'style': paragraph.style.name if paragraph.style else None
        }
    
    def _process_table(self, table: Table) -> Dict[str, Any]:
        """Process a table and extract its content"""
        
        table_data = {
            'type': 'table',
            'rows': [],
            'html': ''
        }
        
        html_rows = []
        
        for row in table.rows:
            row_data = []
            html_cells = []
            
            for cell in row.cells:
                cell_text = cell.text.strip()
                row_data.append(cell_text)
                html_cells.append(f'<td>{cell_text}</td>')
            
            table_data['rows'].append(row_data)
            html_rows.append(f'<tr>{"".join(html_cells)}</tr>')
        
        table_data['html'] = f'<table class="book-table">{"".join(html_rows)}</table>'
        
        return table_data
    
    def _get_heading_level(self, paragraph: Paragraph) -> Optional[int]:
        """Determine if paragraph is a heading and what level"""
        
        if paragraph.style and paragraph.style.name:
            style_name = paragraph.style.name.lower()
            
            if 'heading 1' in style_name:
                return 1
            elif 'heading 2' in style_name:
                return 2
            elif 'heading 3' in style_name:
                return 3
            elif 'heading 4' in style_name:
                return 4
            elif 'heading 5' in style_name:
                return 5
            elif 'heading 6' in style_name:
                return 6
            elif 'title' in style_name:
                return 1
        
        # Check for bold, large text that might be a heading
        if paragraph.runs:
            first_run = paragraph.runs[0]
            if (first_run.bold and 
                first_run.font.size and 
                first_run.font.size.pt > 12 and
                len(paragraph.text.strip()) < 100):
                return 2
        
        return None
    
    def _generate_paragraph_html(self, paragraph: Paragraph, runs_data: List[Dict], heading_level: Optional[int]) -> str:
        """Generate HTML representation of a paragraph"""
        
        if heading_level:
            tag = f'h{heading_level}'
            css_class = f'book-heading-{heading_level}'
        else:
            tag = 'p'
            css_class = 'book-paragraph'
        
        # Process runs to create formatted HTML
        html_content = ""
        for run_data in runs_data:
            text = run_data['text']
            
            # Apply formatting
            if run_data['bold']:
                text = f'<strong>{text}</strong>'
            if run_data['italic']:
                text = f'<em>{text}</em>'
            if run_data['underline']:
                text = f'<u>{text}</u>'
            
            html_content += text
        
        return f'<{tag} class="{css_class}">{html_content}</{tag}>'
    
    def _get_color_hex(self, color) -> Optional[str]:
        """Extract hex color value from font color"""
        try:
            if hasattr(color, 'rgb') and color.rgb:
                rgb = color.rgb
                return f'#{rgb:06x}'
        except:
            pass
        return None
    
    def _process_chapters(self, content_structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process content structure into chapters"""
        
        chapters = []
        current_chapter = {
            'id': 1,
            'title': 'Chapter 1',
            'content': '',
            'html_content': '',
            'paragraphs': [],
            'word_count': 0,
            'page_number': 1
        }
        
        chapter_count = 1
        
        for section in content_structure:
            for element in section['elements']:
                
                # Check if this element should start a new chapter
                if (element['type'] == 'paragraph' and 
                    element['heading_level'] == 1 and 
                    element['text'].strip() and
                    current_chapter['paragraphs']):  # Don't create new chapter if current is empty
                    
                    # Finalize current chapter
                    current_chapter['content'] = '\n'.join(p['text'] for p in current_chapter['paragraphs'])
                    current_chapter['html_content'] = ''.join(p['html'] for p in current_chapter['paragraphs'])
                    chapters.append(current_chapter)
                    
                    # Start new chapter
                    chapter_count += 1
                    current_chapter = {
                        'id': chapter_count,
                        'title': element['text'][:100] if element['text'] else f'Chapter {chapter_count}',
                        'content': '',
                        'html_content': '',
                        'paragraphs': [],
                        'word_count': 0,
                        'page_number': chapter_count
                    }
                
                # Add element to current chapter
                current_chapter['paragraphs'].append(element)
                current_chapter['word_count'] += element.get('word_count', 0)
        
        # Don't forget the last chapter
        if current_chapter['paragraphs']:
            current_chapter['content'] = '\n'.join(p['text'] for p in current_chapter['paragraphs'])
            current_chapter['html_content'] = ''.join(p['html'] for p in current_chapter['paragraphs'])
            chapters.append(current_chapter)
        
        return chapters
    
    def _extract_metadata(self, doc: DocxDocument, book_title: str) -> Dict[str, Any]:
        """Extract metadata from the document"""
        
        try:
            core_props = doc.core_properties
            
            metadata = {
                'title': core_props.title or book_title,
                'author': core_props.author,
                'subject': core_props.subject,
                'created': core_props.created.isoformat() if core_props.created else None,
                'modified': core_props.modified.isoformat() if core_props.modified else None,
                'description': core_props.comments,
                'keywords': core_props.keywords,
                'language': core_props.language,
                'category': core_props.category
            }
            
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Could not extract metadata: {str(e)}")
            return {
                'title': book_title,
                'author': 'Unknown',
                'created': datetime.now(timezone.utc).isoformat()
            }
    
    def save_processed_book(self, book_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Save processed book data to database"""
        
        try:
            from app.models.custom_book import CustomBook, BookChapter
            
            # Create book record
            book = CustomBook(
                user_id=user_id,
                title=book_data['title'],
                description=book_data['metadata'].get('description', ''),
                processing_metadata=book_data['metadata'],  # Store metadata here
                generation_status='completed',
                generation_progress=100,
                total_content_items=book_data['total_pages'],
                book_style='docx_processed',
                word_count=book_data.get('word_count', 0)
            )
            
            db.session.add(book)
            db.session.flush()  # Get the book ID before creating chapters
            
            # Create chapter records
            for chapter_data in book_data['chapters']:
                chapter = BookChapter(
                    book_id=book.id,
                    chapter_number=chapter_data.get('id', chapter_data.get('chapter_number', 1)),
                    title=chapter_data['title'],
                    content_html=chapter_data.get('html_content', chapter_data.get('content', '')),  # Store HTML content here
                    word_count=chapter_data.get('word_count', 0),
                    chapter_metadata={
                        'original_content_length': len(chapter_data.get('content', '')),
                        'processing_timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
                db.session.add(chapter)
            
            db.session.commit()
            
            self.logger.info(f"✅ Saved processed book to database: ID {book.id} with {len(book_data['chapters'])} chapters")
            
            return {
                'success': True,
                'book_id': book.id,
                'message': 'Book saved successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"❌ Error saving book to database: {str(e)}")
            return {
                'success': False,
                'message': f'Error saving book: {str(e)}'
            } 