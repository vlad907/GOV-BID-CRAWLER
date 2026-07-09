"""Send outreach and pull replies through a Gmail account using the standard
SMTP/IMAP protocols + an app password (see README for setup). No Google
Cloud project or OAuth needed.

Nothing here sends on its own - a send only happens when a router endpoint
is invoked by an explicit user action in the app.
"""
import email
import imaplib
import re
import smtplib
from datetime import datetime
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr, parsedate_to_datetime

from ..config import settings


class EmailNotConfigured(RuntimeError):
    pass


class EmailError(RuntimeError):
    pass


def _require_config() -> None:
    if not settings.smtp_user or not settings.smtp_password:
        raise EmailNotConfigured(
            "Email isn't configured. Set SMTP_USER (your Gmail) and SMTP_PASSWORD "
            "(a Gmail app password) in backend/.env - see the README."
        )


def send_email(to_addr: str, subject: str, body: str) -> str:
    """Sends one plain-text email; returns the Message-ID we stamped on it so
    replies can be correlated later."""
    _require_config()

    message_id = make_msgid(domain=settings.smtp_user.split("@")[-1])
    msg = EmailMessage()
    from_display = (
        f"{settings.email_from_name} <{settings.smtp_user}>"
        if settings.email_from_name
        else settings.smtp_user
    )
    msg["From"] = from_display
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = message_id
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailError(
            "Gmail rejected the login. Make sure 2-step verification is on and "
            "SMTP_PASSWORD is a 16-char app password (not your normal password)."
        ) from exc
    except OSError as exc:
        raise EmailError(f"Could not reach the mail server: {exc}") from exc

    return message_id


# --- reply parsing -------------------------------------------------------

PRICE_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)")
LEAD_TIME_RE = re.compile(
    r"(\d{1,3})\s*(?:-|to)?\s*(\d{1,3})?\s*(day|week|business day|wk)s?",
    re.I,
)


def extract_quote(body: str) -> tuple[float | None, str | None]:
    """Best-effort pull of a unit price and lead time from a supplier reply.
    Deliberately conservative - a human still reviews the actual email."""
    price = None
    price_match = PRICE_RE.search(body or "")
    if price_match:
        try:
            price = float(price_match.group(1).replace(",", ""))
        except ValueError:
            price = None

    lead_time = None
    lead_match = LEAD_TIME_RE.search(body or "")
    if lead_match:
        lead_time = lead_match.group(0).strip()

    return price, lead_time


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _plain_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", "replace") if payload else ""


def fetch_replies(known_message_ids: set[str]) -> list[dict]:
    """Reads the inbox and returns messages whose In-Reply-To/References point
    at one of our sent Message-IDs. Each dict is ready to persist as a reply.
    """
    _require_config()

    try:
        conn = imaplib.IMAP4_SSL(settings.imap_host, timeout=30)
        conn.login(settings.smtp_user, settings.smtp_password)
    except imaplib.IMAP4.error as exc:
        raise EmailError(
            "Gmail IMAP login failed. Confirm the app password and that IMAP is "
            "enabled in Gmail settings."
        ) from exc
    except OSError as exc:
        raise EmailError(f"Could not reach IMAP server: {exc}") from exc

    replies: list[dict] = []
    try:
        conn.select("INBOX")
        # Only scan a recent window to keep it fast.
        typ, data = conn.search(None, "ALL")
        ids = data[0].split()[-200:] if data and data[0] else []
        for num in reversed(ids):
            typ, msg_data = conn.fetch(num, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])

            refs = f"{msg.get('In-Reply-To', '')} {msg.get('References', '')}"
            matched = next((mid for mid in known_message_ids if mid and mid in refs), None)
            if not matched:
                continue

            received = None
            if msg.get("Date"):
                try:
                    received = parsedate_to_datetime(msg["Date"])
                except (TypeError, ValueError):
                    received = None

            replies.append(
                {
                    "in_reply_to": matched,
                    "from_addr": parseaddr(_decode(msg.get("From")))[1],
                    "subject": _decode(msg.get("Subject")),
                    "body": _plain_body(msg),
                    "imap_message_id": _decode(msg.get("Message-ID")),
                    "received_at": received or datetime.utcnow(),
                }
            )
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    return replies
