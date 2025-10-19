from flask import Blueprint, request, jsonify, current_app, g
import os
import tempfile
from dotenv import load_dotenv
import requests
import logging
import uuid
from werkzeug.utils import secure_filename
from app.utils.audio_handler import process_audio_file
from datetime import datetime

# Load environment variables
load_dotenv()

speech_to_text_bp = Blueprint('speech_to_text', __name__)

@speech_to_text_bp.route('', methods=['POST'])
def speech_to_text():
    """
    Endpoint for speech-to-text conversion
    Expects audio file in the request
    Returns transcribed text
    """
    try:
        # Check if file is in the request
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Get OpenAI API key from environment variables
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai_api_key:
            current_app.logger.error("OpenAI API key not configured")
            return jsonify({'error': 'OpenAI API key not configured'}), 500
        
        # Save the uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
        audio_file.save(temp_file.name)
        temp_file.close()
        
        try:
            # Make request to OpenAI Whisper API
            with open(temp_file.name, 'rb') as f:
                response = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {openai_api_key}"},
                    files={"file": f},
                    data={"model": "whisper-1"}
                )
            
            # Check response
            if response.status_code != 200:
                current_app.logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return jsonify({'error': f'OpenAI API error: {response.status_code}'}), response.status_code
            
            # Get the transcription
            transcription = response.json()
            transcription_text = transcription['text']
            
            # If user is authenticated, also store the audio file in S3
            s3_url = None
            if hasattr(g, 'user_id') and g.user_id:
                try:
                    # Reopen the file for S3 upload
                    audio_file.seek(0)
                    
                    # Generate a unique filename
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    original_filename = secure_filename(audio_file.filename)
                    unique_filename = f"transcription-{timestamp}-{uuid.uuid4()}{os.path.splitext(original_filename)[1]}"
                    
                    # Process and upload to S3
                    result = process_audio_file(audio_file, g.user_id, transcription_text)
                    if result.get('success'):
                        s3_url = result.get('url')
                        current_app.logger.info(f"Transcribed audio uploaded to S3: {s3_url}")
                except Exception as s3_error:
                    current_app.logger.error(f"Error uploading transcribed audio to S3: {str(s3_error)}")
                    # Continue without S3 upload - transcription still works
            
            # Return the transcription
            return jsonify({
                'success': True,
                'transcription': transcription_text,
                's3_url': s3_url
            })
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
        
    except Exception as e:
        current_app.logger.error(f"Error in speech-to-text: {str(e)}")
        return jsonify({'error': str(e)}), 500 