/**
 * JobCatcher Frontend - Main Application
 * AI-Powered Job Search Platform for Germany
 */

class JobCatcherApp {
    constructor() {
        this.API_BASE = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : 'https://obmscqebvxqz.eu-central-1.clawcloudrun.com';
        
        this.isAuthenticated = false;
        this.currentUser = null;
        this.isInitialized = false;
        
        // 等待DOM加载完成 / Wait for DOM to load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    async init() {
        if (this.isInitialized) return;
        
        console.log('Initializing JobCatcher App...');
        
        try {
            // 显示加载屏幕 / Show loading screen
            this.showLoadingScreen();
            
            // 初始化管理器 / Initialize managers
            this.initializeManagers();
            
            // 检查认证状态 / Check authentication status
            await this.checkAuthStatus();
            
            // 根据认证状态显示相应界面 / Show appropriate interface based on auth status
            if (this.isAuthenticated) {
                await this.showMainApp();
            } else {
                this.showLoginScreen();
            }
            
            this.isInitialized = true;
            console.log('JobCatcher App initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize app:', error);
            this.showError('Failed to initialize application. Please refresh the page.');
        } finally {
            // 隐藏加载屏幕 / Hide loading screen
            this.hideLoadingScreen();
        }
    }
    
    initializeManagers() {
        // 初始化认证管理器 / Initialize auth manager
        if (typeof AuthManager !== 'undefined' && !window.authManager) {
            window.authManager = new AuthManager();
        }

        // 创建职位管理器实例但不初始化 / Create jobs manager instance but don't initialize
        if (typeof JobsManager !== 'undefined' && !window.jobsManager) {
            window.jobsManager = new JobsManager();
        }
        
        // 初始化聊天管理器 / Initialize chat manager
        if (typeof ChatManager !== 'undefined' && !window.chatManager) {
            window.chatManager = new ChatManager();
        }
    }

    async checkAuthStatus() {
        try {
            const response = await fetch(`${this.API_BASE}/api/auth/verify`, {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.isAuthenticated = data.valid || false;
                this.currentUser = data.user || null;
                console.log('🔐 Auth status:', this.isAuthenticated ? 'Authenticated' : 'Not authenticated');
            } else {
                this.isAuthenticated = false;
                this.currentUser = null;
                console.log('🔐 Auth status: Not authenticated (401)');
            }
        } catch (error) {
            console.error('❌ Auth check failed:', error);
            this.isAuthenticated = false;
            this.currentUser = null;
        }
    }
    
    showLoadingScreen() {
        const loadingScreen = document.getElementById('loadingScreen');
        if (loadingScreen) {
            loadingScreen.style.display = 'flex';
        }
    }

    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loadingScreen');
        if (loadingScreen) {
            loadingScreen.style.display = 'none';
        }
    }
    
    showLoginScreen() {
        console.log('📱 Showing login screen');
        
        const loginScreen = document.getElementById('loginScreen');
        const mainApp = document.getElementById('mainApp');
        
        if (loginScreen) {
            loginScreen.style.display = 'flex';
        }
        if (mainApp) {
            mainApp.style.display = 'none';
            mainApp.classList.add('hidden');
        }
        
        // 绑定登录按钮事件 / Bind login button events
        this.bindLoginEvents();
    }
    
    async showMainApp() {
        console.log('📱 Showing main application');
        
        const loginScreen = document.getElementById('loginScreen');
        const mainApp = document.getElementById('mainApp');
        
        if (loginScreen) {
            loginScreen.style.display = 'none';
        }
        if (mainApp) {
            mainApp.style.display = 'block';
            mainApp.classList.remove('hidden');
        }

        // 初始化JobsManager（只在主应用显示时）/ Initialize JobsManager only when main app is shown
        if (window.jobsManager && !window.jobsManager.isInitialized) {
            window.jobsManager.initialize();
        }
        
        // 初始化ChatManager（只在主应用显示时）/ Initialize ChatManager only when main app is shown
        if (window.chatManager && !window.chatManager.isInitialized) {
            window.chatManager.init();
        }
        
        // 更新用户界面 / Update user interface
        this.updateUserInterface();
        
        // 绑定主应用事件 / Bind main app events
        this.bindMainAppEvents();
    }
    
    bindLoginEvents() {
        const googleLoginBtn = document.getElementById('googleLoginBtn');
        if (googleLoginBtn && !googleLoginBtn.hasAttribute('data-bound')) {
            googleLoginBtn.addEventListener('click', () => {
                if (window.authManager) {
                    window.authManager.handleGoogleLogin();
                }
            });
            googleLoginBtn.setAttribute('data-bound', 'true'); // 标记已绑定 / Mark as bound
        }
    }

    bindMainAppEvents() {
        // 绑定退出登录按钮 / Bind logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn && !logoutBtn.hasAttribute('data-bound')) {
            logoutBtn.addEventListener('click', () => {
                if (window.authManager) {
                    window.authManager.handleLogout();
                }
            });
            logoutBtn.setAttribute('data-bound', 'true'); // 标记已绑定 / Mark as bound
        }
        
        // 绑定其他主应用事件 / Bind other main app events
        this.bindNavigationEvents();
    }
    
    bindNavigationEvents() {
        // 可以在这里添加导航相关的事件绑定 / Add navigation event bindings here
        // 例如：标签页切换、侧边栏等 / For example: tab switching, sidebar, etc.
    }
    
    updateUserInterface() {
        // 更新用户信息显示 / Update user info display
        if (this.currentUser) {
            const userNameElement = document.getElementById('userName');
            const userAvatarElement = document.getElementById('userAvatar');
            
            if (userNameElement) {
                userNameElement.textContent = this.currentUser.name || this.currentUser.email || 'User';
            }
            
            if (userAvatarElement && this.currentUser.picture) {
                userAvatarElement.src = this.currentUser.picture;
                userAvatarElement.alt = this.currentUser.name || 'User Avatar';
            }
        }
    }
    
    showError(message) {
        console.error('🚨 App Error:', message);
        
        // 可以在这里显示错误通知 / Show error notification here
        const errorContainer = document.getElementById('errorContainer');
        if (errorContainer) {
            errorContainer.innerHTML = `
                <div class="error-message">
                    <p>${message}</p>
                    <button onclick="location.reload()">Refresh Page</button>
                </div>
            `;
            errorContainer.style.display = 'block';
        }
    }
    
    // 公共方法：重新检查认证状态 / Public method: recheck auth status
    async refreshAuthStatus() {
        await this.checkAuthStatus();
        
        if (this.isAuthenticated) {
            await this.showMainApp();
        } else {
            this.showLoginScreen();
        }
    }

    // 公共方法：获取当前用户 / Public method: get current user
    getCurrentUser() {
        return this.currentUser;
    }

    // 公共方法：检查是否已认证 / Public method: check if authenticated
    getAuthStatus() {
        return this.isAuthenticated;
    }
}

// 初始化应用 / Initialize application
window.app = new JobCatcherApp();