document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let currentRecipientId = null;
    let currentRecipientUsername = null;
    let typingTimeout = null;
    let selectedImage = null;
    let replyToMessageData = null;
    const currentUserId = parseInt(document.body.getAttribute('data-user-id'), 10);

    const notificationSound = new Audio('/static/sounds/notification.mp3');
    let soundEnabled = localStorage.getItem('soundEnabled') === 'false' ? false : true; // Default to true

    function playSound() {
        if (soundEnabled) {
            notificationSound.currentTime = 0; // Rewind to start if already playing
            notificationSound.play().catch(e => console.error("Error playing sound:", e));
        }
    }

    const userItems = document.querySelectorAll('.user-item');
    const chatWindow = document.getElementById('chat-window');
    const noChatSelected = document.getElementById('no-chat-selected');
    const chatWithName = document.getElementById('chat-with-name');
    const chatAvatar = document.getElementById('chat-avatar');
    const messageArea = document.getElementById('message-area');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const imageUpload = document.getElementById('image-upload');
    const imagePreviewArea = document.getElementById('image-preview-area');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image');
    const typingIndicator = document.querySelector('.typing-indicator');
    const replyPreview = document.getElementById('reply-preview');
    const replySender = document.getElementById('reply-sender');
    const replyContent = document.getElementById('reply-content');
    const sidebar = document.getElementById('sidebar');

    function updateUserStatus(userId, isOnline) {
        const userItem = document.querySelector('.user-item[data-user-id="' + userId + '"]');
        if (userItem) {
            const statusDot = userItem.querySelector('.status-dot');
            if (statusDot) {
                statusDot.className = 'status-dot position-absolute bottom-0 end-0 rounded-circle border border-white ' + (isOnline ? 'bg-success' : 'bg-secondary');
            }
            const statusText = userItem.querySelector('.status-text');
            if (statusText) {
                statusText.textContent = isOnline ? 'Online' : 'Offline';
                statusText.className = 'status-text small ' + (isOnline ? 'text-success fw-bold' : 'text-muted');
            }
        }
    }

    socket.on('online_users_list', function(data) {
        if (data.user_ids) {
            data.user_ids.forEach(function(userId) {
                updateUserStatus(userId, true);
            });
        }
    });

    socket.on('user_online', function(data) {
        updateUserStatus(data.user_id, true);
    });

    socket.on('user_offline', function(data) {
        updateUserStatus(data.user_id, false);
    });

    userItems.forEach(function(item) {
        item.addEventListener('click', function() {
            const userId = item.getAttribute('data-user-id');
            const username = item.getAttribute('data-username');
            const avatarSrc = item.querySelector('img').src;

            currentRecipientId = userId;
            currentRecipientUsername = username;
            chatWithName.textContent = username;
            chatAvatar.src = avatarSrc;
            chatWindow.classList.remove('d-none');
            noChatSelected.classList.add('d-none');

            if (sidebar) sidebar.classList.remove('show');

            userItems.forEach(function(u) { u.classList.remove('active'); });
            item.classList.add('active');

            fetch('/messages/' + userId)
                .then(function(response) { return response.json(); })
                .then(function(messages) {
                    messageArea.innerHTML = '';
                    messages.forEach(function(msg) { appendMessage(msg, false); });
                    scrollToBottom();
                    observeNewMessages(); // Observe newly loaded messages
                });
            messageInput.focus();
        });
    });

    messageInput.addEventListener('input', function() {
        if (!currentRecipientId) return;
        socket.emit('typing', { recipient_id: currentRecipientId });
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(function() {
            socket.emit('stop_typing', { recipient_id: currentRecipientId });
        }, 1000);
    });

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const content = messageInput.value.trim();

        if (!currentRecipientId) return;

        if (selectedImage) {
            const formData = new FormData();
            formData.append('file', selectedImage);
            fetch('/upload', { method: 'POST', body: formData })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.url) {
                        sendMessage(content, 'image', data.url);
                        clearImagePreview();
                        messageInput.value = '';
                    }
                });
        } else if (content) {
            sendMessage(content, 'text', null);
            messageInput.value = '';
        }
        messageInput.focus();
    });

    function sendMessage(content, type, imageUrl) {
        const data = {
            recipient_id: currentRecipientId,
            content: content,
            message_type: type
        };
        if (imageUrl) data.image_url = imageUrl;
        if (replyToMessageData) {
            data.reply_to_id = replyToMessageData.id;
            cancelReply();
        }
        socket.emit('private_message', data);
        playSound(); // Play sound after sending message
    }

    imageUpload.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            selectedImage = file;
            imagePreview.src = URL.createObjectURL(file);
            imagePreviewArea.classList.remove('d-none');
        }
    });

    removeImageBtn.addEventListener('click', clearImagePreview);

    function clearImagePreview() {
        selectedImage = null;
        imageUpload.value = '';
        imagePreviewArea.classList.add('d-none');
    }

    function cancelReply() {
        replyToMessageData = null;
        replyPreview.classList.add('d-none');
    }

    window.cancelReply = cancelReply;

    function toggleSound() {
        soundEnabled = !soundEnabled;
        localStorage.setItem('soundEnabled', soundEnabled);
        const soundToggleBtn = document.getElementById('sound-toggle-btn');
        if (soundToggleBtn) {
            updateSoundToggleButton(soundToggleBtn);
        }
    }
    window.toggleSound = toggleSound; // Expose to global scope for HTML event listener

    function updateSoundToggleButton(buttonElement) {
        if (soundEnabled) {
            buttonElement.innerHTML = '<i class="fas fa-volume-up"></i> Sound ON';
            buttonElement.classList.remove('btn-outline-secondary');
            buttonElement.classList.add('btn-secondary');
        } else {
            buttonElement.innerHTML = '<i class="fas fa-volume-mute"></i> Sound OFF';
            buttonElement.classList.remove('btn-secondary');
            buttonElement.classList.add('btn-outline-secondary');
        }
    }



    socket.on('new_message', function(data) {
        if (currentRecipientId) {
            const isFromCurrentRecipient = data.sender_id == currentRecipientId;
            const isSentByMeToCurrentRecipient = data.sender_id == currentUserId && data.recipient_id == currentRecipientId;
            if (isFromCurrentRecipient || isSentByMeToCurrentRecipient) {
                appendMessage(data, true);
                scrollToBottom();
                if (isFromCurrentRecipient) showToast(data.sender_username + ' sent you a message');
            }
        }
    });

    socket.on('message_edited', function(data) {
        const msgEl = document.querySelector('[data-message-id="' + data.message_id + '"] .message-content');
        if (msgEl) {
            msgEl.innerHTML = escapeHtml(data.content) + ' <small class="text-muted">(edited)</small>';
        }
    });

    socket.on('message_deleted', function(data) {
        const msgEl = document.querySelector('[data-message-id="' + data.message_id + '"]');
        if (msgEl) {
            msgEl.innerHTML = '<em class="text-muted">This message was deleted</em>';
            msgEl.classList.add('opacity-50');
        }
    });

    socket.on('user_typing', function(data) {
        if (data.user_id == currentRecipientId) {
            typingIndicator.classList.remove('d-none');
        }
    });

    socket.on('user_stop_typing', function(data) {
        if (data.user_id == currentRecipientId) {
            typingIndicator.classList.add('d-none');
        }
    });

    socket.on('profile_pic_updated', function(data) {
        const userId = data.user_id;
        const newPicUrl = data.profile_pic_url;

        // Update profile pic in the user list sidebar
        const userItemImg = document.querySelector('.user-item[data-user-id="' + userId + '"] img');
        if (userItemImg) {
            userItemImg.src = newPicUrl;
        }

        // Update profile pic in the chat header if it's the current recipient
        if (userId == currentRecipientId) {
            chatAvatar.src = newPicUrl;
        }

        // Update profile pic in the navbar if it's the current user
        if (userId == currentUserId) {
            const navbarProfilePic = document.querySelector('.navbar .nav-item img.rounded-circle');
            if (navbarProfilePic) {
                navbarProfilePic.src = newPicUrl;
            }
        }
    });

    socket.on('read_receipt', function(data) {
        // Find the message element by its ID
        const messageElement = document.querySelector('.message[data-message-id="' + data.message_id + '"]');
        if (messageElement) {
            // Find the read receipt icon within the message
            const readReceiptIcon = messageElement.querySelector('.read-receipt-icon i');
            if (readReceiptIcon) {
                // Update to double checkmark and blue color
                readReceiptIcon.classList.remove('fa-check', 'text-muted');
                readReceiptIcon.classList.add('fa-check-double', 'text-info');
            }
        }
    });

    function appendMessage(data, animate) {
        const div = document.createElement('div');
        const isSent = data.sender_id == currentUserId;

        div.className = 'message ' + (isSent ? 'message-sent' : 'message-received');
        div.setAttribute('data-message-id', data.id);
        div.setAttribute('data-sender-id', data.sender_id); // Add sender ID
        div.setAttribute('data-is-read', data.is_read ? 'true' : 'false'); // Add read status
        if (animate) div.style.animation = 'fadeInUp 0.3s ease';

        let replyHTML = '';
        if (data.reply_to) {
            replyHTML = '<div class="reply-bubble mb-2 p-2 rounded bg-opacity-25 ' + (isSent ? 'bg-light' : 'bg-white') + ' border-start border-primary border-3">' +
                '<small class="fw-bold text-primary">' + data.reply_to.sender_username + '</small>' +
                '<div class="small text-truncate">' + escapeHtml(data.reply_to.content) + '</div></div>';
        }

        let contentHTML = '';
        if (data.message_type === 'image' && data.image_url) {
            contentHTML = '<div class="message-content"><img src="' + data.image_url + '" alt="image" onclick="window.open(this.src,_blank)"></div>';
        } else {
            contentHTML = '<div class="message-content">' + escapeHtml(data.content) + '</div>';
            if (data.is_edited) {
                contentHTML += ' <small class="text-muted">(edited)</small>';
            }
        }

        const messageDate = new Date(data.timestamp + (data.timestamp.includes('Z') ? '' : 'Z'));
        const localTime = messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });

        let readReceiptHtml = '';
        if (isSent) {
            readReceiptHtml = '<span class="read-receipt-icon ms-1">' +
                                '<i class="fas ' + (data.is_read ? 'fa-check-double text-info' : 'fa-check text-muted') + '"></i>' +
                              '</span>';
        }
        div.innerHTML = replyHTML + contentHTML + '<span class="message-time">' + localTime + '</span>' + readReceiptHtml;

        if (isSent && !data.is_deleted) {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions position-absolute top-0 end-0 bg-white shadow-sm rounded p-1 d-none';
            actionsDiv.innerHTML = `<button class="btn btn-sm btn-light py-0 px-1 me-1 reply-btn" title="Reply"><i class="fas fa-reply fa-xs"></i></button>
                <button class="btn btn-sm btn-light py-0 px-1 me-1 edit-btn" title="Edit"><i class="fas fa-edit fa-xs"></i></button>
                <button class="btn btn-sm btn-light py-0 px-1 delete-btn" title="Delete"><i class="fas fa-trash fa-xs text-danger"></i></button>`;
            div.style.position = 'relative';
            div.appendChild(actionsDiv);

            actionsDiv.querySelector('.reply-btn').addEventListener('click', function(e) {
                e.stopPropagation();
                replyToMessage(data.id, data.sender_username, data.content);
            });
            actionsDiv.querySelector('.edit-btn').addEventListener('click', function(e) {
                e.stopPropagation();
                editMessage(data.id, data.content);
            });
            actionsDiv.querySelector('.delete-btn').addEventListener('click', function(e) {
                e.stopPropagation();
                deleteMessage(data.id);
            });

            div.addEventListener('mouseenter', function() { actionsDiv.classList.remove('d-none'); });
            div.addEventListener('mouseleave', function() { actionsDiv.classList.add('d-none'); });
        }

        messageArea.appendChild(div);
        observeNewMessages(); // Observe newly appended message
    }

    window.replyToMessage = function(id, sender, content) {
        replyToMessageData = { id: id, sender_username: sender, content: content };
        replySender.textContent = sender;
        replyContent.textContent = content.substring(0, 50);
        replyPreview.classList.remove('d-none');

        const originalMsg = document.querySelector(`.message[data-message-id="${id}"]`);
        if (originalMsg) {
            originalMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
            originalMsg.style.transition = 'background-color 0.5s ease';
            originalMsg.style.backgroundColor = 'rgba(13, 110, 253, 0.2)';
            setTimeout(() => { originalMsg.style.backgroundColor = ''; }, 2000);
        }
        messageInput.focus();
    };

    window.editMessage = function(id, currentContent) {
        const newContent = prompt('Edit your message:', currentContent || '');
        if (newContent !== null && newContent.trim()) {
            fetch('/message/' + id + '/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newContent.trim() })
            });
        }
    };

    window.deleteMessage = function(id) {
        if (confirm('Delete this message?')) {
            fetch('/message/' + id + '/delete', { method: 'POST' });
        }
    };

    function scrollToBottom() {
        messageArea.scrollTop = messageArea.scrollHeight;
    }

    const messageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const messageElement = entry.target;
                const messageId = messageElement.getAttribute('data-message-id');
                const senderId = parseInt(messageElement.getAttribute('data-sender-id'), 10);
                const isRead = messageElement.getAttribute('data-is-read') === 'true';

                // Only send message_read for received (not sent by current user), unread messages in the current chat
                if (senderId !== currentUserId && senderId == currentRecipientId && !isRead) {
                    socket.emit('message_read', { message_id: messageId });
                    // Mark as read in the DOM to avoid re-emitting
                    messageElement.setAttribute('data-is-read', 'true');
                }
            }
        });
    }, { threshold: 0.5 }); // Trigger when 50% of the message is visible

    // Observe new messages after they are appended
    const observeNewMessages = () => {
        const messagesToObserve = messageArea.querySelectorAll('.message:not([data-is-read="true"])');
        messagesToObserve.forEach(msg => {
            messageObserver.observe(msg);
        });
    };

    // Call observeNewMessages when new messages are added (e.g., after appendMessage or fetch)
    // This will be done in appendMessage and fetch('/messages/').

    const soundToggleBtn = document.getElementById('sound-toggle-btn');
    if (soundToggleBtn) {
        updateSoundToggleButton(soundToggleBtn);
    }

    function showToast(message) {
        const toastHTML = '<div class="toast align-items-center text-bg-primary border-0 show" role="alert" style="animation: slideInRight 0.3s ease;">' +
            '<div class="d-flex"><div class="toast-body"><i class="fas fa-comment-dots me-2"></i>' + message + '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button></div></div>';
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1100';
            document.body.appendChild(container);
        }
        container.insertAdjacentHTML('beforeend', toastHTML);
        setTimeout(function() { if(container.lastElementChild) container.lastElementChild.remove(); }, 3000);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
