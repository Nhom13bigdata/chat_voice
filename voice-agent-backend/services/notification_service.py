import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Mock notification service for SMS and email"""

    def __init__(self):
        # Mock notification history
        self.notification_history = []

    async def send_email(
        self, to: str, subject: str, body: str, cc: Optional[List[str]] = None
    ) -> Dict:
        await asyncio.sleep(0.1)

        notification_id = f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.notification_history.append(
            {
                "id": notification_id,
                "type": "email",
                "to": to,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
            }
        )

        logger.info(f"Email sent to {to}: {subject}")

        return {
            "status": "sent",
            "notification_id": notification_id,
            "type": "email",
            "to": to,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
        }

    async def send_sms(self, to: str, message: str) -> Dict:
        await asyncio.sleep(0.1)

        notification_id = f"SMS-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.notification_history.append(
            {
                "id": notification_id,
                "type": "sms",
                "to": to,
                "message": message[:50],
                "sent_at": datetime.now().isoformat(),
            }
        )

        logger.info(f"SMS sent to {to}: {message[:30]}...")

        return {
            "status": "sent",
            "notification_id": notification_id,
            "type": "sms",
            "to": to,
            "sent_at": datetime.now().isoformat(),
        }

    async def send_appointment_confirmation(
        self, patient_email: str, patient_phone: str, appointment_details: Dict
    ) -> Dict:
        await asyncio.sleep(0.2)

        date = appointment_details.get("date", "TBD")
        time = appointment_details.get("time", "TBD")
        provider = appointment_details.get("provider", "Dr. Smith")

        email_subject = "Appointment Confirmation"
        email_body = f"""
Dear Patient,

Your appointment has been confirmed:

Date: {date}
Time: {time}
Provider: {provider}

Please arrive 15 minutes early to complete any remaining paperwork.

If you need to reschedule, please call us at 555-0100.

Best regards,
Medical Intake System
"""

        email_result = await self.send_email(
            to=patient_email, subject=email_subject, body=email_body
        )

        sms_message = f"Appointment confirmed: {date} at {time} with {provider}. Call 555-0100 to reschedule."
        sms_result = await self.send_sms(to=patient_phone, message=sms_message)

        logger.info(
            f"Appointment confirmation sent to {patient_email} and {patient_phone}"
        )

        return {
            "status": "sent",
            "email": email_result,
            "sms": sms_result,
            "sent_at": datetime.now().isoformat(),
        }

    async def send_intake_completion(
        self, patient_email: str, patient_phone: str, intake_summary: Dict
    ) -> Dict:
        await asyncio.sleep(0.2)

        email_subject = "Medical Intake Completed"
        email_body = f"""
Dear Patient,

Thank you for completing your medical intake form.

Your information has been received and will be reviewed by your provider before your appointment.

Summary:
- Chief Complaint: {intake_summary.get('chief_complaint', 'N/A')}
- Medications: {len(intake_summary.get('medications', []))} listed
- Allergies: {len(intake_summary.get('allergies', []))} listed

You will receive an appointment confirmation shortly.

Best regards,
Medical Intake System
"""

        email_result = await self.send_email(
            to=patient_email, subject=email_subject, body=email_body
        )

        sms_message = "Medical intake completed. You will receive appointment details soon. Thank you!"
        sms_result = await self.send_sms(to=patient_phone, message=sms_message)

        logger.info(f"Intake completion notification sent to {patient_email}")

        return {
            "status": "sent",
            "email": email_result,
            "sms": sms_result,
            "sent_at": datetime.now().isoformat(),
        }

    async def send_reminder(
        self, patient_phone: str, reminder_type: str, details: str
    ) -> Dict:
        await asyncio.sleep(0.1)

        message = f"Reminder: {reminder_type.upper()} - {details}"

        result = await self.send_sms(to=patient_phone, message=message)

        logger.info(f"Reminder sent: {reminder_type}")

        return result

    def get_notification_history(self, limit: int = 10) -> List[Dict]:
        return self.notification_history[-limit:]


# Singleton instance
notification_service = NotificationService()
