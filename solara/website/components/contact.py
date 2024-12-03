import json
import os
import requests

from typing import Any, Dict, Optional
import solara


postmark_api_key = None
contact_email_address = None

try:
    postmark_api_key = os.environ["POSTMARK_API_KEY"]
    contact_email_address = os.environ["SOLARA_CONTACT_EMAIL_ADDRESS"]
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
    success = solara.use_reactive(False)

    def send(*_ignore):
        if postmark_api_key is None or contact_email_address is None:
            error.set("Email service not properly configured. Please contact the site administrator at solara@widgetti.io.")
        elif not first_name.value or not last_name.value or not email.value or not message.value:
            error.set("Please fill out all required fields.")
        else:
            # Create the email content
            msg = {}
            msg["From"] = contact_email_address
            msg["To"] = contact_email_address
            msg["Subject"] = email_subject
            msg["ReplyTo"] = email.value

            # Email body
            msg["HtmlBody"] = f"""
            <b>First Name</b>: {first_name.value}<br />
            <b>Last Name</b>: {last_name.value}<br />
            <b>Email</b>: {email.value}<br />
            <b>Company</b>: {company.value}<br />
            <b>Message</b>: {message.value}<br />
            """

            # Send emails
            try:
                requests.post(
                    "https://api.postmarkapp.com/email",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-Postmark-Server-Token": postmark_api_key,
                    },
                    data=json.dumps(msg),
                )
                requests.post(
                    "https://api.postmarkapp.com/email",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-Postmark-Server-Token": postmark_api_key,
                    },
                    data=json.dumps(
                        {
                            "From": contact_email_address,
                            "To": email.value,
                            "Subject": "Thank you for contacting Solara",
                            "HtmlBody": f"""
                            <p>Hi {first_name.value},</p>
                            <p>Thank you for contacting us! We will get back to you as soon as possible.</p>
                            <p>Best regards,<br />The Solara Team</p>
                            """,
                        }
                    ),
                )
            except Exception as e:
                error.set(f"Error sending email: {e}")
            else:
                success.set(True)
                error.set(None)
                first_name.set("")
                last_name.set("")
                email.set("")
                company.set("")
                message.set("")

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

    solara.Style(
        """
        .v-snack__wrapper {
            box-shadow: none;
        }
        """
    )

    with solara.v.Snackbar(
        v_model=error.value is not None,
        timeout=5000,
        on_v_model=lambda *_: error.set(None),
        left=True,
        color="error",
    ):
        solara.Markdown(error.value or "", style={"--dark-color-text": "white", "--color-text": "white"})
        solara.Button(icon=True, icon_name="mdi-close", color="white", on_click=lambda: error.set(None))

    with solara.v.Snackbar(
        v_model=success.value,
        timeout=5000,
        on_v_model=lambda *_: success.set(False),
        left=True,
        color="success",
    ):
        solara.Markdown("Your message has been sent!", style={"--dark-color-text": "white", "--color-text": "white"})
        solara.Button(icon=True, icon_name="mdi-close", color="white", on_click=lambda: success.set(False))
