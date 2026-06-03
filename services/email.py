import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import settings

# Import raw string assets cleanly
from services.email_templates import BASE_EMAIL_LAYOUT


class EmailService:
    @staticmethod
    def _get_global_context() -> dict:
        """Centralized identity settings used across the header/footer shells."""
        return {
            "app_name": getattr(settings, "APP_NAME", "ETK AI"),
            "company_name": getattr(settings, "COMPANY_NAME", "ETK AI Dashboard"),
            "primary_color": "#3b82f6",
            "current_year": str(datetime.now(timezone.utc).year),
        }

    @classmethod
    def compile_dynamic_email(cls, body_template: str, custom_context: dict) -> str:
        """
        Combines global headers and footers with local child bodies dynamically
        using standard fast string replacement mapping attributes.
        """
        # Gather global configurations and custom local context fields
        globals_dict = cls._get_global_context()
        merged_context = {**globals_dict, **custom_context}

        # Render variables inside the specific child body segment
        compiled_body = body_template
        for key, value in merged_context.items():
            compiled_body = compiled_body.replace(f"{{{key}}}", str(value))

        # Replace the {email_body_content} placeholder in the master layout with the fully rendered child body
        final_markup = BASE_EMAIL_LAYOUT.replace("{email_body_content}", compiled_body)

        # Fill remaining variables inside the shell layout (title, brand markers, etc.)
        for key, value in merged_context.items():
            final_markup = final_markup.replace(f"{{{key}}}", str(value))

        return final_markup

    @classmethod
    async def send_templated_email(
        cls, to_email: str, subject: str, body_template: str, context: dict
    ) -> bool:
        """Compiles templates using dynamic replacement matrices and dispatches cleanly via SMTP."""

        html_content = cls.compile_dynamic_email(body_template, context)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_USER
        msg["To"] = to_email

        fallback = context.get("fallback_text", "Security Notification Update")
        msg.attach(MIMEText(fallback, "plain"))

        msg.attach(MIMEText(html_content, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())
            server.quit()
            print(f"✅ Email sent to {to_email}")

            return True
        except Exception as smtp_error:
            print(f"❌ Mail dispatcher engine execution failure: {str(smtp_error)}")
            return False
