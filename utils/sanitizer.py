def sanitize_link(raw_link: str) -> str:
    """
    Strips query parameters from an X URL.
    Example: https://x.com/user/status/123?s=20 -> https://x.com/user/status/123
    """
    if not raw_link:
        return ""
    
    link = raw_link.split("?")[0].strip()
    
    if link.endswith('/'):
        link = link[:-1]
        

    
    return link
