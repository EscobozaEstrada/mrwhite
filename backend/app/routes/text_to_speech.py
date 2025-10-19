from flask import Blueprint, request, jsonify, current_app, Response
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

text_to_speech_bp = Blueprint('text_to_speech', __name__)

@text_to_speech_bp.route('', methods=['POST'])
def text_to_speech():
    """
    Proxy endpoint for Eleven Labs text-to-speech API
    Expects JSON with 'text' field and optional voice tuning parameters
    Returns audio data
    """
    try:
        # Get the API key from environment variables
        eleven_labs_api_key = os.getenv('ELEVEN_LABS_API_KEY')
        
        if not eleven_labs_api_key:
            current_app.logger.error("Eleven Labs API key not configured")
            return jsonify({'error': 'Eleven Labs API key not configured'}), 500
        
        # Get text from request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        
        # Get voice ID and model from environment variables with defaults
        voice_id = os.getenv('MR_WHITE_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
        model_id = os.getenv('ELEVEN_LABS_MODEL_ID', 'eleven_multilingual_v2')
        
        # Get voice settings from request or use defaults
        stability = float(data.get('stability', os.getenv('ELEVEN_LABS_STABILITY', '0.5')))
        similarity_boost = float(data.get('similarity_boost', os.getenv('ELEVEN_LABS_SIMILARITY_BOOST', '0.75')))
        speed = float(data.get('speed', 1.0))
        
        # Ensure values are within valid ranges
        stability = max(0.0, min(1.0, stability))
        similarity_boost = max(0.0, min(1.0, similarity_boost))
        speed = max(0.7, min(1.2, speed))
        
        # Make request to Eleven Labs API
        eleven_labs_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": eleven_labs_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "speed": speed
            }
        }
        
        current_app.logger.info(f"Sending request to Eleven Labs with voice_id: {voice_id}, model_id: {model_id}, settings: {payload['voice_settings']}")
        
        # Forward the request to Eleven Labs
        response = requests.post(eleven_labs_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            current_app.logger.error(f"Eleven Labs API error: {response.status_code} - {response.text}")
            return jsonify({'error': f'Eleven Labs API error: {response.status_code}'}), response.status_code
        
        # Return the audio data with appropriate headers
        return Response(
            response.content,
            mimetype="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in text-to-speech: {str(e)}")
        return jsonify({'error': str(e)}), 500 