from .auth import auth_bp
from .conversation import conversation_bp
from .contact import contact_bp
from .chatbot import chat_bp as chatbot_bp

from .care_archive import care_archive_bp
from .payment import payment_bp
from .subscription import subscription_bp
from .text_to_speech import text_to_speech_bp
from .speech_to_text import speech_to_text_bp
__all__ = ['auth_bp', 'conversation_bp', 'contact_bp', 'chatbot_bp', 'care_archive_bp', 'payment_bp', 'subscription_bp', 'text_to_speech_bp', 'speech_to_text_bp']