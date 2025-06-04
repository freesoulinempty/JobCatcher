/**
 * JobCatcher Frontend - Jobs Management
 * Handles job search, display, and interactions
 */

class JobsManager {
    constructor() {
        this.API_BASE = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : 'https://obmscqebvxqz.eu-central-1.clawcloudrun.com';
        
        this.currentJobs = [];
        this.isLoading = false;
        this.isInitialized = false; // 防止重复初始化 / Prevent duplicate initialization
        
        // 不自动初始化，等待app.js调用 / Don't auto-initialize, wait for app.js to call
    }
    
    initialize() {
        if (this.isInitialized) {
            console.log('⚠️ JobsManager already initialized, skipping...');
            return;
        }
        
        this.initializeElements();
        this.bindEvents();
        this.isInitialized = true;
        console.log('JobsManager initialized successfully');
    }
    
    initializeElements() {
        this.searchBtn = document.getElementById('searchBtn');
        this.jobTitleInput = document.getElementById('jobTitle');
        this.locationInput = document.getElementById('location');
        this.jobsContainer = document.getElementById('jobsContainer');
        this.resultsCount = document.getElementById('resultsCount');
    }
    
    bindEvents() {
        // 绑定搜索按钮点击事件 / Bind search button click event
        if (this.searchBtn) {
            
            // 移除之前的事件监听器（如果存在）/ Remove previous event listeners if any
            this.searchBtn.removeEventListener('click', this.handleJobSearchBound);
            
            // 绑定方法到this上下文 / Bind method to this context
            this.handleJobSearchBound = (e) => {
                e.preventDefault();
                this.handleJobSearch();
            };
            
            this.searchBtn.addEventListener('click', this.handleJobSearchBound);
        } else {
            console.error('❌ Search button not found!');
        }
        
        // 绑定回车键搜索 / Bind Enter key search
        if (this.jobTitleInput) {
            
            // 移除之前的事件监听器 / Remove previous event listeners
            this.jobTitleInput.removeEventListener('keypress', this.handleJobTitleKeyPressBound);
            
            this.handleJobTitleKeyPressBound = (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleJobSearch();
                }
            };
            
            this.jobTitleInput.addEventListener('keypress', this.handleJobTitleKeyPressBound);
        } else {
            console.error('❌ Job title input not found!');
        }
        
        if (this.locationInput) {
            
            // 移除之前的事件监听器 / Remove previous event listeners
            this.locationInput.removeEventListener('keypress', this.handleLocationKeyPressBound);
            
            this.handleLocationKeyPressBound = (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleJobSearch();
                }
            };
            
            this.locationInput.addEventListener('keypress', this.handleLocationKeyPressBound);
        } else {
            console.error('❌ Location input not found!');
        }
        

    }
    
    async handleJobSearch() {
        if (this.isLoading) return;

        const jobTitle = this.jobTitleInput?.value?.trim();
        const location = this.locationInput?.value?.trim();
        
        if (!jobTitle) {
            alert('Please enter a job title');
            return;
        }
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const response = await fetch(`${this.API_BASE}/api/jobs/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    keywords: jobTitle,  // 🔥 修正字段名：使用keywords / Fixed field name: use keywords
                    city: location || null,  // 🔥 修正字段名：使用city / Fixed field name: use city
                    max_results: 25
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            // 后端返回 {jobs: [...], total_count: N} 格式 Backend returns {jobs: [...], total_count: N} format
            const jobs = data.jobs || [];
            
            this.currentJobs = jobs;
            this.displayJobs(jobs);

        } catch (error) {
            console.error('Job search failed:', error);
            this.showError('Failed to search jobs. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    showLoading() {
        if (this.jobsContainer) {
            this.jobsContainer.innerHTML = '<div class="loading-message">Searching jobs...</div>';
        }
    }
    
    hideLoading() {
        // Loading will be replaced by actual results or error message
    }
    
    displayJobs(jobs) {
        if (!this.jobsContainer) return;
        
        // 确保jobs是数组 Ensure jobs is an array
        if (!Array.isArray(jobs)) {
            console.warn('Jobs data is not an array:', jobs);
            jobs = [];
        }
        
        // 更新结果计数 / Update results count
        if (this.resultsCount) {
            const count = jobs.length;
            this.resultsCount.textContent = `${count} job${count !== 1 ? 's' : ''} found`;
        }

        if (jobs.length === 0) {
            this.showNoJobs();
            return;
        }



        const jobsHTML = jobs.map(job => this.createJobCard(job)).join('');

        this.jobsContainer.innerHTML = jobsHTML;

        // 绑定事件 Bind events
        this.bindJobCardEvents();
    }
    
    createJobCard(job) {
        // 🔥 优先使用full_description，回退到description / Prioritize full_description, fallback to description
        const fullDescription = job.full_description || job.description || 'No description available';
        const shortDescription = job.description || fullDescription || 'No description available';
        
        // 🔥 创建简短描述用于预览 / Create short description for preview
        const truncatedDescription = shortDescription.length > 200 
            ? shortDescription.substring(0, 200) + '...' 
            : shortDescription;
        
        // 🔥 移除匹配度显示 / Remove match score display
        const relevanceScore = '';
        
        // 根据README要求，显示办公形式和薪资信息 / According to README, show work_type and salary info  
        const workTypeTag = job.work_type ? 
            `<span class="simple-tag">${job.work_type}</span>` : '';
        const salaryTag = job.salary ? 
            `<span class="simple-tag">${job.salary}</span>` : '';

        return `
            <div class="job-card" data-job-id="${job.id}">
                <div class="job-header">
                    <h3 class="job-title">${job.title}</h3>
                    <div class="job-meta">
                        <span class="company">
                            <i class="fas fa-building"></i>
                            ${job.company_name}
                        </span>
                        <span class="location">
                            <i class="fas fa-map-marker-alt"></i>
                            ${job.location}
                        </span>
                        ${relevanceScore}
                    </div>
                </div>
                
                ${workTypeTag || salaryTag ? `
                <div class="job-tags">
                    ${workTypeTag}
                    ${salaryTag}
                </div>
                ` : ''}
                
                <div class="job-description">
                    <p>${truncatedDescription}</p>
                </div>
                
                <div class="job-actions">
                    <button class="job-action-btn show-details" data-job-id="${job.id}">
                        <i class="fas fa-info-circle"></i>
                        Show Details
                    </button>
                    <a href="${job.url}" target="_blank" class="job-action-btn apply-btn">
                        <i class="fas fa-external-link-alt"></i>
                        Apply Now
                    </a>
                </div>
                
                <div class="job-full-description" style="display: none;">
                    <div class="full-description-content">
                        <h4><i class="fas fa-file-alt"></i> Complete Job Description</h4>
                        <div class="description-text">${fullDescription}</div>
                        ${job.posted_date ? 
                            `<div class="job-info">
                                <strong><i class="fas fa-calendar"></i> Posted:</strong> ${job.posted_date}
                            </div>` 
                            : ''
                        }
                        ${job.apply_url && job.apply_url !== job.url ? 
                            `<div class="apply-info">
                                <strong><i class="fas fa-link"></i> Direct Application Link:</strong> 
                                <a href="${job.apply_url}" target="_blank">${job.apply_url}</a>
                            </div>` 
                            : ''
                        }
                    </div>
                </div>
            </div>
        `;
    }

    bindJobCardEvents() {
        // 绑定"Show Details"按钮事件 Bind "Show Details" button events
        const detailButtons = document.querySelectorAll('.show-details');
        detailButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const jobId = e.target.getAttribute('data-job-id');
                this.toggleJobDetails(jobId);
            });
        });
    }
    
    toggleJobDetails(jobId) {
        const jobCard = document.querySelector(`[data-job-id="${jobId}"]`);
        if (!jobCard) return;
        
        const fullDescription = jobCard.querySelector('.job-full-description');
        const button = jobCard.querySelector('.show-details');
        
        if (fullDescription.style.display === 'none') {
            fullDescription.style.display = 'block';
            button.textContent = 'Hide Details';
        } else {
            fullDescription.style.display = 'none';
            button.textContent = 'Show Details';
        }
    }
    
    showNoJobs() {
        if (this.jobsContainer) {
            this.jobsContainer.innerHTML = '<div class="no-jobs-message">No jobs found. Try different keywords or location.</div>';
        }
    }
    
    showError(message) {
        if (this.jobsContainer) {
            this.jobsContainer.innerHTML = `<div class="error-message">${message}</div>`;
        }
    }
}

// 导出到全局作用域 Export to global scope
window.JobsManager = JobsManager; 