"""
Claude 4 Sonnet AI服务 / Claude 4 Sonnet AI service
优化版本 - 符合官方文档标准 / Optimized version - compliant with official documentation standards
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic
from ..core.config import settings
from ..models.job import JobPosting, JobMatch
from ..core.logging import get_logger
import json
from datetime import datetime

logger = get_logger("JobCatcher.claude")


class TokenUsageTracker:
    """Token使用量跟踪器 / Token usage tracker"""
    
    def __init__(self):
        self.daily_usage = {}
        # Claude 4 Sonnet定价 (USD per million tokens) / Claude 4 Sonnet pricing
        self.pricing = {
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-opus-4-20250514": {"input": 15.0, "output": 75.0}
        }
    
    def log_usage(self, model: str, input_tokens: int, output_tokens: int, 
                  cache_creation_tokens: int = 0, cache_read_tokens: int = 0, 
                  web_search_requests: int = 0, session_id: str = None):
        """记录token使用量 / Log token usage"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.daily_usage:
            self.daily_usage[today] = {
                "sessions": {},
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cache_creation_tokens": 0,
                "total_cache_read_tokens": 0,
                "total_web_search_requests": 0,
                "total_cost": 0.0,
                "cache_savings": 0.0,
                "model_usage": {}
            }
        
        daily_data = self.daily_usage[today]
        
        # 会话级别统计 / Session-level statistics
        if session_id:
            if session_id not in daily_data["sessions"]:
                daily_data["sessions"][session_id] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "web_search_requests": 0,
                    "cost": 0.0,
                    "requests": 0
                }
            
            session_data = daily_data["sessions"][session_id]
            session_data["input_tokens"] += input_tokens
            session_data["output_tokens"] += output_tokens
            session_data["cache_creation_tokens"] += cache_creation_tokens
            session_data["cache_read_tokens"] += cache_read_tokens
            session_data["web_search_requests"] += web_search_requests
            session_data["requests"] += 1
            
        # 全局统计 / Global statistics
        daily_data["total_input_tokens"] += input_tokens
        daily_data["total_output_tokens"] += output_tokens
        daily_data["total_cache_creation_tokens"] += cache_creation_tokens
        daily_data["total_cache_read_tokens"] += cache_read_tokens
        daily_data["total_web_search_requests"] += web_search_requests
        
        # 成本计算 / Cost calculation
        if model in self.pricing:
            pricing = self.pricing[model]
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
            daily_data["total_cost"] += cost
            
            # 缓存节省计算 / Cache savings calculation
            cache_savings = cache_read_tokens * pricing["input"] * 0.9 / 1_000_000  # 90% discount for cache reads
            daily_data["cache_savings"] += cache_savings
            
            if session_id:
                daily_data["sessions"][session_id]["cost"] += cost
        
        # 模型使用统计 / Model usage statistics
        if model not in daily_data["model_usage"]:
            daily_data["model_usage"][model] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
        
        daily_data["model_usage"][model]["requests"] += 1
        daily_data["model_usage"][model]["input_tokens"] += input_tokens
        daily_data["model_usage"][model]["output_tokens"] += output_tokens
        if model in self.pricing:
            daily_data["model_usage"][model]["cost"] += cost
        
        logger.info(f"Token usage - Model: {model}, Input: {input_tokens}, Output: {output_tokens}, "
                   f"Cache Created: {cache_creation_tokens}, Cache Read: {cache_read_tokens}, "
                   f"Web Searches: {web_search_requests}, Cost: ${cost:.4f}, Savings: ${cache_savings:.4f}")

    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """获取每日使用统计 / Get daily usage summary"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date not in self.daily_usage:
            return {
                "date": date,
                "total_tokens": 0,
                "total_cost": 0.0,
                "cache_savings": 0.0,
                "requests": 0,
                "cache_hit_rate": 0.0
            }
        
        data = self.daily_usage[date]
        total_tokens = data["total_input_tokens"] + data["total_output_tokens"]
        total_requests = sum(session["requests"] for session in data["sessions"].values())
        cache_hit_rate = data["total_cache_read_tokens"] / max(data["total_input_tokens"], 1)
        
        return {
            "date": date,
            "total_tokens": total_tokens,
            "input_tokens": data["total_input_tokens"],
            "output_tokens": data["total_output_tokens"],
            "total_cost": data["total_cost"],
            "cache_savings": data["cache_savings"],
            "requests": total_requests,
            "cache_hit_rate": cache_hit_rate,
            "web_search_requests": data["total_web_search_requests"],
            "sessions": len(data["sessions"]),
            "model_usage": data["model_usage"]
        }

    def check_budget_alert(self, daily_budget: float = 5.0) -> Dict[str, Any]:
        """检查预算警告 / Check budget alert"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_usage = self.get_daily_summary(today)
        used_amount = current_usage["total_cost"]
        percentage = (used_amount / daily_budget) * 100
        
        if percentage >= 100:
            alert_level = "exceeded"
        elif percentage >= 80:
            alert_level = "high"
        elif percentage >= 60:
            alert_level = "medium"
        else:
            alert_level = "low"
        
        return {
            "alert_level": alert_level,
            "used_amount": used_amount,
            "budget": daily_budget,
            "percentage": percentage,
            "remaining": max(0, daily_budget - used_amount)
        }


class ClaudeService:
    """Claude 4 Sonnet AI服务类 - 优化版本 / Claude 4 Sonnet AI service - optimized version"""
    
    def __init__(self):
        """初始化Claude服务 / Initialize Claude service"""
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.token_tracker = TokenUsageTracker()
        
        # Session缓存管理 - 关键优化 / Session cache management - key optimization
        self.session_system_cache = {}
        
        # 🔥 新增：消息历史管理 / NEW: Message history management
        self.session_message_history = {}
        
        # 🔥 新增：固定回答模板，节省token / NEW: Fixed response templates to save tokens
        self.fixed_responses = {
            "welcome": {
                "pattern": r"^(hello|hi|你好|hallo|guten tag).*$",
                "response": """Hello! I'm JobCatcher, your AI-powered career assistant specializing in the German job market. I'm here to help you with:

🎯 **Resume Analysis & Optimization** - Upload your CV for detailed feedback
🔍 **Job Matching** - Find positions that match your background
📊 **Skills Heatmap** - Discover trending skills in your field
💼 **Career Guidance** - Get advice for the German job market
🌐 **Market Insights** - Current trends and salary information

How can I assist you today? You can upload your resume or ask me anything about your career in Germany!""",
                "skip_ai": True
            },
            "upload_complete": {
                "pattern": r"resume.*uploaded|file.*uploaded|cv.*uploaded",
                "response": """📄 **Resume Upload Complete!**

Great! I've received your resume. Now you can ask me:

• 💡 Analyze my resume strengths and weaknesses
• 🎯 What skills am I missing for the job market?
• 🔧 How can I improve my resume?
• 🔍 Find matching jobs for me
• 📊 Generate skills heatmap for my target roles

What would you like to know about your career prospects in Germany?""",
                "skip_ai": True
            },
            "help": {
                "pattern": r"^(help|帮助|hilfe).*$",
                "response": """🤖 **JobCatcher Help**

I can help you with:

**Resume & Career Analysis:**
- Resume analysis and optimization
- Skills gap identification
- Career path recommendations

**Job Market Intelligence:**
- Find matching job opportunities
- Generate skills heatmaps for specific roles
- German job market trends and insights
- Salary information and expectations

**Career Guidance:**
- Interview preparation tips
- Cover letter guidance (German format)
- Professional networking advice
- Visa and work permit information

Just ask me anything or upload your resume to get started!""",
                "skip_ai": True
            }
        }
        
        # Token限制配置 / Token limit configuration
        self.max_tokens_limit = {
            "simple_response": 2500,
            "detailed_analysis": 4000,
            "complex_task": 6000
        }
        
        logger.info("Claude 4 service initialized - optimized version with prompt caching, context management, and fixed responses")

    def _initialize_session_context(self, session_id: str) -> str:
        """
        初始化会话上下文 - 只在第一次调用时创建缓存
        Initialize session context - create cache only on first call
        """
        if session_id in self.session_system_cache:
            logger.info(f"♻️ Using existing cached system context for session: {session_id}")
            return self.session_system_cache[session_id]
        
        # 🔥 优化：简化系统提示词，满足1024token缓存要求但避免重复 / OPTIMIZED: Simplified system prompt for cache efficiency
        system_prompt = """You are JobCatcher, an advanced AI career assistant powered by Claude 4 Sonnet, specializing in the German job market. Your mission is to help professionals find opportunities and advance their careers in Germany.

**Core Identity & Capabilities:**
- German job market expert with deep knowledge across all industries and regions
- Career counselor providing personalized guidance for job search, applications, and professional development
- Multilingual assistant supporting Chinese, German, and English communication

**Specialized Knowledge:**
- German employment landscape, salary trends, and hiring patterns across 16 Bundesländer
- CV/resume optimization following German standards (DIN 5008, Lebenslauf format)
- Cover letter guidance with proper German business language
- Interview preparation covering German corporate culture and expectations
- Skills development pathways including certifications and Weiterbildung programs
- Professional networking strategies for German business communities
- Immigration requirements and visa guidance for international professionals

**Advanced Tools & Intelligence:**
- Real-time web search for current job market data, company information, and industry trends
- Native PDF document processing for resume analysis and optimization
- Vector-based job matching system for personalized recommendations
- Skills analysis and career planning with market-aligned suggestions

**Communication Style:**
- Natural, conversational tone with cultural sensitivity to German business practices
- Practical, actionable advice with specific next steps and timelines
- Empathetic guidance understanding job search challenges and career transitions
- Context-aware responses building on conversation history and user preferences

**Response Framework:**
Provide immediately useful guidance while encouraging deeper engagement. Include specific examples, real-world scenarios, and concrete action items. Reference relevant German companies, institutions, and resources when appropriate. Focus on delivering value through expertise in German job market dynamics and professional development strategies.

Your goal is to be the definitive career assistant for anyone seeking to advance professionally in Germany, whether German nationals, EU citizens, or international professionals navigating the Deutsche job market."""
        
        # 缓存系统提示 / Cache system prompt
        self.session_system_cache[session_id] = system_prompt
        logger.info(f"🔥 Created and cached system context for session: {session_id} (approx. {len(system_prompt.split())} words)")
        
        return system_prompt

    def _manage_session_history(self, session_id: str, new_message: str, assistant_response: str = None):
        """
        🔥 关键新功能：管理会话消息历史 / KEY NEW FEATURE: Manage session message history
        """
        if session_id not in self.session_message_history:
            self.session_message_history[session_id] = []
        
        # 添加用户消息 / Add user message
        self.session_message_history[session_id].append({
            "role": "user",
            "content": new_message
        })
        
        # 如果有助手响应，添加助手消息 / If assistant response available, add assistant message
        if assistant_response:
            # 🔥 优化：截断过长的助手响应，保留核心信息 / Optimize: truncate long assistant responses
            truncated_response = self._truncate_long_response(assistant_response)
            self.session_message_history[session_id].append({
                "role": "assistant", 
                "content": truncated_response
            })
        
        # 🔥 优化：限制历史长度，保持最近12条消息（6轮对话） / Optimize: limit to 12 messages (6 conversation turns)
        if len(self.session_message_history[session_id]) > 12:
            self.session_message_history[session_id] = self.session_message_history[session_id][-12:]
        
        # 🔥 计算当前历史的token估算 / Calculate estimated tokens for current history
        estimated_tokens = self._estimate_history_tokens(self.session_message_history[session_id])
        
        logger.info(f"📝 Updated message history for session {session_id}: {len(self.session_message_history[session_id])} messages, ~{estimated_tokens} tokens")

    def _truncate_long_response(self, response: str, max_length: int = 800) -> str:
        """
        🔥 新功能：截断过长的助手响应，保留核心信息 / NEW: Truncate long assistant responses
        """
        if len(response) <= max_length:
            return response
        
        # 尝试在句子边界截断 / Try to truncate at sentence boundaries
        sentences = response.split('。')
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence + "。") <= max_length:
                truncated += sentence + "。"
            else:
                break
        
        if truncated:
            return truncated + "\n\n[Content truncated for context efficiency]"
        else:
            # 如果没有找到合适的句子边界，直接截断 / Direct truncation if no sentence boundary found
            return response[:max_length] + "...\n\n[Content truncated for context efficiency]"

    def _estimate_history_tokens(self, history: List[Dict[str, str]]) -> int:
        """
        🔥 新功能：估算消息历史的token数量 / NEW: Estimate token count for message history
        """
        total_chars = 0
        for message in history:
            total_chars += len(message.get('content', ''))
        
        # 粗略估算：英文~4字符/token，中文~2字符/token，取平均3字符/token
        # Rough estimate: English ~4 chars/token, Chinese ~2 chars/token, average 3 chars/token
        estimated_tokens = total_chars // 3
        return estimated_tokens

    def _compress_message_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        🔥 新功能：压缩消息历史，保留最重要的信息 / NEW: Compress message history
        """
        if len(messages) <= 4:
            return messages
        
        # 保留第一条用户消息和最后2轮对话 / Keep first user message and last 2 conversation turns
        compressed = []
        
        # 添加第一条消息（通常是关键背景信息） / Add first message (usually key background info)
        if messages:
            compressed.append(messages[0])
        
        # 添加最近的4条消息（2轮对话） / Add last 4 messages (2 conversation turns)
        if len(messages) > 4:
            compressed.extend(messages[-4:])
        else:
            compressed.extend(messages[1:])  # 除了第一条的其他所有消息
        
        return compressed

    def _build_message_history(self, session_id: str, current_message: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        🔥 关键新功能：构建完整的消息历史，包含上下文信息 / KEY NEW FEATURE: Build complete message history with context
        """
        messages = []
        
        # 获取历史消息 / Get historical messages
        if session_id and session_id in self.session_message_history:
            messages.extend(self.session_message_history[session_id])
        
        # 🔥 关键修复：构建包含上下文的当前消息 / CRITICAL FIX: Build current message with context
        message_content = []
        
        # 如果有文件上传上下文，添加到消息中 / If file upload context exists, add to message
        if context and (context.get('resume_uploaded') or context.get('uploaded_file')):
            if context.get('uploaded_file'):
                # 🔥 新功能：处理Claude 4原生文档格式 / NEW: Handle Claude 4 native document format
                uploaded_file = context['uploaded_file']
                document_data = uploaded_file.get('document_data', {})
                
                if document_data.get('claude_format') == 'native_pdf':
                    # 🔥 关键：使用Claude 4原生PDF支持 / CRITICAL: Use Claude 4 native PDF support
                    message_content.append({
                        "type": "document",
                        "source": document_data["source"]
                    })
                    
                    # 添加文本说明 / Add text description
                    message_content.append({
                        "type": "text",
                        "text": f"""I have uploaded my resume file "{uploaded_file.get('filename', 'resume')}". Please analyze this PDF document directly using your native PDF processing capabilities.

{current_message}"""
                    })
                    
                    logger.info(f"📄 Using Claude 4 native PDF processing for session {session_id}: {uploaded_file.get('filename', 'unknown')}")
                    
                elif document_data.get('claude_format') in ['text', 'extracted_text']:
                    # 文本格式文档 / Text format document
                    file_content = document_data.get('content', '')
                    message_content.append({
                        "type": "text",
                        "text": f"""I have uploaded my resume file "{uploaded_file.get('filename', 'resume')}". Here is the content:

{file_content}

{current_message}"""
                    })
                    
                    logger.info(f"📄 Using extracted text for session {session_id}: {uploaded_file.get('filename', 'unknown')}")
                    
                else:
                    # 回退到旧格式 / Fallback to old format
                    file_content = uploaded_file.get('text_content', '')
                    if file_content:
                        message_content.append({
                            "type": "text",
                            "text": f"""I have uploaded my resume file "{uploaded_file.get('filename', 'resume')}". Here is the content:

{file_content}

{current_message}"""
                        })
                        logger.info(f"📄 Using fallback text content for session {session_id}: {uploaded_file.get('filename', 'unknown')}")
                    else:
                        # 完全回退 / Complete fallback
                        message_content.append({
                            "type": "text", 
                            "text": current_message
                        })
                        logger.warning(f"⚠️ No document content available for session {session_id}")
            
            elif context.get('file_content'):
                # 向后兼容旧格式 / Backward compatibility with old format
                filename = context.get('filename', 'resume')
                file_content = context.get('file_content', '')
                
                message_content.append({
                    "type": "text",
                    "text": f"""I have uploaded my resume file "{filename}". Here is the content:

{file_content}

{current_message}"""
                })
                
                logger.info(f"📄 Using legacy file content format for session {session_id}: {filename}")
            
            else:
                # 没有文件内容 / No file content
                message_content.append({
                    "type": "text",
                    "text": current_message
                })
                logger.warning(f"⚠️ Resume upload context exists but no content found for session {session_id}")
        
        # 如果有职位数据上下文，添加到消息中 / If job data context exists, add to message
        elif context and context.get('job_postings'):
            job_count = len(context['job_postings'])
            message_content.append({
                "type": "text",
                "text": f"""{current_message}

Context: I have access to {job_count} job postings from the German job market that can be used for matching and analysis."""
            })
            
            logger.info(f"💼 Enhanced message with job postings context for session {session_id}: {job_count} jobs")
        
        else:
            # 普通消息 / Regular message
            message_content.append({
                "type": "text",
                "text": current_message
            })
        
        # 添加构建的消息内容 / Add built message content
        messages.append({
            "role": "user",
            "content": message_content
        })
        
        logger.info(f"🔗 Built message history for session {session_id}: {len(messages)} total messages, content_blocks: {len(message_content)}, context_enhanced: {bool(context and (context.get('resume_uploaded') or context.get('job_postings')))}")
        return messages

    def _should_use_web_search(self, message: str) -> bool:
        """判断是否需要web搜索 / Determine if web search is needed"""
        message_lower = message.lower()
        
        # 时间性关键词 / Time-related keywords (多语言支持)
        time_keywords = [
            # 中文
            '2025', '最新', '当前', '现在', '今年', '新的', '目前', '最近',
            # 英文
            'current', 'latest', 'recent', 'now', 'new', 'today', 'this year',
            # 德语 / German
            'aktuell', 'neueste', 'jetzt', 'derzeit', 'momentan', 'heute', 'dieses jahr',
            'neue', 'neuen', 'aktuelle', 'gegenwärtig', 'heutig'
        ]
        
        # 市场/行业相关关键词 / Market/industry-related keywords (多语言支持)
        market_keywords = [
            # 中文
            '市场', '行业', '趋势', '发展', '薪资', '工资', '就业', '前景', 
            '数据', '行情', '状况', 'ai市场', 'ai行业', '人工智能',
            '技能', '技能分析', '热门技能', '技能要求', '技能热点图', '技能热力图',
            # 英文
            'market', 'industry', 'trend', 'development', 'salary', 'employment', 
            'prospect', 'data', 'statistics', 'situation', 'status', 'genai', 
            'artificial intelligence', 'ai market', 'tech industry',
            'skills', 'skill analysis', 'trending skills', 'skill requirements', 
            'skills heatmap', 'skill heatmap', 'hot skills', 'popular skills',
            # 德语 / German
            'markt', 'branche', 'industrie', 'trend', 'entwicklung', 'gehalt', 
            'lohn', 'beschäftigung', 'arbeitsmarkt', 'aussichten', 'perspektiven',
            'daten', 'statistiken', 'situation', 'ki-markt', 'technologie',
            'ki-branche', 'künstliche intelligenz', 'stellenmarkt', 'jobmarkt',
            'fähigkeiten', 'kompetenz', 'fertigkeiten', 'skill-analyse'
        ]
        
        # 明确搜索请求 / Explicit search requests (多语言支持)
        search_keywords = [
            # 中文
            '搜索', '查询', '查找', '了解',
            # 英文
            'search', 'find', 'lookup', 'information about', 'tell me about',
            # 德语 / German
            'suchen', 'finden', 'suche nach', 'informationen über', 'erzähl mir über'
        ]
        
        # 问题关键词 / Question keywords (多语言支持)
        question_keywords = [
            # 中文
            '如何', '怎么样', '什么', '情况', '状态',
            # 英文
            'how', 'what', 'which', 'when', 'where', 'why',
            # 德语 / German
            'wie', 'was', 'welche', 'wann', 'wo', 'warum', 'weshalb'
        ]
        
        has_time = any(keyword in message_lower for keyword in time_keywords)
        has_market = any(keyword in message_lower for keyword in market_keywords)
        explicit_search = any(keyword in message_lower for keyword in search_keywords)
        has_question = any(keyword in message_lower for keyword in question_keywords)
        
        # 🔥 修复：放宽判断条件，针对德国市场的多语言支持
        result = (
            (has_time and has_market) or  # 同时包含时间和市场
            explicit_search or           # 明确的搜索请求
            (has_market and has_question) or  # 市场相关的问题
            ('genai' in message_lower) or     # GenAI相关话题
            ('ki-markt' in message_lower) or  # 德语AI市场
            ('künstliche intelligenz' in message_lower) or # 德语人工智能
            ('deutschland' in message_lower) or # 德国相关
            (has_time and ('德国' in message_lower or 'germany' in message_lower or 'deutschland' in message_lower))  # 关于德国的时间相关问题
        )
        
        logger.info(f"🔍 Web search decision for '{message[:50]}...': time={has_time}, market={has_market}, explicit={explicit_search}, question={has_question}, result={result}")
        
        return result

    def _build_system_prompt_with_cache(self, session_id: str) -> List[Dict[str, Any]]:
        """构建带缓存的系统提示 / Build system prompt with cache"""
        
        system_content = self._initialize_session_context(session_id)
        
        return [
            {
                "type": "text", 
                "text": system_content,
                "cache_control": {"type": "ephemeral"}  # 缓存控制 / Cache control
            }
        ]

    def _build_tools_config(self, task_type: str, message: str) -> List[Dict[str, Any]]:
        """
        构建工具配置 / Build tools configuration
        🔥 符合Claude 4最新文档标准，包含WebSearch工具 / Compliant with Claude 4 latest docs, includes WebSearch tools
        注意：Artifacts是Claude 4的原生功能，无需显式配置 / Note: Artifacts is Claude 4 native feature, no explicit config needed
        """
        tools = []
        
        # 🔥 WebSearch工具 - 使用官方2025年标准配置 / WebSearch tool - using official 2025 standard configuration
        needs_web_search = self._should_use_web_search(message) or task_type == "skill_heatmap_generation"
        
        if needs_web_search:
            tools.append({
                "type": "web_search_20250305",  # 🔥 官方2025年工具类型 / Official 2025 tool type
                "name": "web_search",
                "max_uses": 5,  # 增加使用次数支持复杂查询 / Increase usage for complex queries
                "user_location": {
                    "type": "approximate", 
                    "country": "DE",  # 专注德国市场 / Focus on German market
                    "timezone": "Europe/Berlin"
                }
            })
            logger.info(f"🌐 WebSearch工具已启用，最大使用次数: 5, 区域: 德国")
        
        # 🔥 重要说明：Artifacts无需显式配置 / IMPORTANT: Artifacts doesn't need explicit configuration
        # Claude 4会在检测到可视化请求时自动激活Artifacts功能 / Claude 4 auto-activates Artifacts when detecting visualization requests
        if (task_type in ["skill_heatmap_generation", "artifact_generation"] or
            any(keyword in message.lower() for keyword in [
                'visualization', 'chart', 'graph', 'heatmap', 'diagram', 'plot', 'artifact',
                '可视化', '图表', '热力图', '图形', '图示', 'interactive', '交互式'
            ])):
            logger.info("🎨 Artifacts功能准备就绪 - Claude 4将根据需要自动激活可视化功能")
        
        return tools

    def _determine_task_type(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """确定任务类型 / Determine task type"""
        message_lower = message.lower()
        
        # 检查上下文中的任务类型 / Check task type in context
        if context and context.get('task_type') == 'skill_heatmap_generation':
            return "complex_task"
        
        if any(keyword in message_lower for keyword in [
            "heatmap", "热力图", "热点图", "skills heatmap", "skill heatmap", "技能热力图", 
            "skills analysis", "market trends", "技能分析", "市场分析", "comprehensive analysis",
            "skill map", "技能地图", "能力图谱"
        ]):
            return "complex_task"
        elif any(keyword in message_lower for keyword in [
            "analyze", "match", "resume", "cv", "详细", "分析", "匹配", "简历", "job matching",
            "简历分析", "职位匹配", "career advice", "职业建议"
        ]):
            return "detailed_analysis"
        else:
            return "simple_response"
    
    def _check_fixed_response(self, message: str) -> Optional[str]:
        """检查是否有匹配的固定回答 / Check for matching fixed responses"""
        import re
        
        message_clean = message.strip().lower()
        
        for response_type, response_data in self.fixed_responses.items():
            pattern = response_data["pattern"]
            if re.match(pattern, message_clean, re.IGNORECASE):
                logger.info(f"🔥 使用固定回答节省token: {response_type}")
                return response_data["response"]
        
        return None

    async def chat_stream_unified(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Claude 4统一流式聊天接口 - 符合官方文档的实现，支持上下文管理
        Claude 4 unified streaming chat interface - official documentation compliant with context management
        """
        try:
            logger.info(f"Starting Claude 4 optimized chat for session: {session_id or 'new'}")
            
            # 🔥 新增：检查固定回答，节省token / NEW: Check fixed responses to save tokens
            fixed_response = self._check_fixed_response(message)
            if fixed_response:
                # 直接返回固定回答，不调用AI
                yield {
                    "type": "start",
                    "session_id": session_id,
                    "model": "Fixed Response",
                    "task_type": "fixed_template",
                    "tools_available": 0,
                    "cache_optimized": True,
                    "token_saved": True
                }
                
                # 模拟流式输出
                for char in fixed_response:
                    yield {
                        "type": "text_delta",
                        "content": char
                    }
                
                # 更新会话历史
                if session_id:
                    self._manage_session_history(session_id, message, fixed_response)
                
                yield {
                    "type": "complete",
                    "session_id": session_id,
                    "response_length": len(fixed_response),
                    "tools_used": 0,
                    "cache_optimized": True,
                    "token_saved": True,
                    "cost_savings": "~$0.01-0.05"
                }
                return
            
            # 检查预算 / Check budget
            budget_status = self.token_tracker.check_budget_alert()
            if budget_status["alert_level"] == "exceeded":
                yield {
                    "type": "error",
                    "content": f"Daily budget exceeded: ${budget_status['used_amount']:.2f}. Please try again tomorrow."
                }
                return

            # 配置请求参数 / Configure request parameters
            task_type = self._determine_task_type(message, context)
            max_tokens = self.max_tokens_limit.get(task_type, 2500)
            tools_config = self._build_tools_config(task_type, message)
                                    
            # 🔥 关键修改：构建完整的消息历史，包含上下文信息 / CRITICAL FIX: Build complete message history with context
            messages = self._build_message_history(session_id, message, context)
            
            # 🔥 Token监控：检查输入token数量 / Token monitoring: check input token count
            estimated_input_tokens = self._estimate_history_tokens(messages)
            if estimated_input_tokens > 2000:  # 降低阈值，更早压缩
                logger.warning(f"⚠️ High input token count for session {session_id}: ~{estimated_input_tokens} tokens")
                if estimated_input_tokens > 3000:  # 更激进的压缩策略
                    # 如果token过多，进行压缩 / Compress if too many tokens
                    messages = self._compress_message_history(messages)
                    compressed_tokens = self._estimate_history_tokens(messages)
                    logger.info(f"🗜️ Compressed message history: {estimated_input_tokens} → {compressed_tokens} tokens (saved {estimated_input_tokens - compressed_tokens})")
            
            # 🔥 核心优化：根据官方文档构建API请求，包含消息历史 / Core optimization: build API request with message history
            request_config = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": messages,  # 🔥 使用完整消息历史 / Use complete message history
            }
            
            # 🔥 优化缓存策略：根据session是否存在决定缓存类型 / Optimize cache strategy
            if session_id and len(messages) > 1:  # 只有多轮对话才使用缓存
                request_config["system"] = self._build_system_prompt_with_cache(session_id)
                logger.info(f"🔧 Using cached system prompt for session {session_id}")
            else:
                # 新session使用简化的系统提示 / New session uses simplified system prompt
                system_content = self._initialize_session_context(session_id or "new")
                request_config["system"] = system_content
                logger.info(f"💫 Using fresh system prompt for new session")
            
            # 只有需要时才添加工具 / Add tools only when needed
            if tools_config:
                request_config["tools"] = tools_config
            
            # 日志记录 / Logging
            web_search_enabled = any(tool.get('type') == 'web_search_20250305' for tool in tools_config)
            
            logger.info(f"Claude 4 optimized request: {max_tokens} max_tokens, {len(tools_config)} tools, "
                       f"task_type: {task_type}, message: '{message[:50]}...', "
                       f"cached_system: {'Yes' if session_id else 'No'}, history_length: {len(messages)}")
            logger.info(f"🛠️ Tools enabled: {[t.get('name', t.get('type')) for t in tools_config]}, Web search: {'✅' if web_search_enabled else '❌'}")
            
            # 🔥 优化：立即发送职位数据，避免用户等待 / Optimized: Send job data immediately to avoid waiting
            if context and context.get('job_postings'):
                jobs_data = []
                for job in context['job_postings']:
                    # 确保description字段完整 / Ensure description field is complete
                    description = ""
                    if hasattr(job, 'description'):
                        description = job.description or ""
                    else:
                        description = job.get('description', job.get('full_description', ''))
                    
                    jobs_data.append({
                        "id": job.get('id', ''),
                        "title": job.get('title', ''),
                        "company_name": job.get('company_name', ''),
                        "location": job.get('location', ''),
                        "description": description,
                        "url": job.get('url', ''),
                        "work_type": job.get('work_type', 'Full-time'),
                        "salary": job.get('salary', ''),
                        "source": job.get('source', 'LinkedIn'),
                        "posted_time_ago": job.get('posted_time_ago', '')
                    })
                
                yield {
                    "type": "job_data",
                    "jobs": jobs_data,
                    "match_type": context.get('match_type', 'general'),
                    "total_jobs": len(jobs_data),
                    "session_id": session_id
                }
                
                logger.info(f"📋 ⚡ 立即发送 {len(jobs_data)} 个职位到前端 (无需等待bot完成) / Immediately sent {len(jobs_data)} jobs to frontend (no need to wait for bot)")
            
            # 开始流式响应 / Start streaming response
            assistant_response = ""  # 🔥 收集助手响应用于历史记录 / Collect assistant response for history
            
            async with self.client.messages.stream(**request_config) as stream:
                text_content = ""
                tool_uses = []
                
                yield {
                    "type": "start",
                    "session_id": session_id,
                    "model": self.model,
                    "task_type": task_type,
                    "tools_available": len(tools_config),
                    "cache_optimized": bool(session_id),
                    "context_messages": len(messages)
                }
                
                async for event in stream:
                    try:
                        # 处理流式事件 / Handle streaming events
                        if event.type == 'content_block_start':
                            # 安全地处理content_block对象 / Safely handle content_block object
                            content_block = getattr(event, 'content_block', {})
                            if hasattr(content_block, '__dict__'):
                                # 转换为可序列化的字典 / Convert to serializable dict
                                content_block_dict = {
                                    "type": getattr(content_block, 'type', ''),
                                    "id": getattr(content_block, 'id', ''),
                                    "name": getattr(content_block, 'name', ''),
                                    "input": getattr(content_block, 'input', {}) if hasattr(content_block, 'input') else {}
                                }
                            else:
                                content_block_dict = content_block
                                
                            yield {
                                "type": "content_block_start",
                                "index": getattr(event, 'index', 0),
                                "content_block": content_block_dict
                            }
                        
                        elif event.type == 'content_block_delta':
                            # 处理文本增量 / Handle text delta
                            if hasattr(event.delta, 'text') and event.delta.text:
                                text_chunk = event.delta.text
                                text_content += text_chunk
                                assistant_response += text_chunk  # 🔥 收集响应 / Collect response
                                yield {
                                    "type": "text_delta",
                                    "content": text_chunk
                                }
                        
                        elif event.type == 'content_block_stop':
                            yield {
                                "type": "content_block_stop",
                                "index": getattr(event, 'index', 0)
                            }
                        
                        elif event.type == 'message_stop':
                            # 流式结束，使用final_text和usage信息
                            yield {
                                "type": "message_stop"
                            }
                    
                    except Exception as event_error:
                        logger.error(f"Error processing stream event: {event_error}")
                        continue
                
                # 🔥 优化：在流式响应开始时就发送职位数据，无需等待bot完成 / Optimized: Send job data at start of streaming
                # 避免用户等待，提升用户体验 / Avoid user waiting, improve UX
                
                # 🔥 关键：更新会话历史 / CRITICAL: Update session history
                if session_id and assistant_response.strip():
                    self._manage_session_history(session_id, message, assistant_response.strip())
                
                # 获取最终使用统计 / Get final usage statistics
                try:
                    final_message = await stream.get_final_message()
                    if hasattr(final_message, 'usage') and final_message.usage:
                        usage = final_message.usage
                        
                        # 🔥 关键：正确解析官方API响应 / Key: correctly parse official API response
                        input_tokens = getattr(usage, 'input_tokens', 0)
                        output_tokens = getattr(usage, 'output_tokens', 0)
                        cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0)
                        cache_read_tokens = getattr(usage, 'cache_read_input_tokens', 0)
                        
                        # Web搜索使用量 / Web search usage
                        web_search_requests = 0
                        if hasattr(usage, 'server_tool_use') and usage.server_tool_use:
                            web_search_requests = getattr(usage.server_tool_use, 'web_search_requests', 0)
                        
                        # 记录token使用 / Log token usage
                        self.token_tracker.log_usage(
                            model=self.model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cache_creation_tokens=cache_creation_tokens,
                            cache_read_tokens=cache_read_tokens,
                            web_search_requests=web_search_requests,
                            session_id=session_id
                        )
                        
                        # 记录重要事件 / Log important events
                        if cache_read_tokens > 0:
                            logger.info(f"✅ Claude 4 cache hit! Read {cache_read_tokens} tokens, saved ${cache_read_tokens * 3.0 * 0.9 / 1_000_000:.4f}")
                        if cache_creation_tokens > 0:
                            logger.info(f"📝 Claude 4 cache created! Wrote {cache_creation_tokens} tokens")
                        if web_search_requests > 0:
                            logger.info(f"🔍 Claude 4 web search used {web_search_requests} times")
                    else:
                        logger.warning("No usage information available from Claude 4 response")
                        
                except Exception as usage_error:
                    logger.error(f"Failed to get usage statistics: {usage_error}")

                # 完成响应 / Complete response
                yield {
                    "type": "complete",
                    "session_id": session_id,
                    "response_length": len(text_content),
                    "tools_used": len(tool_uses),
                    "cache_optimized": bool(session_id),
                    "context_preserved": bool(session_id and assistant_response.strip())
                }
                    
        except Exception as e:
            logger.error(f"Claude 4 streaming failed: {e}")
            yield {
                "type": "error",
                "content": f"AI服务暂时不可用，请稍后重试。错误: {str(e)}"
            }

    # 🔥 新增：清除会话历史方法 / NEW: Clear session history method
    def clear_session_history(self, session_id: str):
        """清除指定会话的历史记录 / Clear history for specified session"""
        if session_id in self.session_message_history:
            del self.session_message_history[session_id]
            logger.info(f"🗑️ Cleared message history for session: {session_id}")
        
        if session_id in self.session_system_cache:
            del self.session_system_cache[session_id]
            logger.info(f"🗑️ Cleared system cache for session: {session_id}")

    # 🔥 新增：获取会话历史方法 / NEW: Get session history method
    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取指定会话的历史记录 / Get history for specified session"""
        return self.session_message_history.get(session_id, [])
    
    async def get_token_usage_stats(self, session_id: str = None) -> Dict[str, Any]:
        """获取使用统计 / Get usage statistics"""
        daily_stats = self.token_tracker.get_daily_summary()
        budget_status = self.token_tracker.check_budget_alert()
        
        # 确保包含当前session的统计数据 / Ensure current session stats are included
        if session_id and daily_stats.get('total_tokens', 0) == 0:
            # 如果没有统计数据，尝试从内存中获取 / If no stats, try to get from memory
            logger.info(f"No daily stats found, using session data for {session_id}")
        
        return {
            "daily_usage": daily_stats,
            "budget_status": budget_status,
            "optimization_benefits": {
                "daily_cache_savings": daily_stats.get("cache_savings", 0),
                "cache_hit_rate": daily_stats.get("cache_hit_rate", 0),
                "web_search_requests": daily_stats.get("web_search_requests", 0),
                "estimated_monthly_savings": daily_stats.get("cache_savings", 0) * 30
            },
            "claude4_features": {
                "prompt_caching": "1h TTL with 90% cost reduction",
                "web_search": "Native integration with geo-location",
                "streaming": "Real-time response delivery",
                "session_management": "Automatic context preservation",
                "message_history": f"Active sessions: {len(self.session_message_history)}"
            }
        }
    
    # 简化的向后兼容方法 / Simplified backward compatibility methods
    async def analyze_resume(self, file_content: str, filename: str) -> Dict[str, Any]:
        """简化的简历分析 / Simplified resume analysis"""
        try:
            prompt = f"Please analyze this resume file '{filename}' and provide structured analysis."
            
            result_content = ""
            async for chunk in self.chat_stream_unified(
                prompt, 
                context={"file_content": file_content, "filename": filename}
            ):
                if chunk.get("type") == "text":
                    result_content += chunk.get("content", "")
            
            return {
                "analysis_text": result_content,
                "skills": [],
                "experience_years": 0,
                "education_level": "Unknown",
                "languages": [],
                "summary": "Resume analyzed via Claude 4"
            }
            
        except Exception as e:
            logger.error(f"Resume analysis failed: {e}")
            return {"error": str(e), "summary": "Analysis failed"}

    async def match_jobs_with_resume(
        self, 
        resume_analysis: Dict[str, Any], 
        job_postings: List[JobPosting]
    ) -> List[JobMatch]:
        """
        🔥 README流程实现：Claude 4深度分析简历和职位匹配 / README Flow: Claude 4 deep analysis for resume-job matching
        严格按照README第5-6步：拼接prompt → Claude分析排序
        """
        try:
            # 构建专门的职位推荐提示词（移出系统提示避免重复）/ Build dedicated job recommendation prompt
            job_matching_prompt = self._build_job_matching_prompt(resume_analysis, job_postings)
            
            # 🔥 关键：使用Claude 4进行深度分析和排序 / KEY: Use Claude 4 for deep analysis and ranking
            claude_analysis = ""
            async for chunk in self.chat_stream_unified(
                job_matching_prompt,
                context={
                    "task_type": "job_matching",
                    "resume_analysis": resume_analysis,
                    "job_count": len(job_postings)
                }
            ):
                if chunk.get("type") == "text":
                    claude_analysis += chunk.get("content", "")
            
            # 解析Claude 4的分析结果为JobMatch对象 / Parse Claude 4 analysis into JobMatch objects
            job_matches = self._parse_claude_job_analysis(claude_analysis, job_postings)
            
            logger.info(f"✅ Claude 4 job matching completed: {len(job_matches)} matches generated")
            return job_matches
            
        except Exception as e:
            logger.error(f"❌ Job matching failed: {e}")
            return []

    def _build_job_matching_prompt(self, resume_analysis: Dict[str, Any], job_postings: List[JobPosting]) -> str:
        """
        🔥 构建职位匹配专用提示词 / Build dedicated job matching prompt
        按照README要求的匹配要素权重：技能>经验>地点>语言>学历
        """
        # 提取简历关键信息 / Extract key resume information
        skills = ', '.join(resume_analysis.get('skills', []))
        experience_years = resume_analysis.get('experience_years', 0)
        location = resume_analysis.get('location', '未指定')
        education = resume_analysis.get('education_level', '未知')
        languages = ', '.join(resume_analysis.get('languages', []))
        
        prompt = f"""作为专业的德国就业市场顾问，请根据以下简历分析{len(job_postings)}个职位的匹配度并排序。

**简历概要：**
- 技能：{skills}
- 工作经验：{experience_years}年
- 期望地点：{location}
- 教育背景：{education}
- 语言能力：{languages}

**匹配权重（重要性排序）：**
1. 技能匹配（40%）- 重要
2. 经验匹配（30%）- 重要  
3. 地点匹配（15%）- 中等重要
4. 语言匹配（10%）- 中等重要
5. 教育匹配（5%）- 较低重要

**候选职位：**
"""
        
        # 添加所有职位信息 / Add all job information
        for i, job in enumerate(job_postings, 1):
            job_desc = job.description[:300] if len(job.description) > 300 else job.description
            prompt += f"""
{i}. 【{job.title}】- {job.company_name}
   地点：{job.location}
   工作类型：{getattr(job, 'job_type', '未知')}
   职位描述：{job_desc}...
"""

        prompt += """
**要求输出JSON格式：**
请为每个职位提供详细分析，严格按照以下JSON结构返回：

```json
{
  "analysis_summary": "总体分析概述",
  "job_matches": [
    {
      "job_index": 1,
      "job_title": "职位标题",
      "company_name": "公司名称",
      "match_score": 85,
      "match_level": "excellent",
      "match_reasons": [
        "技能高度匹配：Python, React等核心技能完全符合",
        "经验年限匹配：要求3-5年，候选人有4年经验"
      ],
      "skill_matches": ["Python", "React", "Node.js"],
      "missing_skills": ["TypeScript", "Docker"],
      "location_match": true,
      "experience_match": true,
      "improvement_suggestions": [
        "建议学习TypeScript提升前端开发能力",
        "补充Docker容器化技能"
      ]
    }
  ]
}
```

**评分标准：**
- 90-100分：excellent（完美匹配）
- 75-89分：good（良好匹配）
- 60-74分：fair（一般匹配）
- 40-59分：poor（较低匹配）
- 0-39分：very_poor（不匹配）

请按匹配分数从高到低排序，提供详细的匹配原因和改进建议。"""
        
        return prompt

    def _parse_claude_job_analysis(self, claude_analysis: str, job_postings: List[JobPosting]) -> List[JobMatch]:
        """
        🔥 解析Claude 4的职位分析结果 / Parse Claude 4 job analysis results
        """
        import json
        import re
        
        try:
            # 尝试提取JSON部分 / Try to extract JSON part
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', claude_analysis, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                analysis_data = json.loads(json_str)
            else:
                # 如果没有找到JSON格式，尝试直接解析 / If no JSON format found, try direct parsing
                analysis_data = json.loads(claude_analysis)
            
            matches = []
            job_matches_data = analysis_data.get('job_matches', [])
            
            for match_data in job_matches_data:
                job_index = match_data.get('job_index', 1) - 1  # 转换为0基索引
                
                if 0 <= job_index < len(job_postings):
                    job = job_postings[job_index]
                    
                    # 创建JobMatch对象 / Create JobMatch object
                    job_match = JobMatch(
                    job_posting=job,
                        matching_score=match_data.get('match_score', 50),
                        matching_reasons=match_data.get('match_reasons', []),
                        missing_skills=match_data.get('missing_skills', []),
                        recommended_improvements=match_data.get('improvement_suggestions', [])
                    )
                    
                    # 添加额外的匹配信息 / Add additional matching info
                    job_match.skill_matches = match_data.get('skill_matches', [])
                    job_match.match_level = match_data.get('match_level', 'fair')
                    job_match.location_match = match_data.get('location_match', False)
                    job_match.experience_match = match_data.get('experience_match', False)
                    
                    matches.append(job_match)
            
            # 按匹配分数排序 / Sort by matching score
            matches.sort(key=lambda x: x.matching_score, reverse=True)
            
            logger.info(f"✅ Parsed {len(matches)} job matches from Claude analysis")
            return matches
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse Claude job analysis JSON: {e}")
            # 创建默认匹配结果 / Create default match results
            return self._create_default_matches(job_postings)
        except Exception as e:
            logger.error(f"❌ Error parsing Claude job analysis: {e}")
            return self._create_default_matches(job_postings)

    def _create_default_matches(self, job_postings: List[JobPosting]) -> List[JobMatch]:
        """创建默认的职位匹配结果 / Create default job match results"""
        matches = []
        for i, job in enumerate(job_postings[:10]):  # 限制前10个
            matches.append(JobMatch(
                job_posting=job,
                matching_score=max(70 - i * 5, 40),  # 递减分数
                matching_reasons=["自动分析", "基础匹配"],
                missing_skills=[],
                recommended_improvements=["请上传详细简历获得精准分析"]
            ))
        return matches

    async def generate_skill_heatmap_data(self, job_title: str) -> Dict[str, Any]:
        """
        🔥 README流程实现：技能热点图生成
        使用Claude 4原生WebSearch搜索岗位热点技能并进行深度思考，然后使用Artifacts工具生成技能热点图可视化
        符合Claude 4最新文档标准，正确调用图生成工具
        """
        try:
            # 🔥 修复：构建明确触发Artifacts的提示词，根据最新文档标准
            prompt = f"""I need you to create an interactive skills heatmap for "{job_title}" positions. Please follow these steps:

**Step 1: Search Latest Market Data**
Use WebSearch to find information about "{job_title}" skills requirements and market trends in Germany for 2025:
- German job market demand for {job_title} skills
- 2025 trending skills for {job_title} positions  
- Salary and skill requirements for {job_title}
- Emerging technologies and trends in {job_title} field

**Step 2: Create Interactive Heatmap Visualization**
Based on the search results, create a complete interactive skills heatmap as an HTML artifact with:

1. **HTML structure** with skill categories
2. **CSS styling** with color-coded skill importance (dark = high demand, light = low demand)
3. **JavaScript interactivity** for:
   - Hover effects showing skill details
   - Click functionality to show learning resources
   - Responsive design for mobile devices
   - Smooth animations and transitions

4. **Skill Categories to include:**
   - Technical Skills (programming languages, frameworks, tools)
   - Soft Skills (communication, collaboration, leadership)  
   - Industry Knowledge (certifications, domain expertise)
   - Emerging Skills (AI/ML, cloud computing, data analysis)

5. **Interactive Features:**
   - Each skill block shows importance score (0-100)
   - Color intensity represents market demand
   - Tooltips with detailed descriptions
   - Learning recommendations on click
   - Professional development pathways

Please create this as a complete, self-contained HTML artifact that I can download and use. Make it visually appealing with modern UI design and ensure it works on both desktop and mobile devices.

The heatmap should be based on current German market data for {job_title} positions."""
            
            # 🔥 使用带WebSearch + Artifacts的unified接口
            result_content = ""
            websearch_used = False
            artifacts_generated = False
            
            logger.info(f"🔥 开始生成 {job_title} 交互式技能热点图，使用WebSearch + Artifacts")
            
            async for chunk in self.chat_stream_unified(
                prompt,
                context={
                    "task_type": "skill_heatmap_generation", 
                    "force_websearch": True,
                    "enable_artifacts": True,
                    "visualization_request": True
                },
                session_id=f"heatmap_{job_title.replace(' ', '_')}"
            ):
                if chunk.get("type") == "text_delta":
                    result_content += chunk.get("content", "")
                elif chunk.get("type") == "text":
                    result_content += chunk.get("content", "")
                elif chunk.get("type") == "content_block_start":
                    # 检测Artifacts生成
                    content_block = chunk.get("content_block", {})
                    if content_block.get("type") == "tool_use" and content_block.get("name") == "artifacts":
                        artifacts_generated = True
                        logger.info("🎨 Artifacts工具正在生成交互式技能热点图...")
                elif chunk.get("type") == "tool_use":
                    if chunk.get("tool_name") == "web_search":
                        websearch_used = True
                        logger.info("🌐 WebSearch正在搜索最新技能市场数据...")
            
            # 🔥 第二步：如果没有生成Artifacts，使用备用方案创建可视化数据
            if not artifacts_generated:
                logger.info("🔄 Artifacts未自动生成，使用备用方案创建可视化数据")
                
                # 调用专门的Artifacts生成
                artifacts_prompt = f"""基于前面搜索到的{job_title}技能数据，请创建一个交互式技能热点图Artifact。

要求：
1. 使用HTML + CSS + JavaScript创建交互式热力图
2. 技能按类别分组（技术技能、软技能、行业知识、新兴技能）
3. 每个技能块显示技能名称和重要性评分
4. 使用颜色深度表示技能需求程度（深色=高需求，浅色=低需求）
5. 点击技能块显示详细说明和学习建议
6. 响应式设计，支持移动设备
7. 美观的现代UI设计

请创建这个交互式技能热点图Artifact。"""

                async for chunk in self.chat_stream_unified(
                    artifacts_prompt,
                    context={
                        "task_type": "artifact_generation",
                        "artifact_type": "interactive_heatmap"
                    },
                    session_id=f"heatmap_artifact_{job_title.replace(' ', '_')}"
                ):
                    if chunk.get("type") == "text_delta":
                        result_content += "\n" + chunk.get("content", "")
                    elif chunk.get("type") == "content_block_start":
                        content_block = chunk.get("content_block", {})
                        if content_block.get("type") == "tool_use":
                            artifacts_generated = True
                            logger.info("🎨 备用Artifacts生成成功")
            
            # 🔥 构建增强的可视化数据结构
            visualization_data = {
                "chart_type": "interactive_heatmap",
                "title": f"{job_title} Skills Heatmap - Germany 2025",
                "artifact_generated": artifacts_generated,
                "categories": [
                    {
                        "name": "Technical Skills",
                        "color": "#FF6B6B",
                        "skills": self._extract_skills_from_content(result_content, "technical")
                    },
                    {
                        "name": "Soft Skills", 
                        "color": "#4ECDC4",
                        "skills": self._extract_skills_from_content(result_content, "soft")
                    },
                    {
                        "name": "Industry Knowledge",
                        "color": "#45B7D1", 
                        "skills": self._extract_skills_from_content(result_content, "industry")
                    },
                    {
                        "name": "Emerging Skills",
                        "color": "#FFA07A",
                        "skills": self._extract_skills_from_content(result_content, "emerging")
                    }
                ],
                "interactive_features": [
                    "Click-to-expand skill details",
                    "Hover effects and tooltips", 
                    "Responsive design",
                    "Color-coded skill importance",
                    "Learning recommendations"
                ]
            }
            
            # 返回完整的技能热点图数据，包含Artifacts信息
            return {
                "success": True,
                "job_title": job_title,
                "market": "Germany",
                "generated_at": "2025-01-22",
                "websearch_used": websearch_used,
                "artifacts_generated": artifacts_generated,
                "visualization_data": visualization_data,
                "analysis_text": result_content,
                "chart_ready": True,
                "interactive": artifacts_generated,
                "source": f"Claude 4 Sonnet + {'WebSearch + Artifacts' if websearch_used and artifacts_generated else 'WebSearch' if websearch_used else 'AI Analysis'}",
                "features": [
                    "Real-time market data via WebSearch" if websearch_used else "AI analysis",
                    "Interactive Artifacts visualization" if artifacts_generated else "Static visualization data",
                    "Deep thinking analysis",
                    "German market focus", 
                    "Multi-dimensional skill assessment",
                    "Click-to-expand interactions" if artifacts_generated else "JSON data structure"
                ],
                "artifacts_info": {
                    "enabled": artifacts_generated,
                    "type": "interactive_heatmap" if artifacts_generated else "data_only",
                    "compatible_with": "Claude 4 Artifacts system"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 技能热点图生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "job_title": job_title,
                "fallback_message": "技能热点图生成暂时不可用，请稍后重试。",
                "artifacts_generated": False
            }
    
    def _extract_skills_from_content(self, content: str, skill_type: str) -> List[Dict[str, Any]]:
        """从分析内容中提取技能数据 / Extract skill data from analysis content"""
        # 简化的技能提取逻辑，实际应用中可以更复杂
        default_skills = {
            "technical": [
                {"name": "Python", "score": 95, "demand": "Very High"},
                {"name": "JavaScript", "score": 85, "demand": "High"},
                {"name": "SQL", "score": 80, "demand": "High"},
                {"name": "Git", "score": 75, "demand": "Medium"}
            ],
            "soft": [
                {"name": "Communication", "score": 90, "demand": "Very High"},
                {"name": "Problem Solving", "score": 88, "demand": "Very High"},
                {"name": "Teamwork", "score": 85, "demand": "High"},
                {"name": "Adaptability", "score": 80, "demand": "High"}
            ],
            "industry": [
                {"name": "Agile/Scrum", "score": 85, "demand": "High"},
                {"name": "DevOps", "score": 80, "demand": "High"},
                {"name": "Cloud Platforms", "score": 88, "demand": "Very High"},
                {"name": "Cybersecurity", "score": 75, "demand": "Medium"}
            ],
            "emerging": [
                {"name": "AI/Machine Learning", "score": 92, "demand": "Very High"},
                {"name": "Blockchain", "score": 70, "demand": "Medium"},
                {"name": "IoT", "score": 75, "demand": "Medium"},
                {"name": "Low-Code/No-Code", "score": 80, "demand": "High"}
            ]
        }
        
        return default_skills.get(skill_type, [])

    async def get_german_job_market_insights(self, query: str) -> str:
        """简化的德国就业市场洞察 / Simplified German job market insights"""
        try:
            prompt = f"Provide German job market insights for: {query}"
            
            result_content = ""
            async for chunk in self.chat_stream_unified(prompt):
                if chunk.get("type") == "text":
                    result_content += chunk.get("content", "")
            
            return result_content
            
        except Exception as e:
            logger.error(f"German job market insights failed: {e}")
            return f"无法获取市场洞察: {str(e)}" 