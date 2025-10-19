import os
import uuid
import logging
from datetime import datetime, timedelta
import pdfkit
import ebooklib
from ebooklib import epub
from flask import current_app, copy_current_request_context
import boto3
from app import db
from app.models.enhanced_book import EnhancedBook, EnhancedBookChapter, MessageCategory
from app.models.message import Message
from app.models.conversation import Conversation
from app.models.image import UserImage
from app.models.user import User
from app.services.ai_service import AIService
from app.services.content_chunking_service import ContentChunkingService, ContentChunk
from app.book_config.book_types import get_book_type_config, get_photo_layout, should_filter_content, get_filter_keywords, CONTENT_THRESHOLDS
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
import functools
import requests
import tempfile
import shutil

# Import intelligent chat models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../intelligent_chat'))
from intelligent_chat.models.conversation import Message as ICMessage
from intelligent_chat.models.document import Document as ICDocument

logger = logging.getLogger(__name__)

class EnhancedBookService:
    """Service for enhanced book creation with categorization and tone customization"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.chunking_service = ContentChunkingService()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION')
        )
        self.s3_bucket = os.environ.get('S3_BUCKET_NAME')
        # Use a smaller number of workers to avoid overloading the system
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def create_enhanced_book(self, user_id, title, tone_type, text_style, categories, cover_image=None, book_type='general'):
        """Create a new enhanced book"""
        try:
            # Create the book record
            book = EnhancedBook(
                user_id=user_id,
                title=title,
                book_type=book_type,
                selected_categories=categories,
                tone_type=tone_type,
                text_style=text_style,
                status='draft',
                cover_image=cover_image
            )
            db.session.add(book)
            db.session.commit()
            
            logger.info(f"✅ Created enhanced book: {title} (type: {book_type}, id: {book.id})")
            return book.to_dict()
        except Exception as e:
            logger.error(f"Error creating enhanced book: {str(e)}")
            db.session.rollback()
            raise
    
    def categorize_messages(self, user_id, book_id, categories):
        """
        Categorize all messages for a user based on provided categories
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Get all user conversations
            conversations = Conversation.query.filter_by(user_id=user_id).all()
            conversation_ids = [conv.id for conv in conversations]
            
            # Get all messages from these conversations
            messages = Message.query.filter(
                Message.conversation_id.in_(conversation_ids),
                Message.type == 'user'  # Only categorize user messages
            ).order_by(Message.created_at).all()
            
            if not messages:
                raise ValueError("No messages found for categorization")
            
            # Prepare messages for categorization
            message_texts = [msg.content for msg in messages]
            message_ids = [msg.id for msg in messages]
            
            # Use hybrid approach to categorize messages
            categorized_messages = self._categorize_with_hybrid_approach(message_texts, message_ids, categories)
            
            # Store categorizations in database
            for category, msg_ids in categorized_messages.items():
                for msg_id in msg_ids:
                    message_category = MessageCategory(
                        message_id=msg_id,
                        category=category,
                        book_id=book_id
                    )
                    db.session.add(message_category)
            
            db.session.commit()
            
            # Update book status
            book.status = 'categorized'
            db.session.commit()
            
            return categorized_messages
        except Exception as e:
            logger.error(f"Error categorizing messages: {str(e)}")
            db.session.rollback()
            raise
    
    def _categorize_with_ai(self, message_texts, message_ids, categories):
        """
        Use AI to categorize messages into provided categories
        """
        try:
            # Prepare prompt for OpenAI
            prompt = f"""
            You are a message categorization assistant. Your task is to categorize the following messages into these categories:
            {', '.join(categories)}
            
            For each message, assign it to the most appropriate category. Some messages may not fit well into any category,
            in which case you should assign them to the category that fits best.
            
            Here are the messages:
            """
            
            for i, text in enumerate(message_texts):
                prompt += f"\nMessage {i+1}: {text}"
            
            prompt += "\n\nRespond with a JSON object where keys are categories and values are arrays of message indices (1-based)."
            
            # Get categorization from OpenAI
            response_text = self.ai_service.generate_completion(
                messages=[{"role": "system", "content": prompt}],
                max_tokens=2000,
                temperature=0.2
            )
            
            # Parse response to get categorizations
            import json
            import re
            
            # Find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("Could not parse AI response")
            
            categorization_json = json.loads(json_match.group(0))
            
            # Convert 1-based indices to actual message IDs
            result = {}
            for category, indices in categorization_json.items():
                result[category] = [message_ids[i-1] for i in indices if 1 <= i <= len(message_ids)]
            
            return result
        except Exception as e:
            logger.error(f"Error in AI categorization: {str(e)}")
            raise

    def _categorize_with_hybrid_approach(self, message_texts, message_ids, categories):
        """
        Use a hybrid TF-IDF + rule-based approach to categorize messages into provided categories
        """
        try:
            # Dictionary of keywords for each category
            category_keywords = {
                'Health': ['health', 'doctor', 'sick', 'medicine', 'hospital', 'pain', 'symptom', 'illness', 'disease', 'medical', 'treatment', 'therapy', 'cure', 'diagnosis', 'patient'],
                'Nutrition': ['food', 'diet', 'eat', 'meal', 'nutrition', 'vitamin', 'calorie', 'protein', 'carbohydrate', 'fat', 'vegetable', 'fruit', 'organic', 'nutrient', 'healthy eating'],
                'Exercise': ['exercise', 'workout', 'gym', 'fitness', 'run', 'training', 'sport', 'cardio', 'strength', 'muscle', 'weight lifting', 'jogging', 'swimming', 'yoga', 'stretching'],
                'Memories': ['remember', 'memory', 'past', 'childhood', 'experience', 'moment', 'recall', 'reminisce', 'nostalgia', 'history', 'old times', 'flashback', 'recollection', 'memorable', 'unforgettable'],
                'Advice': ['advice', 'suggest', 'recommendation', 'tip', 'guidance', 'help', 'counsel', 'insight', 'wisdom', 'suggestion', 'opinion', 'perspective', 'mentor', 'guide', 'consult'],
                'Stories': ['story', 'tale', 'narrative', 'fiction', 'anecdote', 'account', 'adventure', 'episode', 'experience', 'event', 'incident', 'chapter', 'chronicle', 'saga', 'legend'],
                'Questions': ['question', 'ask', 'inquiry', 'query', 'wonder', 'curious', 'how', 'what', 'when', 'where', 'why', 'who', 'which', 'problem', 'doubt'],
                'Reflections': ['reflect', 'think', 'contemplate', 'ponder', 'meditate', 'introspect', 'consider', 'evaluate', 'analyze', 'examine', 'insight', 'perspective', 'viewpoint', 'opinion', 'thought'],
                'Daily Life': ['daily', 'routine', 'everyday', 'regular', 'habit', 'schedule', 'life', 'ordinary', 'common', 'typical', 'usual', 'mundane', 'normal', 'day-to-day', 'lifestyle'],
                'Goals': ['goal', 'aim', 'objective', 'target', 'aspiration', 'ambition', 'purpose', 'intention', 'plan', 'dream', 'desire', 'achievement', 'success', 'milestone', 'vision'],
                'Challenges': ['challenge', 'difficulty', 'obstacle', 'problem', 'hurdle', 'barrier', 'struggle', 'issue', 'complication', 'setback', 'trouble', 'hardship', 'adversity', 'trial', 'test'],
                'Achievements': ['achievement', 'accomplish', 'success', 'victory', 'triumph', 'win', 'attain', 'reach', 'complete', 'achieve', 'milestone', 'breakthrough', 'feat', 'progress', 'advancement']
            }
            
            # Initialize TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words='english',
                max_features=5000,
                ngram_range=(1, 2)  # Consider both single words and bigrams
            )
            
            # Create category documents by joining keywords
            category_docs = {category: ' '.join(keywords) for category, keywords in category_keywords.items() if category in categories}
            
            # Filter to only include requested categories
            available_categories = [cat for cat in categories if cat in category_keywords]
            
            # If no matching categories are found, use a simple keyword matching approach
            if not available_categories:
                return self._categorize_with_simple_rules(message_texts, message_ids, categories)
            
            # Create a list of all documents (category keywords + messages)
            all_docs = list(category_docs.values()) + message_texts
            
            # Fit and transform the documents
            tfidf_matrix = vectorizer.fit_transform(all_docs)
            
            # Get the feature names (words)
            feature_names = vectorizer.get_feature_names_out()
            
            # Initialize results
            result = {category: [] for category in categories}
            
            # For each message, calculate similarity to each category
            for i, message_idx in enumerate(range(len(category_docs), len(all_docs))):
                message_vector = tfidf_matrix[message_idx]
                
                # Calculate similarity scores
                scores = {}
                for j, category in enumerate(category_docs.keys()):
                    category_vector = tfidf_matrix[j]
                    similarity = cosine_similarity(message_vector, category_vector)[0][0]
                    scores[category] = similarity
                
                # Also apply rule-based scoring for better accuracy
                for category in scores.keys():
                    if category in category_keywords:
                        text_lower = message_texts[i].lower()
                        # Count keyword matches and boost score
                        keyword_matches = sum(1 for keyword in category_keywords[category] if keyword.lower() in text_lower)
                        boost_factor = 0.1 * keyword_matches  # Adjust this factor as needed
                        scores[category] += boost_factor
                
                # Assign to highest scoring category if score is above threshold
                if scores:
                    best_category = max(scores.items(), key=lambda x: x[1])[0]
                    if scores[best_category] > 0:  # Threshold can be adjusted
                        result[best_category].append(message_ids[i])
                    else:
                        # If no good match, assign to a default category or the first one
                        default_category = categories[0]
                        result[default_category].append(message_ids[i])
                
            # Ensure all messages are categorized
            categorized_message_ids = [msg_id for cat_msgs in result.values() for msg_id in cat_msgs]
            uncategorized_message_ids = [msg_id for i, msg_id in enumerate(message_ids) if msg_id not in categorized_message_ids]
            
            if uncategorized_message_ids:
                # Assign uncategorized messages to the first category as a fallback
                default_category = categories[0]
                result[default_category].extend(uncategorized_message_ids)
            
            return result
        except Exception as e:
            logger.error(f"Error in hybrid categorization: {str(e)}")
            # Fallback to simple rule-based approach if TF-IDF fails
            return self._categorize_with_simple_rules(message_texts, message_ids, categories)

    def _categorize_with_simple_rules(self, message_texts, message_ids, categories):
        """
        Use simple rule-based system as fallback for categorization
        """
        try:
            # Dictionary of keywords for each category
            category_keywords = {
                'Health': ['health', 'doctor', 'sick', 'medicine', 'hospital'],
                'Nutrition': ['food', 'diet', 'eat', 'meal', 'nutrition'],
                'Exercise': ['exercise', 'workout', 'gym', 'fitness', 'run'],
                'Memories': ['remember', 'memory', 'past', 'childhood', 'experience'],
                'Advice': ['advice', 'suggest', 'recommendation', 'tip', 'guidance'],
                'Stories': ['story', 'tale', 'narrative', 'fiction', 'anecdote'],
                'Questions': ['question', 'ask', 'inquiry', 'query', 'wonder'],
                'Reflections': ['reflect', 'think', 'contemplate', 'ponder', 'meditate'],
                'Daily Life': ['daily', 'routine', 'everyday', 'regular', 'habit'],
                'Goals': ['goal', 'aim', 'objective', 'target', 'aspiration'],
                'Challenges': ['challenge', 'difficulty', 'obstacle', 'problem', 'hurdle'],
                'Achievements': ['achievement', 'accomplish', 'success', 'victory', 'triumph']
            }
            
            # Initialize results
            result = {category: [] for category in categories}
            
            # Process each message
            for i, text in enumerate(message_texts):
                text_lower = text.lower()
                
                # Calculate scores for each category
                scores = {}
                for category in categories:
                    if category in category_keywords:
                        # Count keyword matches
                        score = sum(1 for keyword in category_keywords[category] 
                                   if keyword in text_lower)
                        scores[category] = score
                
                # Assign to highest scoring category
                if scores:
                    best_category = max(scores.items(), key=lambda x: x[1])[0]
                    if scores[best_category] > 0:  # Only categorize if at least one keyword matched
                        result[best_category].append(message_ids[i])
                    else:
                        # If no matches, assign to first category
                        result[categories[0]].append(message_ids[i])
                else:
                    # If no categories matched, assign to first category
                    result[categories[0]].append(message_ids[i])
            
            return result
        except Exception as e:
            logger.error(f"Error in rule-based categorization: {str(e)}")
            
            # Last resort fallback - distribute messages evenly across categories
            result = {category: [] for category in categories}
            messages_per_category = len(message_ids) // len(categories)
            
            for i, category in enumerate(categories):
                start_idx = i * messages_per_category
                end_idx = start_idx + messages_per_category if i < len(categories) - 1 else len(message_ids)
                result[category] = message_ids[start_idx:end_idx]
            
            return result
    
    def _get_all_user_images(self, user_id, date_range_start=None, date_range_end=None):
        """Fetch ALL images from both old and new systems"""
        images = []
        
        try:
            # 1. Get OLD system images (user_images table)
            old_images_query = db.session.query(UserImage)\
                .filter_by(user_id=user_id, is_deleted=False)
            
            if date_range_start:
                old_images_query = old_images_query.filter(UserImage.created_at >= date_range_start)
            if date_range_end:
                old_images_query = old_images_query.filter(UserImage.created_at <= date_range_end)
            
            for img in old_images_query.all():
                images.append({
                    'source': 'user_images',
                    'id': img.id,
                    's3_url': img.s3_url,
                    'description': img.description or '',
                    'created_at': img.created_at,
                    'categories': img.analysis_data.get('categories', []) if img.analysis_data else [],
                    'emotional_tone': img.analysis_data.get('emotional_tone') if img.analysis_data else None
                })
            
            # 2. Get NEW system images (ic_documents table)
            new_images_query = db.session.query(ICDocument)\
                .filter(
                    ICDocument.user_id == user_id,
                    ICDocument.file_type.in_(['jpg', 'jpeg', 'png', 'gif', 'webp', 'image']),
                    ICDocument.is_deleted == False
                )
            
            if date_range_start:
                new_images_query = new_images_query.filter(ICDocument.created_at >= date_range_start)
            if date_range_end:
                new_images_query = new_images_query.filter(ICDocument.created_at <= date_range_end)
            
            for img in new_images_query.all():
                images.append({
                    'source': 'ic_documents',
                    'id': img.id,
                    's3_url': img.s3_url,
                    'description': img.extracted_text or '',
                    'created_at': img.created_at,
                    'categories': img.image_analysis.get('categories', []) if img.image_analysis else [],
                    'file_type': img.file_type
                })
            
            # Sort by date
            images.sort(key=lambda x: x['created_at'])
            logger.info(f"📸 Found {len(images)} total images (old: {len([i for i in images if i['source']=='user_images'])}, new: {len([i for i in images if i['source']=='ic_documents'])})")
            return images
            
        except Exception as e:
            logger.error(f"Error fetching images: {str(e)}")
            return []
    
    def _get_ic_messages(self, user_id, book_type, date_range_start=None, date_range_end=None):
        """Fetch messages from intelligent chat system with optional filtering"""
        try:
            # Get all messages from ic_messages
            messages_query = db.session.query(ICMessage)\
                .filter_by(user_id=user_id, is_deleted=False)\
                .filter(ICMessage.role == 'user')  # Only user messages
            
            # Apply date range filtering
            if date_range_start:
                messages_query = messages_query.filter(ICMessage.created_at >= date_range_start)
            if date_range_end:
                messages_query = messages_query.filter(ICMessage.created_at <= date_range_end)
            
            messages_query = messages_query.order_by(ICMessage.created_at)
            
            all_messages = messages_query.all()
            
            # Get book type config
            config = get_book_type_config(book_type)
            
            # Filter messages based on book type
            if config['content_filter'] == 'health':
                # Medical book - only health-related
                filtered = [m for m in all_messages if m.active_mode == 'health' or 
                           any(keyword in m.content.lower() for keyword in get_filter_keywords(book_type))]
            elif config['content_filter'] == 'training':
                # Training book - only training-related
                filtered = [m for m in all_messages if 
                           any(keyword in m.content.lower() for keyword in get_filter_keywords(book_type))]
            elif config['content_filter'] == 'social':
                # Family book - social interactions
                filtered = [m for m in all_messages if 
                           any(keyword in m.content.lower() for keyword in get_filter_keywords(book_type))]
            else:
                # Historical, memorial, relationship - use all
                filtered = all_messages
            
            # Fallback: if filtered content is too small, use all messages
            if len(filtered) < CONTENT_THRESHOLDS['fallback_to_all_content_threshold'] and len(all_messages) > 0:
                logger.warning(f"⚠️  Only {len(filtered)} filtered messages, using all {len(all_messages)} messages")
                filtered = all_messages
            
            logger.info(f"💬 Found {len(filtered)} messages (total: {len(all_messages)}, book_type: {book_type})")
            return filtered
            
        except Exception as e:
            logger.error(f"Error fetching ic_messages: {str(e)}")
            return []
    
    def _create_flexible_chapters(self, messages, images, book_type, tone_type, text_style):
        """Create flexible chapters based on book type and content"""
        config = get_book_type_config(book_type)
        chapters = []
        
        if config['organize_by'] == 'timeline':
            # Historical/Memorial: Organize by time periods
            chapters = self._create_timeline_chapters(messages, images, config)
        elif config['organize_by'] == 'emotional_themes':
            # Relationship: Organize by themes
            chapters = self._create_themed_chapters(messages, images, config, 'relationship')
        elif config['organize_by'] == 'medical_categories':
            # Medical: Organize by health categories
            chapters = self._create_themed_chapters(messages, images, config, 'medical')
        elif config['organize_by'] == 'skill_levels':
            # Training: Organize by skills
            chapters = self._create_themed_chapters(messages, images, config, 'training')
        elif config['organize_by'] == 'relationship_types':
            # Family: Organize by relationships
            chapters = self._create_themed_chapters(messages, images, config, 'family')
        else:
            # General or categories: Use user-selected categories
            chapters = self._create_themed_chapters(messages, images, config, 'general')
        
        # Ensure minimum chapters
        if len(chapters) < config['min_chapters']:
            chapters = self._merge_small_chapters(chapters, config['min_chapters'])
        
        return chapters
    
    def _create_timeline_chapters(self, messages, images, config):
        """Create chapters based on timeline"""
        chapters = []
        
        if not messages:
            return chapters
        
        # Group messages by time periods (e.g., every 3 months)
        from collections import defaultdict
        time_groups = defaultdict(list)
        
        for msg in messages:
            # Group by quarter-year
            period_key = f"{msg.created_at.year}-Q{(msg.created_at.month-1)//3 + 1}"
            time_groups[period_key].append(msg)
        
        # Sort time periods
        sorted_periods = sorted(time_groups.keys())
        
        # Create chapters for each period (always create, even with fewer messages)
        for i, period in enumerate(sorted_periods):
            period_messages = time_groups[period]
            
            # Get images from same time period or distribute evenly
            if period_messages:
                period_start = period_messages[0].created_at
                period_end = period_messages[-1].created_at
                period_images = [img for img in images if period_start <= img['created_at'] <= period_end]
                
                # If no images from this period, distribute evenly
                if not period_images and images:
                    img_per_chapter = len(images) // len(sorted_periods)
                    start_idx = i * img_per_chapter
                    end_idx = start_idx + img_per_chapter if i < len(sorted_periods) - 1 else len(images)
                    period_images = images[start_idx:end_idx]
                
                chapters.append({
                    'title': self._format_period_title(period),
                    'messages': period_messages,
                    'images': period_images
                })
        
        # If no chapters were created, create a single chapter with all content
        if not chapters:
            chapters = [{
                'title': 'Our Story',
                'messages': messages,
                'images': images
            }]
        
        return chapters
    
    def _create_themed_chapters(self, messages, images, config, theme_type):
        """Create chapters based on themes/categories"""
        chapters = []
        theme_list = config.get('chapter_themes', [])
        
        if not theme_list or not messages:
            # Fallback: create single chapter with all content
            return [{
                'title': 'Our Story',
                'messages': messages,
                'images': images
            }]
        
        # For book types with specific themes, use AI-based categorization
        if theme_type in ['relationship', 'medical', 'training', 'family']:
            categorized = self._categorize_messages_by_themes(messages, theme_list, theme_type)
        else:
            # Fallback to simple distribution
            categorized = self._distribute_messages_evenly(messages, theme_list)
        
        # Create chapters for each theme
        for i, theme in enumerate(theme_list):
            theme_messages = categorized.get(theme, [])
            
            # Always create chapter, even with fewer messages (minimum 1 message)
            if theme_messages:
                # Distribute images evenly across chapters
                img_per_chapter = len(images) // len(theme_list)
                start_idx = i * img_per_chapter
                end_idx = start_idx + img_per_chapter if i < len(theme_list) - 1 else len(images)
                theme_images = images[start_idx:end_idx]
                
                chapters.append({
                    'title': theme,
                    'messages': theme_messages,
                    'images': theme_images
                })
                logger.info(f"📖 Created chapter '{theme}' with {len(theme_messages)} messages and {len(theme_images)} images")
            else:
                logger.warning(f"⚠️  No messages for theme '{theme}' - skipping chapter")
        
        # If no chapters were created, create a single chapter with all content
        if not chapters:
            logger.warning("⚠️  No chapters created, creating fallback chapter with all content")
            chapters = [{
                'title': 'Our Story',
                'messages': messages,
                'images': images
            }]
        
        # Ensure we have at least the minimum number of chapters
        if len(chapters) < config.get('min_chapters', 3):
            logger.warning(f"⚠️  Only {len(chapters)} chapters created, need {config.get('min_chapters', 3)}")
            # Distribute remaining content evenly
            remaining_messages = []
            remaining_images = []
            
            for chapter in chapters:
                remaining_messages.extend(chapter['messages'])
                remaining_images.extend(chapter['images'])
            
            # Create additional chapters
            while len(chapters) < config.get('min_chapters', 3):
                chapter_num = len(chapters) + 1
                theme = theme_list[chapter_num - 1] if chapter_num <= len(theme_list) else f"Chapter {chapter_num}"
                
                # Distribute remaining content
                msgs_per_chapter = len(remaining_messages) // (config.get('min_chapters', 3) - len(chapters))
                imgs_per_chapter = len(remaining_images) // (config.get('min_chapters', 3) - len(chapters))
                
                start_msg = (chapter_num - len(chapters) - 1) * msgs_per_chapter
                end_msg = start_msg + msgs_per_chapter if chapter_num < config.get('min_chapters', 3) else len(remaining_messages)
                
                start_img = (chapter_num - len(chapters) - 1) * imgs_per_chapter
                end_img = start_img + imgs_per_chapter if chapter_num < config.get('min_chapters', 3) else len(remaining_images)
                
                chapters.append({
                    'title': theme,
                    'messages': remaining_messages[start_msg:end_msg],
                    'images': remaining_images[start_img:end_img]
                })
                logger.info(f"📖 Created additional chapter '{theme}' with {end_msg-start_msg} messages and {end_img-start_img} images")
        
        return chapters
    
    def _categorize_messages_by_themes(self, messages, themes, theme_type):
        """Use AI to categorize messages by specific themes"""
        try:
            # Create theme descriptions for AI
            theme_descriptions = {
                'relationship': {
                    'How We Met': 'Initial meeting, first encounters, getting to know each other',
                    'Learning Each Other': 'Understanding personalities, habits, preferences',
                    'Daily Life Together': 'Routine activities, everyday moments, shared experiences',
                    'Challenges & Growth': 'Difficulties faced together, how you grew stronger',
                    'Special Moments': 'Memorable occasions, celebrations, milestones',
                    'Our Bond Today': 'Current relationship, ongoing connection, present day',
                    'Looking Forward': 'Future plans, hopes, dreams together'
                },
                'medical': {
                    'Health Profile & Baseline': 'Initial health status, basic health information',
                    'Preventive Care': 'Regular checkups, vaccinations, wellness visits',
                    'Nutrition & Diet': 'Food, eating habits, dietary needs, feeding',
                    'Medical History': 'Past illnesses, treatments, medical events',
                    'Ongoing Monitoring': 'Regular health tracking, observations, monitoring',
                    'Surgical Records': 'Surgeries, procedures, medical interventions',
                    'Chronic Conditions': 'Ongoing health issues, long-term care'
                },
                'training': {
                    'Foundation & Basic Commands': 'Basic training, sit, stay, come commands',
                    'Intermediate Skills': 'More advanced commands, leash training, house training',
                    'Behavioral Training': 'Behavior modification, problem solving, good habits',
                    'Advanced Training & Tricks': 'Complex commands, tricks, advanced skills',
                    'Training Philosophy': 'Training approach, methods, principles',
                    'Ongoing Development': 'Continuous learning, skill maintenance, progress'
                },
                'family': {
                    'Family Circle': 'Immediate family members, close family relationships',
                    'Furry Friends': 'Other pets, animal companions, playmates',
                    'Extended Family & Visitors': 'Relatives, friends, people who visit',
                    'Community Connections': 'Neighbors, local community, social interactions',
                    'Special Moments Together': 'Celebrations, gatherings, memorable events',
                    'The Social Butterfly': 'Social personality, interactions with others'
                }
            }
            
            descriptions = theme_descriptions.get(theme_type, {})
            
            # Prepare messages for AI categorization
            message_texts = [m.content for m in messages]
            
            # Create prompt for AI
            prompt = f"""You are categorizing messages about a dog into {theme_type} book chapters.

Themes and their descriptions:
"""
            for theme in themes:
                description = descriptions.get(theme, f"Content related to {theme}")
                prompt += f"- {theme}: {description}\n"
            
            prompt += f"\nMessages to categorize:\n"
            for i, text in enumerate(message_texts[:50]):  # Limit to first 50 messages
                prompt += f"{i+1}. {text[:200]}...\n"  # Truncate long messages
            
            prompt += f"\nCategorize each message into the most appropriate theme. Respond with JSON format:\n"
            prompt += f"{{\n"
            for theme in themes:
                prompt += f'  "{theme}": [message_numbers],\n'
            prompt += f"}}\n"
            prompt += f"Ensure all messages are categorized. If a message doesn't fit any theme, put it in the first theme."
            
            # Get AI response
            response_text = self.ai_service.generate_completion(
                messages=[{"role": "system", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse JSON response
            import json
            import re
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("Could not parse AI response")
            
            categorization_json = json.loads(json_match.group(0))
            
            # Convert to message objects
            result = {}
            for theme in themes:
                message_indices = categorization_json.get(theme, [])
                result[theme] = [messages[i-1] for i in message_indices if 1 <= i <= len(messages)]
                logger.info(f"🎯 Theme '{theme}': {len(result[theme])} messages")
            
            logger.info(f"📊 Total categorized messages: {sum(len(msgs) for msgs in result.values())} / {len(messages)}")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI theme categorization: {str(e)}")
            # Fallback to even distribution
            return self._distribute_messages_evenly(messages, themes)
    
    def _distribute_messages_evenly(self, messages, themes):
        """Distribute messages evenly across themes as fallback"""
        result = {}
        messages_per_theme = len(messages) // len(themes)
        
        for i, theme in enumerate(themes):
            start_idx = i * messages_per_theme
            if i == len(themes) - 1:  # Last theme gets remaining messages
                end_idx = len(messages)
            else:
                end_idx = start_idx + messages_per_theme
            result[theme] = messages[start_idx:end_idx]
        
        return result
    
    def _format_period_title(self, period):
        """Format time period into readable chapter title"""
        year, quarter = period.split('-Q')
        months = {
            '1': 'January - March',
            '2': 'April - June',
            '3': 'July - September',
            '4': 'October - December'
        }
        return f"{months.get(quarter, '')} {year}"
    
    def _merge_small_chapters(self, chapters, min_chapters):
        """Merge small chapters to meet minimum"""
        if len(chapters) >= min_chapters or len(chapters) == 0:
            return chapters
        
        # Simple merge: combine adjacent chapters
        while len(chapters) < min_chapters and len(chapters) > 1:
            # Merge last two chapters
            last = chapters.pop()
            chapters[-1]['messages'].extend(last['messages'])
            chapters[-1]['images'].extend(last['images'])
            chapters[-1]['title'] = f"{chapters[-1]['title']} & {last['title']}"
        
        return chapters

    def generate_book_chapters(self, user_id, book_id):
        """
        Generate book chapters from ic_messages with photos
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Update book status
            book.status = 'processing'
            db.session.commit()
            
            logger.info(f"🎨 Generating chapters for book '{book.title}' (type: {book.book_type})")
            
            # Fetch messages from ic_messages
            messages = self._get_ic_messages(user_id, book.book_type)
            
            # Fetch images from both tables
            images = self._get_all_user_images(user_id)
            
            if not messages:
                raise ValueError("No messages found for book generation")
            
            # Create flexible chapters based on book type
            chapters_data = self._create_flexible_chapters(
                messages, 
                images, 
                book.book_type,
                book.tone_type,
                book.text_style
            )
            
            logger.info(f"📚 Created {len(chapters_data)} chapters")
            
            # Generate content for each chapter and save to database
            for idx, chapter_data in enumerate(chapters_data, 1):
                # Generate AI content from messages
                message_texts = [m.content for m in chapter_data['messages']]
                chapter_content = self._generate_chapter_content(
                    message_texts,
                    chapter_data['title'],
                    book.tone_type,
                    book.text_style
                )
                
                # Store chapter images as JSON in content (will be used in PDF generation)
                chapter_images_json = json.dumps([{
                    's3_url': img['s3_url'],
                    'description': img['description']
                } for img in chapter_data['images']])
                
                # Create chapter
                chapter = EnhancedBookChapter(
                    book_id=book_id,
                    title=chapter_data['title'],
                    content=chapter_content + f"\n<!-- IMAGES: {chapter_images_json} -->",  # Embed images in content
                    category=chapter_data['title'],
                    order=idx
                )
                db.session.add(chapter)
                logger.info(f"  ✅ Chapter {idx}: {chapter_data['title']} ({len(message_texts)} messages, {len(chapter_data['images'])} images)")
            
            db.session.commit()
            
            # Update book status
            book.status = 'completed'
            db.session.commit()
            
            logger.info(f"✅ Book generation completed: {book.title}")
            return book.to_dict()
        except Exception as e:
            logger.error(f"❌ Error generating book chapters: {str(e)}")
            book.status = 'error'
            db.session.commit()
            db.session.rollback()
            raise
    
    def _generate_chapter_content(self, messages, category, tone_type, text_style):
        """
        Generate chapter content based on messages, tone, and style
        """
        try:
            # Prepare prompt for OpenAI
            prompt = f"""
            You are a professional book writer. Your task is to convert the following messages into a cohesive book chapter.
            
            Category: {category}
            Tone: {tone_type} (friendly, narrative, or playful)
            Text Style: {text_style} (e.g., formal, casual)
            
            IMPORTANT INSTRUCTIONS:
            1. Transform these messages into a flowing narrative that reads like a professional book chapter.
            2. DO NOT include any chapter numbers or titles in the content (e.g., DO NOT write "Chapter 5: Health").
            3. DO NOT start with phrases like "In this chapter" or "This chapter".
            4. Simply write the content as a cohesive narrative with proper paragraphs.
            5. Focus on creating a smooth, engaging narrative that feels like a professionally written book.
            6. Organize the content logically with clear paragraph breaks.
            
            Here are the messages:
            """
            
            for i, text in enumerate(messages):
                prompt += f"\nMessage {i+1}: {text}"
            
            prompt += f"\n\nWrite a book chapter with a {tone_type} tone and {text_style} style based on these messages. Remember, DO NOT include chapter numbers or titles in your response."
            
            # Get chapter content from OpenAI
            chapter_content = self.ai_service.generate_completion(
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1500,
                temperature=0.7
            )
            
            return chapter_content
        except Exception as e:
            logger.error(f"Error generating chapter content: {str(e)}")
            raise
    
    def generate_pdf(self, user_id, book_id):
        """
        Generate PDF from book chapters using WeasyPrint and Jinja2 templates
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Get user for author name
            user = User.query.get(user_id)
            author_name = user.username if user else "Anonymous"
            
            # Get chapters
            chapters = EnhancedBookChapter.query.filter_by(book_id=book_id).order_by(EnhancedBookChapter.order).all()
            if not chapters:
                raise ValueError("No chapters found for this book")
            
            # Create a temporary folder for the book
            temp_folder = current_app.config.get('TEMP_FOLDER', '/tmp')
            book_temp_folder = os.path.join(temp_folder, f"enhanced_book_{book_id}_{uuid.uuid4().hex}")
            os.makedirs(book_temp_folder, exist_ok=True)
            
            # Get photo layout config for this book type
            photo_layout = get_photo_layout(get_book_type_config(book.book_type)['photo_priority'])
            logger.info(f"📸 Photo layout: {photo_layout['layout_class']}")
            
            # Create images folder in temp directory
            images_folder = os.path.join(book_temp_folder, "images")
            os.makedirs(images_folder, exist_ok=True)
            
            # Prepare chapters data with images
            chapters_data = []
            for chapter in chapters:
                clean_title = chapter.title
                if ":" in clean_title:
                    clean_title = clean_title.split(":", 1)[1].strip()
                
                content = chapter.content
                
                # Extract images JSON from content
                chapter_images = []
                images_match = re.search(r'<!-- IMAGES: (.*?) -->', content)
                if images_match:
                    try:
                        chapter_images = json.loads(images_match.group(1))
                        # Remove the comment from content
                        content = content.replace(images_match.group(0), '')
                    except:
                        pass
                
                # Download images to temp folder
                local_images = []
                for idx, img in enumerate(chapter_images):
                    try:
                        response = requests.get(img['s3_url'], timeout=10)
                        if response.status_code == 200:
                            img_ext = img['s3_url'].split('.')[-1].split('?')[0] or 'jpg'
                            local_img_path = os.path.join(images_folder, f"chapter_{chapter.order}_img_{idx}.{img_ext}")
                            with open(local_img_path, 'wb') as f:
                                f.write(response.content)
                            local_images.append({
                                'path': local_img_path,
                                'description': img['description']
                            })
                            logger.info(f"  📥 Downloaded image {idx+1} for chapter {chapter.order}")
                    except Exception as e:
                        logger.warning(f"  ⚠️  Failed to download image: {str(e)}")
                
                content = re.sub(r'^Chapter \d+:.*?\n', '', content, flags=re.MULTILINE)
                
                # Parse paragraphs and intersperse images naturally
                paragraphs = content.split('\n\n')
                paragraphs = [p.strip() for p in paragraphs if p.strip()]
                
                # Calculate image placement positions
                formatted_content = ""
                if local_images and len(paragraphs) > 0:
                    # Distribute images evenly throughout the text
                    # Place images after every N paragraphs, where N = total_paragraphs / (num_images + 1)
                    num_images = len(local_images)
                    num_paragraphs = len(paragraphs)
                    
                    # Calculate spacing - at least 2 paragraphs between images
                    spacing = max(2, num_paragraphs // (num_images + 1))
                    
                    image_idx = 0
                    paragraph_count = 0
                    
                    for i, paragraph in enumerate(paragraphs):
                        # Add paragraph
                        formatted_content += f"<p>{paragraph}</p>\n"
                        paragraph_count += 1
                        
                        # Check if we should insert an image after this paragraph
                        should_insert_image = (
                            image_idx < num_images and  # Still have images to place
                            paragraph_count >= spacing and  # Enough paragraphs have passed
                            i < len(paragraphs) - 1  # Not the last paragraph
                        )
                        
                        if should_insert_image:
                            img = local_images[image_idx]
                            formatted_content += f'''
                            <div class="image-container">
                                <img src="file://{img['path']}" alt="{img['description']}" class="chapter-image">
                                <p class="image-caption">{img['description']}</p>
                            </div>
                            '''
                            image_idx += 1
                            paragraph_count = 0  # Reset counter
                    
                    # If there are remaining images, add them at the end
                    while image_idx < num_images:
                        img = local_images[image_idx]
                        formatted_content += f'''
                        <div class="image-container">
                            <img src="file://{img['path']}" alt="{img['description']}" class="chapter-image">
                            <p class="image-caption">{img['description']}</p>
                        </div>
                        '''
                        image_idx += 1
                else:
                    # No images, just format paragraphs
                    for paragraph in paragraphs:
                        formatted_content += f"<p>{paragraph}</p>\n"
                
                chapters_data.append({
                    'title': chapter.title,
                    'clean_title': clean_title,
                    'content': content,
                    'formatted_content': formatted_content,
                    'images': []  # Images are now embedded in formatted_content
                })
            
            # Set up Jinja2 environment
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template('book/content.html')
            
            # Render template with data
            html_content = template.render(
                book=book,
                author_name=author_name,
                chapters=chapters_data,
                font_family=self._get_font_family(book.text_style),
                photo_layout=photo_layout
            )
            
            # Save HTML to file for debugging
            html_path = os.path.join(book_temp_folder, "book.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML content saved to: {html_path}")
            
            # Generate PDF
            pdf_filename = f"enhanced_book_{book_id}_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join(book_temp_folder, pdf_filename)
            
            # Create PDF using WeasyPrint
            HTML(string=html_content).write_pdf(pdf_path)
            
            # Upload to S3
            s3_key = f"books/{user_id}/{pdf_filename}"
            self.s3_client.upload_file(
                pdf_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs={'ContentType': 'application/pdf'}
            )
            
            # Update book with PDF URL
            book.pdf_url = f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
            db.session.commit()
            
            # Clean up temp files
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            # Clean up temp folder
            import shutil
            if os.path.exists(book_temp_folder):
                shutil.rmtree(book_temp_folder)
            
            return book.pdf_url
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise
    
    def generate_epub(self, user_id, book_id):
        """
        Generate EPUB from book chapters
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Get user for author name
            user = User.query.get(user_id)
            author_name = user.username if user else "Anonymous"
            
            # Get chapters
            chapters = EnhancedBookChapter.query.filter_by(book_id=book_id).order_by(EnhancedBookChapter.order).all()
            if not chapters:
                raise ValueError("No chapters found for this book")
            
            # Create EPUB book
            epub_book = epub.EpubBook()
            epub_book.set_identifier(f"enhanced-book-{book_id}")
            epub_book.set_title(book.title)
            epub_book.set_language('en')
            epub_book.add_author(author_name)
            
            # Add CSS
            style = '''
            @namespace epub "http://www.idpf.org/2007/ops";
            body {
                font-family: ''' + self._get_font_family(book.text_style) + ''';
            }
            h1 {
                text-align: center;
                margin-bottom: 50px;
            }
            h2 {
                margin-top: 40px;
            }
            .chapter {
                margin-bottom: 30px;
            }
            .image-container {
                margin: 20px 0;
                text-align: center;
            }
            .chapter-image {
                max-width: 100%;
                height: auto;
            }
            .image-caption {
                font-size: 0.9em;
                font-style: italic;
                color: #666;
                margin-top: 10px;
            }
            '''
            
            css = epub.EpubItem(
                uid="style_default",
                file_name="style/default.css",
                media_type="text/css",
                content=style
            )
            epub_book.add_item(css)
            
            # Create chapters
            epub_chapters = []
            toc = []
            spine = ['nav']
            
            for i, chapter in enumerate(chapters):
                content = chapter.content
                
                # Extract images JSON from content
                chapter_images = []
                images_match = re.search(r'<!-- IMAGES: (.*?) -->', content)
                if images_match:
                    try:
                        chapter_images = json.loads(images_match.group(1))
                        # Remove the comment from content
                        content = content.replace(images_match.group(0), '')
                    except:
                        pass
                
                # Download and add images to EPUB
                epub_images = []
                for idx, img in enumerate(chapter_images):
                    try:
                        response = requests.get(img['s3_url'], timeout=10)
                        if response.status_code == 200:
                            img_ext = img['s3_url'].split('.')[-1].split('?')[0] or 'jpg'
                            img_filename = f"chapter_{i+1}_img_{idx}.{img_ext}"
                            
                            # Determine media type
                            media_type = f"image/{img_ext}" if img_ext in ['jpg', 'jpeg', 'png', 'gif'] else 'image/jpeg'
                            
                            # Create EPUB image item
                            epub_img = epub.EpubItem(
                                uid=f"img_{i+1}_{idx}",
                                file_name=f"images/{img_filename}",
                                media_type=media_type,
                                content=response.content
                            )
                            epub_book.add_item(epub_img)
                            epub_images.append({
                                'filename': img_filename,
                                'description': img['description']
                            })
                            logger.info(f"  📥 Added image {idx+1} to EPUB for chapter {i+1}")
                    except Exception as e:
                        logger.warning(f"  ⚠️  Failed to download image for EPUB: {str(e)}")
                
                # Parse paragraphs and intersperse images naturally
                content = re.sub(r'^Chapter \d+:.*?\n', '', content, flags=re.MULTILINE)
                paragraphs = content.split('\n\n')
                paragraphs = [p.strip() for p in paragraphs if p.strip()]
                
                # Create formatted content with interspersed images
                formatted_content = ""
                if epub_images and len(paragraphs) > 0:
                    num_images = len(epub_images)
                    num_paragraphs = len(paragraphs)
                    spacing = max(2, num_paragraphs // (num_images + 1))
                    
                    image_idx = 0
                    paragraph_count = 0
                    
                    for j, paragraph in enumerate(paragraphs):
                        formatted_content += f"<p>{paragraph}</p>\n"
                        paragraph_count += 1
                        
                        should_insert_image = (
                            image_idx < num_images and
                            paragraph_count >= spacing and
                            j < len(paragraphs) - 1
                        )
                        
                        if should_insert_image:
                            img = epub_images[image_idx]
                            formatted_content += f'''
                            <div class="image-container">
                                <img src="images/{img['filename']}" alt="{img['description']}" class="chapter-image" />
                                <p class="image-caption">{img['description']}</p>
                            </div>
                            '''
                            image_idx += 1
                            paragraph_count = 0
                    
                    # Add remaining images at the end
                    while image_idx < num_images:
                        img = epub_images[image_idx]
                        formatted_content += f'''
                        <div class="image-container">
                            <img src="images/{img['filename']}" alt="{img['description']}" class="chapter-image" />
                            <p class="image-caption">{img['description']}</p>
                        </div>
                        '''
                        image_idx += 1
                else:
                    # No images, just format paragraphs
                    for paragraph in paragraphs:
                        formatted_content += f"<p>{paragraph}</p>\n"
                
                epub_chapter = epub.EpubHtml(
                    title=chapter.title,
                    file_name=f'chapter_{i+1}.xhtml',
                    lang='en'
                )
                epub_chapter.content = f'<h2>{chapter.title}</h2><div class="chapter">{formatted_content}</div>'
                epub_chapter.add_item(css)
                
                epub_book.add_item(epub_chapter)
                epub_chapters.append(epub_chapter)
                toc.append(epub.Link(f'chapter_{i+1}.xhtml', chapter.title, f'chapter{i+1}'))
                spine.append(epub_chapter)
            
            # Add TOC and spine
            epub_book.toc = toc
            epub_book.spine = spine
            epub_book.add_item(epub.EpubNcx())
            epub_book.add_item(epub.EpubNav())
            
            # Generate EPUB
            epub_filename = f"enhanced_book_{book_id}_{uuid.uuid4().hex}.epub"
            epub_path = os.path.join(current_app.config['TEMP_FOLDER'], epub_filename)
            
            epub.write_epub(epub_path, epub_book)
            
            # Upload to S3
            s3_key = f"books/{user_id}/{epub_filename}"
            self.s3_client.upload_file(
                epub_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs={'ContentType': 'application/epub+zip'}
            )
            
            # Update book with EPUB URL
            book.epub_url = f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
            db.session.commit()
            
            # Clean up temp file
            if os.path.exists(epub_path):
                os.remove(epub_path)
            
            return book.epub_url
        except Exception as e:
            logger.error(f"Error generating EPUB: {str(e)}")
            raise
    
    def _get_font_family(self, text_style):
        """
        Get font family based on text style
        """
        font_mapping = {
            'poppins': "'Poppins', sans-serif",
            'times new roman': "'Times New Roman', serif",
            'arial': "'Arial', sans-serif",
            'georgia': "'Georgia', serif",
            'courier': "'Courier New', monospace",
        }
        
        return font_mapping.get(text_style.lower(), "'Arial', sans-serif")
    
    def update_chapter(self, user_id, book_id, chapter_id, title, content):
        """
        Update a chapter's title and content
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Get the chapter
            chapter = EnhancedBookChapter.query.get(chapter_id)
            if not chapter or chapter.book_id != book_id:
                raise ValueError("Chapter not found or does not belong to this book")
            
            # Update chapter
            chapter.title = title
            chapter.content = content
            chapter.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return chapter.to_dict()
        except Exception as e:
            logger.error(f"Error updating chapter: {str(e)}")
            db.session.rollback()
            raise
    
    def delete_chapter(self, user_id, book_id, chapter_id):
        """Delete a chapter"""
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Get the chapter
            chapter = EnhancedBookChapter.query.get(chapter_id)
            if not chapter or chapter.book_id != book_id:
                raise ValueError("Chapter not found or does not belong to the book")
            
            # Delete the chapter
            db.session.delete(chapter)
            db.session.commit()
            
            return {'success': True, 'message': 'Chapter deleted successfully'}
        except Exception as e:
            logger.error(f"Error deleting chapter: {str(e)}")
            db.session.rollback()
            raise
    
    def delete_book(self, user_id, book_id):
        """Delete an enhanced book and all its chapters"""
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Delete the book (chapters will be cascade deleted)
            db.session.delete(book)
            db.session.commit()
            
            logger.info(f"Book {book_id} deleted successfully for user {user_id}")
            return {'success': True, 'message': 'Book deleted successfully'}
        except Exception as e:
            logger.error(f"Error deleting book: {str(e)}")
            db.session.rollback()
            raise
            
    def process_ai_chat_edit(self, user_id, book_id, message, book_context, chat_history=None):
        """
        Process AI chat for chapter editing
        
        Args:
            user_id: User ID
            book_id: Book ID
            message: User message
            book_context: Context about the book and chapter
            chat_history: Previous chat messages
            
        Returns:
            Dictionary with AI response and edited content
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # First, classify the intent
            intent_prompt = f"""
Analyze the following user message and determine if they are:
1. Asking for information or a question about the chapter
2. Requesting a summary or analysis
3. Explicitly requesting an edit or change to the content

User message: {message}

Return ONLY ONE of these values: "information", "summary", or "edit"
"""
            
            intent = self.ai_service.generate_completion([
                {"role": "system", "content": intent_prompt},
                {"role": "user", "content": message}
            ], max_tokens=20).strip().lower()
            
            # Generate appropriate response based on intent
            if intent in ["information", "summary"]:
                # Generate conversational response without editing
                conversation_prompt = f"""
You are an expert AI writing assistant helping with a book chapter.

BOOK CONTEXT:
- Book Title: {book_context.get('bookTitle', 'Unknown')}
- Chapter Title: {book_context.get('chapterTitle', 'Unknown')}
- Book Tone: {book_context.get('tone', 'neutral')}
- Writing Style: {book_context.get('textStyle', 'narrative')}

CHAPTER CONTENT:
{book_context.get('chapterContent', '')}

USER QUESTION: {message}

Provide a helpful response to the user's question WITHOUT editing the chapter content.
"""
                
                response = self.ai_service.generate_completion([
                    {"role": "system", "content": conversation_prompt},
                    {"role": "user", "content": message}
                ], max_tokens=1000)
                
                return {
                    'message': response,
                    'editedContent': None,
                    'intent': intent
                }
            else:
                # Check if content needs chunking (over 2000 tokens/~8000 chars)
                chapter_content = book_context.get('chapterContent', '')
                estimated_tokens = len(chapter_content.split()) * 1.3
                
                # If content is small enough, use the original method
                if estimated_tokens < 2000:
                    return self._process_simple_edit(message, book_context)
                else:
                    # Use the chunked editing approach for long content
                    return self._process_chunked_edit(message, book_context)
            
        except Exception as e:
            logger.error(f"Error processing AI chat edit: {str(e)}")
            raise
    
    def _process_simple_edit(self, message, book_context):
        """Process edit for short content using the original method"""
        system_prompt = f"""
You are an expert AI writing assistant that directly edits book chapters based on user instructions.
Your task is to ALWAYS return the COMPLETE EDITED CHAPTER CONTENT with the requested changes applied.
Do not provide explanations or conversational responses - ONLY return the edited content.

BOOK CONTEXT:
- Book Title: {book_context.get('bookTitle', 'Unknown')}
- Chapter Title: {book_context.get('chapterTitle', 'Unknown')}
- Book Tone: {book_context.get('tone', 'neutral')}
- Writing Style: {book_context.get('textStyle', 'narrative')}

USER INSTRUCTION: {message}

CURRENT CHAPTER CONTENT:
{book_context.get('chapterContent', '')}

IMPORTANT: Your response should contain ONLY the edited chapter content. Do not include any explanations, 
comments, or conversation. Return the complete chapter with the requested changes applied.
"""
        
        # Generate AI response (direct edit)
        edited_content = self.ai_service.generate_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Edit the chapter according to the instructions above."}
        ], max_tokens=2000, temperature=0.7)
        
        # Create a brief confirmation message
        confirmation_message = f"I've edited the chapter according to your request: \"{message}\""
        
        return {
            'message': confirmation_message,
            'editedContent': edited_content,
            'intent': 'edit'
        }
    
    def _process_chunked_edit(self, message, book_context):
        """
        Process edit for long content using chunking approach
        
        Args:
            message: User edit request
            book_context: Book and chapter context
            
        Returns:
            Dictionary with AI response and edited content
        """
        try:
            chapter_content = book_context.get('chapterContent', '')
            logger.info(f"Starting chunked processing for content of length {len(chapter_content)}")
            
            # Step 1: Content Preparation - Split content into chunks
            chunks = self.chunking_service.chunk_content(chapter_content)
            logger.info(f"Content split into {len(chunks)} chunks")
            
            # Step 2: Determine which chunks to process based on the edit request
            chunks_to_process = self.chunking_service.get_chunk_for_edit(chapter_content, message, chunks)
            logger.info(f"Selected {len(chunks_to_process)} chunks for processing based on edit request")
            
            # Step 3: Process each chunk in parallel
            try:
                logger.info(f"Starting parallel processing of {len(chunks_to_process)} chunks")
                processed_chunks = self._process_chunks_parallel(chunks_to_process, message, book_context)
            except Exception as e:
                logger.error(f"Parallel processing failed: {str(e)}", exc_info=True)
                logger.info("Falling back to sequential processing")
                processed_chunks = self._process_chunks_sequential(chunks_to_process, message, book_context)
            
            # Count successfully processed chunks
            successful_chunks = sum(1 for chunk in processed_chunks if chunk.is_processed)
            logger.info(f"Successfully processed {successful_chunks} out of {len(chunks_to_process)} chunks")
            
            # Step 4: Merge processed chunks
            logger.info("Merging processed chunks")
            merged_content = self.chunking_service.merge_processed_chunks(processed_chunks)
            
            # Step 5: Create a confirmation message
            num_chunks = len(chunks_to_process)
            confirmation_message = f"I've edited the chapter according to your request: \"{message}\". "
            if num_chunks > 1:
                confirmation_message += f"The content was processed in {num_chunks} sections to handle its length."
            
            return {
                'message': confirmation_message,
                'editedContent': merged_content,
                'intent': 'edit',
                'chunks_processed': num_chunks,
                'chunks_successful': successful_chunks,
                'is_chunked_processing': True
            }
            
        except Exception as e:
            logger.error(f"Error in chunked edit processing: {str(e)}", exc_info=True)
            # Fallback to simple edit if chunking fails
            logger.info("Falling back to simple edit due to error in chunked processing")
            return self._process_simple_edit(message, book_context)
            
    def _process_chunks_sequential(self, chunks, message, book_context):
        """
        Process chunks sequentially as a fallback
        
        Args:
            chunks: List of ContentChunk objects to process
            message: User edit request
            book_context: Book and chapter context
            
        Returns:
            List of processed ContentChunk objects
        """
        logger.info(f"Processing {len(chunks)} chunks sequentially")
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"Processing chunk {i+1}/{len(chunks)} (ID: {chunk.chunk_id}) sequentially")
                processed_chunk = self._process_single_chunk(chunk, message, book_context)
                processed_chunks.append(processed_chunk)
                logger.info(f"Chunk {i+1}/{len(chunks)} processed successfully")
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}/{len(chunks)}: {str(e)}", exc_info=True)
                # Keep the original chunk if processing failed
                processed_chunks.append(chunk)
        
        return processed_chunks
    
    def _process_chunks_parallel(self, chunks, message, book_context):
        """
        Process multiple chunks in parallel
        
        Args:
            chunks: List of ContentChunk objects to process
            message: User edit request
            book_context: Book and chapter context
            
        Returns:
            List of processed ContentChunk objects
        """
        # Process chunks in parallel using ThreadPoolExecutor
        futures = []
        
        # Get the current Flask app for application context
        from flask import current_app
        app = current_app._get_current_object()
        logger.info(f"Retrieved current Flask app for application context: {app}")
        
        # Create a copy of the request context for each thread
        for i, chunk in enumerate(chunks):
            logger.info(f"Submitting chunk {i+1}/{len(chunks)} (ID: {chunk.chunk_id}) for processing")
            
            # Wrap the function with copy_current_request_context to maintain request context
            @copy_current_request_context
            def process_chunk_with_context(chunk=chunk, message=message, book_context=book_context):
                try:
                    with app.app_context():
                        return self._process_single_chunk(chunk, message, book_context)
                except Exception as e:
                    logger.error(f"Error in thread for chunk {chunk.chunk_id}: {str(e)}", exc_info=True)
                    return chunk
            
            future = self.executor.submit(process_chunk_with_context)
            futures.append(future)
        
        # Wait for all futures to complete and collect results
        processed_chunks = []
        for i, future in enumerate(futures):
            try:
                logger.info(f"Waiting for chunk {i+1}/{len(chunks)} to complete")
                processed_chunk = future.result(timeout=60)  # Add timeout to prevent hanging
                processed_chunks.append(processed_chunk)
                logger.info(f"Chunk {i+1}/{len(chunks)} (ID: {chunks[i].chunk_id}) processed successfully")
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}/{len(chunks)} (ID: {chunks[i].chunk_id}): {str(e)}", exc_info=True)
                # Keep the original chunk if processing failed
                processed_chunks.append(chunks[i])
        
        return processed_chunks
    
    def _process_single_chunk(self, chunk, message, book_context):
        """
        Process a single content chunk
        
        Args:
            chunk: ContentChunk object to process
            message: User edit request
            book_context: Book and chapter context
            
        Returns:
            Processed ContentChunk object
        """
        try:
            # Create a modified context with just this chunk's content
            chunk_context = book_context.copy()
            chunk_context['chapterContent'] = chunk.content
            
            # Add context about chunk position
            if chunk.order > 0:
                chunk_context['chunkInfo'] = f"This is part {chunk.order + 1} of the chapter content."
                if chunk.overlap_before:
                    chunk_context['overlapBefore'] = chunk.overlap_before
            
            # Prepare system prompt for this chunk
            system_prompt = f"""
You are an expert AI writing assistant that directly edits book chapters based on user instructions.
Your task is to ALWAYS return the COMPLETE EDITED CHUNK CONTENT with the requested changes applied.
Do not provide explanations or conversational responses - ONLY return the edited content.

BOOK CONTEXT:
- Book Title: {chunk_context.get('bookTitle', 'Unknown')}
- Chapter Title: {chunk_context.get('chapterTitle', 'Unknown')}
- Book Tone: {chunk_context.get('tone', 'neutral')}
- Writing Style: {chunk_context.get('textStyle', 'narrative')}
{f"- Chunk Info: {chunk_context.get('chunkInfo')}" if 'chunkInfo' in chunk_context else ""}

USER INSTRUCTION: {message}

CURRENT CHUNK CONTENT:
{chunk.content}

IMPORTANT: Your response should contain ONLY the edited chunk content. Do not include any explanations, 
comments, or conversation. Return the complete chunk with the requested changes applied.
Maintain consistency with the overall chapter style and narrative flow.
"""
            
            # Generate AI response for this chunk
            edited_content = self.ai_service.generate_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Edit this chunk according to the instructions above."}
            ], max_tokens=2000, temperature=0.7)
            
            # Update the chunk with processed content
            chunk.processed_content = edited_content
            chunk.is_processed = True
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk.chunk_id}: {str(e)}")
            # Return the original chunk if processing failed
            return chunk
            
    def _categorize_recent_uncategorized_messages(self, user_id, book_id, categories):
        """
        Categorize recent messages that haven't been categorized yet for a specific book
        
        Args:
            user_id: User ID
            book_id: Book ID
            categories: List of categories to use for categorization
            
        Returns:
            Dictionary of categorized messages
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                logger.error(f"Book {book_id} not found or access denied for user {user_id}")
                return {}
            
            # Get all user conversations from the last 7 days
            recent_date = datetime.utcnow() - timedelta(days=7)
            conversations = Conversation.query.filter_by(user_id=user_id).filter(
                Conversation.updated_at >= recent_date
            ).all()
            
            if not conversations:
                logger.info(f"No recent conversations found for user {user_id}")
                return {}
            
            conversation_ids = [conv.id for conv in conversations]
            
            # Get all messages from these conversations
            all_messages = Message.query.filter(
                Message.conversation_id.in_(conversation_ids),
                Message.type == 'user'  # Only categorize user messages
            ).order_by(Message.created_at).all()
            
            if not all_messages:
                logger.info(f"No recent messages found for user {user_id}")
                return {}
            
            # Get all messages that are already categorized for this book
            categorized_message_ids = db.session.query(MessageCategory.message_id).filter(
                MessageCategory.book_id == book_id
            ).all()
            categorized_message_ids = [msg_id[0] for msg_id in categorized_message_ids]
            
            # Filter out messages that are already categorized
            uncategorized_messages = [msg for msg in all_messages if msg.id not in categorized_message_ids]
            
            if not uncategorized_messages:
                logger.info(f"No uncategorized messages found for book {book_id}")
                return {}
            
            logger.info(f"Found {len(uncategorized_messages)} uncategorized messages for book {book_id}")
            
            # Prepare messages for categorization
            message_texts = [msg.content for msg in uncategorized_messages]
            message_ids = [msg.id for msg in uncategorized_messages]
            
            # Use hybrid approach to categorize messages
            categorized_messages = self._categorize_with_hybrid_approach(message_texts, message_ids, categories)
            
            # Store categorizations in database
            for category, msg_ids in categorized_messages.items():
                for msg_id in msg_ids:
                    message_category = MessageCategory(
                        message_id=msg_id,
                        category=category,
                        book_id=book_id
                    )
                    db.session.add(message_category)
            
            db.session.commit()
            logger.info(f"Successfully categorized {len(message_ids)} recent messages for book {book_id}")
            
            return categorized_messages
        except Exception as e:
            logger.error(f"Error categorizing recent messages: {str(e)}")
            db.session.rollback()
            return {}
            
    def get_formatted_recent_chats(self, user_id, book_id, tone_type, text_style, category=None, chapter_id=None):
        """
        Get and format recent chat messages for a book
        
        Args:
            user_id: User ID
            book_id: Book ID
            tone_type: Book tone type
            text_style: Book text style
            category: Optional category to filter messages
            chapter_id: Optional chapter ID to track last fetch time
            
        Returns:
            Dictionary with formatted content and message count
        """
        try:
            # Get the book
            book = EnhancedBook.query.get(book_id)
            if not book or book.user_id != user_id:
                raise ValueError("Book not found or access denied")
            
            # Get the chapter if chapter_id is provided
            chapter = None
            if chapter_id:
                logger.info(f"Looking up chapter with ID: {chapter_id}")
                chapter = EnhancedBookChapter.query.get(chapter_id)
                if not chapter:
                    logger.error(f"Chapter with ID {chapter_id} not found")
                    raise ValueError("Chapter not found")
                elif chapter.book_id != book_id:
                    logger.error(f"Chapter {chapter_id} does not belong to book {book_id}")
                    raise ValueError("Chapter does not belong to the book")
                else:
                    logger.info(f"Found chapter: {chapter.title} (ID: {chapter.id})")
                    logger.info(f"Chapter last_chat_fetch_at: {chapter.last_chat_fetch_at}")
            
            # First, categorize any recent uncategorized messages
            logger.info(f"Categorizing recent uncategorized messages for book {book_id}")
            categories = [chapter.category for chapter in book.chapters] if book.chapters else ["General"]
            self._categorize_recent_uncategorized_messages(user_id, book_id, categories)
            
            # Determine the cutoff date for recent messages
            if chapter and chapter.last_chat_fetch_at:
                # If we have a last fetch timestamp, use it
                recent_date = chapter.last_chat_fetch_at
                logger.info(f"Using last fetch time for chapter {chapter_id}: {recent_date}")
            else:
                # Otherwise use the default 7-day window
                recent_date = datetime.utcnow() - timedelta(days=7)
                logger.info(f"Using default 7-day window: {recent_date}")
                if chapter:
                    logger.info(f"Chapter {chapter_id} has no last_chat_fetch_at timestamp")
            
            # Get recent conversations since the cutoff date
            conversations = Conversation.query.filter_by(user_id=user_id).filter(
                Conversation.updated_at >= recent_date
            ).order_by(Conversation.updated_at.desc()).limit(5).all()
            
            logger.info(f"Found {len(conversations)} conversations since {recent_date}")
            
            if not conversations:
                logger.info("No conversations found")
                return {'formattedContent': '', 'messageCount': 0}
            
            conversation_ids = [conv.id for conv in conversations]
            
            # Get messages from these conversations that were created after the cutoff date
            messages_query = Message.query.filter(
                Message.conversation_id.in_(conversation_ids),
                Message.created_at > recent_date  # Only get messages created after the cutoff date
            )
            
            # If category is provided, filter messages by category
            if category:
                logger.info(f"Filtering messages by category: {category}")
                # Get message IDs that belong to this category
                category_message_ids = db.session.query(MessageCategory.message_id).filter(
                    MessageCategory.book_id == book_id,
                    MessageCategory.category == category
                ).all()
                
                category_message_ids = [msg_id[0] for msg_id in category_message_ids]
                logger.info(f"Found {len(category_message_ids)} messages in category '{category}'")
                
                if category_message_ids:
                    messages_query = messages_query.filter(Message.id.in_(category_message_ids))
                else:
                    # No messages found for this category
                    logger.info(f"No messages found in category '{category}'")
                    return {'formattedContent': '', 'messageCount': 0}
            
            # Execute the query and order by creation time
            messages = messages_query.order_by(Message.created_at.asc()).all()
            
            logger.info(f"Found {len(messages)} messages after applying all filters")
            
            if not messages:
                logger.info("No messages found after filtering")
                return {'formattedContent': '', 'messageCount': 0}
            
            # Format messages for AI
            message_texts = []
            for msg in messages:
                if msg.type == 'user':
                    message_texts.append(f"User: {msg.content}")
                else:
                    message_texts.append(f"Assistant: {msg.content}")
            
            # Prepare the prompt for AI formatting
            prompt = f"""
Format the following conversation into cohesive prose for a book chapter.
The book has a {tone_type} tone and {text_style} writing style.
Remove any technical details, code, or irrelevant information.
Focus on creating engaging, well-structured content that flows naturally.
{f"This content is for the '{category}' category of the book." if category else ""}

CONVERSATION:
{"\n".join(message_texts[-30:])}  # Limit to last 30 messages

FORMAT INSTRUCTIONS:
1. Write in {tone_type} tone
2. Use {text_style} writing style
3. Create proper paragraphs with good flow
4. Remove any technical jargon or irrelevant details
5. Focus on the narrative and key points
6. Do not include any meta-commentary about the formatting process
"""

            # Generate formatted content
            formatted_content = self.ai_service.generate_response(prompt, max_tokens=1500)
            
            # Update the last fetch timestamp if we have a chapter
            if chapter:
                old_timestamp = chapter.last_chat_fetch_at
                chapter.last_chat_fetch_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Updated last fetch time for chapter {chapter_id} from {old_timestamp} to {chapter.last_chat_fetch_at}")
            
            return {
                'formattedContent': formatted_content,
                'messageCount': len(messages)
            } 
        except Exception as e:
            logger.error(f"Error getting formatted recent chats: {str(e)}")
            raise 