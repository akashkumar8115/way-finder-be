import base64
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv  
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from src.services.otp_generation.otp_service import otp_service
from sqlalchemy.ext.asyncio import AsyncSession



load_dotenv()


def welcome_email(to_email):
    from_email = os.getenv('FROM_EMAIL')

    # # Create the verification link with query parameters
    # verification_link = f"http://localhost:3000/login/verify-account?email={to_email}&verification_token={verification_token}"

    # Prepare the email message
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject='Welcome to xPi',
       html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to xPi</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0; /* Light grey border */
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
        .email-header {{
            text-align: center;
            background-color: #f97316; /* Orange-600 */
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
        }}
        .email-content {{
            padding: 20px;
        }}
        .button {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #4F47E4; /* Purple-Blue background */
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 5px;
            text-align: center;
            font-weight: bold; /* Optional for better readability */
            border: none; /* Ensure no borders override the design */
        }}
        .button:hover,
        .button:focus,
        .button:active,
        .button:visited {{
            color: #ffffff; /* Keep text white on hover, focus, active, and visited states */
            text-decoration: none; /* Remove underline on hover/focus */
            outline: none; /* Remove focus outline */
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>Welcome to xPi!</h1>
        </div>
        <div class="email-content">
            <h2 style="color: #2c3e50;">Welcome Aboard!</h2>
            <p>Dear <strong>User</strong>,</p>
            <p>We're excited to have you join xPi! At xPi, we help you share your ideas and reach a wider audience effortlessly. Your journey with us starts now, and we're here to assist every step of the way.</p>
            <p>We’re thrilled to have you on board and look forward to helping you grow and succeed.</p>
            <p><strong>Welcome to the xPi family!</strong></p>
            <p>Best regards,<br>
            The xPi Team</p>
        </div>
    </div>
</body>
</html>
"""


    )

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)

    except Exception as e:
        print(str(e))




async def send_email_verification_otp(to_email: str, db: AsyncSession):
    """Send an email with OTP for verification"""
    from_email = os.getenv('FROM_EMAIL')
    
    # # Generate OTP for this email
    # otp = otp_service.generate_otp(to_email)

    # Generate OTP for this email
    otp = await otp_service.generate_otp(to_email, 'email', db)
    
    # Prepare the email message
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject='Verify Your Email for Digital Sigange Registration',
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Verification - xPi</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
        .email-header {{
            text-align: center;
            background-color: #f97316;
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
        }}
        .email-content {{
            padding: 20px;
        }}
        .otp-container {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f0f0f0;
            border-radius: 5px;
            text-align: center;
            font-size: 24px;
            letter-spacing: 5px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>Email Verification</h1>
        </div>
        <div class="email-content">
            <h2 style="color: #2c3e50;">Verify Your Email</h2>
            <p>Dear User,</p>
            <p>Thank you for registering with Digital Signage. To Verify your email, please use the following verification code:</p>
            
            <div class="otp-container">
                {otp}
            </div>
            
            <p>This code will expire in 15 minutes.</p>
            <p>If you did not request this verification, please ignore this email.</p>
            <p>Best regards,<br>
            The xPi Team</p>
        </div>
    </div>
</body>
</html>
"""
    )

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        # print(response.status_code)
        # print(response.body)
        # print(response.headers)
        
        return {
            "status": "success",
            "message": "Verification email sent successfully"
        }
    
    except Exception as e:
        print(str(e))
        return {
            "status": "error",
            "message": f"Failed to send verification email: {str(e)}"
        }




def send_password_reset_email(to_email: str, reset_token: str):
    """Send an email with password reset link"""
    from_email = os.getenv('FROM_EMAIL')
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Create the reset password link
    reset_link = f"{frontend_url}/reset_password?token={reset_token}"
    
    # Prepare the email message
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject='Reset Your Password - Digital Signage',
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset - xPi</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
        .email-header {{
            text-align: center;
            background-color: #f97316;
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
        }}
        .email-content {{
            padding: 20px;
        }}
        .button {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #4F47E4;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 5px;
            text-align: center;
            font-weight: bold;
            border: none;
        }}
        .button:hover,
        .button:focus,
        .button:active,
        .button:visited {{
            color: #ffffff;
            text-decoration: none;
            outline: none;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>Password Reset</h1>
        </div>
        <div class="email-content">
            <h2 style="color: #2c3e50;">Reset Your Password</h2>
            <p>Dear User,</p>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" class="button">Reset Password</a>
            </p>
            
            <p>This link will expire in 24 hours.</p>
            <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
            <p>Best regards,<br>
            The xPi Team</p>
        </div>
    </div>
</body>
</html>
"""
    )

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        return {
            "status": "success",
            "message": "Password reset email sent successfully"
        }
    
    except Exception as e:
        print(str(e))
        return {
            "status": "error",
            "message": f"Failed to send password reset email: {str(e)}"
        }


