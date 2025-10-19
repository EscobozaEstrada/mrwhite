from langchain.tools import tool
from flask import current_app, g
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

@tool("email_files")
def emailer(file_request: str) -> str:
    """Email files to the user.
    
    Args:
        file_request: Information about which files the user wants emailed to them.
                     Can be specific file names or general requests like "all PDF files" or "recent uploads".
    """
    try:
        print(f"Emailer tool called with file_request: '{file_request}'")
        
        # Get the user ID and email from the flask global context if available
        user_id = None
        user_email = None
        
        # Try to get user info from Flask's g object first
        try:
            if hasattr(g, 'user_id'):
                user_id = g.user_id
                print(f"Using user_id from Flask context: {user_id}")
            if hasattr(g, 'user_email'):
                user_email = g.user_email
                print(f"Using user_email from Flask context: {user_email}")
        except:
            pass
            
        # If not available from context, try environment variable
        if not user_id:
            user_id = os.getenv("CURRENT_USER_ID")
            if user_id:
                print(f"Using user_id from environment variable: {user_id}")
        
        if not user_email:
            user_email = os.getenv("CURRENT_USER_EMAIL")
            if user_email:
                print(f"Using user_email from environment variable: {user_email}")
        
        # If still no email, check database
        if not user_email and user_id:
            try:
                db_url = os.getenv("DATABASE_URL")
                if db_url:
                    engine = create_engine(db_url)
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT email FROM user WHERE id = :user_id"), {"user_id": user_id})
                        user_data = result.fetchone()
                        if user_data:
                            user_email = user_data[0]
                            print(f"Retrieved user_email from database: {user_email}")
            except Exception as e:
                print(f"Error retrieving email from database: {str(e)}")
        
        # Check if we have required information
        if not user_id:
            return "I couldn't identify your user account. Please try again or contact support."
        
        if not user_email:
            return "I couldn't find your email address. Please specify your email address or contact support."
        
        # Parse the file request to identify which files to send
        file_names = extract_file_names(file_request)
        file_types = identify_file_types(file_request)
        
        # Check if specific files were requested
        if not file_names and not file_types:
            return "Please specify which files you'd like me to email to you. For example, you can say 'Send me the PDF I uploaded yesterday' or 'Email me my latest spreadsheet'."
        
        # DUMMY IMPLEMENTATION: In a real system, you would fetch the actual files from storage
        # For now, we'll simulate finding files based on the request
        
        # Simulate checking the database for matching files
        matched_files = []
        
        # In a real implementation, you would:
        # 1. Query your database or file storage system for files matching the user's request
        # 2. Filter by user_id to ensure they only get their own files
        # 3. Retrieve the file paths or URLs
        
        # For the dummy implementation, we'll pretend we found these files
        if file_names:
            for name in file_names:
                matched_files.append({
                    "name": name,
                    "url": f"https://example.com/files/{name}",
                    "type": guess_file_type(name)
                })
        
        if file_types and not matched_files:
            # Simulate finding files by type
            dummy_files = {
                "pdf": ["report.pdf", "documentation.pdf"],
                "document": ["notes.docx", "letter.doc"],
                "image": ["photo.jpg", "screenshot.png"],
                "spreadsheet": ["data.xlsx", "budget.csv"],
                "presentation": ["slides.pptx"],
                "archive": ["backup.zip"]
            }
            
            for file_type in file_types:
                file_type_lower = file_type.lower()
                if file_type_lower in dummy_files:
                    for name in dummy_files[file_type_lower]:
                        matched_files.append({
                            "name": name,
                            "url": f"https://example.com/files/{name}",
                            "type": file_type
                        })
        
        # Check if we found any files
        if not matched_files:
            return f"I couldn't find any files matching your request for '{file_request}'. Please check the file names or try with different criteria."
        
        # DUMMY IMPLEMENTATION: Simulate sending an email
        # In a real implementation, you would:
        # 1. Download the files or get their contents
        # 2. Attach them to an email
        # 3. Send the email using SMTP
        
        # Simulate successful email sending
        file_list = ", ".join([file["name"] for file in matched_files])
        
        # Dummy email sending logic - in a real implementation, use the code below
        """
        # Set up email
        msg = MIMEMultipart()
        msg['From'] = os.getenv("MAIL_USERNAME")
        msg['To'] = user_email
        msg['Subject'] = f"Your Requested Files from Mr. White"
        
        # Email body
        body = f"Hello,\n\nAs requested, here are the files you asked for: {file_list}.\n\nBest regards,\nMr. White"
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach files (this would download or retrieve the actual files in a real implementation)
        for file in matched_files:
            # In a real system, you would get the file contents here
            attachment = MIMEApplication("Dummy file content")
            attachment['Content-Disposition'] = f'attachment; filename="{file["name"]}"'
            msg.attach(attachment)
        
        # Send email
        try:
            server = smtplib.SMTP(os.getenv("MAIL_SERVER"), int(os.getenv("MAIL_PORT")))
            server.starttls()
            server.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return f"I encountered an error while trying to send the email: {str(e)}"
        """
        
        print(f"Simulated sending email to {user_email} with files: {file_list}")
        return f"I've sent the following files to your email address ({user_email}): {file_list}. Please check your inbox shortly."
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Error in emailer tool: {str(e)}\n{traceback_str}")
        return f"I encountered an error while trying to email your files: {str(e)}. Please try again or contact support if the issue persists."

def extract_file_names(text):
    """Extract specific file names from the request text."""
    
    # Common file extensions
    extensions = r'\.(pdf|docx?|xlsx?|pptx?|csv|txt|jpe?g|png|gif|zip|rar)'
    
    # Find words that look like filenames with extensions
    potential_files = re.findall(r'\b[\w\-\s]+' + extensions + r'\b', text, re.IGNORECASE)
    
    # Additional check for phrases like "send me file.pdf"
    specific_files = re.findall(r'send\s+(?:me|the)\s+([\w\-\s]+' + extensions + r')', text, re.IGNORECASE)
    
    # Combine and clean results
    file_names = []
    for match in potential_files + specific_files:
        if isinstance(match, tuple):  # If the regex captured groups
            file_name = ''.join(match)
        else:
            file_name = match
        
        file_name = file_name.strip()
        if file_name and file_name not in file_names:
            file_names.append(file_name)
    
    return file_names

def identify_file_types(text):
    """Identify mentioned file types in the text."""
    file_types = []
    
    # Check for common file types
    if re.search(r'pdf|document', text, re.IGNORECASE):
        file_types.append("pdf")
    if re.search(r'jpe?g|png|gif|image|photo|picture', text, re.IGNORECASE):
        file_types.append("image")
    if re.search(r'docx?|txt|text file|word document', text, re.IGNORECASE):
        file_types.append("document")
    if re.search(r'xlsx?|csv|spreadsheet|excel', text, re.IGNORECASE):
        file_types.append("spreadsheet")
    if re.search(r'pptx?|presentation|powerpoint|slides', text, re.IGNORECASE):
        file_types.append("presentation")
    if re.search(r'zip|rar|tar|gz|archive|compressed', text, re.IGNORECASE):
        file_types.append("archive")
    
    return file_types

def guess_file_type(filename):
    """Guess the type of file from its name."""
    lower_name = filename.lower()
    
    if lower_name.endswith(('.pdf')):
        return "pdf"
    elif lower_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
        return "image"
    elif lower_name.endswith(('.doc', '.docx', '.txt', '.rtf')):
        return "document"
    elif lower_name.endswith(('.xls', '.xlsx', '.csv')):
        return "spreadsheet"
    elif lower_name.endswith(('.ppt', '.pptx')):
        return "presentation"
    elif lower_name.endswith(('.zip', '.rar', '.tar', '.gz')):
        return "archive"
    else:
        return "file"
