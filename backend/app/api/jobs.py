"""
职位搜索API / Job search API
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Optional
from ..models.job import JobPosting, JobSearchRequest
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search")
async def search_jobs(
    request: JobSearchRequest,
    http_request: Request
) -> dict:
    """
    搜索职位 / Search jobs
    根据README要求：只从向量数据库检索，不再实时爬取 / According to README: only search from vector DB, no real-time scraping
    
    Args:
        request: 搜索请求参数 / Search request parameters
        
    Returns:
        搜索结果 / Search results
    """
    try:
        logger.info(f"Job search request: keywords='{request.keywords}', city='{request.city}'")
        
        # 根据README用户搜索流程：只从Chroma向量数据库检索 / According to README user search flow: only retrieve from Chroma vector DB
        vector_jobs = []
        try:
            # 使用向量搜索进行语义匹配 / Use vector search for semantic matching
            search_query = request.keywords or "job position"  # 默认查询
            
            logger.info(f"Vector DB semantic query: '{search_query}' (limit: 25)")
            
            vector_jobs = await _search_jobs_in_vector_db(
                search_query, 
                request.city,
                http_request,
                limit=25
            )
            logger.info(f"Vector DB search result: {len(vector_jobs)} jobs")
            if vector_jobs:
                logger.info(f"Sample vector job: {vector_jobs[0].title} at {vector_jobs[0].company_name}")
                
        except Exception as e:
            logger.error(f"Vector DB semantic search failed: {e}")
            vector_jobs = []
        
        logger.info(f"Returning {len(vector_jobs)} jobs to frontend")
        
        return {
            "jobs": [job.model_dump() for job in vector_jobs],
            "total_count": len(vector_jobs)
        }
        
    except Exception as e:
        logger.error(f"搜索职位时发生错误 / Error searching jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败 / Search failed: {str(e)}")


async def _store_jobs_in_vector_db(jobs: List[JobPosting], request: Request):
    """将职位存储到向量数据库 / Store jobs in vector database"""
    try:
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        openai_client = db_connections['openai_client']
        
        # 导入embedding函数 / Import embedding functions
        from ..database.connection import get_text_embedding
        
        stored_count = 0
        skipped_count = 0
        
        for job in jobs:
            # 检查是否已存在（去重机制）/ Check if already exists (deduplication)
            try:
                existing = jobs_collection.get(ids=[job.id])
                if existing['ids']:
                    skipped_count += 1
                    continue
            except:
                pass  # 如果查询失败，继续存储 / If query fails, continue storing
                
            # 构建用于向量化的文档内容（英德语）/ Build document content for vectorization (English/German)
            document = f"Job: {job.title} Company: {job.company_name} Location: {job.location} Description: {job.description[:500]}"
            
            # 使用OpenAI text-embedding-3-small模型进行向量化 / Use OpenAI text-embedding-3-small for vectorization
            logger.info(f"Vectorizing job with OpenAI: {job.title} at {job.company_name}")
            try:
                embedding = get_text_embedding(openai_client, document)
                logger.info(f"✅ Successfully generated embedding (dimension: {len(embedding)})")
            except Exception as e:
                logger.error(f"❌ Failed to generate embedding for job {job.id}: {e}")
                continue
            
            # 添加到向量数据库 / Add to vector database
            # 确保所有metadata字段都不包含None值 / Ensure no None values in metadata
            metadata = {
                "id": job.id,
                "title": job.title or "",
                "company_name": job.company_name or "",
                "location": job.location or "",
                "work_type": job.work_type.value if job.work_type else "",
                "contract_type": job.contract_type or "",
                "experience_level": job.experience_level.value if job.experience_level else "",
                "sector": job.sector or "",
                "salary": job.salary or "",
                "source": job.source.value if job.source else "",
                "url": str(job.url) if job.url else "",
                "apply_url": str(job.apply_url) if job.apply_url else "",
                "posted_time_ago": job.posted_time_ago or "",
                "applications_count": str(job.applications_count) if job.applications_count else "0",
                "description_preview": (job.description[:200] if job.description else ""),
                "full_description": job.description or "",
                "embedding_model": "text-embedding-3-small"
            }
            
            jobs_collection.add(
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[job.id]
            )
            stored_count += 1
            
        logger.info(f"Vector DB storage: {stored_count} new jobs vectorized with OpenAI text-embedding-3-small and stored, {skipped_count} duplicates skipped")
        return stored_count
            
    except Exception as e:
        logger.error(f"Failed to store jobs in vector DB: {e}")
        return 0


async def _search_jobs_in_vector_db(
    job_title: str, 
    location: Optional[str],
    request: Request,
    limit: int = 25
) -> List[JobPosting]:
    """
    向量数据库搜索 - 2025年多语言语义搜索最佳实践 / Vector DB search - 2025 multilingual semantic search best practices
    支持英德语互搜和深度语义理解 / Support English-German cross-search and deep semantic understanding
    """
    try:
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        openai_client = db_connections['openai_client']
        
        # 导入embedding函数 / Import embedding functions
        from ..database.connection import get_text_embedding
        
        # === 第一阶段：多语言查询扩展 / Stage 1: Multilingual query expansion ===
        
        # 1. 基础查询 / Basic query
        base_queries = [job_title]
        
        # 2. 增强的英德语翻译映射 / Enhanced English-German translation mapping
        translation_map = {
            # === 开发相关 / Development related ===
            "developer": ["entwickler", "programmierer", "software engineer", "coder", "dev", "entwicklung"],
            "entwickler": ["developer", "programmer", "software engineer", "coder", "dev"],
            "engineer": ["ingenieur", "entwickler", "techniker", "eng"],
            "ingenieur": ["engineer", "developer", "technician", "technical specialist"],
            "software": ["software", "anwendung", "programm", "app", "application"],
            "programmer": ["programmierer", "entwickler", "coder", "coding"],
            "programmierer": ["programmer", "developer", "coder", "software engineer"],
            "coding": ["programmierung", "entwicklung", "programming"],
            "programmierung": ["coding", "programming", "development"],
            
            # === 前端后端 / Frontend/Backend ===
            "frontend": ["frontend", "front-end", "ui", "user interface", "client-side", "vorderseite"],
            "backend": ["backend", "back-end", "server-side", "api", "serverseite"],
            "fullstack": ["full-stack", "vollstack", "full stack", "end-to-end"],
            "full stack": ["fullstack", "vollstack", "frontend backend", "complete stack"],
            "ui": ["benutzeroberfläche", "user interface", "interface"],
            "ux": ["benutzererfahrung", "user experience", "usability"],
            
            # === 技术栈关键词 / Tech stack keywords ===
            "python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular", "typescript"],
            "java": ["java", "spring", "hibernate", "maven", "gradle"],
            "web": ["web", "website", "internet", "online", "webseite", "internet"],
            "react": ["react", "reactjs", "react.js"],
            "node": ["nodejs", "node.js", "express"],
            "database": ["datenbank", "db", "sql", "mysql", "postgresql"],
            "datenbank": ["database", "db", "data storage"],
            "ai": ["artificial intelligence", "künstliche intelligenz", "ki", "machine learning"],
            "ml": ["machine learning", "maschinelles lernen", "ai", "artificial intelligence"],
            
            # === 数据相关 / Data related ===
            "data scientist": ["datenwissenschaftler", "data analyst", "analyst", "data researcher"],
            "analyst": ["analytiker", "data analyst", "business analyst", "researcher"],
            "datenwissenschaftler": ["data scientist", "data analyst", "data researcher"],
            "data": ["daten", "data analysis", "analytics", "information"],
            "daten": ["data", "information", "analytics"],
            "analytics": ["analytik", "analysis", "datenanalyse"],
            
            # === 管理相关 / Management related ===
            "manager": ["manager", "leiter", "führungskraft", "teamleiter", "direktor"],
            "leiter": ["manager", "leader", "head", "director", "supervisor"],
            "teamleiter": ["team leader", "team manager", "lead", "supervisor"],
            "project manager": ["projektmanager", "project lead", "pm"],
            "projektmanager": ["project manager", "project lead", "pm"],
            "director": ["direktor", "leiter", "head"],
            "direktor": ["director", "head", "manager"],
            
            # === 护理医疗 / Healthcare/Nursing ===
            "nurse": ["krankenschwester", "krankenpfleger", "pflegekraft", "schwester", "pfleger"],
            "krankenschwester": ["nurse", "healthcare worker", "medical professional"],
            "pflegekraft": ["nurse", "caregiver", "healthcare worker", "care professional"],
            "pfleger": ["nurse", "caregiver", "male nurse"],
            "medical": ["medizinisch", "healthcare", "gesundheitswesen"],
            "healthcare": ["gesundheitswesen", "medical", "medizin"],
            "study nurse": ["study nurse", "studienassistenz", "klinische forschung"],
            
            # === 销售营销 / Sales/Marketing ===
            "sales": ["verkauf", "vertrieb", "verkäufer", "sales representative"],
            "verkauf": ["sales", "selling", "commerce"],
            "vertrieb": ["sales", "distribution", "business development"],
            "marketing": ["marketing", "werbung", "promotion"],
            "werbung": ["marketing", "advertising", "promotion"],
            "business development": ["geschäftsentwicklung", "business dev", "bd"],
            
            # === 工作级别 / Job levels ===
            "junior": ["junior", "einsteiger", "entry level", "beginner", "anfänger"],
            "einsteiger": ["junior", "entry level", "beginner", "starter"],
            "senior": ["senior", "erfahren", "lead", "experienced", "expert"],
            "erfahren": ["senior", "experienced", "expert", "advanced"],
            "lead": ["lead", "leader", "principal", "hauptentwickler"],
            "principal": ["principal", "senior", "expert", "chief"],
            
            # === 工作类型 / Work types ===
            "internship": ["praktikum", "intern", "trainee", "stage"],
            "praktikum": ["internship", "intern", "trainee", "apprenticeship"],
            "trainee": ["trainee", "praktikant", "auszubildender"],
            "remote": ["remote", "homeoffice", "telearbeit", "distant"],
            "hybrid": ["hybrid", "teilweise remote", "mixed"],
            
            # === 行业特定 / Industry specific ===
            "consultant": ["berater", "consulting", "beratung"],
            "berater": ["consultant", "advisor", "consulting"],
            "architect": ["architekt", "system architect", "solution architect"],
            "architekt": ["architect", "designer", "planner"],
            "devops": ["devops", "dev ops", "operations", "deployment"],
            "qa": ["quality assurance", "testing", "qualitätssicherung", "tester"],
            "testing": ["testing", "qa", "qualitätssicherung", "software testing"],
        }
        
        # 3. 生成扩展查询 / Generate expanded queries
        expanded_queries = []
        job_title_lower = job_title.lower()
        
        # 直接翻译映射 / Direct translation mapping
        for key, translations in translation_map.items():
            if key in job_title_lower:
                for translation in translations:
                    expanded_queries.append(translation)
                    expanded_queries.append(f"{translation} job position")
                break
        
        # 4. 基于职位类型的语义扩展 / Semantic expansion based on job types
        semantic_expansions = []
        
        if any(term in job_title_lower for term in ['software', 'developer', 'entwickler', 'engineer', 'programming', 'coding']):
            semantic_expansions.extend([
                "software development programming coding",
                "web application mobile development", 
                "python javascript java react nodejs",
                "frontend backend fullstack development",
                "software engineer developer programmer",
                "entwicklung programmierung software engineer"
            ])
        elif any(term in job_title_lower for term in ['data', 'analyst', 'analytics', 'datenwissenschaft']):
            semantic_expansions.extend([
                "data analysis analytics python sql",
                "machine learning artificial intelligence",
                "business intelligence reporting dashboard",
                "data scientist analyst researcher",
                "datenanalyst datenwissenschaftler analytics"
            ])
        elif any(term in job_title_lower for term in ['nurse', 'nursing', 'pflege', 'krankenschwester', 'medical']):
            semantic_expansions.extend([
                "healthcare medical nursing patient care",
                "hospital clinic healthcare worker",
                "registered nurse healthcare professional",
                "krankenpflege medizinische versorgung",
                "pflegekraft krankenschwester pfleger"
            ])
        elif any(term in job_title_lower for term in ['manager', 'management', 'leiter', 'führung']):
            semantic_expansions.extend([
                "management leadership team supervisor",
                "project manager team leader director",
                "business management executive leadership",
                "teamleitung projektmanagement führung",
                "manager leiter direktor führungskraft"
            ])
        elif any(term in job_title_lower for term in ['sales', 'verkauf', 'vertrieb']):
            semantic_expansions.extend([
                "sales business development account manager",
                "customer relationship sales representative",
                "verkauf vertrieb kundenbetreuung",
                "business development sales manager"
            ])
        else:
            # 通用职位扩展 / Generic job expansion
            semantic_expansions.extend([
                f"{job_title} position job role work",
                f"{job_title} career opportunity employment",
                f"{job_title} stelle arbeit beruf"
            ])
        
        # 5. 组合所有查询 / Combine all queries
        all_search_queries = (
            base_queries + 
            expanded_queries + 
            semantic_expansions
        )
        
        # 添加地点信息 / Add location information
        if location and location.strip():
            location_enhanced = []
            for query in all_search_queries[:8]:  # 限制数量避免过多查询
                location_enhanced.append(f"{query} {location}")
                location_enhanced.append(f"{query} in {location}")
            all_search_queries.extend(location_enhanced)
        
        # 去重并限制查询数量 / Deduplicate and limit query count
        unique_queries = list(set(all_search_queries))[:15]  # 最多15个查询
        
        logger.info(f"Generated {len(unique_queries)} search queries for '{job_title}'")
        
        # === 第二阶段：多查询向量搜索 / Stage 2: Multi-query vector search ===
        
        all_results = {}  # 用于去重和评分 / For deduplication and scoring
        
        for query_text in unique_queries:
            try:
                # 生成查询向量 / Generate query vector
                query_embedding = get_text_embedding(openai_client, query_text)
                
                # 执行向量搜索 / Execute vector search
                results = jobs_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(limit * 2, 80)  # 获取更多候选结果
                )
                
                # 处理结果 / Process results
                if results['metadatas'] and results['distances']:
                    for i, metadata in enumerate(results['metadatas'][0]):
                        try:
                            similarity_distance = results['distances'][0][i]
                            doc_id = results['ids'][0][i] if results['ids'] else f"doc_{i}"
                            
                            # 动态相似度阈值（更宽松以获取更多候选）/ Dynamic similarity threshold (more relaxed)
                            max_distance = 1.8  # 更宽松的阈值以获取更多语义相关结果
                            
                            if similarity_distance <= max_distance:
                                if doc_id in all_results:
                                    # 更新现有结果 / Update existing result
                                    all_results[doc_id]['similarity_scores'].append(similarity_distance)
                                    all_results[doc_id]['query_matches'] += 1
                                    all_results[doc_id]['matched_queries'].append(query_text)
                                else:
                                    # 添加新结果 / Add new result
                                    all_results[doc_id] = {
                                        'metadata': metadata,
                                        'similarity_scores': [similarity_distance],
                                        'query_matches': 1,
                                        'original_distance': similarity_distance,
                                        'matched_queries': [query_text]
                                    }
                        except Exception as e:
                            logger.warning(f"处理搜索结果时出错: {str(e)}")
                            continue
                            
            except Exception as e:
                logger.warning(f"查询执行出错: {query_text}, 错误: {str(e)}")
                continue
        
        # === 第三阶段：智能评分和排序 / Stage 3: Intelligent scoring and ranking ===
        
        scored_results = []
        
        for doc_id, result_data in all_results.items():
            try:
                metadata = result_data['metadata']
                similarity_scores = result_data['similarity_scores']
                query_matches = result_data['query_matches']
                matched_queries = result_data['matched_queries']
                
                # 基础相似度评分 / Base similarity score
                avg_distance = sum(similarity_scores) / len(similarity_scores)
                base_score = max(0, (2.0 - avg_distance))
                
                # 多查询匹配奖励 / Multi-query match bonus
                match_bonus = min(query_matches * 0.15, 0.4)  # 增加多查询匹配奖励
                
                # 深度关键词匹配评分 / Deep keyword matching score
                title = metadata.get('title', '').lower()
                description = metadata.get('full_description', '').lower()
                company = metadata.get('company_name', '').lower()
                
                # 计算详细的关键词匹配 / Calculate detailed keyword matching
                keyword_score = 0
                title_match_score = 0  # 单独计算标题匹配分数
                original_keywords = job_title.lower().split()
                
                # 检查原始关键词 / Check original keywords
                for keyword in original_keywords:
                    if len(keyword) > 2:
                        if keyword in title:
                            keyword_score += 0.8  # 标题匹配权重提升
                            title_match_score += 1  # 标题匹配计数
                        elif keyword in description:
                            keyword_score += 0.4  # 描述匹配权重大幅提升
                        elif keyword in company:
                            keyword_score += 0.1  # 公司名匹配权重
                
                # 检查翻译后的关键词 / Check translated keywords
                translation_match_score = 0
                for original_keyword in original_keywords:
                    if original_keyword in translation_map:
                        for translated_keyword in translation_map[original_keyword]:
                            if translated_keyword in title:
                                keyword_score += 0.7  # 标题翻译匹配
                                title_match_score += 1
                                translation_match_score += 1
                            elif translated_keyword in description:
                                keyword_score += 0.35  # 描述翻译匹配权重大幅提升
                
                # 增强的职位相关性检查 / Enhanced job relevance check
                relevance_penalty = 0
                irrelevant_keywords = {
                    # 技术职位不应匹配非技术职位 / Tech positions shouldn't match non-tech positions
                    'software': ['sales manager', 'marketing manager', 'hr manager', 'strategy director', 'business manager', 'account manager', 'consultant', 'nurse', 'medical'],
                    'developer': ['sales', 'marketing', 'hr', 'human resources', 'strategy', 'business development', 'account', 'nurse', 'medical', 'healthcare'],
                    'engineer': ['sales manager', 'marketing', 'hr', 'strategy director', 'business consultant', 'nurse', 'medical assistant'],
                    'programmer': ['sales', 'marketing', 'strategy', 'business', 'manager', 'director', 'consultant', 'nurse', 'medical'],
                    'python': ['sales', 'marketing', 'strategy', 'director', 'manager', 'consultant', 'nurse', 'medical', 'hr'],
                    'javascript': ['sales', 'marketing', 'strategy', 'business', 'consultant', 'nurse', 'medical'],
                    'web developer': ['sales', 'marketing', 'strategy', 'business consultant', 'nurse', 'medical'],
                    
                    # 护理职位不应匹配技术职位 / Nursing positions shouldn't match tech positions
                    'nurse': ['developer', 'programmer', 'software engineer', 'it administrator', 'system administrator', 'network', 'web developer', 'python', 'javascript'],
                    'medical': ['software', 'developer', 'programmer', 'it administrator', 'web development'],
                    'healthcare': ['software engineer', 'developer', 'programmer', 'it support'],
                    
                    # 数据科学职位的特定过滤 / Data science position specific filtering
                    'data analyst': ['sales manager', 'hr manager', 'strategy director', 'business manager', 'account manager', 'nurse', 'medical'],
                    'data scientist': ['sales manager', 'marketing manager', 'hr manager', 'strategy director', 'business manager', 'account manager', 'area sales', 'sales development', 'sales consultant', 'regional sales', 'nurse', 'medical'],
                    'analytics': ['sales manager', 'marketing manager', 'hr manager', 'strategy director', 'nurse', 'medical'],
                    'machine learning': ['sales', 'marketing', 'hr', 'strategy director', 'business manager', 'nurse', 'medical'],
                    'ai engineer': ['sales', 'marketing', 'hr', 'strategy director', 'nurse', 'medical'],
                    
                    # 销售职位不应匹配技术职位 / Sales positions shouldn't match tech positions
                    'sales': ['developer', 'programmer', 'software engineer', 'data scientist', 'data analyst', 'nurse', 'medical assistant'],
                    'marketing': ['developer', 'programmer', 'software engineer', 'data scientist', 'nurse', 'medical'],
                    
                    # 管理职位过滤 / Management position filtering
                    'manager': ['nurse', 'medical assistant', 'healthcare aide', 'developer', 'programmer'],
                    'director': ['nurse', 'medical assistant', 'developer', 'programmer'],
                    'consultant': ['nurse', 'medical assistant']  # 顾问职位减少技术过滤，因为可能有技术顾问
                }
                
                job_title_key = job_title.lower()
                
                # 改进的相关性检查 - 更精确的匹配 / Improved relevance check - more precise matching
                search_terms = job_title_key.split()
                job_title_lower = title.lower()
                
                # 检查技术vs非技术的严重冲突 / Check tech vs non-tech serious conflicts
                tech_search_terms = ['software', 'developer', 'engineer', 'programmer', 'python', 'javascript', 'react', 'frontend', 'backend', 'fullstack', 'web developer', 'data scientist', 'machine learning', 'ai', 'cloud', 'entwickler']
                non_tech_job_indicators = ['sales manager', 'marketing manager', 'strategy director', 'business manager', 'account manager', 'hr manager', 'facilities manager', 'operations manager']
                
                # 判断搜索是否为技术类 / Determine if search is technical
                is_tech_search = any(tech_term in job_title_key for tech_term in tech_search_terms)
                
                # 判断职位是否为明显的非技术管理类 / Determine if job is clearly non-tech management
                is_non_tech_job = any(non_tech_indicator in job_title_lower for non_tech_indicator in non_tech_job_indicators)
                
                # 特殊处理data scientist搜索 / Special handling for data scientist search
                if 'data scientist' in job_title_key or 'data science' in job_title_key:
                    # data scientist搜索的严格过滤 / Strict filtering for data scientist search
                    unwanted_for_data_science = [
                        'strategy consultant', 'strategy director', 'business consultant',
                        'information technology specialist', 'head of information technology', 
                        'chief information officer', 'it administrator', 'it-administrator',
                        'head of it service', 'senior manager', 'operations analyst',
                        'analytical consultant', 'senior consultant'
                    ]
                    
                    for unwanted in unwanted_for_data_science:
                        if unwanted in job_title_lower:
                            relevance_penalty = -2.5  # 更严厉的惩罚
                            logger.warning(f"Data Science职位过滤: 搜索'{job_title}' 但找到'{title}' (惩罚: {relevance_penalty})")
                            break
                
                # 一般技术vs非技术冲突检查 / General tech vs non-tech conflict check
                elif is_tech_search and is_non_tech_job:
                    relevance_penalty = -2.0  # 技术vs非技术重大惩罚
                    logger.warning(f"技术vs非技术冲突: 搜索'{job_title}' 但找到'{title}' (惩罚: {relevance_penalty})")
                
                # 护理vs技术冲突 / Nursing vs tech conflict
                elif 'nurse' in job_title_key and any(tech in job_title_lower for tech in ['software', 'developer', 'engineer', 'programmer']):
                    relevance_penalty = -2.0  # 护理vs技术重大惩罚
                    logger.warning(f"护理vs技术冲突: 搜索'{job_title}' 但找到'{title}' (惩罚: {relevance_penalty})")
                
                # AI搜索的特殊处理 / Special handling for AI search
                elif 'ai' in job_title_key:
                    ai_irrelevant = ['facilities manager', 'senior manager', 'operations manager', 'sales manager']
                    for irrelevant in ai_irrelevant:
                        if irrelevant in job_title_lower:
                            relevance_penalty = -1.8
                            logger.warning(f"AI职位过滤: 搜索'{job_title}' 但找到'{title}' (惩罚: {relevance_penalty})")
                            break
                
                # 标题匹配强制要求 / Title match requirement
                title_requirement_met = title_match_score > 0 or translation_match_score > 0
                if not title_requirement_met:
                    # 如果标题完全不匹配，大幅降低评分 / If title doesn't match at all, drastically reduce score
                    keyword_score *= 0.3
                
                # 技术栈深度匹配 / Tech stack deep matching
                tech_stack_score = 0
                tech_keywords = ['python', 'javascript', 'java', 'react', 'node', 'angular', 'vue', 'sql', 'docker', 'kubernetes', 'aws', 'azure']
                
                for tech in tech_keywords:
                    if tech in job_title_lower and tech in description:
                        tech_stack_score += 0.15  # 技术栈权重降低
                
                # 地理位置匹配 / Geographic location matching
                location_score = 0
                if location and location.strip():
                    location_lower = location.lower()
                    job_location = metadata.get('location', '').lower()
                    if location_lower in job_location or job_location in location_lower:
                        location_score = 0.15  # 地理位置权重降低
                    # 部分位置匹配 / Partial location matching
                    elif any(loc_part in job_location for loc_part in location_lower.split() if len(loc_part) > 2):
                        location_score = 0.08
                
                # 工作类型相关性 / Work type relevance
                work_type_score = 0
                work_type = metadata.get('work_type', '').lower()
                if any(wt in job_title_lower for wt in ['intern', 'praktikum', 'trainee']) and 'intern' in work_type:
                    work_type_score = 0.1  # 工作类型权重降低
                
                # 最终综合评分 - 优化权重分配 / Final comprehensive score - optimized weight distribution
                final_score = (
                    base_score * 0.15 +           # 基础语义相似度 (15%)
                    match_bonus * 0.10 +          # 多查询匹配 (10%)
                    keyword_score * 0.60 +        # 关键词匹配权重最高 (60%)
                    tech_stack_score * 0.08 +     # 技术栈匹配 (8%)
                    location_score * 0.04 +       # 地理位置匹配 (4%)
                    work_type_score * 0.03 +      # 工作类型匹配 (3%)
                    relevance_penalty             # 相关性惩罚
                )
                
                # 确保评分不为负数 / Ensure score is not negative
                final_score = max(0.01, final_score)
                
                # 创建JobPosting对象 / Create JobPosting object
                job_posting = JobPosting(
                    id=metadata.get('id', f'vec_{doc_id}'),
                    title=metadata.get('title', ''),
                    company_name=metadata.get('company_name', ''),
                    location=metadata.get('location', ''),
                    work_type=metadata.get('work_type', 'Full-time'),
                    salary=metadata.get('salary', ''),
                    description=metadata.get('full_description', ''),
                    url=metadata.get('url', ''),
                    source=metadata.get('source', 'LinkedIn'),
                    posted_time_ago=metadata.get('posted_time_ago', ''),
                    posted_date=None
                )
                
                scored_results.append((final_score, job_posting, {
                    'query_matches': query_matches,
                    'avg_distance': avg_distance,
                    'keyword_score': keyword_score,
                    'matched_queries': matched_queries[:3]  # 记录前3个匹配的查询
                }))
                
            except Exception as e:
                logger.warning(f"处理结果评分时出错: {str(e)}")
                continue
        
        # === 第四阶段：确保返回25个结果 / Stage 4: Ensure 25 results are returned ===
        
        # 如果结果不足25个，放宽阈值重新搜索 / If results < 25, relax threshold and search again
        if len(scored_results) < limit:
            logger.info(f"初始搜索结果不足({len(scored_results)}/{limit})，放宽阈值继续搜索...")
            
            # 使用更宽松的阈值获取更多结果 / Use more relaxed threshold for more results
            relaxed_results = {}
            relaxed_threshold = 2.5  # 非常宽松的阈值
            
            for query_text in unique_queries[:5]:  # 限制查询数量避免过度计算
                try:
                    query_embedding = get_text_embedding(openai_client, query_text)
                    results = jobs_collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(limit * 4, 150)  # 获取更多候选结果
                    )
                    
                    if results['metadatas'] and results['distances']:
                        for i, metadata in enumerate(results['metadatas'][0]):
                            try:
                                similarity_distance = results['distances'][0][i]
                                doc_id = results['ids'][0][i] if results['ids'] else f"doc_{i}"
                                
                                # 使用宽松阈值 / Use relaxed threshold
                                if similarity_distance <= relaxed_threshold:
                                    if doc_id not in all_results:  # 只添加新结果
                                        relaxed_results[doc_id] = {
                                            'metadata': metadata,
                                            'similarity_scores': [similarity_distance],
                                            'query_matches': 1,
                                            'original_distance': similarity_distance,
                                            'matched_queries': [query_text]
                                        }
                            except Exception:
                                continue
                except Exception:
                    continue
            
            # 处理新发现的结果 / Process newly found results
            for doc_id, result_data in relaxed_results.items():
                try:
                    metadata = result_data['metadata']
                    similarity_distance = result_data['original_distance']
                    
                    # 基础评分（对于宽松搜索，给予较低但非零的评分）/ Basic score for relaxed search
                    base_score = max(0.1, (3.0 - similarity_distance))
                    
                    # 简化的关键词匹配 / Simplified keyword matching
                    title = metadata.get('title', '').lower()
                    description = metadata.get('full_description', '').lower()
                    
                    keyword_score = 0
                    for keyword in job_title.lower().split():
                        if len(keyword) > 2:
                            if keyword in title:
                                keyword_score += 0.2
                            elif keyword in description:
                                keyword_score += 0.1
                    
                    # 最终评分 / Final score
                    final_score = base_score * 0.7 + keyword_score * 0.3
                    
                    # 创建JobPosting对象 / Create JobPosting object
                    job_posting = JobPosting(
                        id=metadata.get('id', f'relax_{doc_id}'),
                        title=metadata.get('title', ''),
                        company_name=metadata.get('company_name', ''),
                        location=metadata.get('location', ''),
                        work_type=metadata.get('work_type', 'Full-time'),
                        salary=metadata.get('salary', ''),
                        description=metadata.get('full_description', ''),
                        url=metadata.get('url', ''),
                        source=metadata.get('source', 'LinkedIn'),
                        posted_time_ago=metadata.get('posted_time_ago', ''),
                        posted_date=None
                    )
                    
                    scored_results.append((final_score, job_posting, {
                        'query_matches': 1,
                        'avg_distance': similarity_distance,
                        'keyword_score': keyword_score,
                        'matched_queries': ['relaxed_search']
                    }))
                    
                except Exception as e:
                    logger.warning(f"处理宽松搜索结果时出错: {str(e)}")
                    continue
                    
            logger.info(f"宽松搜索后结果数量: {len(scored_results)}")
        
        # 按评分排序并返回结果 / Sort by score and return results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # 确保返回指定数量的结果，如果仍然不足则填充默认结果 / Ensure specified number of results
        if len(scored_results) < limit:
            # 如果还是不够，从数据库随机获取一些职位填充 / If still not enough, get some random jobs
            try:
                additional_needed = limit - len(scored_results)
                random_results = jobs_collection.get(limit=additional_needed * 2)
                
                existing_ids = {job[1].id for job in scored_results}
                
                if random_results['metadatas']:
                    for metadata in random_results['metadatas']:
                        if len(scored_results) >= limit:
                            break
                            
                        job_id = metadata.get('id', '')
                        if job_id not in existing_ids:
                            try:
                                job_posting = JobPosting(
                                    id=job_id,
                                    title=metadata.get('title', ''),
                                    company_name=metadata.get('company_name', ''),
                                    location=metadata.get('location', ''),
                                    work_type=metadata.get('work_type', 'Full-time'),
                                    salary=metadata.get('salary', ''),
                                    description=metadata.get('full_description', ''),
                                    url=metadata.get('url', ''),
                                    source=metadata.get('source', 'LinkedIn'),
                                    posted_time_ago=metadata.get('posted_time_ago', ''),
                                    posted_date=None
                                )
                                
                                scored_results.append((0.1, job_posting, {
                                    'query_matches': 0,
                                    'avg_distance': 2.0,
                                    'keyword_score': 0,
                                    'matched_queries': ['fallback']
                                }))
                                existing_ids.add(job_id)
                                
                            except Exception:
                                continue
                
                logger.info(f"添加随机填充结果后总数: {len(scored_results)}")
                
            except Exception as e:
                logger.warning(f"获取填充结果时出错: {str(e)}")
        
        # 最终确保精确返回limit数量的结果 / Finally ensure exactly limit number of results
        final_jobs = [job for score, job, meta in scored_results[:limit]]
        
        # 记录调试信息 / Log debug information
        if final_jobs:
            logger.info(f"搜索完成: '{job_title}' -> 候选数={len(all_results)}, 最终返回={len(final_jobs)}")
            if scored_results:
                top_result = scored_results[0]
                logger.info(f"最佳匹配: {top_result[1].title} (评分: {top_result[0]:.3f})")
        else:
            logger.warning(f"搜索'{job_title}'未找到任何结果")
        
        return final_jobs
        
    except Exception as e:
        logger.error(f"向量数据库搜索失败: {str(e)}")
        return []


@router.delete("/cleanup")
async def cleanup_old_jobs():
    """
    清理过期职位数据 / Cleanup expired job data
    注意：根据README，数据清理应该通过定时任务完成，此API仅用于手动触发
    """
    try:
        # 这里可以调用定时任务的清理逻辑 / Can call scheduled cleanup logic here
        logger.info("Manual cleanup triggered via API")
        return {"message": "Cleanup task triggered", "status": "success"}
        
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}") 


@router.get("/debug/stats")
async def get_database_stats(request: Request):
    """
    获取数据库统计信息 / Get database statistics
    """
    try:
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        
        # 获取总数据量 / Get total data count
        total_jobs = jobs_collection.count()
        
        # 使用get方法获取前10个记录 / Use get method to fetch first 10 records
        sample_results = jobs_collection.get(limit=10)
        
        sample_titles = []
        software_related_count = 0
        if sample_results['metadatas']:
            for metadata in sample_results['metadatas']:
                title = metadata.get('title', '')
                sample_titles.append(title)
                # 检查是否包含software相关关键词 / Check if contains software-related keywords
                title_lower = title.lower()
                software_keywords = ["software", "developer", "engineer", "programming", "coding", "dev", "tech"]
                if any(keyword in title_lower for keyword in software_keywords):
                    software_related_count += 1
        
        return {
            "total_jobs_in_db": total_jobs,
            "sample_job_titles": sample_titles,
            "software_related_in_sample": software_related_count,
            "collection_name": jobs_collection.name
        }
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/debug/search_keyword/{keyword}")
async def search_keyword_debug(keyword: str, request: Request):
    """
    调试搜索：查找包含特定关键词的职位 / Debug search: find jobs containing specific keywords
    """
    try:
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        
        # 获取所有数据 / Get all data
        all_results = jobs_collection.get()
        
        matching_jobs = []
        keyword_lower = keyword.lower()
        
        if all_results['metadatas']:
            for metadata in all_results['metadatas']:
                title = metadata.get('title', '').lower()
                description = metadata.get('full_description', '').lower()
                company = metadata.get('company_name', '').lower()
                
                # 检查关键词是否出现在标题、描述或公司名中 / Check if keyword appears in title, description, or company
                if (keyword_lower in title or 
                    keyword_lower in description or 
                    keyword_lower in company):
                    matching_jobs.append({
                        'title': metadata.get('title', ''),
                        'company': metadata.get('company_name', ''),
                        'location': metadata.get('location', ''),
                        'description_preview': (metadata.get('full_description', '') or '')[:200]
                    })
        
        return {
            "keyword": keyword,
            "total_jobs_in_db": jobs_collection.count(),
            "matching_count": len(matching_jobs),
            "matching_jobs": matching_jobs[:20]  # 返回前20个匹配结果 / Return first 20 matches
        }
        
    except Exception as e:
        logger.error(f"Failed to search keyword debug: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}") 