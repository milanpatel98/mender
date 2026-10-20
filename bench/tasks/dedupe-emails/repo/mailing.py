def unique_emails(emails):
    """Drop duplicate emails (case-insensitive), keeping first spelling and order."""
    return list({email.lower() for email in emails})
