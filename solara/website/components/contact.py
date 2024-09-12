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

    def send(*_ignore):
        if postmark_api_key is None or contact_email_address is None:
            error.set("Email service not properly configured. Please contact the site administrator at solara@widgetti.io.")
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

            # Send the email
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
