document.getElementById('db-btn').addEventListener('click', () => {
    // Open the local backend dashboard
    chrome.tabs.create({ url: "http://localhost:8000/" });
});
