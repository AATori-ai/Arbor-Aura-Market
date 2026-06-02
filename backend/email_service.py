"""Email notification service for ArborAura Market.
Supports SMTP sending with a fallback log mode when not configured.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@arboraura.fi")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an HTML email. Returns True on success, False on failure.
    Falls back to logging when SMTP is not configured.
    """
    if not SMTP_HOST or not SMTP_USER:
        logger.info(f"[EMAIL FAKED] To: {to} | Subject: {subject}")
        return True  # Faked success in dev mode

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [to], msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")
        return False


def email_listing_approved(user_email: str, listing_title: str, listing_id: int) -> bool:
    """Notify user that their listing was approved."""
    url = f"{SITE_URL}/?listing={listing_id}"
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;padding:24px">
<h2 style="color:#2D6A4F;">✅ Ilmoituksesi on hyväksytty!</h2>
<p>Hei,</p>
<p>Ilmoituksesi <strong>"{listing_title}"</strong> on tarkastettu ja hyväksytty julkaistavaksi.</p>
<p>Voit nähdä sen täällä: <a href="{url}" style="color:#2D6A4F;">{url}</a></p>
<br><hr>
<p style="font-size:.85rem;color:#666;">Your listing has been approved! / Your listing <strong>"{listing_title}"</strong> has been reviewed and approved.</p>
</body></html>"""
    subject_fi = f"✅ Ilmoitus hyväksytty: {listing_title}"
    return send_email(user_email, subject_fi, html)


def email_listing_rejected(user_email: str, listing_title: str, reason: str = "") -> bool:
    """Notify user that their listing was rejected."""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;padding:24px">
<h2 style="color:#dc2626;">❌ Ilmoitustasi ei hyväksytty</h2>
<p>Hei,</p>
<p>Ilmoituksesi <strong>"{listing_title}"</strong> ei läpäissyt tarkastusta.</p>
{f'<p>Syy: {reason}</p>' if reason else '<p>Ole hyvä ja tarkista ilmoituksesi ja yritä uudelleen.</p>'}
<br><hr>
<p style="font-size:.85rem;color:#666;">Your listing was not approved. Please review your ad and try again.</p>
</body></html>"""
    subject_fi = f"❌ Ilmoitus hylätty: {listing_title}"
    return send_email(user_email, subject_fi, html)


def email_registration_welcome(user_email: str, user_name: str) -> bool:
    """Send welcome email upon registration."""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;padding:24px">
<h2 style="color:#2D6A4F;">🌿 Tervetuloa ArborAura Markettiin!</h2>
<p>Hei {user_name},</p>
<p>Tervetuloa! Olet nyt rekisteröitynyt ArborAura Market -palveluun.</p>
<p>Voit nyt <a href="{SITE_URL}" style="color:#2D6A4F;">selata ilmoituksia</a> ja jättää omia ilmoituksia.</p>
<ul>
<li>💰 Ilmoitusten jättäminen on maksutonta</li>
<li>🔒 Tietosi ovat turvassa GDPR:n mukaisesti</li>
<li>💬 Ole hyvä ja lue käyttöehtomme ja turvallisuusvinkit</li>
</ul>
<br><hr>
<p style="font-size:.85rem;color:#666;">Welcome to ArborAura Market! You can now browse and post listings.</p>
</body></html>"""
    return send_email(user_email, "🌿 Tervetuloa ArborAura Markettiin / Welcome!", html)


def email_contact_reply(user_email: str, subject: str, reply_body: str) -> bool:
    """Send a reply to a contact form submission."""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;padding:24px">
<h2 style="color:#2D6A4F;">📧 Vastaus viestiisi / Reply to your message</h2>
<p>{reply_body}</p>
<br><hr>
<p style="font-size:.85rem;color:#666;">ArborAura Market - Asiakaspalvelu / Customer Support</p>
</body></html>"""
    return send_email(user_email, f"Re: {subject}", html)
