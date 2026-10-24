(function extractBookmarks() {
    const links = new Set();
    let lastHeight = 0;
    let attempts = 0;
    const maxRetries = 5; 
    
    console.log("Extraction started. Keep tab focused...");

    const timer = setInterval(() => {
        document.querySelectorAll('a[href*="/status/"]').forEach(a => {
            const cleanUrl = a.href.split('/photo/')[0].split('/video/')[0].split('?')[0];
            links.add(cleanUrl);
        });
        
        window.scrollTo(0, document.body.scrollHeight);
        
        if (document.body.scrollHeight === lastHeight) {
            attempts++;
            if (attempts >= maxRetries) { 
                clearInterval(timer);
                console.clear();
                const result = [...links];
                console.log(result.join('\n'));
                console.log(`\nExtraction terminated. Total unique status links: ${result.length}`);
            }
        } else {
            attempts = 0;
        }
        lastHeight = document.body.scrollHeight;
    }, 1500);
})();