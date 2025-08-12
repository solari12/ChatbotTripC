import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from ..models.schemas import UserInfoRequest
import logging
import os

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for booking workflow"""
    
    def __init__(self):
        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.booking_email = os.getenv("BOOKING_EMAIL", "booking@tripc.ai")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@tripc.ai")
        
        # Check if SMTP is configured
        self.smtp_configured = bool(self.smtp_username and self.smtp_password)
    
    async def send_booking_inquiry(self, user_info: UserInfoRequest) -> bool:
        """Send booking inquiry email to booking@tripc.ai"""
        try:
            if not self.smtp_configured:
                logger.warning("SMTP not configured, skipping email send")
                return False
            
            # Create email content
            subject = f"Đặt chỗ mới - {user_info.name}"
            if user_info.language.value == "en":
                subject = f"New Booking Request - {user_info.name}"
            
            # Create email body
            body = self._create_booking_email_body(user_info)
            
            # Send email
            success = await self._send_email(
                to_email=self.booking_email,
                subject=subject,
                body=body
            )
            
            if success:
                logger.info(f"Booking inquiry email sent successfully for {user_info.name}")
            else:
                logger.error(f"Failed to send booking inquiry email for {user_info.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending booking inquiry email: {e}")
            return False
    
    async def send_confirmation_email(self, user_info: UserInfoRequest) -> bool:
        """Send confirmation email to user"""
        try:
            if not self.smtp_configured:
                logger.warning("SMTP not configured, skipping confirmation email")
                return False
            
            # Create confirmation email content
            subject = "Xác nhận đặt chỗ - TripC"
            if user_info.language.value == "en":
                subject = "Booking Confirmation - TripC"
            
            body = self._create_confirmation_email_body(user_info)
            
            # Send confirmation email
            success = await self._send_email(
                to_email=user_info.email,
                subject=subject,
                body=body
            )
            
            if success:
                logger.info(f"Confirmation email sent successfully to {user_info.email}")
            else:
                logger.error(f"Failed to send confirmation email to {user_info.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending confirmation email: {e}")
            return False
    
    def _create_booking_email_body(self, user_info: UserInfoRequest) -> str:
        """Create booking inquiry email body"""
        language = user_info.language.value
        
        if language == "vi":
            body = f"""
            <html>
            <body>
                <h2>Yêu cầu đặt chỗ mới</h2>
                <p><strong>Tên khách hàng:</strong> {user_info.name}</p>
                <p><strong>Email:</strong> {user_info.email}</p>
                <p><strong>Số điện thoại:</strong> {user_info.phone}</p>
                <p><strong>Nội dung yêu cầu:</strong></p>
                <p>{user_info.message}</p>
                <p><strong>Platform:</strong> {user_info.platform.value}</p>
                <p><strong>Device:</strong> {user_info.device.value}</p>
                <p><strong>Ngôn ngữ:</strong> {user_info.language.value}</p>
                <hr>
                <p><em>Email này được gửi tự động từ TripC.AI Chatbot</em></p>
            </body>
            </html>
            """
        else:
            body = f"""
            <html>
            <body>
                <h2>New Booking Request</h2>
                <p><strong>Customer Name:</strong> {user_info.name}</p>
                <p><strong>Email:</strong> {user_info.email}</p>
                <p><strong>Phone:</strong> {user_info.phone}</p>
                <p><strong>Request Details:</strong></p>
                <p>{user_info.message}</p>
                <p><strong>Platform:</strong> {user_info.platform.value}</p>
                <p><strong>Device:</strong> {user_info.device.value}</p>
                <p><strong>Language:</strong> {user_info.language.value}</p>
                <hr>
                <p><em>This email was sent automatically from TripC.AI Chatbot</em></p>
            </body>
            </html>
            """
        
        return body
    
    def _create_confirmation_email_body(self, user_info: UserInfoRequest) -> str:
        """Create confirmation email body"""
        language = user_info.language.value
        
        if language == "vi":
            body = f"""
            <html>
            <body>
                <h2>Xác nhận yêu cầu đặt chỗ</h2>
                <p>Xin chào {user_info.name},</p>
                <p>Cảm ơn bạn đã gửi yêu cầu đặt chỗ qua TripC.AI Chatbot.</p>
                <p><strong>Chi tiết yêu cầu:</strong></p>
                <p>{user_info.message}</p>
                <p>Đội ngũ của chúng tôi sẽ liên hệ với bạn trong thời gian sớm nhất để xác nhận và hoàn tất việc đặt chỗ.</p>
                <p>Nếu bạn có bất kỳ câu hỏi nào, vui lòng liên hệ với chúng tôi qua email: {self.booking_email}</p>
                <br>
                <p>Trân trọng,</p>
                <p>Đội ngũ TripC</p>
                <hr>
                <p><em>Email này được gửi tự động từ TripC.AI Chatbot</em></p>
            </body>
            </html>
            """
        else:
            body = f"""
            <html>
            <body>
                <h2>Booking Request Confirmation</h2>
                <p>Hello {user_info.name},</p>
                <p>Thank you for submitting your booking request through TripC.AI Chatbot.</p>
                <p><strong>Request Details:</strong></p>
                <p>{user_info.message}</p>
                <p>Our team will contact you as soon as possible to confirm and complete your booking.</p>
                <p>If you have any questions, please contact us at: {self.booking_email}</p>
                <br>
                <p>Best regards,</p>
                <p>TripC Team</p>
                <hr>
                <p><em>This email was sent automatically from TripC.AI Chatbot</em></p>
            </body>
            </html>
            """
        
        return body
    
    async def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(self.from_email, to_email, text)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def is_smtp_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        return self.smtp_configured
    
    def get_booking_email(self) -> str:
        """Get booking email address"""
        return self.booking_email