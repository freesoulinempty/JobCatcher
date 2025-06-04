/**
 * JobCatcher Frontend - AI Chat Manager
 * Claude 4 Sonnet Integration with Unified Tool Calling
 */

// JobCatcher Chat Manager - Unified Claude 4 Interface
console.log('ChatManager loaded - Version: 20250131-UNIFIED');

class ChatManager {
    constructor() {
        this.API_BASE = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : 'https://obmscqebvxqz.eu-central-1.clawcloudrun.com';
        
        this.chatHistory = [];
        this.isTyping = false;
        this.resumeUploaded = false;
        this.currentStreamingMessage = null;
        this.currentStreamingContent = ''; // 累积流式内容 / Accumulated streaming content
        this.sessionId = null; // 会话ID管理 / Session ID management
        this.sessionState = { // 会话状态 / Session state
            resumeAnalysis: null,
            jobPostings: [],
            toolResults: []
        };
        this.isInitialized = false; // 初始化状态 / Initialization status
    }

    /**
     * Initialize chat system
     */
    init() {
        if (this.isInitialized) return;
        
        this.setupEventListeners();
        this.setupFileUpload();
        this.showWelcomeMessage();
        this.generateSessionId();
        this.isInitialized = true;
        
        console.log('ChatManager initialized successfully');
    }

    /**
     * Generate new session ID
     */
    generateSessionId() {
        this.sessionId = 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        console.log('New session created:', this.sessionId);
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

        // Add clear session button
        const clearBtn = document.getElementById('clear-session-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearSession());
        }
    }

    /**
     * Setup file upload functionality
     */
    setupFileUpload() {
        const fileInput = document.getElementById('fileInput');

        if (fileInput) {
            // File input change
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
    }

    /**
     * Handle file selection
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleFileUpload(file);
            // Clear the input so the same file can be selected again
            event.target.value = '';
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

        // Add user message with sending animation
        const userMessageElement = this.addUserMessageWithAnimation(message);

        // 不需要预先显示typing indicator，等到流式响应开始时再处理
        // No need to show typing indicator upfront, handle it when streaming starts

        try {
            // Send message to unified bot interface
            await this.sendMessageToUnifiedBot(message);
        } catch (error) {
            console.error('Failed to send message:', error);
            this.hideTypingIndicator();
            this.createErrorMessage('Sorry, I encountered an error. Please try again.');
        }
    }

    /**
     * Send message to unified bot interface
     */
    async sendMessageToUnifiedBot(message) {
        this.isTyping = true;

        try {
            // Prepare context with session information
            const context = {
                session_id: this.sessionId,
                chat_history: this.chatHistory.slice(-10), // 保留最近10条消息 / Keep last 10 messages
                resume_uploaded: this.resumeUploaded,
                ...this.sessionState
            };

            // 🔥 修改：正确处理新的文档格式 / MODIFIED: Properly handle new document format
            if (this.uploadedFile) {
                context.uploaded_file = this.uploadedFile;
                context.resume_uploaded = true;
                
                // 记录文档格式类型 / Log document format type
                const documentFormat = this.uploadedFile.document_data?.claude_format || 'unknown';
                console.log(`📄 Sending message with ${documentFormat} document format for file: ${this.uploadedFile.filename}`);
            }

            const response = await fetch(`${this.API_BASE}/api/chat/unified`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ 
                    message: message,
                    context: context
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Handle unified streaming response
            await this.handleUnifiedStreamingResponse(response);

        } finally {
            this.isTyping = false;
            this.hideTypingIndicator();
        }
    }

    /**
     * Handle unified streaming response with tool calling support
     */
    async handleUnifiedStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // 延迟创建消息，等到有实际内容时再创建 / Delayed message creation
        this.currentStreamingMessage = null;
        this.currentStreamingContent = ''; // 重置累积内容 / Reset accumulated content
        let currentContent = '';
        let currentTool = null;

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            await this.processUnifiedEvent(data, currentContent, currentTool);
                            
                            // Update current state based on event
                            if (data.type === 'text_delta') {
                                currentContent += data.content || '';
                            } else if (data.type === 'tool_use_start') {
                                currentTool = data.tool_name;
                            } else if (data.type === 'tool_execution_complete') {
                                currentTool = null;
                            } else if (data.type === 'complete') {
                                // Conversation complete
                                this.sessionId = data.session_id || this.sessionId;
                            }

                        } catch (e) {
                            console.warn('Failed to parse event:', line, e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Streaming error:', error);
            this.createErrorMessage('Sorry, there was an error during the conversation.');
        } finally {
            this.hideTypingIndicator();
            this.hideWebSearchIndicator();
            this.hideToolExecutionIndicator();
            
            // Add assistant message to history
            if (this.currentStreamingContent) {
                this.chatHistory.push({ 
                    role: 'assistant', 
                    content: this.currentStreamingContent 
                });
            }
        }
    }

    /**
     * Process unified streaming events
     */
    async processUnifiedEvent(event, currentContent, currentTool) {
        const { type } = event;

        switch (type) {
            case 'start':
                // Stream started
                console.log('Stream started:', event);
                break;

            // 思考模式已禁用 / Thinking mode disabled
            // case 'thinking_start':
            // case 'thinking':  
            // case 'thinking_complete':

            case 'text_start':
                // Text content started
                break;

            case 'text':
            case 'text_delta':
                // 🔧 修复：支持两种事件类型 / Fix: Support both event types
                console.log('📝 Received text event:', event); // 🔧 调试日志
                if (event.content) {
                    // 累积内容
                    this.currentStreamingContent += event.content;
                    console.log('📝 Accumulated content length:', this.currentStreamingContent.length); // 🔧 调试日志
                    
                    // 如果还没有消息容器且有内容，创建消息
                    if (!this.currentStreamingMessage && this.currentStreamingContent.trim()) {
                        // 确保隐藏任何typing indicator
                        this.hideTypingIndicator();
                        this.currentStreamingMessage = this.createEmptyBotMessage();
                        console.log('📝 Created bot message container'); // 🔧 调试日志
                    }
                    
                    // 更新消息内容
                    if (this.currentStreamingMessage) {
                        this.updateStreamingMessage();
                    }
                } else {
                    console.warn('📝 Text event without content:', event); // 🔧 调试日志
                }
                break;

            case 'content_block_start':
                // 处理内容块开始，包括server_tool_use / Handle content block start including server_tool_use
                if (event.content_block && event.content_block.type === 'server_tool_use') {
                    if (event.content_block.name === 'web_search') {
                        this.showWebSearchIndicator();
                        console.log('🔍 Web search tool started:', event.content_block.id);
                    } else {
                        this.showToolExecutionIndicator(event.content_block.name);
                    }
                } else if (event.content_block && event.content_block.type === 'web_search_tool_result') {
                    console.log('🔍 Web search results received:', event.content_block.content?.length, 'results');
                    this.hideWebSearchIndicator();
                }
                break;

            case 'tool_use_start':
                // 向后兼容：工具开始执行 / Backward compatibility: Tool execution started
                if (event.tool_name === 'web_search') {
                    this.showWebSearchIndicator();
                } else {
                this.showToolExecutionIndicator(event.tool_name);
                }
                break;

            case 'web_search_result':
                // 向后兼容：Web搜索完成 / Backward compatibility: Web search completed  
                this.hideWebSearchIndicator();
                break;

            case 'tool_input_delta':
                // Tool input being constructed
                // Could show tool parameters being built
                break;

            case 'tool_execution_start':
                // Tool actually executing
                this.updateToolExecutionIndicator(event.tool_name, 'executing');
                break;

            case 'tool_execution_complete':
                // 工具执行完成 / Tool execution completed
                this.hideToolExecutionIndicator();
                this.handleToolResult(event.tool_name, event.result);
                break;

            case 'conversation_complete':
                // Conversation round completed
                this.hideTypingIndicator();
                break;

            case 'error':
                // Error occurred
                console.error('Bot error:', event.content);
                this.createErrorMessage(event.content || 'An error occurred');
                break;

            case 'job_data':
                // 🔥 README第9步：接收职位数据并显示在左侧 / README step 9: Receive job data and display on left side
                console.log('📋 Received job data:', event.jobs?.length, 'jobs');
                if (event.jobs && Array.isArray(event.jobs)) {
                    this.displayJobsInPanel(event.jobs, event.match_type);
                }
                break;

            case 'complete':
                // Stream completely finished
                console.log('Stream completed:', event);
                break;

            default:
                console.log('Unknown event type:', type, event);
        }
    }

    /**
     * Handle tool execution results
     */
    handleToolResult(toolName, result) {

        switch (toolName) {
            case 'analyze_resume':
                if (result && !result.error) {
                    this.sessionState.resumeAnalysis = result;
                }
                break;

            case 'match_jobs_with_resume':
                if (result && result.matches) {
                    this.displayJobMatches(result.matches);
                }
                break;

            case 'generate_skill_heatmap':
                if (result && result.skills) {
                    this.displaySkillHeatmap(result);
                }
                break;

            case 'get_market_insights':
                // Market insights are usually returned as text content
                // No special UI handling needed as it's in the conversation
                break;

            case 'web_search':
                // Web search results are integrated into the conversation
                this.hideWebSearchIndicator();
                break;

            default:
                console.log('Unhandled tool result:', toolName, result);
        }
    }

    /**
     * Show tool execution indicator
     */
    showToolExecutionIndicator(toolName) {
        this.hideWebSearchIndicator(); // Hide other indicators
        
        const indicator = document.createElement('div');
        indicator.id = 'tool-execution-indicator';
        indicator.className = 'typing-indicator';
        
        const toolDisplayNames = {
            'analyze_resume': '📄 Analyzing resume...',
            'match_jobs_with_resume': '🎯 Matching jobs...',
            'generate_skill_heatmap': '📊 Generating skill heatmap...',
            'get_market_insights': '💼 Getting market insights...',
            'web_search': '🌐 Searching latest information...'
        };

        indicator.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-content">
                <span class="tool-name">${toolDisplayNames[toolName] || `🔧 Using ${toolName}...`}</span>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.appendChild(indicator);
            this.scrollToBottom();
        }
    }

    /**
     * Update tool execution indicator
     */
    updateToolExecutionIndicator(toolName, status) {
        const indicator = document.getElementById('tool-execution-indicator');
        if (indicator) {
            const toolNameSpan = indicator.querySelector('.tool-name');
            if (toolNameSpan && status === 'executing') {
                toolNameSpan.textContent = `🔄 Executing ${toolName}...`;
            }
        }
    }

    /**
     * Hide tool execution indicator
     */
    hideToolExecutionIndicator() {
        const indicator = document.getElementById('tool-execution-indicator');
        if (indicator) {
            indicator.remove();
        }
    }



    /**
     * Display job matches - 复用JobsManager逻辑 / Reuse JobsManager logic
     */
    displayJobMatches(matches) {
        // 🔥 复用现有的JobsManager / Reuse existing JobsManager
        if (window.jobsManager && typeof window.jobsManager.displayJobs === 'function') {
            // Convert matches to job format
            const jobs = matches.map(match => ({
                ...match.job,
                match_score: match.match_score,
                match_reasons: match.match_reasons
            }));
            
            // 使用统一的显示方法 / Use unified display method
            this.displayJobsInPanel(jobs, 'matched');
        } else {
            console.error('JobsManager not available for displaying job matches');
        }
    }

    /**
     * 🔥 README第9步：显示职位数据在左侧面板 / README step 9: Display job data in left panel  
     * 复用现有的JobsManager来避免代码重复 / Reuse existing JobsManager to avoid code duplication
     */
    displayJobsInPanel(jobs, matchType = 'general') {
        console.log(`📋 Displaying ${jobs.length} jobs in left panel (${matchType} matching)`);
        
        // 🔥 复用现有的JobsManager / Reuse existing JobsManager
        if (window.jobsManager && typeof window.jobsManager.displayJobs === 'function') {
            // 使用现有的JobsManager来显示职位 / Use existing JobsManager to display jobs
            window.jobsManager.displayJobs(jobs);
            
            // 添加个性化匹配指示器 / Add personalized matching indicator
            if (matchType === 'personalized') {
                this.addPersonalizedMatchIndicator();
            }
            
            // 显示成功通知 / Show success notification
            this.showNotification(`Found ${jobs.length} ${matchType} job matches!`, 'success');
            
        } else {
            console.error('JobsManager not available, using fallback display');
            this.fallbackDisplayJobs(jobs, matchType);
        }
    }

    /**
     * 添加个性化匹配指示器 / Add personalized matching indicator
     */
    addPersonalizedMatchIndicator() {
        const jobsContainer = document.getElementById('jobsContainer');
        if (!jobsContainer) return;
        
        // 检查是否已经有指示器 / Check if indicator already exists
        if (jobsContainer.querySelector('.match-indicator')) return;
        
        const matchIndicator = document.createElement('div');
        matchIndicator.className = 'match-indicator personalized';
        matchIndicator.innerHTML = `
            <i class="fas fa-user-check"></i>
            <span>Personalized matches based on your resume</span>
        `;
        
        // 在第一个职位卡片之前插入 / Insert before first job card
        const firstJobCard = jobsContainer.querySelector('.job-card');
        if (firstJobCard) {
            jobsContainer.insertBefore(matchIndicator, firstJobCard);
        } else {
            jobsContainer.prepend(matchIndicator);
        }
    }

    /**
     * 备用职位显示方法（当JobsManager不可用时）/ Fallback job display method
     */
    fallbackDisplayJobs(jobs, matchType) {
        const jobsContainer = document.getElementById('jobsContainer');
        const resultsCount = document.getElementById('resultsCount');
        
        if (resultsCount) {
            resultsCount.textContent = `${jobs.length} jobs found`;
        }
        
        if (!jobsContainer) {
            console.error('Jobs container not found');
            return;
        }
        
        if (jobs.length === 0) {
            jobsContainer.innerHTML = '<div class="no-jobs-message">No jobs found.</div>';
            return;
        }
        
        // 创建简单的职位列表 / Create simple job list
        const jobsHTML = jobs.map(job => `
            <div class="job-card" data-job-id="${job.id}">
                <div class="job-header">
                    <h3 class="job-title">${this.escapeHtml(job.title || 'Unknown Position')}</h3>
                    <div class="company-name">${this.escapeHtml(job.company_name || 'Unknown Company')}</div>
                </div>
                <div class="job-meta">
                    <span class="location">
                        <i class="fas fa-map-marker-alt"></i>
                        ${this.escapeHtml(job.location || 'Location not specified')}
                    </span>
                </div>
                <div class="job-actions">
                    ${job.url ? `
                    <a href="${job.url}" target="_blank" class="job-action-btn apply-btn">
                        <i class="fas fa-external-link-alt"></i>
                        Apply Now
                    </a>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        jobsContainer.innerHTML = jobsHTML;
    }

    /**
     * Display skill heatmap
     */
    displaySkillHeatmap(heatmapData) {
        // Could integrate with a visualization library
        // For now, the heatmap info is in the conversation
    }

    /**
     * Create empty bot message for streaming
     */
    createEmptyBotMessage() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) {
            console.error('Chat messages container not found');
            return null;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="streaming-content"></div>
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        return messageDiv;
    }

    /**
     * Update streaming message with accumulated content
     */
    updateStreamingMessage() {
        if (!this.currentStreamingMessage) {
            console.warn('No current streaming message to update');
            return;
        }

        const contentElement = this.currentStreamingMessage.querySelector('.streaming-content');
        if (contentElement) {
            // 使用formatMessage进行Markdown解析
            const formattedContent = this.formatMessage(this.currentStreamingContent);
            contentElement.innerHTML = formattedContent;
            this.scrollToBottom();
        } else {
            console.error('Streaming content element not found');
        }
    }

    /**
     * Handle file upload with proper backend API integration
     */
    async handleFileUpload(file) {
        if (!file) return;

        const chatMessages = document.getElementById('chat-messages');
        
        // Show upload indicator
        const uploadIndicator = document.createElement('div');
        uploadIndicator.className = 'message bot-message';
        uploadIndicator.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="upload-indicator">
                    📁 Uploading file: ${file.name}
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(uploadIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            // Prepare form data for upload
            const formData = new FormData();
            formData.append('file', file);
            formData.append('user_id', 'default_user'); // TODO: Get from auth system

            // Upload file to backend
            const uploadResponse = await fetch(`${this.API_BASE}/api/upload/resume`, {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error(`Upload failed: ${uploadResponse.status}`);
            }

            const uploadResult = await uploadResponse.json();
            
            // Remove upload indicator
            chatMessages.removeChild(uploadIndicator);
            
            // Show upload success message
            const successMessage = document.createElement('div');
            successMessage.className = 'message bot-message';
            successMessage.innerHTML = `
                <div class="bot-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="upload-success">
                        ✅ Uploaded file: ${uploadResult.filename}
                        ${uploadResult.claude_native_support ? 
                          '<br><span class="claude-native">🔥 Using Claude 4 native PDF processing for optimal performance</span>' : 
                          '<br><span class="text-extracted">📝 Text content extracted</span>'
                        }
                        <br><span class="file-size">Size: ${(uploadResult.size / 1024).toFixed(1)} KB</span>
                    </div>
                </div>
            `;
            chatMessages.appendChild(successMessage);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // 🔥 关键：保存上传文件信息，包含Claude 4原生格式数据 / CRITICAL: Save uploaded file info with Claude 4 native format data
            this.uploadedFile = {
                filename: uploadResult.filename,
                unique_filename: uploadResult.unique_filename,
                file_path: uploadResult.file_path,
                content_type: uploadResult.content_type,
                size: uploadResult.size,
                // 🔥 新增：Claude 4原生文档数据 / NEW: Claude 4 native document data
                document_data: uploadResult.document_data,
                claude_native_support: uploadResult.claude_native_support,
                // 保持向后兼容性 / Maintain backward compatibility
                text_content: uploadResult.document_data?.content || ''
            };

            console.log('📄 File upload completed:', this.uploadedFile);
            
            // 🔥 优化：显示温馨提示而不是自动分析 / OPTIMIZED: Show friendly prompt instead of auto-analysis
            setTimeout(() => {
                this.showUploadCompleteMessage();
            }, 1000);

        } catch (error) {
            console.error('File upload error:', error);
            
            // Remove upload indicator
            if (chatMessages.contains(uploadIndicator)) {
                chatMessages.removeChild(uploadIndicator);
            }
            
            // Show error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'message bot-message error';
            errorMessage.innerHTML = `
                <div class="bot-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="upload-error">
                        ❌ Upload failed: ${error.message}
                        <br>Please try again with a different file.
                    </div>
                </div>
            `;
            chatMessages.appendChild(errorMessage);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    /**
     * Clear current session
     */
    async clearSession() {
        try {
            // Clear session on server
            await fetch(`${this.API_BASE}/api/chat/session/${this.sessionId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            // Reset local state
            this.chatHistory = [];
            this.sessionState = {
                resumeAnalysis: null,
                jobPostings: [],
                toolResults: []
            };
            this.resumeUploaded = false;
            
            // Generate new session
            this.generateSessionId();
            
            // Clear chat UI
            this.clearChatUI();
            
            // Show welcome message
            this.showWelcomeMessage();
            
            this.showNotification('Session cleared. You can start a new conversation.', 'success');

        } catch (error) {
            console.error('Failed to clear session:', error);
            this.showNotification('Failed to clear session', 'error');
        }
    }

    /**
     * Clear chat UI
     */
    clearChatUI() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            // Remove all messages except welcome
            const messages = chatMessages.querySelectorAll('.message:not(.welcome-message)');
            messages.forEach(msg => msg.remove());
        }
    }

    /**
     * Add user message with sending animation
     */
    addUserMessageWithAnimation(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) {
            console.error('Chat messages container not found');
            return null;
        }

        // Create user message element
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message sending';

        messageDiv.innerHTML = `
            <div class="user-avatar-chat">
                <i class="fas fa-user"></i>
            </div>
            <div class="message-content">
                ${this.formatMessage(message)}
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Add to chat history
        this.chatHistory.push({ 
            role: 'user', 
            content: message 
        });

        // Remove sending class after animation
        setTimeout(() => {
            messageDiv.classList.remove('sending');
        }, 500);

        return messageDiv;
    }

    /**
     * Create error message without using addMessage
     */
    createErrorMessage(errorText) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) {
            console.error('Chat messages container not found');
            return null;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';

        messageDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                ${this.formatMessage(errorText)}
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        return messageDiv;
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator(message = '🤔 Claude正在深度思考...') {
        if (document.querySelector('.typing-indicator-message')) {
            return; // Already showing
        }

        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) {
            console.error('Chat messages container not found');
            return;
        }

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
                <span class="typing-text">${message}</span>
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
     * Show WebSearch indicator - 显示联网搜索提示
     */
    showWebSearchIndicator() {
        // Remove existing indicator if any
        this.hideWebSearchIndicator();

        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) {
            console.error('Chat messages container not found');
            return;
        }

        // 创建WebSearch消息，类似typing indicator但是用于搜索
        const searchDiv = document.createElement('div');
        searchDiv.className = 'message bot-message websearch-indicator-message';
        searchDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="websearch-indicator">
                    <i class="fas fa-globe websearch-icon"></i>
                    <span class="websearch-text">Searching the web...</span>
                </div>
            </div>
        `;

        chatMessages.appendChild(searchDiv);
        this.scrollToBottom();
    }

    /**
     * Hide WebSearch indicator - 隐藏联网搜索提示
     */
    hideWebSearchIndicator() {
        const searchIndicator = document.querySelector('.websearch-indicator-message');
        if (searchIndicator) {
            searchIndicator.remove();
        }
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
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
     * Format message content with Markdown support
     */
    formatMessage(content) {
        if (!content) return '';
        
        // First escape HTML to prevent XSS
        let formatted = this.escapeHtml(content);
        
        // Parse Markdown elements
        formatted = this.parseMarkdown(formatted);
        
        // Convert URLs to links (after Markdown parsing to avoid conflicts)
        formatted = formatted.replace(
            /(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        return formatted;
    }

    /**
     * Parse Markdown content to HTML - Enhanced version
     */
    parseMarkdown(text) {
        let html = text;
        
        // 预处理：保护代码块内容不被其他规则影响
        const codeBlocks = [];
        html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
            const index = codeBlocks.length;
            codeBlocks.push(code);
            return `__CODE_BLOCK_${index}__`;
        });
        
        const inlineCodes = [];
        html = html.replace(/`([^`]+)`/g, (match, code) => {
            const index = inlineCodes.length;
            inlineCodes.push(code);
            return `__INLINE_CODE_${index}__`;
        });
        
        // Headers (#### ### ## #) - 从最长到最短匹配
        html = html.replace(/^#### (.*$)/gm, '<h4>$1</h4>');
        html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');
        
        // Bold text (**text** or __text__) - 改进正则表达式
        html = html.replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/__([^_\n]+?)__/g, '<strong>$1</strong>');
        
        // Italic text (*text* or _text_) - 避免与bold冲突
        html = html.replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>');
        html = html.replace(/(?<!_)_([^_\n]+?)_(?!_)/g, '<em>$1</em>');
        
        // Process lists with better handling
        html = this.processListsEnhanced(html);
        
        // Blockquotes (> text) - 支持多行
        html = html.replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>');
        
        // Horizontal rules (--- or ***)
        html = html.replace(/^---+$/gm, '<hr>');
        html = html.replace(/^\*\*\*+$/gm, '<hr>');
        
        // 恢复代码块
        codeBlocks.forEach((code, index) => {
            html = html.replace(`__CODE_BLOCK_${index}__`, `<pre><code>${this.escapeHtml(code)}</code></pre>`);
        });
        
        // 恢复内联代码
        inlineCodes.forEach((code, index) => {
            html = html.replace(`__INLINE_CODE_${index}__`, `<code>${this.escapeHtml(code)}</code>`);
        });
        
        // Line breaks - 改进换行处理
        html = html.replace(/\n(?!<\/?(h[1-6]|ul|ol|li|blockquote|pre|hr|div))/g, '<br>');
        
        return html;
    }

    /**
     * Enhanced list processing with better nesting support
     */
    processListsEnhanced(text) {
        const lines = text.split('\n');
        const result = [];
        let inUnorderedList = false;
        let inOrderedList = false;
        let listLevel = 0;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            
            // 计算缩进级别
            const indent = line.length - line.trimStart().length;
            const currentLevel = Math.floor(indent / 2); // 每2个空格为一级
            
            // Check for unordered list item (- item or * item)
            if (/^[-*] (.+)/.test(trimmedLine)) {
                if (inOrderedList) {
                    result.push('</ol>');
                    inOrderedList = false;
                }
                if (!inUnorderedList || currentLevel !== listLevel) {
                    if (inUnorderedList && currentLevel > listLevel) {
                        // 嵌套列表
                        result.push('<ul>');
                    } else if (inUnorderedList && currentLevel < listLevel) {
                        // 退出嵌套
                        for (let j = listLevel; j > currentLevel; j--) {
                            result.push('</ul>');
                        }
                    } else if (!inUnorderedList) {
                        result.push('<ul>');
                    }
                    inUnorderedList = true;
                    listLevel = currentLevel;
                }
                result.push(trimmedLine.replace(/^[-*] (.+)/, '<li>$1</li>'));
            }
            // Check for ordered list item (1. item, 2. item, etc.)
            else if (/^\d+\. (.+)/.test(trimmedLine)) {
                if (inUnorderedList) {
                    result.push('</ul>');
                    inUnorderedList = false;
                }
                if (!inOrderedList || currentLevel !== listLevel) {
                    if (inOrderedList && currentLevel > listLevel) {
                        result.push('<ol>');
                    } else if (inOrderedList && currentLevel < listLevel) {
                        for (let j = listLevel; j > currentLevel; j--) {
                            result.push('</ol>');
                        }
                    } else if (!inOrderedList) {
                        result.push('<ol>');
                    }
                    inOrderedList = true;
                    listLevel = currentLevel;
                }
                result.push(trimmedLine.replace(/^\d+\. (.+)/, '<li>$1</li>'));
            }
            // Regular line
            else {
                if (inUnorderedList) {
                    for (let j = 0; j <= listLevel; j++) {
                        result.push('</ul>');
                    }
                    inUnorderedList = false;
                }
                if (inOrderedList) {
                    for (let j = 0; j <= listLevel; j++) {
                        result.push('</ol>');
                    }
                    inOrderedList = false;
                }
                listLevel = 0;
                result.push(line); // Keep original line with indentation
            }
        }
        
        // Close any remaining lists
        if (inUnorderedList) {
            for (let j = 0; j <= listLevel; j++) {
                result.push('</ul>');
            }
        }
        if (inOrderedList) {
            for (let j = 0; j <= listLevel; j++) {
                result.push('</ol>');
            }
        }
        
        return result.join('\n');
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
     * 🔥 新功能：显示上传完成提示 / NEW: Show upload complete prompt
     * 给用户提示可以问什么问题，而不是强制分析 / Give users suggestions without forcing analysis
     */
    showUploadCompleteMessage() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const promptMessage = document.createElement('div');
        promptMessage.className = 'message bot-message upload-complete-prompt';
        promptMessage.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="upload-complete-content">
                    <h4>📄 Resume Upload Complete!</h4>
                    <p>Great! I've received your resume. Now you can ask me anything about it, such as:</p>
                    
                    <div class="suggestion-chips">
                        <div class="chip" onclick="chatManager.sendSuggestedMessage('Analyze my resume and tell me what strengths and weaknesses you see')">
                            💡 Analyze my resume strengths and weaknesses
                        </div>
                        <div class="chip" onclick="chatManager.sendSuggestedMessage('What skills are missing from my resume for current job market?')">
                            🎯 What skills am I missing for the job market?
                        </div>
                        <div class="chip" onclick="chatManager.sendSuggestedMessage('How can I improve my resume for software engineering roles?')">
                            🔧 How can I improve my resume?
                        </div>
                        <div class="chip" onclick="chatManager.sendSuggestedMessage('Find me jobs that match my background and experience')">
                            🔍 Find matching jobs for me
                        </div>
                        <div class="chip" onclick="chatManager.sendSuggestedMessage('Show me a skills heatmap for my target job roles')">
                            📊 Generate skills heatmap
                        </div>
                    </div>
                    
                    <p class="flexible-prompt">
                        💬 <strong>Or ask anything else!</strong> I'm here to help with resume analysis, job matching, 
                        career advice, skill gap analysis, and more. Just type your question below.
                    </p>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(promptMessage);
        this.scrollToBottom();
    }

    /**
     * 发送建议的消息 / Send suggested message
     */
    sendSuggestedMessage(message) {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value = message;
            this.autoResizeTextarea(chatInput);
            this.updateSendButtonState();
            // 可选：自动发送，或者让用户点击发送按钮
            // this.handleSendMessage();
        }
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
}

// Initialize chat manager
const chatManager = new ChatManager();

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    chatManager.init();
});

// Export for global access
window.chatManager = chatManager; 