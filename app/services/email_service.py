import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger("rayhana.email")


def print_dev_verification_code(*, email: str, code: str) -> None:
    print(f"RAYHANA VERIFICATION CODE for {email}: {code}")


def print_dev_password_reset_code(*, email: str, code: str) -> None:
    print(f"RAYHANA PASSWORD RESET CODE for {email}: {code}")


def smtp_is_configured() -> bool:
    return all(
        [
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
            settings.SMTP_FROM_EMAIL,
        ]
    )


def missing_smtp_fields() -> list[str]:
    fields = {
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
        "SMTP_USERNAME": settings.SMTP_USERNAME,
        "SMTP_PASSWORD": settings.SMTP_PASSWORD,
        "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
    }

    return [name for name, value in fields.items() if not value]


def smtp_port() -> int:
    try:
        return int(settings.SMTP_PORT or 587)
    except ValueError:
        return 587


def is_development() -> bool:
    return settings.ENVIRONMENT.lower() == "development"


async def send_verification_email(
    *,
    to_email: str,
    full_name: str,
    code: str,
) -> bool:
    if not smtp_is_configured():
        if is_development():
            print_dev_verification_code(email=to_email, code=code)
        return False

    subject = "Verify your Rayhana account"
    body = f"""Hello {full_name},

Welcome to Rayhana

Your email verification code is:

{code}

This code expires in 15 minutes.

If you did not create a Rayhana account, you can safely ignore this email.

Rayhana Team
Smart Basil Care
"""

    await send_email(to_email=to_email, subject=subject, body=body)
    return True


async def send_password_reset_email(
    *,
    to_email: str,
    full_name: str,
    code: str,
) -> bool:
    if not smtp_is_configured():
        if is_development():
            print_dev_password_reset_code(email=to_email, code=code)
        return False

    subject = "Reset your Rayhana password"
    body = f"""Hello {full_name},

We received a request to reset your Rayhana password.

Your reset code is:

{code}

This code expires in 15 minutes.

If you did not request this, you can safely ignore this email.

Rayhana Team
Smart Basil Care
"""

    await send_email(to_email=to_email, subject=subject, body=body)
    return True


async def send_test_email(*, to_email: str) -> bool:
    subject = "Rayhana test email"
    body = """Hello,

This is a test email from Rayhana.

Your SMTP configuration is working correctly.

Rayhana Team
Smart Basil Care
"""

    if not smtp_is_configured():
        return False

    await send_email(to_email=to_email, subject=subject, body=body)
    return True


async def send_email(*, to_email: str, subject: str, body: str) -> None:
    try:
        await asyncio.to_thread(
            _send_email_sync,
            to_email=to_email,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        log_smtp_error(exc)
        raise


def log_smtp_error(exc: Exception) -> None:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        error_type = "SMTPAuthenticationError"
    elif isinstance(exc, smtplib.SMTPConnectError):
        error_type = "SMTPConnectError"
    elif isinstance(exc, TimeoutError):
        error_type = "TimeoutError"
    else:
        error_type = type(exc).__name__

    print(f"[Rayhana SMTP ERROR] {error_type}: {exc}")
    logger.exception("SMTP email sending failed: %s", exc)


def _send_email_sync(*, to_email: str, subject: str, body: str) -> None:
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = formataddr(
        (settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL)
    )
    message["To"] = to_email

    port = smtp_port()
    smtp_client = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP

    with smtp_client(settings.SMTP_HOST, port, timeout=15) as smtp:
        smtp.ehlo()
        if port != 465:
            # Gmail SMTP uses smtp.gmail.com:587 with STARTTLS.
            smtp.starttls()
            smtp.ehlo()
        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
