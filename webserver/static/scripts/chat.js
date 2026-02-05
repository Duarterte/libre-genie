document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    let CLIENT_ID = localStorage.getItem("client_id");
    let SECRET = localStorage.getItem("client_secret");
    
    // Inject message specific styles since style.css handles layout but maybe not bubbles
    const style = document.createElement('style');
    style.textContent = `
        .chat-message {
            margin: 5px 10px;
            padding: 8px 12px;
            border-radius: 12px;
            max-width: 80%;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
        }
        .chat-message.user {
            align-self: flex-end;
            background-color: bisque; /* Matching button color from style.css */
            color: #333;
            margin-left: auto;
            border-bottom-right-radius: 2px;
        }
        .chat-message.assistant {
            align-self: flex-start;
            background-color: rgba(255, 255, 255, 0.8);
            color: #333;
            margin-right: auto;
            border-bottom-left-radius: 2px;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Loading Indicator */
        .typing-indicator {
            display: flex;
            align-items: center;
            column-gap: 4px;
            padding: 10px 15px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 12px;
            border-bottom-left-radius: 2px;
            width: fit-content;
            margin: 5px 10px;
            margin-right: auto;
        }
        .dot {
            width: 6px;
            height: 6px;
            background: #555;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    `;
    document.head.appendChild(style);

    const chatBox = document.getElementById('chat-box'); // This is .chat-view
    const statusDiv = document.getElementById('status');
    const inputField = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    
    let isWaitingForResponse = false;

    function showLoading() {
        if (isWaitingForResponse) return;
        isWaitingForResponse = true;
        const div = document.createElement('div');
        div.className = 'typing-indicator';
        div.id = 'loading-indicator';
        div.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function removeLoading() {
        const loader = document.getElementById('loading-indicator');
        if (loader) {
            loader.remove();
        }
        isWaitingForResponse = false;
    }

    // Registration
    async function ensureRegistration() {
        if (!CLIENT_ID) {
            // Polyfill for insecure contexts (HTTP)
            if (typeof crypto.randomUUID !== 'function') {
                CLIENT_ID = "browser_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
                SECRET = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
            } else {
                CLIENT_ID = "browser_" + crypto.randomUUID();
                SECRET = crypto.randomUUID();
            }

            localStorage.setItem("client_id", CLIENT_ID);
            localStorage.setItem("client_secret", SECRET);
            
            try {
                await fetch('/api/register_device', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({client_id: CLIENT_ID, secret: SECRET})
                });
            } catch (err) {
                console.error("Registration skipped:", err);
            }
        }
    }

    // Helper to manage status text/visibility with optional auto-hide
    function setStatus(text = "", visible = true, autoHideMs = 0) {
        if (!statusDiv) return;
        // clear any pending hide timer
        if (statusDiv._hideTimer) {
            clearTimeout(statusDiv._hideTimer);
            delete statusDiv._hideTimer;
        }
        statusDiv.innerText = text;
        statusDiv.style.display = visible ? "block" : "none";
        if (autoHideMs > 0 && visible) {
            statusDiv._hideTimer = setTimeout(() => {
                statusDiv.style.display = "none";
                statusDiv.innerText = "";
                delete statusDiv._hideTimer;
            }, autoHideMs);
        }
    }

    // WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let ws;
    let reconnectInterval = 2000;

    function connectWS() {
        // Avoid duplicate connects
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

        console.log("Connecting to WS:", wsUrl);
        // We do not show "Connecting..." status on UI to avoid flicker/annoyance

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("WS Connected.");
            // Hide any stuck status
            setStatus("", false);
            reconnectInterval = 2000;
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'chat_response') {
                    removeLoading();
                    appendMessage('assistant', data.content);
                }
            } catch (e) {
                // If text only
                console.log("WS Message (raw):", event.data);
            }
        };

        ws.onclose = (e) => {
            console.log("WS Closed:", e.code, e.reason);
            // Don't clear status here; let the timer or existing alert persist
            setTimeout(connectWS, reconnectInterval);
            reconnectInterval = Math.min(reconnectInterval * 1.5, 30000);
        };

        ws.onerror = (err) => {
            console.error("WS Error:", err);
            // Let onclose handle reconnection timing
        };
    }

    function appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = `chat-message ${role}`;
        div.innerHTML = marked.parse(text);
        chatBox.appendChild(div);
        // Scroll to bottom
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function renderHistory(history) {
        history.forEach(msg => {
            appendMessage(msg.role, msg.content);
        });
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function loadHistory() {
        await ensureRegistration();
        try {
            const url = `/api/chat/history?client_id=${CLIENT_ID}&secret=${SECRET}`;
            const response = await fetch(url);
            
            if (response.status === 403) {
                console.warn("Client invalid (DB reset?), re-registering...");
                localStorage.removeItem("client_id");
                localStorage.removeItem("client_secret");
                CLIENT_ID = null;
                SECRET = null;
                await ensureRegistration();
                // Retry history fetch once
                const retryUrl = `/api/chat/history?client_id=${CLIENT_ID}&secret=${SECRET}`;
                const retryResp = await fetch(retryUrl);
                if (!retryResp.ok) return;
                const retryData = await retryResp.json();
                renderHistory(retryData);
                return;
            }

            if (response.ok) {
                const history = await response.json();
                renderHistory(history);
            }
        } catch (e) {
            console.error("History load error:", e);
        }
    }

    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;
        
        await ensureRegistration();

        appendMessage('user', text);
        inputField.value = '';
        showLoading();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: text,
                    client_id: CLIENT_ID,
                    secret: SECRET
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                removeLoading();
                appendMessage('assistant', `Error: ${response.status} ${response.statusText}`);
            } else if (data.response) {
                // FALLBACK: If WS hasn't handled it yet (loader still present)
                if (isWaitingForResponse) {
                     removeLoading();
                     appendMessage('assistant', data.response);
                }
            }
        } catch (e) {
            removeLoading();
            console.error(e);
            appendMessage('assistant', 'Failed to send message.');
        }
    }

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    // Start
    loadHistory();
    connectWS();
});
