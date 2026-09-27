def sanitize_link(raw_link: str) -> str:
    """
    Strips query parameters from a Twitter/X URL and normalizes the domain.
    Example: https://twitter.com/user/status/123?s=20 -> https://x.com/user/status/123
    """
    if not raw_link:
        return ""
    
    link = raw_link.split("?")[0].strip()
    
    if link.endswith('/'):
        link = link[:-1]
        
    link = link.replace("https://twitter.com/", "https://x.com/")
    link = link.replace("https://www.twitter.com/", "https://x.com/")
    link = link.replace("http://twitter.com/", "https://x.com/")
    link = link.replace("http://www.twitter.com/", "https://x.com/")
    
    return link
