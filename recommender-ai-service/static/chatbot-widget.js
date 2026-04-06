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

    // 2. Chèn bộ xương HTML (Widget Skeleton)
    const container = document.createElement("div");
    container.id = "book-ai-widget-container";
    container.innerHTML = `
        <!-- Cửa sổ Chat -->
        <div class="book-ai-window" id="book-ai-window">
            <div class="book-ai-header">
                <div class="book-ai-header-title">
                    <i></i> Trợ lý Tư vấn AI
                </div>
                <button class="book-ai-close" id="book-ai-close-btn">&times;</button>
            </div>
            
            <div class="book-ai-body" id="book-ai-body">
                <!-- Tin nhắn mặc định chào hỏi -->
                <div class="book-ai-msg book-ai-msg-ai">
                    <p>Chào bạn! Mình là Trợ lý AI của cửa hàng. Mình có thể tư vấn các dịch vụ hoặc sách phù hợp với bạn dựa trên Deep Learning. Bạn có câu hỏi gì không?</p>
                </div>
                
                <!-- Typing Indicator -->
                <div class="book-ai-typing" id="book-ai-typing">
                    <div class="book-ai-dot"></div>
                    <div class="book-ai-dot"></div>
                    <div class="book-ai-dot"></div>
                </div>
            </div>
            
            <div class="book-ai-footer">
                <input type="text" class="book-ai-input" id="book-ai-input" placeholder="Hỏi gì đó..." autocomplete="off">
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

    // 3. Logic Tương tác (Interactivity)
    const fab = document.getElementById("book-ai-fab");
    const win = document.getElementById("book-ai-window");
    const closeBtn = document.getElementById("book-ai-close-btn");
    const sendBtn = document.getElementById("book-ai-send-btn");
    const input = document.getElementById("book-ai-input");
    const body = document.getElementById("book-ai-body");
    const typing = document.getElementById("book-ai-typing");

    // Default Fake Profile Configuration (nếu Frontend của bạn chưa truyền vào)
    // Tương lai: `window.BookAI_Profile = { userId: 1, age: 25, ... }`
    const getUserProfile = () => {
        return window.BookAI_Profile || { age: 25, gender: "male", location_id: 1 };
    };
    const getUserId = () => {
        const profile = getUserProfile();
        return String((profile && profile.user_id) || "anonymous");
    };
    const storageKey = () => `book_ai_chat_history:${getUserId()}`;
    const MAX_MESSAGES = 24; // 12 turns (user+assistant)

    const loadHistory = () => {
        try {
            const raw = localStorage.getItem(storageKey());
            const parsed = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(parsed)) return [];
            return parsed.filter(
                (m) =>
                    Array.isArray(m) &&
                    m.length === 2 &&
                    (m[0] === "user" || m[0] === "assistant") &&
                    typeof m[1] === "string" &&
                    m[1].trim()
            ).slice(-MAX_MESSAGES);
        } catch (_e) {
            return [];
        }
    };

    const saveHistory = (history) => {
        try {
            localStorage.setItem(storageKey(), JSON.stringify(history.slice(-MAX_MESSAGES)));
        } catch (_e) {
            // Ignore storage errors (private mode/quota)
        }
    };

    // Toggle Chat Window
    fab.addEventListener("click", () => {
        win.classList.add("book-ai-open");
        fab.style.display = "none";
        input.focus();
    });

    closeBtn.addEventListener("click", () => {
        win.classList.remove("book-ai-open");
        setTimeout(() => { fab.style.display = "flex"; }, 300);
    });

    const scrollToBottom = () => {
        body.scrollTop = body.scrollHeight;
    };

    const addMessage = (text, isUser = false) => {
        const msgDiv = document.createElement("div");
        msgDiv.className = `book-ai-msg ${isUser ? 'book-ai-msg-user' : 'book-ai-msg-ai'}`;
        
        // Simple Markdown Parser (Bold & Bullets)
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\s*-\s/g, '<br>• ');
            
        msgDiv.innerHTML = `<p>${formatted}</p>`;
        
        // Chèn tin nhắn mới NẰM TRÊN Indicator Typing
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

        // Add user msg
        addMessage(text, true);
        chatHistory.push(["user", text]);
        chatHistory = chatHistory.slice(-MAX_MESSAGES);
        saveHistory(chatHistory);
        input.value = "";
        
        // Show Typing
        typing.classList.add("book-ai-show");
        scrollToBottom();

        try {
            const resp = await fetch(apiUrl, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    query: text,
                    user_profile: getUserProfile(),
                    chat_history: chatHistory
                })
            });

            typing.classList.remove("book-ai-show");

            if (!resp.ok) {
                const errText = await resp.text();
                console.error("[BookAI] Server error:", resp.status, errText);
                addMessage(`Máy chủ phản hồi lỗi ${resp.status}. Chi tiết: ${errText.slice(0,200)}`, false);
                return;
            }

            const data = await resp.json();
            
            if(data.answer) {
                addMessage(data.answer, false);
                if (Array.isArray(data.chat_history)) {
                    chatHistory = data.chat_history.slice(-MAX_MESSAGES);
                } else {
                    chatHistory.push(["assistant", data.answer]);
                    chatHistory = chatHistory.slice(-MAX_MESSAGES);
                }
                saveHistory(chatHistory);
            } else if (data.error) {
                addMessage(`⚠️ Lỗi AI: ${data.error}`, false);
            } else {
                addMessage("Oops! Đã có lỗi khi trả về câu trả lời.", false);
            }
        } catch (error) {
            console.error("[BookAI] Fetch failed:", error);
            typing.classList.remove("book-ai-show");
            addMessage(`⚠️ Không thể kết nối AI (${error.message}). Hãy kiểm tra recommender-ai-service đang chạy tại ${hostUrl}`, false);
        }
    };

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSend();
    });

})();
