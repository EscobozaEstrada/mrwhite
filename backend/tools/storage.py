from langchain.tools import tool
from flask import current_app, g
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@tool("store_file")
def storage(file_info: str) -> str:
    """Store files, images, PDFs, or Google Drive links in the database.
    
    Args:
        file_info: Information about the file to store. Can include file paths, Google Drive links, 
                  or descriptions of files that were mentioned.
    """
    try:
        print(f"Storage tool called with file_info: '{file_info}'")
        
        # Get the user ID from the flask global context if available
        user_id = None
        
        # Try to get user_id from Flask's g object first
        try:
            if hasattr(g, 'user_id'):
                user_id = g.user_id
                print(f"Using user_id from Flask context: {user_id}")
        except:
            pass
            
        # If not available from context, try environment variable
        if not user_id:
            user_id = os.getenv("CURRENT_USER_ID")
            if user_id:
                print(f"Using user_id from environment variable: {user_id}")
        
        # If still not available, default to "1"
        if not user_id:
            user_id = "1"
            print(f"No user_id found, defaulting to: {user_id}")
            
        # Check if the input contains Google Drive links
        drive_links = extract_drive_links(file_info)
        
        # Generate a dummy storage timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Dummy implementation: Just log the file info and return success message
        if drive_links:
            # Handle Google Drive links
            link_count = len(drive_links)
            plural = "links" if link_count > 1 else "link"
            links_str = ", ".join(drive_links)
            print(f"Storing {link_count} Google Drive {plural} for user {user_id}: {links_str}")
            return f"Successfully stored {link_count} Google Drive {plural}. The content will be processed and made available for querying shortly."
        else:
            # Try to identify file types mentioned
            file_types = identify_file_types(file_info)
            
            if file_types:
                types_str = ", ".join(file_types)
                print(f"Storing {types_str} files for user {user_id}")
                return f"Successfully stored your {types_str} files at {timestamp}. They are now available in your knowledge base and can be referenced in future conversations."
            else:
                # Generic response if no specific file types identified
                print(f"Storing unspecified file(s) for user {user_id}")
                return f"Successfully stored your files at {timestamp}. They are now available in your knowledge base."
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Error in storage tool: {str(e)}\n{traceback_str}")
        return f"I encountered an error while trying to store your files: {str(e)}. Please try again or contact support if the issue persists."

def extract_drive_links(text):
    """Extract Google Drive links from text."""
    # Regex pattern for Google Drive links
    patterns = [
        r'https?://drive\.google\.com/\S+',
        r'https?://docs\.google\.com/\S+',
    ]
    
    links = []
    for pattern in patterns:
        links.extend(re.findall(pattern, text))
    
    return links

def identify_file_types(text):
    """Identify mentioned file types in the text."""
    file_types = []
    
    # Check for common file types
    if re.search(r'\.pdf|pdf|PDF|document', text, re.IGNORECASE):
        file_types.append("PDF")
    if re.search(r'\.jpe?g|\.png|\.gif|image|photo|picture', text, re.IGNORECASE):
        file_types.append("image")
    if re.search(r'\.docx?|\.txt|text file|word document', text, re.IGNORECASE):
        file_types.append("document")
    if re.search(r'\.xlsx?|\.csv|spreadsheet|excel', text, re.IGNORECASE):
        file_types.append("spreadsheet")
    if re.search(r'\.pptx?|presentation|powerpoint', text, re.IGNORECASE):
        file_types.append("presentation")
    if re.search(r'\.zip|\.rar|\.tar|\.gz|archive|compressed', text, re.IGNORECASE):
        file_types.append("archive")
    
    return file_types

# The function name is "previous" but the agent might call it as "get_previous_message"
# @tool("store_files")
# def store_files(query: str) -> str:
#     """Store files that are uploaded by the user.
    
#     Args:
#         query: The query to search for in previous messages. Should be the user's actual question. 
#         files: The files that are uploaded by the user.
#     """
    