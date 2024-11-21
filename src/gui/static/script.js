document.addEventListener('DOMContentLoaded', function() {
    const chatBox = document.getElementById('chat-box');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');

    // Add event listeners
    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            if (e.shiftKey) {
                // Allow new line when Shift+Enter is pressed
                return;
            } else {
                e.preventDefault(); // Prevent default Enter behavior
                sendMessage();
            }
        }
    });

    chatInput.addEventListener('input', function() {
        adjustInputHeight();
    });

    function adjustInputHeight() {
        chatInput.style.height = 'auto'; // Reset height
        const maxHeight = 100; // Maximum height in pixels
        const scrollHeight = chatInput.scrollHeight;
        
        if (scrollHeight > maxHeight) {
            chatInput.style.height = `${maxHeight}px`;
            chatInput.style.overflowY = 'auto';
        } else {
            chatInput.style.height = `${scrollHeight}px`;
            chatInput.style.overflowY = 'hidden';
        }
    }

    function sendMessage() {
        const query = chatInput.value.trim();
        if (!query) return;

        addMessage('User', query);
        chatInput.value = ''; // Clear input field
        adjustInputHeight(); // Reset input field height

        fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                addMessage('MAP_IT', data.error);
            } else {
                addMessage('MAP_IT', JSON.stringify(data, null, 2));
            }
        })
        .catch(err => {
            addMessage('MAP_IT', 'Failed to connect to the server.');
        });
    }

    function addMessage(sender, message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'User' ? 'user' : 'flask');
        messageDiv.innerHTML = `<strong>${sender}:</strong> <pre>${message}</pre>`;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});