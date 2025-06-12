# JobCatcher Frontend & Backend Development Documentation


https://github.com/user-attachments/assets/4bf811ad-2bf0-4b8f-83f4-bf8b48df008f


## Project Overview

JobCatcher is an AI-powered intelligent job search and matching platform driven by Claude 4 Sonnet, focused on the German job market, leveraging AI-native capabilities to minimize code development, vibe coding with Cursor.
(To be improved: 1. job recommendation process: jobs cannot be recommended without user request 2. Skills heatmap: the returned content should be an HTML rendered web page, not information sent by the bot 3. The number of jobs is not enough 4. The token consumption is too high).

## Technology Architecture

### Core AI Engine
- **Claude 4 Sonnet** - Primary AI model
  - Hybrid reasoning mode (instant response + deep thinking)
  - Advanced programming capabilities
  - Enhanced tool usage and parallel processing
  - Improved instruction following and memory capabilities
  - Native WebSearch

### Backend Technology Stack
- **FastAPI** (0.115.0+) - High-performance web framework
- **LangChain** (0.3.25+) - LLM application development framework
- **Pydantic** (2.7.0+) - Data validation
- **RAG** - Vector retrieval
- **SQLite** - User session storage
- **Chroma** - Vector storage for job data

### Frontend Technology Stack
- **HTML5** - Semantic structure
- **CSS3** - Modern styling design (Grid/Flexbox layout)
- **JavaScript ES6+** - Interactive logic and API calls
- **Responsive design** - Desktop/tablet/mobile support
- **Google OAuth** - User authentication

## Frontend Development Standards

### Interface Layout Design

#### Main Interface Structure
- **Google OAuth 2.0 Login Page**: Entry page, enter main interface after login
- **Left-Right Split Design (50%:50%)**:
  - **Left Side Job Display Area**:
    - Job search bar, city search bar (on the same row)
    - Job data display area below (job cards), supports vertical scrolling
    - Display basic job info (job title, company name, location, work type, job link, job description)
    - Click "show detail" to expand current job card for detailed info
    - Click job to jump to corresponding external job detail link
  - **Right Side AI Chat Area**:
    - Smart chat box, supports resume upload and AI conversation (streaming output)
    - Real-time display of resume analysis results and optimization suggestions
    - Supports skills heatmap generation and job consultation

#### UI Design Requirements
- **Interface Language**: All UI text in English
- **Design Style**: Clean and refreshing interface style
- **Visual Effects**: Artistic gradients and animation effects, floating effects
- **Responsive Design**: Adapt to various devices

### Frontend Feature Implementation

#### User Authentication
- Integrate Google OAuth 2.0 login
- User session management
- Login state maintenance

#### Job Search Interface
- Job search bar and city search bar layout (same row)
- Job card display component
- Job detail expand/collapse functionality
- External link jump handling
- Vertical scroll loading

#### AI Chat Interface
- File upload component (supports PDF/DOC/TXT)
- Streaming conversation output
- Message history records
- Skills heatmap display

## Backend Development Standards

### API Architecture Design

#### Core Interfaces
1. **User Authentication Interface**
   - Google OAuth verification
   - User session management
   - Login state checking

2. **Job Search Interface**
   - Job keywords + city search
   - Search results return

3. **Resume Processing Interface**
   - File upload handling
   - Resume parsing
   - Vectorization storage

4. **AI Conversation Interface**
   - Streaming conversation response
   - Claude 4 Sonnet integration
   - Skills heatmap generation

### Data Source Integration

#### Apify LinkedIn Scraper
- **Actor ID**: `valig/linkedin-jobs-scraper`
- **Supported Website**: LinkedIn.de
- **Scheduled Crawling**: Daily scheduled crawling of preset job data, crawl only by job title, empty city name, 50 jobs per title (by relevance) (published within 7 days)
- **Preset Jobs**: "engineer","manager","IT","Finance","Sales","Nurse","Consultant","software developer","python","java"
- **Cost**: €0.01/call (50 jobs); Scheduled crawling cost: €0.01 * 10 * 30 = €3/month
- **Latest Development Documentation**: https://docs.apify.com/api/client/python/docs/overview/introduction
- **Input Format**:
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
- **Output Format**:
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

#### Zyte API Scraper
- **Supported Website**: Indeed.de
- **Scheduled Crawling**: Daily scheduled crawling, crawl only by job title, empty city name, 25 jobs per title
- **Preset Job Titles**: "Web","cloud","AI","Data","software"
- **Cost**: €0.001/call, €0.001 * 26 * 5 * 30 = €4/month
- **Note**: First crawl job list, then crawl job details, very slow, need sufficient wait time or async processing
- **Latest Development Documentation**: https://docs.zyte.com/zyte-api/usage/reference.html

### Data Storage Solution

#### SQLite
- User session storage
- User authentication information management

#### Chroma Vector Database
- Vector storage and retrieval of job data
- Resume vectorization storage
- Similarity matching queries
- text-embedding-3-small

#### Data Cleaning Mechanism
- **Scheduled Cleaning**: Daily scheduled access to all job URLs in Chroma, clean if URL is invalid
- **Zombie Job Cleaning**: Clean job data from 14 days ago to prevent zombie jobs

## Core Business Workflows

### User Search Workflow
1. User searches "job title" + "location" in main page search bar
2. Backend uses "job title" + "location" vector info as query, retrieves most similar jobs from Chroma
3. Send to frontend and display (job title, company name, location, work type, job detail link, job description)

### Job Recommendation Workflow
1. User uploads resume in chat box → Frontend accepts → Backend receives and sends to agent
2. Agent uses Claude 4 native capabilities to parse PDF, extract key information (location, skills, education, experience, languages, etc.)
3. Embedding vectorization → Store in Chroma (deduplicate when storing to avoid duplicate jobs in Chroma)
4. User resume vector info (location, skills, education, experience, languages) as query, retrieve most similar jobs from Chroma (return 25 jobs)
5. Backend concatenates Claude 4 generated user resume analysis results + Chroma matched job data into one prompt
6. Backend sends prompt to Claude for job analysis and ranking
7. Frontend bot chatbot sends message
8. Backend gets Claude 4 ranked job data → Backend sends job data to frontend (job title, company name, location, work type, job detail link, job detail description)
9. Frontend places jobs in left job display area (by matching score from top to bottom)

### Resume and Job Matching Mechanism
- **Matching Leader**: RAG performs initial matching based on resume vector info, Claude 4 adopts "matching factors" for deep thinking matching
- **Matching Factors**: 
  - Location (medium importance)
  - Skills (important)
  - Education (not very important)
  - Experience (important)
  - Languages (medium importance)

## Claude 4 Sonnet Agent System

### Unified Agent Processing Functions
- Leverage Claude 4's native document understanding capabilities for deep resume analysis
- Provide resume optimization suggestions, tech stack recommendations, learning advice
- Recommend top 25 matching jobs based on resume analysis results
- Recommended jobs ranked by matching score displayed in left display area
- Generate job skills heatmap (Claude 4 native WebSearch searches for trending job skills and performs deep thinking, then calls Artifacts tool to generate skills heatmap)
- Generate skills heatmap and personalized learning recommendations
- Provide German job market consultation and career guidance (Claude 4 native WebSearch searches for employment market information)
- Support trilingual communication in Chinese, German, and English
- Answer questions about job tech stacks and requirements

### AI-Driven Personalized Services
- **Intelligent Resume Analysis**: 
  - Claude 4 native PDF/DOC/TXT document processing capabilities
  - Return detailed analysis results through chat box after analysis
  - Provide optimization suggestions and tech stack recommendations
- **Precise Job Matching**: Matching score based on semantic understanding
- **Skills Gap Analysis**: AI-driven skill assessment and heatmap generation
- **Learning Path Recommendations**: Personalized career development advice (Claude 4 native WebSearch searches for job skills and current trending learning paths for this profession)
- **Job Tech Stack Analysis**: Generate skill requirement heatmap for specific positions (Claude 4 native WebSearch searches for job skills and current trending requirements and tech stacks for this profession)

## Security and Privacy

### Security Authentication
- Google OAuth 2.0 login
- User session management
- Data privacy protection

## Environment Requirements

### Python Dependencies
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

### Environment Variable Configuration
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

## Startup Instructions

### Backend Startup
```bash
# Enter backend directory
cd JobCatcher/backend

# Activate virtual environment
source ../../bin/activate

# Set PYTHONPATH
export PYTHONPATH=/home/devbox/project/JobCatcher/backend:$PYTHONPATH

# Start backend service
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Startup
```bash
# Enter frontend directory
cd JobCatcher/frontend

# Start frontend service
python -m http.server 7860
```

## Development Notes

### Code Standards
- All code comments use Chinese and English bilingual
- Interface language uniformly uses English
- Strictly develop according to README requirements, do not add extra features
- Follow FastAPI and modern Python development best practices

### Testing and Deployment
- Do not create test breakpoints during development
- All functions completed in main workflow
- Timely read and resolve terminal errors
- Ensure port occupation check before service startup
