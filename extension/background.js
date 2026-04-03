// Cyber Safety Background Worker

const API_URL = "http://localhost:8000";

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "ANALYZE_DOM") {
        analyzeTextBatch(request.payload)
            .then(data => sendResponse({ success: true, data: data }))
            .catch(err => sendResponse({ success: false, error: err.toString() }));
        
        return true; // Keep message channel open for async response
    }
});

async function analyzeTextBatch(textNodes) {
    // textNodes is an array of strings
    try {
        const response = await fetch(`${API_URL}/analyze_dom`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ texts: textNodes })
        });
        
        if (!response.ok) {
            throw new Error(`API returned status ${response.status}`);
        }
        
        const result = await response.json();
        return result.results; // Array of booleans/flags matching the input array
    } catch (e) {
        console.error("DOM Analysis Error:", e);
        throw e;
    }
}
