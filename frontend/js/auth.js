/**
 * JobCatcher Frontend - Authentication Handler
 * Google OAuth 2.0 Integration
 */

class AuthManager {
    constructor() {
        this.API_BASE = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : 'https://obmscqebvxqz.eu-central-1.clawcloudrun.com';
        
        // 绑定方法到实例 / Bind methods to instance
        this.handleGoogleLogin = this.handleGoogleLogin.bind(this);
        this.setLoginButtonLoading = this.setLoginButtonLoading.bind(this);
        this.showAuthError = this.showAuthError.bind(this);
        this.hideAuthError = this.hideAuthError.bind(this);
    }

    /**
     * Initialize Google Sign-In
     */
    initGoogleAuth() {
        // Load Google Platform Library
        if (typeof gapi !== 'undefined') {
            gapi.load('auth2', () => {
                gapi.auth2.init({
                    client_id: this.getGoogleClientId()
                });
            });
        }
    }

    /**
     * Get Google Client ID from meta tag
     */
    getGoogleClientId() {
        const meta = document.querySelector('meta[name="google-signin-client_id"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /**
     * Handle Google OAuth login
     */
    async handleGoogleLogin() {
        try {
            console.log('🔐 Starting Google OAuth login...');
            
            // Show loading state
            this.setLoginButtonLoading(true);

            // Get OAuth authorization URL from backend
            const response = await fetch(`${this.API_BASE}/api/auth/login`, {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Got OAuth URL, redirecting to Google...');
                
                // Redirect to Google OAuth
                window.location.href = data.authorization_url;
            } else {
                throw new Error('Failed to get OAuth URL');
            }
        } catch (error) {
            console.error('❌ Google login failed:', error);
            this.setLoginButtonLoading(false);
            this.showAuthError('Login failed. Please try again.');
        }
    }

    /**
     * Handle OAuth callback (called by backend redirect)
     */
    async handleOAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        const error = urlParams.get('error');

        if (error) {
            this.showAuthError(decodeURIComponent(error));
            return false;
        }

        if (token) {
            // Store token if needed (backend handles cookies)
            localStorage.setItem('auth_token', token);
            
            // Redirect to main app
            window.location.href = '/';
            return true;
        }

        return false;
    }

    /**
     * Check if user is authenticated
     */
    async isAuthenticated() {
        try {
            const response = await fetch(`${this.API_BASE}/api/auth/verify`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                if (result.authenticated) {
                    // 获取用户资料 Get user profile
                    const profileResponse = await fetch(`${this.API_BASE}/api/auth/profile`, {
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (profileResponse.ok) {
                        const user = await profileResponse.json();
                        return { authenticated: true, user };
                    }
                }
                return { authenticated: false, user: null };
            } else {
                return { authenticated: false, user: null };
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            return { authenticated: false, user: null };
        }
    }

    /**
     * Logout user
     */
    async handleLogout() {
        try {
            console.log('🔐 Logging out...');
            
            const response = await fetch(`${this.API_BASE}/api/auth/logout`, {
                method: 'POST',
                credentials: 'include'
            });

            // Clear local storage
            localStorage.removeItem('auth_token');
            
            // Redirect to login page
            window.location.reload();
            return true;
        } catch (error) {
            console.error('❌ Logout failed:', error);
            return false;
        }
    }

    /**
     * Get current user info
     */
    async getCurrentUser() {
        try {
            const response = await fetch(`${this.API_BASE}/api/auth/profile`, {
                credentials: 'include'
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('Failed to get user info');
            }
        } catch (error) {
            console.error('Get user failed:', error);
            return null;
        }
    }

    /**
     * Refresh authentication token
     */
    async refreshToken() {
        try {
            const response = await fetch(`${this.API_BASE}/api/auth/refresh`, {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('auth_token', data.token);
                return true;
            } else {
                throw new Error('Failed to refresh token');
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
            return false;
        }
    }

    /**
     * Set login button loading state
     */
    setLoginButtonLoading(loading) {
        const loginBtn = document.getElementById('googleLoginBtn');
        if (loginBtn) {
            if (loading) {
                loginBtn.style.opacity = '0.7';
                loginBtn.style.pointerEvents = 'none';
                
                // Change text to show loading
                const span = loginBtn.querySelector('span');
                if (span) {
                    span.textContent = 'Connecting...';
                }
                
                // Add loading spinner
                const icon = loginBtn.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-spinner fa-spin';
                }
            } else {
                loginBtn.style.opacity = '1';
                loginBtn.style.pointerEvents = 'auto';
                
                // Reset text
                const span = loginBtn.querySelector('span');
                if (span) {
                    span.textContent = 'Continue with Google';
                }
                
                // Reset icon
                const icon = loginBtn.querySelector('i');
                if (icon) {
                    icon.className = 'fab fa-google';
                }
            }
        }
    }

    /**
     * Show authentication error message
     */
    showAuthError(message) {
        console.error('🚨 Auth Error:', message);
        
        // Create or update error message element
        let errorElement = document.getElementById('authError');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.id = 'authError';
            errorElement.className = 'auth-error';
            
            // Insert after login button
            const loginBtn = document.getElementById('googleLoginBtn');
            if (loginBtn && loginBtn.parentNode) {
                loginBtn.parentNode.insertBefore(errorElement, loginBtn.nextSibling);
            }
        }
        
        errorElement.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>${message}</span>
        `;
        errorElement.style.display = 'flex';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorElement) {
                errorElement.style.display = 'none';
            }
        }, 5000);
    }

    /**
     * Hide authentication error message
     */
    hideAuthError() {
        const errorElement = document.getElementById('authError');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
}