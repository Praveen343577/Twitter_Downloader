(function extractTwitterBookmarks() {
    let links = new Set();
    let currentScroll = window.scrollY;
    let retries = 0;

    const SCROLL_STEP = 750; 
    const INTERVAL_MS = 1500; 
    const MAX_RETRIES = 6;


    let scroller = setInterval(() => {
        document.querySelectorAll('a[href*="/status/"]').forEach(el => {
            const cleanUrl = el.href.split('/photo/')[0].split('/video/')[0].split('/analytics')[0].split('?')[0];
            links.add(cleanUrl);
        });

        currentScroll += SCROLL_STEP;
        
        if (currentScroll > document.body.scrollHeight) {
            currentScroll = document.body.scrollHeight;
        }

        window.scrollTo(0, currentScroll);

        if (currentScroll >= document.body.scrollHeight) {
            retries++;
            if (retries > MAX_RETRIES) {
                clearInterval(scroller);
                const result = Array.from(links);
                console.log(result.join('\n'));
                console.log(`\nExtraction complete. Found ${links.size} unique links.`);
            }
        } else {
            retries = 0;
        }
    }, INTERVAL_MS);
})();