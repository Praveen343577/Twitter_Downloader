def sanitize_link(raw_link: str) -> str:
    """
    Strips query parameters from a Twitter/X URL.
    Example: https://x.com/user/status/123?s=20&lang=en -> https://x.com/user/status/123
    Handles all common Twitter URL forms: twitter.com, x.com, t.co
    """
    if not raw_link:
        return ""
    return raw_link.split("?")[0].strip()
