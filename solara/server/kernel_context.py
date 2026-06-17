import logging

# ... (rest of the file remains the same)

if context.session_id != session_id:
    if session_id.startswith("session-id-cookie-unavailable:"):
        logger.warning("Session cookie was not available during websocket reconnection (possible cookie expiration or browser settings)")
    else:
        logger.critical("Session id mismatch when reusing kernel (hack attempt?): %s != %s", context.session_id, session_id)
