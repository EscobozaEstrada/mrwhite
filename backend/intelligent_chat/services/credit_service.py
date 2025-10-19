"""
Credit System Service for Intelligent Chat
Handles credit deduction by calling Flask backend API
"""
import logging
import aiohttp
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class IntelligentChatCreditService:
    """
    Credit system for intelligent chat with different costs based on mode and features
    Uses Flask backend API for credit operations
    """
    
    # Credit costs for intelligent chat
    CREDIT_COSTS = {
        "normal_chat": 2,           # $0.02 - Normal chat mode
        "health_mode": 4,            # $0.04 - Health mode (per message)
        "wayofdog_mode": 2,          # $0.02 - Way of Dog mode
        "document_upload": 4,        # $0.04 - Document/image upload
        "health_with_document": 8,   # $0.08 - Health mode + document upload
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.flask_base_url = os.getenv("FLASK_BASE_URL", "http://localhost:5001")
    
    async def check_and_deduct_credits(
        self, 
        user_id: int, 
        active_mode: Optional[str], 
        has_documents: bool = False,
        metadata: Optional[Dict] = None,
        cookies: Optional[Dict] = None
    ) -> Tuple[bool, str, int]:
        """
        Check if user has enough credits and deduct them based on chat mode and features
        
        Args:
            user_id: User ID
            active_mode: Current chat mode (health, wayofdog, or None for normal)
            has_documents: Whether documents were uploaded
            metadata: Additional metadata for the transaction
            cookies: Request cookies for authentication
            
        Returns:
            Tuple of (success: bool, message: str, credits_deducted: int)
        """
        try:
            # Calculate credit cost based on mode and features
            credit_cost = self._calculate_credit_cost(active_mode, has_documents)
            
            # Map intelligent chat modes to Flask credit actions
            flask_action = self._map_to_flask_action(active_mode, has_documents)
            
            # Prepare metadata for Flask backend
            flask_metadata = {
                "mode": active_mode or "normal",
                "has_documents": has_documents,
                "credit_cost": credit_cost,
                "intelligent_chat": True
            }
            if metadata:
                flask_metadata.update(metadata)
            
            # Call Flask backend to check and deduct credits
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.flask_base_url}/api/credit-system/check-and-deduct",
                    json={
                        "user_id": user_id,
                        "action": flask_action,
                        "metadata": flask_metadata
                    },
                    cookies=cookies or {},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return True, result.get("message", "Success"), credit_cost
                    elif response.status == 402:
                        error_data = await response.json()
                        return False, error_data.get("message", "Insufficient credits"), 0
                    else:
                        error_text = await response.text()
                        return False, f"Credit system error: {error_text}", 0
            
        except Exception as e:
            self.logger.error(f"Error checking/deducting credits: {str(e)}")
            return False, "Credit system error", 0
    
    def _calculate_credit_cost(self, active_mode: Optional[str], has_documents: bool) -> int:
        """
        Calculate credit cost based on mode and document upload
        """
        if active_mode == "health":
            if has_documents:
                return self.CREDIT_COSTS["health_with_document"]  # 8 credits
            else:
                return self.CREDIT_COSTS["health_mode"]  # 4 credits
        elif active_mode == "wayofdog":
            return self.CREDIT_COSTS["wayofdog_mode"]  # 2 credits
        else:
            # Normal chat mode
            if has_documents:
                return self.CREDIT_COSTS["normal_chat"] + self.CREDIT_COSTS["document_upload"]  # 2 + 4 = 6 credits
            else:
                return self.CREDIT_COSTS["normal_chat"]  # 2 credits
    
    def _map_to_flask_action(self, active_mode: Optional[str], has_documents: bool) -> str:
        """
        Map intelligent chat modes to Flask credit system actions
        """
        if active_mode == "health":
            if has_documents:
                return "health_assessment"  # 15 credits (closest to our 8)
            else:
                return "chat_message_health"  # 8 credits (closest to our 4)
        elif active_mode == "wayofdog":
            return "chat_message_basic"  # 2 credits
        else:
            # Normal chat mode
            if has_documents:
                return "document_upload"  # 8 credits (closest to our 6)
            else:
                return "chat_message_basic"  # 2 credits
    
    async def get_user_credits(self, user_id: int, cookies: Optional[Dict] = None) -> Optional[int]:
        """
        Get user's current credit balance from Flask backend
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.flask_base_url}/api/credit-system/user/{user_id}/credits",
                    cookies=cookies or {},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("credits_balance", 0)
                    else:
                        self.logger.error(f"Failed to get user credits: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error getting user credits: {str(e)}")
            return None