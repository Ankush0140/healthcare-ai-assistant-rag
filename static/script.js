document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatContainer = document.getElementById('chatContainer');
    const uploadBox = document.getElementById('uploadBox');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const docsList = document.getElementById('docsList');
    const newChatBtn = document.getElementById('newChatBtn');

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        // Enable/disable send button
        if (this.value.trim().length > 0) {
            sendBtn.removeAttribute('disabled');
        } else {
            sendBtn.setAttribute('disabled', 'true');
        }
    });

    // Handle Enter key (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim().length > 0) {
                sendMessage();
            }
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    newChatBtn.addEventListener('click', () => {
        chatContainer.innerHTML = `
            <div class="message assistant">
                <div class="avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="message-content">
                    <p>New chat started. How can I assist you today?</p>
                </div>
            </div>
        `;
    });

    // File Upload Logic
    uploadBox.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.type !== 'application/pdf') {
            showUploadStatus('Only PDF files are supported.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showUploadStatus('Uploading and analyzing document...', 'loading');

        try {
            const response = await fetch('/ingest', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                showUploadStatus(`Successfully processed ${data.chunks_stored} chunks.`, 'success');
                addDocumentToList(file.name);
            } else {
                showUploadStatus(`Error: ${data.detail}`, 'error');
            }
        } catch (error) {
            showUploadStatus(`Upload failed: ${error.message}`, 'error');
        } finally {
            fileInput.value = ''; // Reset
        }
    });

    function showUploadStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = `upload-status ${type}`;
        
        if (type !== 'loading') {
            setTimeout(() => {
                uploadStatus.textContent = '';
                uploadStatus.className = 'upload-status';
            }, 5000);
        }
    }

    function addDocumentToList(filename) {
        const docHtml = `
            <div class="doc-item">
                <i class="fa-solid fa-file-pdf"></i>
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${filename}</span>
            </div>
        `;
        docsList.insertAdjacentHTML('beforeend', docHtml);
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Reset input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendBtn.setAttribute('disabled', 'true');

        // Add user message
        appendMessage('user', text);

        // Add loading indicator
        const loadingId = appendLoading();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            });

            const data = await response.json();
            
            // Remove loading
            document.getElementById(loadingId).remove();

            if (response.ok) {
                appendAssistantMessage(data);
            } else {
                appendMessage('assistant', `Error: ${data.detail || 'Failed to get a response.'}`);
            }
        } catch (error) {
            document.getElementById(loadingId).remove();
            appendMessage('assistant', `Connection error: ${error.message}`);
        }
    }

    function appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        
        const avatarHtml = role === 'user' 
            ? '<i class="fa-solid fa-user"></i>' 
            : '<i class="fa-solid fa-robot"></i>';

        // Parse markdown if it's the assistant
        const contentHtml = role === 'assistant' ? marked.parse(text) : `<p>${text}</p>`;

        div.innerHTML = `
            <div class="avatar">${avatarHtml}</div>
            <div class="message-content">
                ${contentHtml}
            </div>
        `;
        
        chatContainer.appendChild(div);
        scrollToBottom();
    }

    function appendLoading() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.className = `message assistant`;
        div.id = id;
        
        div.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        chatContainer.appendChild(div);
        scrollToBottom();
        return id;
    }

    function appendAssistantMessage(data) {
        const div = document.createElement('div');
        div.className = `message assistant`;
        
        // Parse the main answer markdown
        let html = marked.parse(data.answer);

        // Add Confidence Badge
        if (data.intent === 'rag_qa' && data.confidence !== undefined) {
            const confClass = data.confidence > 0.5 ? 'confidence-high' : 'confidence-low';
            const icon = data.confidence > 0.5 ? 'fa-check-circle' : 'fa-exclamation-triangle';
            html = `
                <div class="confidence-badge ${confClass}">
                    <i class="fa-solid ${icon}"></i> Confidence: ${(data.confidence * 100).toFixed(0)}%
                </div>
            ` + html;
        }

        // Add Reservation Slot styling if applicable
        if (data.intent === 'reservation' && data.available_slots.length > 0) {
            html += `<div style="margin-top:15px; display:flex; gap:10px; flex-wrap:wrap;">`;
            data.available_slots.forEach(slot => {
                html += `<button style="background:var(--accent-bg); color:var(--accent-color); border:1px solid var(--accent-color); padding:8px 15px; border-radius:8px; cursor:pointer;">${slot}</button>`;
            });
            html += `</div>`;
        }

        // Add Sources
        if (data.sources && data.sources.length > 0) {
            let sourcesHtml = '<div class="sources-container"><div class="sources-title">Sources</div>';
            
            // Deduplicate sources by filename and page
            const uniqueSources = [];
            const seen = new Set();
            data.sources.forEach(s => {
                const key = `${s.source}-p${s.page}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    uniqueSources.push(s);
                }
            });

            uniqueSources.forEach(s => {
                sourcesHtml += `
                    <div class="source-badge" title="${s.preview.replace(/"/g, '&quot;')}">
                        <i class="fa-solid fa-file-pdf"></i>
                        ${s.source} (Page ${s.page})
                    </div>
                `;
            });
            sourcesHtml += '</div>';
            html += sourcesHtml;
        }

        div.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content">
                ${html}
            </div>
        `;
        
        chatContainer.appendChild(div);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
});
