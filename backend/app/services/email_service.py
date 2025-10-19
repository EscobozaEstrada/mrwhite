from typing import Optional, Dict, Any, Tuple
from flask import current_app
from app.models.contact import Contact
from app import db
from app.utils.mail import send_email


class EmailService:
    """Service class for handling email operations"""
    
    @staticmethod
    def submit_contact_form(name: str, email: str, message: str, phone: Optional[str] = None, 
                          user_id: Optional[int] = None, subject: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Submit a contact form and send notification email
        
        Returns:
            Tuple of (success: bool, message: str, contact_data: Optional[Dict])
        """
        try:
            # Validate required fields
            if not all([name, email, message]):
                return False, 'Name, email, and message are required', None
            
            # Create contact entry
            contact = Contact(
                name=name,
                email=email,
                phone=phone or '',
                subject=subject or 'Contact Form Inquiry',
                message=message,
                user_id=user_id
            )
            
            db.session.add(contact)
            db.session.commit()
            
            # Send notification email to admin
            email_sent = EmailService._send_contact_notification(contact)
            
            if email_sent:
                return True, 'Your message has been submitted successfully.', contact.to_dict()
            else:
                return True, 'Your message has been submitted, but there was an issue sending the notification email.', contact.to_dict()
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting contact form: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def send_password_reset_email(email: str, reset_url: str) -> bool:
        """
        Send password reset email
        
        Returns:
            Success status
        """
        try:
            subject = "Mr. White - Password Reset"
            html_content = EmailService._get_password_reset_template(reset_url)
            return send_email(email, subject, html_content)
        except Exception as e:
            current_app.logger.error(f"Error sending password reset email: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(email: str, username: str) -> bool:
        """
        Send welcome email to new users
        
        Returns:
            Success status
        """
        try:
            subject = "Welcome to Mr. White - Your AI Dog Care Assistant"
            html_content = EmailService._get_welcome_template(username)
            return send_email(email, subject, html_content)
        except Exception as e:
            current_app.logger.error(f"Error sending welcome email: {str(e)}")
            return False
    
    @staticmethod
    def send_file_email(email: str, files: list, user_name: str = "User") -> bool:
        """
        Send files to user via email
        
        Returns:
            Success status
        """
        try:
            subject = "Mr. White - Your Requested Files"
            html_content = EmailService._get_file_email_template(files, user_name)
            return send_email(email, subject, html_content)
        except Exception as e:
            current_app.logger.error(f"Error sending file email: {str(e)}")
            return False
    
    @staticmethod
    def _send_contact_notification(contact: Contact) -> bool:
        """Send contact form notification to admin"""
        try:
            admin_email = current_app.config.get('ADMIN_EMAIL')
            subject = f"Mr. White Contact: {contact.subject}"
            html_content = EmailService._get_contact_notification_template(contact)
            return send_email(admin_email, subject, html_content)
        except Exception as e:
            current_app.logger.error(f"Error sending contact notification: {str(e)}")
            return False
    
    @staticmethod
    def _get_password_reset_template(reset_url: str) -> str:
        """Get HTML template for password reset email"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #000; color: #fff; border-radius: 5px;">
                    <h2 style="color: #fff; text-align: center;">Mr. White Password Reset</h2>
                    <p>Hello,</p>
                    <p>You requested a password reset for your Mr. White account.</p>
                    <p>Please click the link below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" style="display: inline-block; background-color: #fff; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Your Password</a>
                    </p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you did not request this, please ignore this email.</p>
                    <hr style="border: 1px solid #333; margin: 20px 0;">
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - AI Assistant for Dog Care & Beyond</p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _get_welcome_template(username: str) -> str:
        """Get HTML template for welcome email"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #000; color: #fff; border-radius: 5px;">
                    <h2 style="color: #fff; text-align: center;">Welcome to Mr. White!</h2>
                    <p>Hello {username},</p>
                    <p>Welcome to Mr. White - your AI-powered dog care assistant!</p>
                    <p>You can now:</p>
                    <ul>
                        <li>Ask questions about dog care and training</li>
                        <li>Upload documents for personalized advice</li>
                        <li>Get expert guidance on your pet's needs</li>
                        <li>Access our comprehensive knowledge base</li>
                    </ul>
                    <p style="text-align: center;">
                        <a href="{current_app.config['FRONTEND_URL']}" style="display: inline-block; background-color: #fff; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Start Chatting</a>
                    </p>
                    <hr style="border: 1px solid #333; margin: 20px 0;">
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - AI Assistant for Dog Care & Beyond</p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _get_contact_notification_template(contact: Contact) -> str:
        """Get HTML template for contact form notification"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Contact Form Submission</title>
            </head>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #e0e0e0; line-height: 1.6; background-color: #121212; margin: 0; padding: 0;">
                <div style="max-width: 600px; margin: 20px auto; background-color: #1e1e1e; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <!-- Header with gradient background -->
                    <div style="padding: 30px; background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%); text-align: center; border-bottom: 1px solid #333;">
                        <img src="https://master-white-project.s3.us-east-1.amazonaws.com/public/logo1.png" alt="Mr. White Logo" style="max-height: 60px; margin-bottom: 15px;">
                        <h2 style="color: #D3B86A; margin: 0; padding: 0; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.4);">New Contact Message</h2>
                    </div>
                    
                    <!-- Content area -->
                    <div style="padding: 35px 30px;">
                        <!-- Subject section with accent border -->
                        <div style="padding-bottom: 25px; margin-bottom: 25px; border-bottom: 2px solid #333;">
                            <h3 style="margin: 0 0 10px 0; color: #D3B86A; font-size: 18px;">Subject</h3>
                            <p style="margin: 0; padding: 0; font-size: 16px; color: #cccccc;">{contact.subject or 'Contact Form Inquiry'}</p>
                        </div>
                        
                        <!-- Contact details with icons -->
                        <div style="padding-bottom: 25px; margin-bottom: 25px; background-color: #252525; border-radius: 8px; padding: 20px;">
                            <h3 style="margin: 0 0 15px 0; color: #D3B86A; font-size: 18px;">Contact Details</h3>
                            
                            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                                <div style="width: 24px; margin-right: 10px; color: #cccccc;">👤</div>
                                <div>
                                    <strong style="color: #aaaaaa;">Name:</strong> 
                                    <span style="color: #e0e0e0;">{contact.name}</span>
                                </div>
                            </div>
                            
                            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                                <div style="width: 24px; margin-right: 10px; color: #cccccc;">✉️</div>
                                <div>
                                    <strong style="color: #aaaaaa;">Email:</strong> 
                                    <span style="color: #e0e0e0;">{contact.email}</span>
                                </div>
                            </div>
                            
                            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                                <div style="width: 24px; margin-right: 10px; color: #cccccc;">📞</div>
                                <div>
                                    <strong style="color: #aaaaaa;">Phone:</strong> 
                                    <span style="color: #e0e0e0;">{contact.phone or 'Not provided'}</span>
                                </div>
                            </div>
                            
                            <div style="display: flex; align-items: center;">
                                <div style="width: 24px; margin-right: 10px; color: #cccccc;">🆔</div>
                                <div>
                                    <strong style="color: #aaaaaa;">User ID:</strong> 
                                    <span style="color: #e0e0e0;">{contact.user_id or 'Not logged in'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Message section with styled box -->
                        <div>
                            <h3 style="margin: 0 0 15px 0; color: #D3B86A; font-size: 18px;">Message</h3>
                            <div style="background-color: #252525; padding: 20px; border-radius: 8px; border-left: 4px solid #D3B86A;">
                                <p style="margin: 0; padding: 0; color: #e0e0e0; line-height: 1.7;">{contact.message}</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Action button -->
                    <div style="padding: 0 30px 30px; text-align: center;">
                        <a href="mailto:{contact.email}" style="display: inline-block; background: #D3B86A; color: black; padding: 12px 30px; text-decoration: none; border-radius: 20px; font-weight: 500; margin-top: 10px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);">Reply to {contact.name}</a>
                    </div>
                    
                    <!-- Footer -->
                    <div style="padding: 20px; background-color: #121212; text-align: center; border-top: 1px solid #333;">
                        <p style="margin: 0; padding: 0; color: #888888; font-size: 13px;">This is an automated notification from Mr. White.</p>
                        <p style="margin: 8px 0 0 0; padding: 0; color: #888888; font-size: 13px;">© 2025 Mr. White - AI Assistant for Dog Care & Beyond</p>
                    </div>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _get_file_email_template(files: list, user_name: str) -> str:
        """Get HTML template for file email"""
        files_list = ""
        for file in files:
            files_list += f"<li><a href='{file.get('url', '#')}' style='color: #fff;'>{file.get('name', 'Unnamed File')}</a></li>"
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #000; color: #fff; border-radius: 5px;">
                    <h2 style="color: #fff; text-align: center;">Your Requested Files</h2>
                    <p>Hello {user_name},</p>
                    <p>Here are the files you requested:</p>
                    <ul>
                        {files_list}
                    </ul>
                    <p>Please download the files as they may expire after some time.</p>
                    <hr style="border: 1px solid #333; margin: 20px 0;">
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - AI Assistant for Dog Care & Beyond</p>
                </div>
            </body>
        </html>
        """ 