(function() {
    const existingContainer = document.getElementById("ecommerce-ai-widget-container");
    if (existingContainer) {
        const existingFab = document.getElementById("ecommerce-ai-fab");
        const existingWin = document.getElementById("ecommerce-ai-window");
        if (existingFab && existingWin && !existingWin.classList.contains("ecommerce-ai-open")) {
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
    link.href = `${staticBase}/static/chatbot-widget.css?v=20260408`;
    document.head.appendChild(link);

    // Chèn bộ xương HTML (Widget Skeleton)
    const container = document.createElement("div");
    container.id = "ecommerce-ai-widget-container";
    container.innerHTML = `
        <!-- Cửa sổ Chat -->
        <div class="ecommerce-ai-window" id="ecommerce-ai-window">
            <div class="ecommerce-ai-header">
                <div class="ecommerce-ai-header-title">
                    <i></i> Mochi Tư Vấn 💖
                </div>
                <button class="ecommerce-ai-close" id="ecommerce-ai-close-btn">&times;</button>
            </div>
            
            <div class="ecommerce-ai-body" id="ecommerce-ai-body">
                <!-- Tin nhắn mặc định chào hỏi -->
                <div class="ecommerce-ai-msg ecommerce-ai-msg-ai">
                    <p>Chào bạn nè! Mình là Mochi, trợ lý tư vấn siêu cấp đáng yêu của E-Commerce nè. 🌸 Bạn đang tìm sản phẩm gì đó? Cứ nói mình biết nha! ✨</p>
                </div>
                
                <!-- Typing Indicator -->
                <div class="ecommerce-ai-typing" id="ecommerce-ai-typing">
                    <div class="ecommerce-ai-dot"></div>
                    <div class="ecommerce-ai-dot"></div>
                    <div class="ecommerce-ai-dot"></div>
                </div>
            </div>
            
            <div class="ecommerce-ai-footer">
                <input type="text" class="ecommerce-ai-input" id="ecommerce-ai-input" placeholder="Nhắn gì đó với Mochi nha..." autocomplete="off">
                <button class="ecommerce-ai-send" id="ecommerce-ai-send-btn">
                    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
                </button>
            </div>
        </div>

        <!-- Nút Trợ lý (FAB) -->
        <div class="ecommerce-ai-fab" id="ecommerce-ai-fab">
            <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"></path></svg>
        </div>
    `;
    document.body.appendChild(container);

    // Behavioral Tracking Logic (Session based)
    const trackLocalBehavior = () => {
        const path = window.location.pathname;
        const match = path.match(/\/products\/(\d+)\//);
        if (match) {
            const productId = match[1];
            let behaviors = JSON.parse(sessionStorage.getItem("mochi_recent_behaviors") || "[]");
            // Only add if not already the last one
            if (behaviors[behaviors.length - 1] !== `view_product_${productId}`) {
                behaviors.push(`view_product_${productId}`);
                sessionStorage.setItem("mochi_recent_behaviors", JSON.stringify(behaviors.slice(-5)));
            }
        }
    };
    trackLocalBehavior();

    const getRecentBehaviors = () => {
        return JSON.parse(sessionStorage.getItem("mochi_recent_behaviors") || "[]");
    };

    // 3. Logic Tương tác (Interactivity)
    const fab = document.getElementById("ecommerce-ai-fab");
    const win = document.getElementById("ecommerce-ai-window");
    const closeBtn = document.getElementById("ecommerce-ai-close-btn");
    const sendBtn = document.getElementById("ecommerce-ai-send-btn");
    const input = document.getElementById("ecommerce-ai-input");
    const body = document.getElementById("ecommerce-ai-body");
    const typing = document.getElementById("ecommerce-ai-typing");

    // Default Fake Profile Configuration
    const getUserProfile = () => {
        return window.BookAI_Profile || { age: 25, gender: "male", location_id: 1 };
    };
    const getUserId = () => {
        const profile = getUserProfile();
        return String((profile && profile.user_id) || "anonymous");
    };
    const storageKey = () => `ecommerce_ai_chat_history:${getUserId()}`;
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
        win.classList.add("ecommerce-ai-open");
        fab.style.display = "none";
        input.focus();
    });

    closeBtn.addEventListener("click", () => {
        win.classList.remove("ecommerce-ai-open");
        setTimeout(() => { fab.style.display = "flex"; }, 300);
    });

    const scrollToBottom = () => { body.scrollTop = body.scrollHeight; };

    const addMessage = (text, isUser = false) => {
        const msgDiv = document.createElement("div");
        msgDiv.className = `ecommerce-ai-msg ${isUser ? 'ecommerce-ai-msg-user' : 'ecommerce-ai-msg-ai'}`;
        
        // Markdown nhẹ: link, bold, bullet, xuống dòng
        let formatted = text
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="ecommerce-ai-product-link">$1</a>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/^\s*[-*]\s+/gm, "• ")
            .replace(/\n/g, "<br>");
            
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
        
        typing.classList.add("ecommerce-ai-show");
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

            typing.classList.remove("ecommerce-ai-show");

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
            typing.classList.remove("ecommerce-ai-show");
            addMessage("Mochi không thức dậy được để trả lời bạn... 😿", false);
        }
    };

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keypress", (e) => { if (e.key === "Enter") handleSend(); });

})();
