/**
 * JobCatcher Frontend - AI Chat Manager
 * Claude 4 Sonnet Integration for Career Assistance
 */

class ChatManager {
    constructor() {
        this.API_BASE = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : 'https://obmscqebvxqz.eu-central-1.clawcloudrun.com';
        
        this.chatHistory = [];
        this.isTyping = false;
        this.resumeUploaded = false;
        this.currentStreamingMessage = null;
    }

    /**
     * Initialize chat system
     */
    init() {
        this.setupEventListeners();
        this.setupFileUpload();
        this.showWelcomeMessage();
    }

    /**
     * Setup event listeners for chat functionality
     */
    setupEventListeners() {
        // Chat input handling
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');

        if (chatInput && sendBtn) {
            // Send message on button click
            sendBtn.addEventListener('click', () => this.handleSendMessage());

            // Send message on Enter key (but allow Shift+Enter for new lines)
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSendMessage();
                }
            });

            // Auto-resize textarea
            chatInput.addEventListener('input', () => this.autoResizeTextarea(chatInput));

            // Update send button state
            chatInput.addEventListener('input', () => this.updateSendButtonState());
        }
    }

    /**
     * Setup file upload functionality
     */
    setupFileUpload() {
        const fileInput = document.getElementById('file-input');
        const fileUploadArea = document.getElementById('file-upload-area');

        if (fileInput && fileUploadArea) {
            // File input change
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

            // Drag and drop events
            fileUploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
            fileUploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            fileUploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));

            // Click to upload
            const uploadBtn = fileUploadArea.querySelector('.upload-btn');
            if (uploadBtn) {
                uploadBtn.addEventListener('click', () => fileInput.click());
            }
        }
    }

    /**
     * Show welcome message
     */
    showWelcomeMessage() {
        // Welcome message is already in HTML, no need to add programmatically
        this.scrollToBottom();
    }

    /**
     * Handle sending a message
     */
    async handleSendMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();

        if (!message || this.isTyping) {
            return;
        }

        // Clear input and reset height
        chatInput.value = '';
        this.autoResizeTextarea(chatInput);
        this.updateSendButtonState();

        // Add user message to chat
        this.addMessage('user', message);

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send message to backend
            await this.sendMessageToBot(message);
        } catch (error) {
            console.error('Failed to send message:', error);
            this.hideTypingIndicator();
            this.addMessage('bot', 'Sorry, I encountered an error. Please try again.');
        }
    }

    /**
     * Send message to bot and handle streaming response
     */
    async sendMessageToBot(message) {
        this.isTyping = true;

        try {
            const response = await fetch(`${this.API_BASE}/api/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ 
                    message: message,
                    history: this.chatHistory.slice(-10) // Send last 10 messages for context
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Handle streaming response
            await this.handleStreamingResponse(response);

        } catch (error) {
            console.error('Bot message failed:', error);
            throw error;
        } finally {
            this.isTyping = false;
        }
    }

    /**
     * Handle streaming response from the bot
     */
    async handleStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let botMessage = '';

        // Hide typing indicator and create message container
        this.hideTypingIndicator();
        const messageElement = this.addMessage('bot', '', true); // Empty message for streaming
        const contentElement = messageElement.querySelector('.message-content');

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.trim() === '') continue;
                    
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'content' && data.content) {
                                botMessage += data.content;
                                contentElement.innerHTML = this.formatMessage(botMessage);
                                this.scrollToBottom();
                            } else if (data.type === 'job_recommendations' && data.jobs) {
                                // Handle job recommendations
                                this.displayJobRecommendations(data.jobs);
                            } else if (data.type === 'skill_chart' && data.chart_data) {
                                // Handle skill chart
                                this.displaySkillChart(data.chart_data);
                            }
                        } catch (e) {
                            // Ignore malformed JSON
                            console.warn('Malformed JSON in stream:', line);
                        }
                    }
                }
            }

            // Add final message to history
            this.chatHistory.push({ role: 'assistant', content: botMessage });

        } catch (error) {
            console.error('Error reading stream:', error);
            contentElement.innerHTML = 'Sorry, I encountered an error while processing your request.';
        }
    }

    /**
     * Add message to chat UI
     */
    addMessage(sender, content, isStreaming = false) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatarClass = sender === 'bot' ? 'bot-avatar' : 'user-avatar-chat';
        const avatarIcon = sender === 'bot' ? 'fas fa-robot' : 'fas fa-user';

        messageDiv.innerHTML = `
            <div class="${avatarClass}">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                ${isStreaming ? '' : this.formatMessage(content)}
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Add to chat history if not streaming
        if (!isStreaming && content) {
            this.chatHistory.push({ 
                role: sender === 'bot' ? 'assistant' : 'user', 
                content: content 
            });
        }

        return messageDiv;
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        if (document.querySelector('.typing-indicator-message')) {
            return; // Already showing
        }

        const chatMessages = document.getElementById('chat-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator-message';
        typingDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;

        chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        const typingMessage = document.querySelector('.typing-indicator-message');
        if (typingMessage) {
            typingMessage.remove();
        }
    }

    /**
     * Handle file selection
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleFileUpload(file);
        }
    }

    /**
     * Handle file drop
     */
    handleFileDrop(event) {
        event.preventDefault();
        const fileUploadArea = document.getElementById('file-upload-area');
        fileUploadArea.classList.remove('dragover');

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.handleFileUpload(files[0]);
        }
    }

    /**
     * Handle drag over
     */
    handleDragOver(event) {
        event.preventDefault();
        const fileUploadArea = document.getElementById('file-upload-area');
        fileUploadArea.classList.add('dragover');
    }

    /**
     * Handle drag leave
     */
    handleDragLeave(event) {
        event.preventDefault();
        const fileUploadArea = document.getElementById('file-upload-area');
        fileUploadArea.classList.remove('dragover');
    }

    /**
     * Handle file upload
     */
    async handleFileUpload(file) {
        const allowedTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ];

        if (!allowedTypes.includes(file.type)) {
            this.showNotification('Please upload a PDF, DOC, DOCX, or TXT file', 'error');
            return;
        }

        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            this.showNotification('File size must be less than 10MB', 'error');
            return;
        }

        // Add file upload message
        this.addMessage('user', `📄 Uploading resume: ${file.name}`);
        this.showTypingIndicator();

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.API_BASE}/api/upload/resume`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result = await response.json();
            this.hideTypingIndicator();
            
            // Mark resume as uploaded
            this.resumeUploaded = true;
            this.updateUploadAreaState();

            // Add success message
            this.addMessage('bot', result.message || 'Resume uploaded successfully! Let me analyze it for you.');

            // Automatically trigger resume analysis
            await this.analyzeResume();

        } catch (error) {
            console.error('Resume upload failed:', error);
            this.hideTypingIndicator();
            this.addMessage('bot', 'Sorry, I couldn\'t upload your resume. Please try again.');
        }
    }

    /**
     * Analyze uploaded resume
     */
    async analyzeResume() {
        this.showTypingIndicator();

        try {
            const response = await fetch(`${this.API_BASE}/api/chat/analyze-resume`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            // Handle streaming analysis response
            await this.handleStreamingResponse(response);

        } catch (error) {
            console.error('Resume analysis failed:', error);
            this.hideTypingIndicator();
            this.addMessage('bot', 'I encountered an error while analyzing your resume. Please try again.');
        }
    }

    /**
     * Display job recommendations in left panel
     */
    displayJobRecommendations(jobs) {
        if (window.app && window.app.displayJobs) {
            window.app.displayJobs(jobs);
            window.app.updateResultsCount(jobs.length);
            
            // Add chat message about recommendations
            this.addMessage('bot', `I found ${jobs.length} job recommendations based on your resume. Check them out in the left panel! 🎯`);
        }
    }

    /**
     * Display skill chart
     */
    displaySkillChart(chartData) {
        // Add chart container to chat
        const chartMessage = this.addMessage('bot', '', true);
        const contentElement = chartMessage.querySelector('.message-content');
        
        contentElement.innerHTML = `
            <div class="skill-chart-container">
                <h4>📊 Your Skill Analysis</h4>
                <div class="skill-chart" id="skill-chart-${Date.now()}"></div>
                <p class="chart-description">This chart shows your current skills and market demand.</p>
            </div>
        `;

        // You could integrate with Chart.js or similar library here
        // For now, show a simple skill list
        const chartDiv = contentElement.querySelector('.skill-chart');
        if (chartData.skills) {
            chartDiv.innerHTML = chartData.skills.map(skill => `
                <div class="skill-item">
                    <span class="skill-name">${skill.name}</span>
                    <div class="skill-bar">
                        <div class="skill-level" style="width: ${skill.level}%"></div>
                    </div>
                    <span class="skill-percentage">${skill.level}%</span>
                </div>
            `).join('');
        }
    }

    /**
     * Update upload area state based on resume upload status
     */
    updateUploadAreaState() {
        const uploadArea = document.getElementById('file-upload-area');
        if (!uploadArea) return;

        if (this.resumeUploaded) {
            uploadArea.innerHTML = `
                <div class="upload-content uploaded">
                    <i class="fas fa-check-circle"></i>
                    <p>Resume uploaded successfully!</p>
                    <p class="upload-hint">You can upload a new resume anytime</p>
                    <button class="upload-btn" onclick="document.getElementById('file-input').click()">
                        Upload New Resume
                    </button>
                </div>
            `;
        }
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    /**
     * Update send button state
     */
    updateSendButtonState() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        
        if (chatInput && sendBtn) {
            const hasText = chatInput.value.trim().length > 0;
            sendBtn.disabled = !hasText || this.isTyping;
            sendBtn.style.opacity = (!hasText || this.isTyping) ? '0.5' : '1';
        }
    }

    /**
     * Scroll chat to bottom
     */
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    /**
     * Format message content
     */
    formatMessage(content) {
        if (!content) return '';
        
        // Escape HTML and convert newlines to line breaks
        const escaped = this.escapeHtml(content);
        
        // Convert URLs to links
        const withLinks = escaped.replace(
            /(https?:\/\/[^\s]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Convert newlines to line breaks
        return withLinks.replace(/\n/g, '<br>');
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span>${message}</span>
                <button class="notification-close" onclick="this.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Clear chat history
     */
    clearChat() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            // Keep only the welcome message
            const welcomeMessage = chatMessages.querySelector('.welcome-message');
            chatMessages.innerHTML = '';
            if (welcomeMessage) {
                chatMessages.appendChild(welcomeMessage);
            }
        }
        
        this.chatHistory = [];
        this.resumeUploaded = false;
        this.updateUploadAreaState();
    }

    /**
     * Get chat history
     */
    getChatHistory() {
        return this.chatHistory;
    }
}

// Initialize chat manager
const chatManager = new ChatManager();

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    chatManager.init();
});

// Export for global access
window.chatManager = chatManager; 