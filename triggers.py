# triggers.py

BANNED_WORDS = ["spam", "hate", "abuse", "offensive", "toxic", "fake", "shit", "fuck"]

def validate_content_trigger(content):
    """
    Simulates a BEFORE_INSERT trigger for content moderation.
    Checks if the content contains any banned words.
    """
    if not content:
        return True, ""
    
    content_lower = content.lower()
    for word in BANNED_WORDS:
        if word in content_lower:
            return False, f"Content moderation: The word '{word}' is not allowed."
            
    # Example of another check: Character limit
    if len(content) > 500:
        return False, "Content moderation: Content exceeds the 500-character limit."
        
    return True, ""
