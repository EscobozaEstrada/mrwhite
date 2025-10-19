"""
Claude Vision Service for Dog Image Analysis
Generates personalized descriptions of dog photos
"""
import logging
import json
import base64
from typing import Dict, Optional
import boto3
from config.settings import settings

logger = logging.getLogger(__name__)


class VisionService:
    """Service for analyzing dog images using Claude Vision"""
    
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        # Use the same model as streaming (Claude Haiku supports vision too!)
        self.vision_model_id = settings.BEDROCK_MODEL_ID
    
    async def analyze_dog_image(
        self,
        image_data: str,  # base64 encoded image
        dog_context: Dict[str, Optional[str]]
    ) -> str:
        """
        Analyze a dog image with personalized context
        
        Args:
            image_data: Base64 encoded image string (with or without data:image prefix)
            dog_context: Dict with keys: name, breed, age, gender, color
        
        Returns:
            Personalized description of what's visible in the photo
        """
        try:
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',', 1)[1]
            
            # Build personalized prompt
            name = dog_context.get('name', 'this dog')
            breed = dog_context.get('breed', 'Unknown')
            age = dog_context.get('age')
            gender = dog_context.get('gender', 'Unknown')
            color = dog_context.get('color', 'Unknown')
            
            prompt = f"""You are analyzing a photo of a dog with the following details:
- Name: {name}
- Breed: {breed}"""
            
            if age:
                prompt += f"\n- Age: {age} years old"
            if gender and gender != 'Unknown':
                prompt += f"\n- Gender: {gender}"
            if color and color != 'Unknown':
                prompt += f"\n- Color: {color}"
            
            prompt += f"""

Please describe what you see in this specific photo of {name}. Focus on:
1. **Physical appearance visible in the photo** (coat condition, body posture, facial expression)
2. **What {name} is doing** in the photo (sitting, playing, running, standing, etc.)
3. **The setting/environment** (indoors, outdoors, park, home, beach, etc.)
4. **Any notable features or characteristics** you can observe
5. **The overall mood/energy** conveyed in the photo

IMPORTANT:
- Describe ONLY what you can SEE in this specific photo
- DO NOT make assumptions about age or breed that might conflict with the provided information
- Keep the description natural and personalized to {name}
- Use 2-3 paragraphs, around 150-200 words
- This description will help provide better advice about {name}

Be descriptive but concise. Focus on observable details that would be useful for understanding {name}'s current state and environment."""
            
            # Prepare request body for Claude Vision
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",  # Assume JPEG, Claude handles PNG/JPEG/WebP
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            logger.info(f"🖼️ Analyzing image for {name} ({breed})...")
            
            # Call Claude Vision via Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.vision_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            description = response_body['content'][0]['text']
            
            logger.info(f"✅ Generated description for {name}: {len(description)} chars")
            return description.strip()
            
        except Exception as e:
            logger.error(f"❌ Vision analysis failed: {str(e)}")
            # Return a fallback description
            return f"A photo of {dog_context.get('name', 'a dog')}. (Vision analysis unavailable)"
    
    async def analyze_chat_image(
        self,
        image_data: str,  # base64 encoded image
        user_dog_profiles: list,
        filename: str = "uploaded_image"
    ) -> str:
        """
        Analyze a chat-uploaded image with smart dog detection
        
        Args:
            image_data: Base64 encoded image string (with or without data:image prefix)
            user_dog_profiles: List of user's dog profiles with context
            filename: Original filename for context
        
        Returns:
            Personalized description if dog context found, otherwise generic description
        """
        try:
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',', 1)[1]
            
            # If no dog profiles, use generic description
            if not user_dog_profiles:
                return await self._generate_generic_image_description(image_data, filename)
            
            # If only one dog, use that dog's context
            if len(user_dog_profiles) == 1:
                dog = user_dog_profiles[0]
                dog_context = {
                    "name": dog.get('name', 'your dog'),
                    "breed": dog.get('breed', 'Unknown'),
                    "age": dog.get('age'),
                    "gender": dog.get('gender', 'Unknown'),
                    "color": dog.get('color', 'Unknown')
                }
                return await self.analyze_dog_image(image_data, dog_context)
            
            # Multiple dogs - try single dog analysis first, then fallback to multi-dog
            # This is more aggressive and will likely produce better personalized descriptions
            return await self._analyze_with_aggressive_single_dog_detection(image_data, user_dog_profiles, filename)
            
        except Exception as e:
            logger.error(f"❌ Chat image analysis failed: {str(e)}")
            return await self._generate_generic_image_description(image_data, filename)
    
    async def _analyze_with_aggressive_single_dog_detection(
        self,
        image_data: str,
        user_dog_profiles: list,
        filename: str
    ) -> str:
        """Aggressively try to identify a single dog, fallback to multi-dog if needed"""
        try:
            # Build context for all dogs
            dogs_info = []
            for dog in user_dog_profiles:
                dog_info = f"- {dog.get('name', 'Unknown')} ({dog.get('breed', 'Unknown breed')})"
                if dog.get('age'):
                    dog_info += f", {dog.get('age')} years old"
                if dog.get('color') and dog.get('color') != 'Unknown':
                    dog_info += f", {dog.get('color')} color"
                dogs_info.append(dog_info)
            
            dogs_context = "\n".join(dogs_info)
            
            prompt = f"""You are analyzing a photo that contains a dog. Here are the possible dogs it could be:

{dogs_context}

CRITICAL INSTRUCTIONS - BE AGGRESSIVE AND CONFIDENT:
- **This photo shows ONE of these dogs** - identify which one it is
- **Look at the breed, size, color, and characteristics** to make a confident identification
- **ALWAYS start your description with the dog's actual name** (e.g., "This photo shows Max...")
- **Be confident in your identification** - don't be vague or generic
- **Use personal pronouns** (e.g., "Max is sitting..." not "The dog is sitting...")
- **Reference the dog's known characteristics** (e.g., "Max's golden coat", "Bella's fluffy white fur")

IDENTIFICATION RULES:
- If it's a Golden Retriever/large golden dog → It's Max
- If it's a Pomeranian/small fluffy dog → It's Bella
- If it's brown/golden colored → It's Max
- If it's white/small → It's Bella

Describe what you see focusing on:
1. **Start with the dog's name** (e.g., "This photo shows Max...")
2. **What the dog is doing** in the photo
3. **The setting/environment** 
4. **Physical appearance and mood**
5. **Reference their known characteristics**

IMPORTANT:
- **ALWAYS use the dog's actual name** - be confident!
- **Make it personal and specific** to the dog's profile
- **Use 2-3 paragraphs, around 150-200 words**
- **This description will help provide better advice about the dog**

Be descriptive but concise. Focus on observable details that would be useful for understanding the dog's current state and environment."""
            
            # Prepare request body for Claude Vision
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            logger.info(f"🖼️ Analyzing image with aggressive single dog detection...")
            
            # Call Claude Vision via Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.vision_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            description = response_body['content'][0]['text']
            
            logger.info(f"✅ Generated aggressive single dog description: {len(description)} chars")
            return description.strip()
            
        except Exception as e:
            logger.error(f"❌ Aggressive single dog analysis failed: {str(e)}")
            # Fallback to multi-dog analysis
            return await self._analyze_with_multiple_dogs(image_data, user_dog_profiles, filename)
    
    async def _analyze_with_multiple_dogs(
        self,
        image_data: str,
        user_dog_profiles: list,
        filename: str
    ) -> str:
        """Analyze image when user has multiple dogs"""
        try:
            # Build context for multiple dogs
            dogs_info = []
            for dog in user_dog_profiles:
                dog_info = f"- {dog.get('name', 'Unknown')} ({dog.get('breed', 'Unknown breed')})"
                if dog.get('age'):
                    dog_info += f", {dog.get('age')} years old"
                if dog.get('color') and dog.get('color') != 'Unknown':
                    dog_info += f", {dog.get('color')} color"
                dogs_info.append(dog_info)
            
            dogs_context = "\n".join(dogs_info)
            
            prompt = f"""You are analyzing a photo that may contain one or more of these dogs:

{dogs_context}

Please describe what you see in this photo, focusing on:
1. **Which dog(s) are visible** (if any) - try to identify by breed, size, color, or other distinguishing features
2. **What the dog(s) are doing** in the photo (sitting, playing, running, etc.)
3. **The setting/environment** (indoors, outdoors, park, home, etc.)
4. **Physical appearance and mood** of any visible dogs
5. **Any notable activities or interactions**

CRITICAL INSTRUCTIONS:
- **ALWAYS use the dog's actual name** if you can identify them by breed, size, or color
- **Be confident in your identification** - if it looks like a Golden Retriever, it's likely Max
- **If it looks like a Pomeranian, it's likely Bella**
- **Start your description with the dog's name** (e.g., "This photo shows Max...")
- **Use personal pronouns** (e.g., "Max is sitting..." not "The dog is sitting...")
- **Reference the dog's known characteristics** (e.g., "Max's golden coat", "Bella's fluffy white fur")
- **Make it personal and specific** to the dog's profile information

IMPORTANT:
- If you can identify a specific dog, use their name in the description
- If multiple dogs are visible, describe each one by name
- If no dogs are clearly visible, describe what you do see
- Keep the description natural and helpful for understanding the dog's current state
- Use 2-3 paragraphs, around 150-200 words
- This description will help provide better advice about the dog(s)

Be descriptive but concise. Focus on observable details that would be useful for understanding the dog's current state and environment."""
            
            # Prepare request body for Claude Vision
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            logger.info(f"🖼️ Analyzing image with multiple dog context...")
            
            # Call Claude Vision via Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.vision_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            description = response_body['content'][0]['text']
            
            logger.info(f"✅ Generated multi-dog description: {len(description)} chars")
            return description.strip()
            
        except Exception as e:
            logger.error(f"❌ Multi-dog analysis failed: {str(e)}")
            return await self._generate_generic_image_description(image_data, filename)
    
    async def _generate_generic_image_description(
        self,
        image_data: str,
        filename: str
    ) -> str:
        """Generate generic image description as fallback"""
        try:
            prompt = f"""Analyze this image and provide a comprehensive description that includes:

1. Main subject/subjects in the image
2. Setting/environment/background
3. Colors, lighting, and mood
4. Any text visible in the image
5. Objects, animals, or people present
6. Activities or actions taking place
7. Style or type of image (photo, artwork, screenshot, etc.)
8. Any notable details or interesting features

Provide a natural, detailed description that would help someone understand what's in the image without seeing it. If this appears to be related to pets, dogs, or animals, please include specific details about breed, size, color, behavior, or health-related observations."""
            
            # Prepare request body for Claude Vision
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            logger.info(f"🖼️ Generating generic description for {filename}...")
            
            # Call Claude Vision via Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.vision_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            description = response_body['content'][0]['text']
            
            logger.info(f"✅ Generated generic description: {len(description)} chars")
            return description.strip()
            
        except Exception as e:
            logger.error(f"❌ Generic description failed: {str(e)}")
            return f"A photo uploaded as {filename}. (Vision analysis unavailable)"


# Singleton instance
vision_service = VisionService()
