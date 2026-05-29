import logging
import uuid

# ... (rest of the file remains the same)

if not session_id:
    logger.warning("no session cookie")
    session_id = "session-id-cookie-unavailable:" + str(uuid4())