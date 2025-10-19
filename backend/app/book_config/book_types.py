"""
Book Type Configurations for Enhanced Book Generation
"""

# Book type definitions with their configurations
BOOK_TYPES = {
    'relationship': {
        'name': 'Relationship Book',
        'description': 'Inspirational piece using all shared relationship data',
        'min_chapters': 4,
        'max_chapters': 8,
        'content_filter': 'all',  # Use all content
        'photo_priority': 'medium',
        'photo_to_text_ratio': 0.3,
        'organize_by': 'emotional_themes',
        'chapter_themes': [
            'How We Met',
            'Learning Each Other',
            'Daily Life Together',
            'Challenges & Growth',
            'Special Moments',
            'Our Bond Today',
            'Looking Forward'
        ],
        'keywords': ['bond', 'relationship', 'love', 'connection', 'together', 'friendship', 'companion']
    },
    'historical': {
        'name': 'Historical Book',
        'description': 'Chronological accounting of life with photos and stories',
        'min_chapters': 3,
        'max_chapters': 12,
        'content_filter': 'all',  # Use all content
        'photo_priority': 'maximum',
        'photo_to_text_ratio': 0.6,
        'organize_by': 'timeline',
        'auto_split_by_months': 3,  # Create chapter every 3 months
        'keywords': []  # No specific filtering, use all
    },
    'medical': {
        'name': 'Medical Record',
        'description': 'Summary of physical data and health tracking records',
        'min_chapters': 5,
        'max_chapters': 8,
        'content_filter': 'health',  # Only health-related content
        'photo_priority': 'low',
        'photo_to_text_ratio': 0.1,
        'organize_by': 'medical_categories',
        'chapter_themes': [
            'Health Profile & Baseline',
            'Preventive Care',
            'Nutrition & Diet',
            'Medical History',
            'Ongoing Monitoring',
            'Surgical Records',
            'Chronic Conditions'
        ],
        'keywords': ['health', 'vet', 'medical', 'doctor', 'sick', 'medicine', 'hospital', 'treatment', 
                     'vaccination', 'checkup', 'symptom', 'diagnosis', 'medication', 'surgery', 'dental',
                     'weight', 'diet', 'nutrition', 'food', 'eating', 'wellness']
    },
    'training': {
        'name': 'Training Book',
        'description': 'Comprehensive training journey and skill development',
        'min_chapters': 4,
        'max_chapters': 6,
        'content_filter': 'training',  # Only training-related content
        'photo_priority': 'medium',
        'photo_to_text_ratio': 0.2,
        'organize_by': 'skill_levels',
        'chapter_themes': [
            'Foundation & Basic Commands',
            'Intermediate Skills',
            'Behavioral Training',
            'Advanced Training & Tricks',
            'Training Philosophy',
            'Ongoing Development'
        ],
        'keywords': ['train', 'training', 'command', 'obedience', 'behavior', 'learn', 'practice', 
                     'sit', 'stay', 'come', 'down', 'heel', 'fetch', 'trick', 'skill', 'lesson']
    },
    'family': {
        'name': 'Family & Friends Book',
        'description': 'Social interactions and relationships with people and other dogs',
        'min_chapters': 5,
        'max_chapters': 7,
        'content_filter': 'social',  # Social interactions
        'photo_priority': 'high',
        'photo_to_text_ratio': 0.4,
        'organize_by': 'relationship_types',
        'chapter_themes': [
            'Family Circle',
            'Furry Friends',
            'Extended Family & Visitors',
            'Community Connections',
            'Special Moments Together',
            'The Social Butterfly'
        ],
        'keywords': ['family', 'friend', 'friends', 'social', 'people', 'visitor', 'guest', 'dog park',
                     'playdate', 'group', 'party', 'gathering', 'community', 'neighbor']
    },
    'memorial': {
        'name': "Dog's Life Book (Memorial)",
        'description': 'Comprehensive tribute celebrating their life',
        'min_chapters': 5,
        'max_chapters': 10,
        'content_filter': 'all',  # Use all content
        'photo_priority': 'maximum',
        'photo_to_text_ratio': 0.7,
        'organize_by': 'life_stages',
        'chapter_themes': [
            'The Beginning of Our Story',
            'Puppyhood Magic',
            'Prime of Life',
            'Later Years & Wisdom',
            'Their Unique Spirit',
            'Our Favorite Memories',
            'Their Legacy',
            'Photo Gallery'
        ],
        'keywords': []  # No specific filtering, use all
    },
    'general': {
        'name': 'General Book',
        'description': 'General purpose book with user-selected categories',
        'min_chapters': 3,
        'max_chapters': 8,
        'content_filter': 'categories',  # Use user-selected categories
        'photo_priority': 'medium',
        'photo_to_text_ratio': 0.3,
        'organize_by': 'categories',
        'chapter_themes': [],  # Dynamic based on user selection
        'keywords': []
    }
}

# Photo layout configurations by priority
PHOTO_LAYOUTS = {
    'maximum': {
        'photos_per_chapter': 'unlimited',
        'layout_class': 'photo-gallery',
        'caption_style': 'detailed',
        'spacing': 'generous'
    },
    'high': {
        'photos_per_chapter': 10,
        'layout_class': 'photo-integrated-high',
        'caption_style': 'standard',
        'spacing': 'normal'
    },
    'medium': {
        'photos_per_chapter': 6,
        'layout_class': 'photo-integrated',
        'caption_style': 'brief',
        'spacing': 'compact'
    },
    'low': {
        'photos_per_chapter': 3,
        'layout_class': 'photo-minimal',
        'caption_style': 'minimal',
        'spacing': 'tight'
    }
}

# Content filtering thresholds
CONTENT_THRESHOLDS = {
    'min_messages_per_chapter': 5,
    'min_total_messages': 15,
    'fallback_to_all_content_threshold': 20  # If filtered content < 20 messages, use all
}


def get_book_type_config(book_type: str) -> dict:
    """Get configuration for a specific book type"""
    return BOOK_TYPES.get(book_type, BOOK_TYPES['general'])


def get_photo_layout(priority: str) -> dict:
    """Get photo layout configuration"""
    return PHOTO_LAYOUTS.get(priority, PHOTO_LAYOUTS['medium'])


def should_filter_content(book_type: str) -> bool:
    """Check if content should be filtered for this book type"""
    config = get_book_type_config(book_type)
    return config['content_filter'] not in ['all', 'categories']


def get_filter_keywords(book_type: str) -> list:
    """Get filtering keywords for a book type"""
    config = get_book_type_config(book_type)
    return config.get('keywords', [])

