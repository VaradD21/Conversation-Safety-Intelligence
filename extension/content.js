// Cyber Safety Content Script
// Scans text on the page transparently and requests analysis

let scanQueue = [];
let scanNodes = [];
let scanTimer = null;
const BATCH_SIZE = 20;

// Find all text-heavy elements
function collectTextNodes() {
    const selector = 'p, h1, h2, h3, span, div.comment, blockquote';
    const elements = document.querySelectorAll(selector);
    
    elements.forEach(el => {
        // Skip already scanned or hidden elements
        if (el.dataset.safetyScanned || el.innerText.trim().length < 10 || window.getComputedStyle(el).display === 'none') {
            return;
        }
        
        // Mark as scanned to prevent infinite loops
        el.dataset.safetyScanned = "true";
        
        // Push to queue
        scanQueue.push(el.innerText.trim());
        scanNodes.push(el);
    });
    
    if (scanQueue.length > 0) {
        scheduleScan();
    }
}

function scheduleScan() {
    if (scanTimer) clearTimeout(scanTimer);
    
    // Debounce: Wait 1.5 seconds after DOM mutations settle
    scanTimer = setTimeout(() => {
        processQueue();
    }, 1500);
}

function processQueue() {
    if (scanQueue.length === 0) return;
    
    // Take a batch
    const batchText = scanQueue.slice(0, BATCH_SIZE);
    const batchNodes = scanNodes.slice(0, BATCH_SIZE);
    
    scanQueue = scanQueue.slice(BATCH_SIZE);
    scanNodes = scanNodes.slice(BATCH_SIZE);
    
    chrome.runtime.sendMessage({
        type: "ANALYZE_DOM",
        payload: batchText
    }, response => {
        if (response && response.success) {
            applyProtections(batchNodes, response.data);
        }
        
        // If more in queue, process next batch immediately
        if (scanQueue.length > 0) {
            processQueue();
        }
    });
}

function applyProtections(nodes, results) {
    // results is an array of objects: { is_hazardous: bool, reason: string }
    for (let i = 0; i < nodes.length; i++) {
        if (i >= results.length) break;
        
        const node = nodes[i];
        const res = results[i];
        
        if (res.is_hazardous) {
            // Apply blur
            node.classList.add('safety-blurred');
            
            // Create Warning Overlay
            const overlay = document.createElement('div');
            overlay.className = 'safety-warning-overlay';
            overlay.innerHTML = `
                <span>⚠️ Potential harmful content hidden.</span>
                <button class="safety-show-btn">Show anyway</button>
            `;
            
            // Add click listener to show
            overlay.querySelector('.safety-show-btn').addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                node.classList.remove('safety-blurred');
                overlay.remove();
            });
            
            // Append overlay right before the node or as a child if block level
            if (node.parentNode) {
                 node.parentNode.insertBefore(overlay, node);
            }
        }
    }
}

// Observe infinite scrolling / dynamic loading
const observer = new MutationObserver((mutations) => {
    let shouldScan = false;
    for (let m of mutations) {
        if (m.addedNodes.length > 0) {
            shouldScan = true;
            break;
        }
    }
    if (shouldScan) {
        collectTextNodes();
    }
});

observer.observe(document.body, { childList: true, subtree: true });

// Initial scan
setTimeout(collectTextNodes, 1000);
