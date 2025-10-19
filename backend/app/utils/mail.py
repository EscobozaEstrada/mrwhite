import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_email(to, subject, html_content):
    """
    Send an email using the configured SMTP server.
    
    Args:
        to (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to
        
        # Attach HTML content
        part = MIMEText(html_content, 'html')
        msg.attach(part)
        
        # Setup the server
        server = smtplib.SMTP(
            current_app.config['MAIL_SERVER'], 
            current_app.config['MAIL_PORT']
        )

        # print("Checkpoint 1")
        
        if current_app.config['MAIL_USE_TLS']:
            # print("Checkpoint 2")
            server.starttls()

        # print("Checkpoint 3")
            
        # Login if credentials are provided
        if current_app.config['MAIL_USERNAME'] and current_app.config['MAIL_PASSWORD']:
            # print("Checkpoint 4")
            server.login(
                current_app.config['MAIL_USERNAME'], 
                current_app.config['MAIL_PASSWORD']
            )

        # print("Checkpoint 5")
        # Send the email
        server.sendmail(
            current_app.config['MAIL_DEFAULT_SENDER'],
            to,
            msg.as_string()
        )

        # print("Checkpoint 6")
        # Close connection
        server.quit()

        # print("Checkpoint 7")
        return True
    except Exception as e:
        # print("Checkpoint 8")
        print(f"Error sending email: {e}")
        return False 