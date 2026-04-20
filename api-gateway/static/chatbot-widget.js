(function() {
    const existingContainer = document.getElementById("book-ai-widget-container");
    if (existingContainer) {
        const existingFab = document.getElementById("book-ai-fab");
        const existingWin = document.getElementById("book-ai-window");
        if (existingFab && existingWin && !existingWin.classList.contains("book-ai-open")) {
            // Ensure FAB is visible again after page transitions/reloads.
            existingFab.style.display = "flex";
        }
        return;
    }

    // Proxy qua api-gateway cùng origin — tránh hoàn toàn CORS
    const hostUrl = window.BookAI_HostUrl || "";   // "" = same origin (localhost:8000)
    const apiUrl  = `${hostUrl}/ai/chat/`;
    
    // Dùng static cùng origin để tránh phụ thuộc recommender-ai-service.
    const staticBase = window.BookAI_StaticUrl || "";
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${staticBase}/static/chatbot-widget.css?v=20260406`;
    document.head.appendChild(link);

    // Chèn bộ xương HTML (Widget Skeleton)
    const container = document.createElement("div");
    container.id = "book-ai-widget-container";
    container.innerHTML = `
        <!-- Cửa sổ Chat -->
        <div class="book-ai-window" id="book-ai-window">
            <div class="book-ai-header">
                <div class="book-ai-header-title">
                    <i></i> Mochi Tư Vấn 💖
                </div>
                <button class="book-ai-close" id="book-ai-close-btn">&times;</button>
            </div>
            
            <div class="book-ai-body" id="book-ai-body">
                <!-- Tin nhắn mặc định chào hỏi -->
                <div class="book-ai-msg book-ai-msg-ai">
                    <p>Chào bạn nè! Mình là Mochi, trợ lý tư vấn siêu cấp đáng yêu của tiệm sách nè. 🌸 Bạn đang tìm sách gì để đọc cho "chill" hay để học tập đó? Cứ nói mình biết nha! ✨</p>
                </div>
                
                <!-- Typing Indicator -->
                <div class="book-ai-typing" id="book-ai-typing">
                    <div class="book-ai-dot"></div>
                    <div class="book-ai-dot"></div>
                    <div class="book-ai-dot"></div>
                </div>
            </div>
            
            <div class="book-ai-footer">
                <input type="text" class="book-ai-input" id="book-ai-input" placeholder="Nhắn gì đó với Mochi nha..." autocomplete="off">
                <button class="book-ai-send" id="book-ai-send-btn">
                    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
                </button>
            </div>
        </div>

        <!-- Nút Trợ lý (FAB) -->
        <div class="book-ai-fab" id="book-ai-fab">
            <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"></path></svg>
        </div>
    `;
    document.body.appendChild(container);

    // Behavioral Tracking Logic (Session based)
    const trackLocalBehavior = () => {
        const path = window.location.pathname;
        const match = path.match(/\/books\/(\d+)\//);
        if (match) {
            const bookId = match[1];
            let behaviors = JSON.parse(sessionStorage.getItem("mochi_recent_behaviors") || "[]");
            // Only add if not already the last one
            if (behaviors[behaviors.length - 1] !== `view_book_${bookId}`) {
                behaviors.push(`view_book_${bookId}`);
                sessionStorage.setItem("mochi_recent_behaviors", JSON.stringify(behaviors.slice(-5)));
            }
        }
    };
    trackLocalBehavior();

    const getRecentBehaviors = () => {
        return JSON.parse(sessionStorage.getItem("mochi_recent_behaviors") || "[]");
    };

    // 3. Logic Tương tác (Interactivity)
    const fab = document.getElementById("book-ai-fab");
    const win = document.getElementById("book-ai-window");
    const closeBtn = document.getElementById("book-ai-close-btn");
    const sendBtn = document.getElementById("book-ai-send-btn");
    const input = document.getElementById("book-ai-input");
    const body = document.getElementById("book-ai-body");
    const typing = document.getElementById("book-ai-typing");

    // Default Fake Profile Configuration
    const getUserProfile = () => {
        return window.BookAI_Profile || { age: 25, gender: "male", location_id: 1 };
    };
    const getUserId = () => {
        const profile = getUserProfile();
        return String((profile && profile.user_id) || "anonymous");
    };
    const storageKey = () => `book_ai_chat_history:${getUserId()}`;
    const MAX_MESSAGES = 24;

    const loadHistory = () => {
        try {
            const raw = localStorage.getItem(storageKey());
            const parsed = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(parsed)) return [];
            return parsed.slice(-MAX_MESSAGES);
        } catch (_e) { return []; }
    };

    const saveHistory = (history) => {
        try {
            localStorage.setItem(storageKey(), JSON.stringify(history.slice(-MAX_MESSAGES)));
        } catch (_e) {}
    };

    fab.addEventListener("click", () => {
        win.classList.add("book-ai-open");
        fab.style.display = "none";
        input.focus();
    });

    closeBtn.addEventListener("click", () => {
        win.classList.remove("book-ai-open");
        setTimeout(() => { fab.style.display = "flex"; }, 300);
    });

    const scrollToBottom = () => { body.scrollTop = body.scrollHeight; };

    const addMessage = (text, isUser = false) => {
        const msgDiv = document.createElement("div");
        msgDiv.className = `book-ai-msg ${isUser ? 'book-ai-msg-user' : 'book-ai-msg-ai'}`;
        
        // Simple Markdown
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
            
        msgDiv.innerHTML = `<p>${formatted}</p>`;
        body.insertBefore(msgDiv, typing);
        scrollToBottom();
    };

    let chatHistory = loadHistory();
    if (chatHistory.length > 0) {
        chatHistory.forEach(([role, content]) => addMessage(content, role === "user"));
    }

    const handleSend = async () => {
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, true);
        chatHistory.push(["user", text]);
        saveHistory(chatHistory);
        input.value = "";
        
        typing.classList.add("book-ai-show");
        scrollToBottom();

        try {
            const resp = await fetch(apiUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    user_id: getUserId(),
                    history: chatHistory,
                    recent_behaviors: getRecentBehaviors()
                })
            });

            typing.classList.remove("book-ai-show");

            if (!resp.ok) {
                addMessage("Hic, Mochi gặp chút lỗi kết nối mạng rồi... 😿 Thử lại tí nha!", false);
                return;
            }

            const data = await resp.json();
            if(data.answer) {
                addMessage(data.answer, false);
                chatHistory.push(["assistant", data.answer]);
                saveHistory(chatHistory);
            }
        } catch (error) {
            typing.classList.remove("book-ai-show");
            addMessage("Mochi không thức dậy được để trả lời bạn... 😿", false);
        }
    };

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keypress", (e) => { if (e.key === "Enter") handleSend(); });

})();

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSend();
    });

})();
