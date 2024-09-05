import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from typing import Any, Dict, Optional
import solara


# Set up email server details
smtp_server = "smtp.gmail.com"
smtp_port = 465  # For SSL
email_user = None
email_password = None
try:
    email_user = os.environ.get("CONTACT_EMAIL_USER")
    email_password = os.environ.get("CONTACT_EMAIL_PASSWORD")
except Exception:
    pass


@solara.component
def Contact(
    style: Dict[str, Any] = {},
    title="Contact Us",
    subtitle="We'd love to hear from you!",
    submit_label="Submit",
    email_subject="Contact Form Submission",
):
    first_name = solara.use_reactive("")
    last_name = solara.use_reactive("")
    email = solara.use_reactive("")
    company = solara.use_reactive("")
    message = solara.use_reactive("")
    error: solara.Reactive[Optional[str]] = solara.use_reactive(None)

    def send(*_ignore):
        if email_user is None or email_password is None:
            error.set("Email server details not set. Please set environment variables.")
        else:
            # Create the email content
            msg = MIMEMultipart()
            msg["From"] = email_user
            msg["To"] = "contact@solara.dev"
            msg["Subject"] = email_subject

            # Email body
            body = f"""
            First Name: {first_name.value}
            Last Name: {last_name.value}
            Email: {email.value}
            Company: {company.value}
            Message: {message.value}
            """
            msg.attach(MIMEText(body, "plain"))

            # Send the email
            try:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                server.login(email_user, email_password)
                server.sendmail(email_user, msg["To"], msg.as_string())
                server.quit()
                print("Email sent successfully!")
            except Exception as e:
                error.set(f"Error sending email: {e}")

    with solara.Card(title=title, style={"width": "100%", "max-width": "1024px", **style}):
        solara.Markdown(subtitle)
        solara.Text("* Required fields")
        with solara.Row():
            solara.InputText(label="First Name *", value=first_name)
            solara.InputText(label="Last Name *", value=last_name)
        with solara.Row():
            solara.InputText(label="Email *", value=email)
            solara.InputText(label="Company", value=company)
        solara.v.Textarea(placeholder="Message *", v_model=message.value, on_v_model=message.set)
        with solara.CardActions():
            solara.Button(label=submit_label, color="primary", on_click=send)
            solara.Button(
                label="Clear",
                color="secondary",
                text=True,
                on_click=lambda: [first_name.set(""), last_name.set(""), email.set(""), company.set(""), message.set("")],
            )

    def close_snackbar(*_ignore):
        error.set(None)

    solara.Style(
        """
        .v-snack__wrapper {
            box-shadow: none;
        }
        """
    )

    with solara.v.Snackbar(
        v_model=error.value is not None,
        timeout=50000,
        on_v_model=close_snackbar,
        left=True,
        color="transparent",
    ):
        with solara.Error(error.value):
            solara.Button(icon=True, icon_name="mdi-close", color="white", on_click=close_snackbar)
