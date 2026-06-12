(function () {
    "use strict";

    function formatTime(iso) {
        if (!iso) return "";
        var d = new Date(iso);
        if (isNaN(d.getTime())) {
            var s = String(iso);
            if (s.length >= 16) return s.slice(11, 16);
            return s;
        }
        var hh = String(d.getHours()).padStart(2, "0");
        var mm = String(d.getMinutes()).padStart(2, "0");
        return hh + ":" + mm;
    }

    function formatDay(iso) {
        if (!iso) return "Hôm nay";
        var d = new Date(iso);
        if (isNaN(d.getTime())) return "Trao đổi";
        var today = new Date();
        var sameDay = d.toDateString() === today.toDateString();
        if (sameDay) return "Hôm nay";
        var dd = String(d.getDate()).padStart(2, "0");
        var mo = String(d.getMonth() + 1).padStart(2, "0");
        return dd + "/" + mo + "/" + d.getFullYear();
    }

    function escapeHtml(text) {
        return String(text || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function SupportChat(root) {
        this.root = root;
        this.apiUrl = root.dataset.apiUrl;
        this.csrfToken = root.dataset.csrfToken;
        this.viewerRole = root.dataset.viewerRole || "customer";
        this.customerLabel = root.dataset.customerLabel || "Khách hàng";
        this.messagesEl = root.querySelector("[data-chat-messages]");
        this.inputEl = root.querySelector("[data-chat-input]");
        this.sendBtn = root.querySelector("[data-chat-send]");
        this.composerEl = root.querySelector("[data-chat-composer]");
        this.liveEl = root.querySelector("[data-chat-live]");
        this.statusBadgeEl = root.querySelector("[data-chat-status-badge]");
        this.closedNoteEl = root.querySelector("[data-chat-closed-note]");
        this.lastHash = "";
        this.lastData = null;
        this.pending = false;
        this.pollTimer = null;
        var contentEl = document.getElementById("ticket-initial-content");
        var createdEl = document.getElementById("ticket-initial-created-at");
        this.initialContent = contentEl ? JSON.parse(contentEl.textContent || '""') : "";
        this.initialCreatedAt = createdEl ? JSON.parse(createdEl.textContent || '""') : "";
    }

    SupportChat.prototype.isMine = function (reply) {
        if (reply._optimistic) return true;
        if (this.viewerRole === "staff") return !!reply.is_staff;
        return !reply.is_staff;
    };

    SupportChat.prototype.senderLabel = function (reply) {
        if (reply._optimistic) {
            return this.viewerRole === "staff" ? "Bạn" : "Bạn";
        }
        if (reply.is_staff) return "Nhân viên hỗ trợ";
        return this.viewerRole === "staff" ? this.customerLabel : "Bạn";
    };

    SupportChat.prototype.buildRows = function (data) {
        var rows = [];
        if (this.initialContent) {
            rows.push({
                id: "__initial__",
                is_staff: false,
                message: this.initialContent,
                created_at: this.initialCreatedAt || data.created_at,
                _initial: true,
            });
        }
        (data.replies || []).forEach(function (r) {
            rows.push(r);
        });
        return rows;
    };

    SupportChat.prototype.render = function (data, forceScroll) {
        var self = this;
        var rows = this.buildRows(data);
        if (!rows.length) {
            this.messagesEl.innerHTML = '<div class="support-chat-empty">Chưa có tin nhắn. Hãy bắt đầu cuộc trò chuyện!</div>';
            return;
        }

        var html = "";
        var lastDay = "";
        rows.forEach(function (reply) {
            var day = formatDay(reply.created_at);
            if (day !== lastDay) {
                html += '<div class="support-chat-day-divider">' + escapeHtml(day) + "</div>";
                lastDay = day;
            }

            var mine = self.isMine(reply);
            var rowClass = reply._initial ? "is-mine" : (mine ? "is-mine" : "is-theirs");
            html += '<div class="support-chat-row ' + rowClass + '" data-reply-id="' + escapeHtml(reply.id) + '">';
            html += '<div style="max-width:100%;">';
            html += '<div class="support-chat-meta">';
            html += '<span class="support-chat-sender">' + escapeHtml(self.senderLabel(reply)) + "</span>";
            html += "<span>" + escapeHtml(formatTime(reply.created_at)) + "</span>";
            html += "</div>";
            html += '<div class="support-chat-bubble">' + escapeHtml(reply.message) + "</div>";
            html += "</div></div>";
        });

        var atBottom = this.messagesEl.scrollHeight - this.messagesEl.scrollTop - this.messagesEl.clientHeight < 48;
        this.messagesEl.innerHTML = html;
        if (forceScroll || atBottom) {
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        }

        if (this.statusBadgeEl && data.status_label) {
            this.statusBadgeEl.textContent = data.status_label;
            this.statusBadgeEl.className = "badge " + (data.status_badge || "badge-secondary");
        }
        document.querySelectorAll("[data-ticket-status-label]").forEach(function (el) {
            if (data.status_label) el.textContent = data.status_label;
        });
        document.querySelectorAll("[data-ticket-status-badge]").forEach(function (el) {
            if (data.status_badge) el.className = "badge " + data.status_badge;
        });

        var canReply = !!data.can_reply;
        if (this.composerEl) {
            this.composerEl.classList.toggle("is-disabled", !canReply);
        }
        if (this.inputEl) this.inputEl.disabled = !canReply;
        if (this.sendBtn) this.sendBtn.disabled = !canReply;
        if (this.closedNoteEl) {
            this.closedNoteEl.hidden = canReply;
        }
    };

    SupportChat.prototype.setLive = function (online) {
        if (!this.liveEl) return;
        this.liveEl.classList.toggle("is-offline", !online);
        this.liveEl.querySelector("[data-live-text]").textContent = online ? "Đang kết nối" : "Mất kết nối";
    };

    SupportChat.prototype.fetchMessages = function (forceScroll) {
        var self = this;
        return fetch(this.apiUrl, { credentials: "same-origin", cache: "no-store" })
            .then(function (res) {
                if (!res.ok) throw new Error("poll failed");
                return res.json();
            })
            .then(function (data) {
                self.setLive(true);
                var hash = JSON.stringify({
                    replies: data.replies || [],
                    status: data.status,
                    status_label: data.status_label,
                });
                if (hash !== self.lastHash) {
                    self.lastHash = hash;
                    self.lastData = data;
                    self.render(data, forceScroll);
                }
                return data;
            })
            .catch(function () {
                self.setLive(false);
            });
    };

    SupportChat.prototype.sendMessage = function () {
        var self = this;
        if (this.pending || !this.inputEl) return;
        var text = (this.inputEl.value || "").trim();
        if (!text) return;

        this.pending = true;
        if (this.sendBtn) this.sendBtn.disabled = true;

        var optimistic = {
            id: "tmp-" + Date.now(),
            is_staff: this.viewerRole === "staff",
            message: text,
            created_at: new Date().toISOString(),
            _optimistic: true,
        };

        var current = Object.assign(
            { replies: [], can_reply: true, created_at: this.initialCreatedAt },
            this.lastData || {}
        );
        current.replies = (current.replies || []).concat([optimistic]);
        this.render(current, true);
        this.inputEl.value = "";
        this.autoResize();

        fetch(this.apiUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this.csrfToken,
            },
            body: JSON.stringify({ message: text }),
        })
            .then(function (res) {
                return res.json().then(function (body) {
                    if (!res.ok) throw new Error(body.error || "send failed");
                    return body;
                });
            })
            .then(function (data) {
                self.lastHash = JSON.stringify({
                    replies: data.replies || [],
                    status: data.status,
                    status_label: data.status_label,
                });
                self.lastData = data;
                self.render(data, true);
            })
            .catch(function (err) {
                alert(err.message || "Không gửi được tin nhắn. Vui lòng thử lại.");
                self.fetchMessages(true);
            })
            .finally(function () {
                self.pending = false;
                if (self.sendBtn) self.sendBtn.disabled = false;
                if (self.inputEl) self.inputEl.focus();
            });
    };

    SupportChat.prototype.autoResize = function () {
        if (!this.inputEl) return;
        this.inputEl.style.height = "auto";
        this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 120) + "px";
    };

    SupportChat.prototype.startPolling = function () {
        var self = this;
        var tick = function () {
            if (!document.hidden) self.fetchMessages(false);
        };
        this.fetchMessages(true);
        this.pollTimer = setInterval(tick, 2000);
        document.addEventListener("visibilitychange", function () {
            if (!document.hidden) self.fetchMessages(false);
        });
    };

    SupportChat.prototype.bind = function () {
        var self = this;
        if (this.sendBtn) {
            this.sendBtn.addEventListener("click", function () {
                self.sendMessage();
            });
        }
        if (this.inputEl) {
            this.inputEl.addEventListener("input", function () {
                self.autoResize();
            });
            this.inputEl.addEventListener("keydown", function (e) {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    self.sendMessage();
                }
            });
        }
    };

    SupportChat.prototype.init = function () {
        this.bind();
        this.startPolling();
        if (this.inputEl) this.inputEl.focus();
    };

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-support-chat]").forEach(function (root) {
            new SupportChat(root).init();
        });
    });
})();
