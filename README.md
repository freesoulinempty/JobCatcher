# JobCatcher 前后端开发文档 / JobCatcher Frontend & Backend Development Documentation

## 项目概述 / Project Overview

JobCatcher 是一个基于Claude 4 Sonnet驱动的智能职位搜索和匹配平台，专注于德国就业市场，充分利用AI原生能力，最小化代码开发，全流程vibe coding使用cursor开发。

JobCatcher is an AI-powered intelligent job search and matching platform driven by Claude 4 Sonnet, focused on the German job market, leveraging AI-native capabilities to minimize code development, vibe coding with Cursor.

## 技术架构 / Technology Architecture

### 核心AI引擎 / Core AI Engine
- **Claude 4 Sonnet** - 主要AI模型 / Primary AI model
  - 混合推理模式（即时响应 + 深度思考） / Hybrid reasoning mode (instant response + deep thinking)
  - 先进的编程能力 / Advanced programming capabilities
  - 增强的工具使用和并行处理 / Enhanced tool usage and parallel processing
  - 改进的指令遵循和记忆能力 / Improved instruction following and memory capabilities
  - 原生WebSearch / Native WebSearch

### 后端技术栈 / Backend Technology Stack
- **FastAPI** (0.115.0+) - 高性能Web框架 / High-performance web framework
- **LangChain** (0.3.25+) - LLM应用开发框架 / LLM application development framework
- **Pydantic** (2.7.0+) - 数据验证 / Data validation
- **RAG** - 向量检索 / Vector retrieval
- **SQLite** - 用户session存储 / User session storage
- **Chroma** - 向量存储职位数据 / Vector storage for job data

### 前端技术栈 / Frontend Technology Stack
- **HTML5** - 语义化结构 / Semantic structure
- **CSS3** - 现代样式设计(Grid/Flexbox布局) / Modern styling design (Grid/Flexbox layout)
- **JavaScript ES6+** - 交互逻辑和API调用 / Interactive logic and API calls
- **响应式设计** - 支持桌面/平板/移动端 / Responsive design - desktop/tablet/mobile support
- **Google OAuth** - 用户认证 / User authentication

## 前端开发规范 / Frontend Development Standards

### 界面布局设计 / Interface Layout Design

#### 主界面结构 / Main Interface Structure
- **Google OAuth 2.0登录页** / **Google OAuth 2.0 Login Page**: 首页登录后进入主界面 / Entry page, enter main interface after login
- **左右分栏设计(50%:50%)** / **Left-Right Split Design (50%:50%)**:
  - **左侧职位展示区域** / **Left Side Job Display Area**:
    - 职位搜索栏,城市搜索栏(都在同一行) / Job search bar, city search bar (on the same row)
    - 下方职位数据展示区域(岗位卡片)，支持上下滚动 / Job data display area below (job cards), supports vertical scrolling
    - 显示职位基本信息(岗位名称、公司名称、工作地点、办公形式、岗位详情链接、岗位详情) / Display basic job info (job title, company name, location, work type, job link, job description)
    - 点击"show detail"当前岗位卡片展开展示详细信息 / Click "show detail" to expand current job card for detailed info
    - 点击职位可跳转到对应的外部职位详情链接 / Click job to jump to corresponding external job detail link
  - **右侧AI聊天区域** / **Right Side AI Chat Area**:
    - 智能聊天框,支持简历上传和AI对话(流式输出) / Smart chat box, supports resume upload and AI conversation (streaming output)
    - 实时显示简历分析结果和优化建议 / Real-time display of resume analysis results and optimization suggestions
    - 支持技能热点图生成和职位咨询 / Supports skills heatmap generation and job consultation

#### UI设计要求 / UI Design Requirements
- **界面语言** / **Interface Language**: 所有界面语言为英语 / All UI text in English
- **设计风格** / **Design Style**: 简洁清爽的界面风格 / Clean and refreshing interface style
- **视觉效果** / **Visual Effects**: 艺术化渐变和动画效果，浮动效果 / Artistic gradients and animation effects, floating effects
- **响应式设计** / **Responsive Design**: 适配各种设备 / Adapt to various devices

### 前端功能实现 / Frontend Feature Implementation

#### 用户认证 / User Authentication
- 集成Google OAuth 2.0登录 / Integrate Google OAuth 2.0 login
- 用户会话管理 / User session management
- 登录状态维护 / Login state maintenance

#### 职位搜索界面 / Job Search Interface
- 职位搜索栏和城市搜索栏布局(同一行) / Job search bar and city search bar layout (same row)
- 职位卡片展示组件 / Job card display component
- 职位详情展开/收起功能 / Job detail expand/collapse functionality
- 外部链接跳转处理 / External link jump handling
- 上下滚动加载 / Vertical scroll loading

#### AI聊天界面 / AI Chat Interface
- 文件上传组件(支持PDF/DOC/TXT) / File upload component (supports PDF/DOC/TXT)
- 流式对话输出 / Streaming conversation output
- 消息历史记录 / Message history records
- 技能热点图展示 / Skills heatmap display

## 后端开发规范 / Backend Development Standards

### API架构设计 / API Architecture Design

#### 核心接口 / Core Interfaces
1. **用户认证接口** / **User Authentication Interface**
   - Google OAuth验证 / Google OAuth verification
   - 用户会话管理 / User session management
   - 登录状态检查 / Login state checking

2. **职位搜索接口** / **Job Search Interface**
   - 职位关键词+城市进行搜索 / Job keywords + city search
   - 搜索结果返回 / Search results return

3. **简历处理接口** / **Resume Processing Interface**
   - 文件上传处理 / File upload handling
   - 简历解析 / Resume parsing
   - 向量化存储 / Vectorization storage

4. **AI对话接口** / **AI Conversation Interface**
   - 流式对话响应 / Streaming conversation response
   - Claude 4 Sonnet集成 / Claude 4 Sonnet integration
   - 技能热点图生成 / Skills heatmap generation

### 数据源集成 / Data Source Integration

#### Apify LinkedIn爬虫 / Apify LinkedIn Scraper
- **Actor ID**: `valig/linkedin-jobs-scraper`
- **支持网站** / **Supported Website**: LinkedIn.de
- **定时爬取** / **Scheduled Crawling**: 每日定时爬取预设岗位的数据,只根据岗位名称爬取,城市名称为空,每个岗位50条(按照相关性)(发布时间7天内) / Daily scheduled crawling of preset job data, crawl only by job title, empty city name, 50 jobs per title (by relevance) (published within 7 days)
- **预设岗位** / **Preset Jobs**: "engineer","manager","IT","Finance","Sales","Nurse","Consultant","software developer","python","java"
- **成本** / **Cost**: €0.01/次调用(50个岗位) ; 定时爬取成本: €0.01 * 10 * 30 = €3 /月 / €0.01/call (50 jobs); Scheduled crawling cost: €0.01 * 10 * 30 = €3/month
- **最新开发文档** / **Latest Development Documentation**: https://docs.apify.com/api/client/python/docs/overview/introduction
- **input格式** / **Input Format**:
```python
{
  "limit": ,
  "location": "Germany",
  "proxy": {
    "useApifyProxy": true,
    "apifyProxyGroups": [
      "RESIDENTIAL"
    ]
  },
  "title": "python"
}
```
- **output格式** / **Output Format**:
```python
[{
  "id": "4239505508",
  "url": "https://de.linkedin.com/jobs/view/junior-ai-engineer-m-w-d-at-ki-performance-gmbh-4239505508",
  "title": "Junior AI Engineer (m/w/d)",
  "location": "Munich, Bavaria, Germany",
  "companyName": "KI performance GmbH",
  "companyUrl": "https://de.linkedin.com/company/ki-performance-gmbh",
  "recruiterName": "",
  "recruiterUrl": "",
  "experienceLevel": "Mid-Senior level",
  "contractType": "Full-time",
  "workType": "Information Technology",
  "sector": "IT Services and IT Consulting",
  "salary": "",
  "applyType": "EXTERNAL",
  "applyUrl": "https://kigroup.recruitee.com/o/junior-ai-engineer-mwd/c/new?source=LinkedIn+Basic+Jobs",
  "postedTimeAgo": "3 weeks ago",
  "postedDate": "2025-05-03T00:00:00.000Z",
  "applicationsCount": "Be among the first 25 applicants",
  "description": "this is the description"
}]
```

#### Zyte API爬虫 / Zyte API Scraper
- **支持网站** / **Supported Website**: Indeed.de
- **定时爬取** / **Scheduled Crawling**: 每天定时爬取,只根据岗位名称爬取,城市名称为空,每个岗位25条数据 / Daily scheduled crawling, crawl only by job title, empty city name, 25 jobs per title
- **预设岗位名称** / **Preset Job Titles**: "Web","cloud","AI","Data","software"
- **成本** / **Cost**: €0.001/次调用,€0.001 * 26 * 5 * 30 = €4 /月 / €0.001/call, €0.001 * 26 * 5 * 30 = €4/month
- **注意** / **Note**: 先爬取岗位列表,再爬取岗位详情,速度很慢,需要留够等待时间或者异步处理 / First crawl job list, then crawl job details, very slow, need sufficient wait time or async processing
- **最新开发文档** / **Latest Development Documentation**: https://docs.zyte.com/zyte-api/usage/reference.html

### 数据存储方案 / Data Storage Solution

#### SQLite
- 用户session存储 / User session storage
- 用户认证信息管理 / User authentication information management

#### Chroma向量数据库 / Chroma Vector Database
- 向量存储和检索职位数据 / Vector storage and retrieval of job data
- 简历向量化存储 / Resume vectorization storage
- 相似度匹配查询 / Similarity matching queries
- text-embedding-3-small

#### 数据清理机制 / Data Cleaning Mechanism
- **定时清理** / **Scheduled Cleaning**: 每天定时访问Chroma中所有岗位URL,如果URL失效则清理 / Daily scheduled access to all job URLs in Chroma, clean if URL is invalid
- **僵尸岗位清理** / **Zombie Job Cleaning**: 清理14天之前的岗位数据,防止僵尸岗位 / Clean job data from 14 days ago to prevent zombie jobs

## 核心业务流程 / Core Business Workflows

### 用户搜索流程 / User Search Workflow
1. 用户在主页搜索栏搜索"岗位名称"+"地点" / User searches "job title" + "location" in main page search bar
2. 后端把"岗位名称"+"地点"向量信息作为查询,检索Chroma最相似岗位 / Backend uses "job title" + "location" vector info as query, retrieves most similar jobs from Chroma
3. 发送给前端并展示(岗位名称,公司名称,工作地点,办公方式,岗位详情链接,岗位描述) / Send to frontend and display (job title, company name, location, work type, job detail link, job description)

### 职位推荐流程 / Job Recommendation Workflow
1. 用户在对话框上传简历 → 前端接受 → 后端接收发送给agent / User uploads resume in chat box → Frontend accepts → Backend receives and sends to agent
2. agent使用claude4原生能力解析pdf,提取关键信息(地点,技能,学历,经历,语言等) / Agent uses Claude 4 native capabilities to parse PDF, extract key information (location, skills, education, experience, languages, etc.)
3. embedding向量化 → 存入Chroma(存入时去重,避免Chroma内有重复岗位) / Embedding vectorization → Store in Chroma (deduplicate when storing to avoid duplicate jobs in Chroma)
4. 用户简历向量信息(地点,技能,学历,经历,语言)作为查询,检索Chroma最相似岗位(返回岗位数量25个) / User resume vector info (location, skills, education, experience, languages) as query, retrieve most similar jobs from Chroma (return 25 jobs)
5. 后端把Claude4生成的用户简历分析结果+Chroma匹配到的岗位数据拼接为一个prompt / Backend concatenates Claude 4 generated user resume analysis results + Chroma matched job data into one prompt
6. 后端把prompt发送给claude进行分析岗位和排序 / Backend sends prompt to Claude for job analysis and ranking
7. 前端bot聊天机器人发送信息 / Frontend bot chatbot sends message
8. 后端获取claude4排序后的岗位数据 → 后端把岗位数据发送给前端(岗位名称、公司名称、工作地点、办公形式、岗位详情链接、岗位详情描述) / Backend gets Claude 4 ranked job data → Backend sends job data to frontend (job title, company name, location, work type, job detail link, job detail description)
9. 前端把岗位放在左侧岗位展示区(按照匹配度从上到下) / Frontend places jobs in left job display area (by matching score from top to bottom)

### 简历和岗位匹配机制 / Resume and Job Matching Mechanism
- **匹配主导者** / **Matching Leader**: RAG根据简历向量信息进行初匹配,claude4采纳"匹配要素"进行深度思考(thinking)进行匹配 / RAG performs initial matching based on resume vector info, Claude 4 adopts "matching factors" for deep thinking matching
- **匹配要素** / **Matching Factors**: 
  - 地点(中等重要) / Location (medium importance)
  - 技能(重要) / Skills (important)
  - 学历(不是很重要) / Education (not very important)
  - 经历(重要) / Experience (important)
  - 语言(中等重要) / Languages (medium importance)

## Claude 4 Sonnet Agent系统 / Claude 4 Sonnet Agent System

### 统一Agent处理功能 / Unified Agent Processing Functions
- 利用Claude 4的原生文档理解能力深度分析简历 / Leverage Claude 4's native document understanding capabilities for deep resume analysis
- 提供简历优化建议、技术栈建议、学习建议 / Provide resume optimization suggestions, tech stack recommendations, learning advice
- 基于简历分析结果推荐最匹配的25个岗位 / Recommend top 25 matching jobs based on resume analysis results
- 推荐岗位按匹配度排序显示在左侧展示区域 / Recommended jobs ranked by matching score displayed in left display area
- 生成岗位技能热点图(claude4原生WebSearch功能搜索岗位热点技能并进行深度思考(thinking),后调用Artifacts工具生成技能热点图片) / Generate job skills heatmap (Claude 4 native WebSearch searches for trending job skills and performs deep thinking, then calls Artifacts tool to generate skills heatmap)
- 生成技能热点图和个性化学习建议 / Generate skills heatmap and personalized learning recommendations
- 提供德国就业市场咨询和职业指导(claude4原生WebSearch功能搜索就业市场信息) / Provide German job market consultation and career guidance (Claude 4 native WebSearch searches for employment market information)
- 支持中文和德语和英语三语交流 / Support trilingual communication in Chinese, German, and English
- 回答岗位技术栈和要求相关问题 / Answer questions about job tech stacks and requirements

### AI驱动的个性化服务 / AI-Driven Personalized Services
- **智能简历分析** / **Intelligent Resume Analysis**: 
  - Claude 4原生PDF/DOC/TXT文档处理能力 / Claude 4 native PDF/DOC/TXT document processing capabilities
  - 分析后通过聊天框返回详细分析结果 / Return detailed analysis results through chat box after analysis
  - 提供优化建议和技术栈建议 / Provide optimization suggestions and tech stack recommendations
- **精准职位匹配** / **Precise Job Matching**: 基于语义理解的匹配度评分 / Matching score based on semantic understanding
- **技能差距分析** / **Skills Gap Analysis**: AI驱动的技能评估和热点图生成 / AI-driven skill assessment and heatmap generation
- **学习路径推荐** / **Learning Path Recommendations**: 个性化职业发展建议(claude4原生WebSearch功能搜索岗位技能以及此职业当前火热的学习路线) / Personalized career development advice (Claude 4 native WebSearch searches for job skills and current trending learning paths for this profession)
- **职位技术栈分析** / **Job Tech Stack Analysis**: 针对特定岗位生成技能要求热点图(claude4原生WebSearch功能搜索岗位技能以及此职业当前火热的要求以及技术栈) / Generate skill requirement heatmap for specific positions (Claude 4 native WebSearch searches for job skills and current trending requirements and tech stacks for this profession)

## 安全与隐私 / Security and Privacy

### 安全认证 / Security Authentication
- Google OAuth 2.0 登录 / Google OAuth 2.0 login
- 用户会话管理 / User session management
- 数据隐私保护 / Data privacy protection

## 环境要求 / Environment Requirements

### Python依赖 / Python Dependencies
```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
langchain>=0.3.25
langchain-anthropic>=0.1.0
chromadb>=0.5.0
anthropic>=0.52.0
apify-client>=1.10.0
zyte-api>=0.7.0
sqlalchemy>=2.0.30
aiosqlite>=0.20.0
python-multipart>=0.0.20
python-jose[cryptography]>=3.4.0
python-dotenv>=1.0.0
requests>=2.32.0
httpx>=0.27.0
PyPDF2>=3.0.1
python-docx>=1.1.0
passlib[bcrypt]>=1.7.4
google-auth-oauthlib>=1.2.0
```

### 环境变量配置 / Environment Variable Configuration
```
ANTHROPIC_API_KEY=your_claude_api_key
APIFY_API_TOKEN=your_apify_token
ZYTE_API_KEY=your_zyte_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///./jobcatcher.db
CHROMA_DB_PATH=./data/chroma_db
```

## 启动说明 / Startup Instructions

### 后端启动 / Backend Startup
```bash
# 进入后端目录 / Enter backend directory
cd JobCatcher/backend

# 激活虚拟环境 / Activate virtual environment
source ../../bin/activate

# 设置PYTHONPATH / Set PYTHONPATH
export PYTHONPATH=/home/devbox/project/JobCatcher/backend:$PYTHONPATH

# 启动后端服务 / Start backend service
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动 / Frontend Startup
```bash
# 进入前端目录 / Enter frontend directory
cd JobCatcher/frontend

# 启动前端服务 / Start frontend service
python -m http.server 7860
```

## 开发注意事项 / Development Notes

### 代码规范 / Code Standards
- 所有代码注释使用中英双语 / All code comments use Chinese and English bilingual
- 界面语言统一使用英语 / Interface language uniformly uses English
- 严格按照README要求开发，不添加额外功能 / Strictly develop according to README requirements, do not add extra features
- 遵循FastAPI和现代Python开发最佳实践 / Follow FastAPI and modern Python development best practices

### 测试和部署 / Testing and Deployment
- 开发过程中不创建测试断点 / Do not create test breakpoints during development
- 所有功能在主流程中完成 / All functions completed in main workflow
- 及时读取并解决终端报错 / Timely read and resolve terminal errors
- 确保服务启动前检查端口占用 / Ensure port occupation check before service startup
