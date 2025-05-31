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
        
        console.log('🔧 Initializing JobsManager...');
        this.initializeElements();
        this.bindEvents();
        this.isInitialized = true;
        console.log('✅ JobsManager initialized successfully');
    }
    
    initializeElements() {
        this.searchBtn = document.getElementById('searchBtn');
        this.jobTitleInput = document.getElementById('jobTitle');
        this.locationInput = document.getElementById('location');
        this.jobsContainer = document.getElementById('jobsContainer');
        this.resultsCount = document.getElementById('resultsCount');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.noJobsMessage = document.getElementById('noJobsMessage');
    }
    
    bindEvents() {
        console.log('🔧 Binding JobsManager events...');
        
        // 绑定搜索按钮点击事件 / Bind search button click event
        if (this.searchBtn) {
            console.log('✅ Search button found, binding click event');
            
            // 移除之前的事件监听器（如果存在）/ Remove previous event listeners if any
            this.searchBtn.removeEventListener('click', this.handleJobSearchBound);
            
            // 绑定方法到this上下文 / Bind method to this context
            this.handleJobSearchBound = (e) => {
                console.log('🔍 Search button clicked');
                e.preventDefault();
                this.handleJobSearch();
            };
            
            this.searchBtn.addEventListener('click', this.handleJobSearchBound);
        } else {
            console.error('❌ Search button not found!');
        }
        
        // 绑定回车键搜索 / Bind Enter key search
        if (this.jobTitleInput) {
            console.log('✅ Job title input found, binding keypress event');
            
            // 移除之前的事件监听器 / Remove previous event listeners
            this.jobTitleInput.removeEventListener('keypress', this.handleJobTitleKeyPressBound);
            
            this.handleJobTitleKeyPressBound = (e) => {
                if (e.key === 'Enter') {
                    console.log('🔍 Enter key pressed in job title input');
                    e.preventDefault();
                    this.handleJobSearch();
                }
            };
            
            this.jobTitleInput.addEventListener('keypress', this.handleJobTitleKeyPressBound);
        } else {
            console.error('❌ Job title input not found!');
        }
        
        if (this.locationInput) {
            console.log('✅ Location input found, binding keypress event');
            
            // 移除之前的事件监听器 / Remove previous event listeners
            this.locationInput.removeEventListener('keypress', this.handleLocationKeyPressBound);
            
            this.handleLocationKeyPressBound = (e) => {
                if (e.key === 'Enter') {
                    console.log('🔍 Enter key pressed in location input');
                    e.preventDefault();
                    this.handleJobSearch();
                }
            };
            
            this.locationInput.addEventListener('keypress', this.handleLocationKeyPressBound);
        } else {
            console.error('❌ Location input not found!');
        }
        
        console.log('🔧 JobsManager events binding completed');
    }
    
    async handleJobSearch() {
        console.log('🚀 Starting job search...');

        if (this.isLoading) {
            console.log('⏳ Search already in progress, skipping...');
            return;
        }

        const jobTitle = this.jobTitleInput?.value?.trim();
        const location = this.locationInput?.value?.trim();
        
        console.log('📝 Search parameters:', { jobTitle, location });
        
        if (!jobTitle) {
            console.log('❌ No job title provided');
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
                    job_title: jobTitle,  // 修正字段名：query -> job_title
                    location: location || null,
                    max_results: 25  // 修正字段名：limit -> max_results
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
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'block';
        }
        if (this.jobsContainer) {
            this.jobsContainer.style.display = 'none';
        }
        if (this.noJobsMessage) {
            this.noJobsMessage.style.display = 'none';
        }
    }
    
    hideLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'none';
        }
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

        // 按相关性排序 Sort by relevance
        jobs.sort((a, b) => {
            // 可以根据需要添加排序逻辑 Add sorting logic as needed
            return 0;
        });

        const jobsHTML = jobs.map(job => this.createJobCard(job)).join('');

        this.jobsContainer.innerHTML = jobsHTML;
        this.jobsContainer.style.display = 'block';
        
        if (this.noJobsMessage) {
            this.noJobsMessage.style.display = 'none';
    }

        // 绑定事件 Bind events
        this.bindJobCardEvents();
    }
    
    createJobCard(job) {
        const description = job.description || 'No description available';
        const truncatedDescription = description.length > 150 
            ? description.substring(0, 150) + '...' 
            : description;
        
        // 根据README要求，只显示办公形式(work_type)标签 / According to README, only show work_type tag
        const workTypeTag = job.work_type ? 
            `<span class="tag work-type">${job.work_type}</span>` : '';

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
                    </div>
                </div>
                
                ${workTypeTag ? `
                <div class="job-tags">
                    ${workTypeTag}
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
                        <div class="description-text">${description}</div>
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
            this.jobsContainer.style.display = 'none';
        }
        if (this.noJobsMessage) {
            this.noJobsMessage.style.display = 'block';
    }
    }
    
    showError(message) {
        if (this.jobsContainer) {
            this.jobsContainer.innerHTML = `
                <div class="error-message">
                    <p>${message}</p>
            </div>
        `;
            this.jobsContainer.style.display = 'block';
        }
    }
}

// 导出到全局作用域 Export to global scope
window.JobsManager = JobsManager; 