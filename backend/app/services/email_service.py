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
            admin_email = current_app.config.get('ADMIN_EMAIL', current_app.config['MAIL_USERNAME'])
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
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - Guide to All Paws</p>
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
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - Guide to All Paws</p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _get_contact_notification_template(contact: Contact) -> str:
        """Get HTML template for contact form notification"""
        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Contact Form Submission</title>
            </head>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; background-color: #f9f9f9; margin: 0; padding: 0;">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; margin-top: 20px;">
                    <tr>
                        <td style="padding: 20px; background-color: #000000;">
                            <h2 style="color: #ffffff; margin: 0; padding: 0; text-align: center;">Mr. White - New Contact Message</h2>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding-bottom: 20px; border-bottom: 1px solid #eeeeee;">
                                        <p style="margin: 0; padding: 0;"><strong>Subject:</strong> {contact.subject or 'Contact Form Inquiry'}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 20px 0;">
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td width="120" style="padding-bottom: 10px;"><strong>Name:</strong></td>
                                                <td style="padding-bottom: 10px;">{contact.name}</td>
                                            </tr>
                                            <tr>
                                                <td width="120" style="padding-bottom: 10px;"><strong>Email:</strong></td>
                                                <td style="padding-bottom: 10px;"><a href="mailto:{contact.email}" style="color: #0066cc; text-decoration: none;">{contact.email}</a></td>
                                            </tr>
                                            <tr>
                                                <td width="120" style="padding-bottom: 10px;"><strong>Phone:</strong></td>
                                                <td style="padding-bottom: 10px;">{contact.phone or 'Not provided'}</td>
                                            </tr>
                                            <tr>
                                                <td width="120" style="padding-bottom: 10px;"><strong>User ID:</strong></td>
                                                <td style="padding-bottom: 10px;">{contact.user_id or 'Not logged in'}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 20px 0; border-top: 1px solid #eeeeee;">
                                        <p style="margin: 0 0 10px 0; padding: 0;"><strong>Message:</strong></p>
                                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-top: 5px;">
                                            <p style="margin: 0; padding: 0; white-space: pre-wrap;">{contact.message}</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px; background-color: #f5f5f5; text-align: center; font-size: 12px; color: #666666;">
                            <p style="margin: 0; padding: 0;">This is an automated message from Mr. White - Guide to All Paws.</p>
                            <p style="margin: 5px 0 0 0; padding: 0;">Please respond to the sender directly at <a href="mailto:{contact.email}" style="color: #0066cc; text-decoration: none;">{contact.email}</a>.</p>
                        </td>
                    </tr>
                </table>
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
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - Guide to All Paws</p>
                </div>
            </body>
        </html>
        """ 