"""
Claude 4 Sonnet AI服务 / Claude 4 Sonnet AI service
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic
from ..core.config import settings
from ..models.job import JobPosting, JobMatch
from ..models.user import ResumeAnalysis
import logging
import json

logger = logging.getLogger(__name__)


class ClaudeService:
    """Claude 4 Sonnet AI服务类 / Claude 4 Sonnet AI service class"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        
    async def analyze_resume(self, file_content: str, filename: str) -> Dict[str, Any]:
        """
        分析简历内容 / Analyze resume content
        
        Args:
            file_content: 文件内容 / File content
            filename: 文件名 / Filename
            
        Returns:
            分析结果 / Analysis result
        """
        try:
            prompt = f"""
            请分析以下简历内容，并返回JSON格式的结构化信息:

            文件名: {filename}
            简历内容:
            {file_content}

            请提取以下信息并以JSON格式返回:
            {{
                "skills": ["技能1", "技能2", ...],
                "experience_years": 工作年限数字,
                "education_level": "学历水平",
                "languages": ["语言1", "语言2", ...],
                "preferred_location": "期望工作地点",
                "core_competencies": ["核心竞争力1", "核心竞争力2", ...],
                "work_experience": [
                    {{
                        "company": "公司名",
                        "position": "职位",
                        "duration": "工作时长",
                        "description": "工作描述"
                    }}
                ],
                "education": [
                    {{
                        "institution": "学校",
                        "degree": "学位",
                        "field": "专业",
                        "year": "毕业年份"
                    }}
                ],
                "summary": "简历整体总结",
                "strengths": ["优势1", "优势2", ...],
                "improvement_suggestions": ["建议1", "建议2", ...]
            }}
            
            请确保返回的是有效的JSON格式。
            """
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 提取JSON内容 / Extract JSON content
            content = response.content[0].text
            
            # 尝试解析JSON / Try to parse JSON
            try:
                analysis_result = json.loads(content)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分 / If direct parsing fails, try to extract JSON part
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    analysis_result = json.loads(json_match.group())
                else:
                    raise ValueError("无法解析AI返回的JSON")
            
            logger.info(f"Successfully analyzed resume: {filename}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Resume analysis failed: {e}")
            return {
                "error": str(e),
                "skills": [],
                "experience_years": 0,
                "education_level": "未知",
                "languages": [],
                "preferred_location": None,
                "summary": "分析失败"
            }
    
    async def match_jobs_with_resume(
        self, 
        resume_analysis: Dict[str, Any], 
        job_postings: List[JobPosting]
    ) -> List[JobMatch]:
        """
        基于简历分析匹配职位 / Match jobs based on resume analysis
        
        Args:
            resume_analysis: 简历分析结果 / Resume analysis result
            job_postings: 职位列表 / Job postings list
            
        Returns:
            匹配结果列表 / List of job matches
        """
        try:
            # 构建匹配提示 / Build matching prompt
            jobs_text = "\n\n".join([
                f"职位ID: {job.id}\n标题: {job.title}\n公司: {job.company_name}\n"
                f"地点: {job.location}\n描述: {job.description[:500]}..."
                for job in job_postings
            ])
            
            prompt = f"""
            请根据以下简历分析结果，对提供的职位进行匹配度评分和排序:

            简历分析结果:
            - 技能: {resume_analysis.get('skills', [])}
            - 工作年限: {resume_analysis.get('experience_years', 0)}
            - 学历: {resume_analysis.get('education_level', '')}
            - 语言: {resume_analysis.get('languages', [])}
            - 期望地点: {resume_analysis.get('preferred_location', '')}
            - 核心竞争力: {resume_analysis.get('core_competencies', [])}

            职位列表:
            {jobs_text}

            请为每个职位评分（0-100分）并按匹配度排序，返回JSON格式:
            {{
                "matches": [
                    {{
                        "job_id": "职位ID",
                        "match_score": 分数,
                        "match_reasons": ["匹配原因1", "匹配原因2"],
                        "skill_matches": ["匹配的技能1", "匹配的技能2"],
                        "location_match": true/false,
                        "experience_match": true/false
                    }}
                ]
            }}
            
            匹配评分标准:
            - 技能匹配度 (重要): 40分
            - 经验匹配度 (重要): 30分  
            - 地点匹配度 (中等重要): 20分
            - 学历匹配度 (不是很重要): 10分
            
            请按匹配度从高到低排序，只返回JSON格式。
            """
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # 解析匹配结果 / Parse matching results
            try:
                match_data = json.loads(content)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    match_data = json.loads(json_match.group())
                else:
                    raise ValueError("无法解析匹配结果")
            
            # 构建JobMatch对象列表 / Build JobMatch objects list
            job_matches = []
            job_dict = {job.id: job for job in job_postings}
            
            for match in match_data.get('matches', []):
                job_id = match.get('job_id')
                if job_id in job_dict:
                    job_match = JobMatch(
                        job=job_dict[job_id],
                        match_score=match.get('match_score', 0),
                        match_reasons=match.get('match_reasons', []),
                        skill_matches=match.get('skill_matches', []),
                        location_match=match.get('location_match', False),
                        experience_match=match.get('experience_match', False)
                    )
                    job_matches.append(job_match)
            
            logger.info(f"Successfully matched {len(job_matches)} jobs")
            return job_matches
            
        except Exception as e:
            logger.error(f"Job matching failed: {e}")
            return []
    
    async def chat_stream(self, message: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        流式聊天响应 / Streaming chat response
        
        Args:
            message: 用户消息 / User message
            context: 上下文信息 / Context information
            
        Yields:
            响应流 / Response stream
        """
        try:
            # 构建系统提示 / Build system prompt
            system_prompt = """
            你是JobCatcher平台的AI助手，专门帮助用户进行职业规划和求职指导。
            你可以：
            1. 分析简历并提供优化建议
            2. 推荐匹配的职位
            3. 提供德国就业市场信息和咨询
            4. 生成技能热点图和学习建议
            5. 回答职位技术栈相关问题
            
            请用中文、英文或德文回答，根据用户的语言偏好。
            保持专业、友好和有用的态度。
            """
            
            # 构建用户消息 / Build user message
            user_message = message
            if context:
                user_message += f"\n\n上下文信息: {json.dumps(context, ensure_ascii=False)}"
            
            # 创建流式响应 / Create streaming response
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Chat streaming failed: {e}")
            yield f"抱歉，处理您的请求时出现错误: {str(e)}"
    
    async def generate_skill_heatmap_data(self, job_title: str) -> Dict[str, Any]:
        """
        生成技能热点图数据 / Generate skill heatmap data
        使用Claude 4原生WebSearch功能搜索岗位热点技能
        
        Args:
            job_title: 职位标题 / Job title
            
        Returns:
            技能热点图数据 / Skill heatmap data
        """
        try:
            prompt = f"""
            请搜索2025年"{job_title}"职位的最新技能要求和市场趋势，然后生成技能热点图数据。

            请基于当前就业市场信息，返回JSON格式的技能热点图数据：
            {{
                "job_title": "{job_title}",
                "skills": [
                    {{
                        "name": "技能名称",
                        "importance": 重要度分数(1-100),
                        "demand": 需求度分数(1-100),
                        "category": "技能类别(如:编程语言、框架、工具等)",
                        "trend": "上升/稳定/下降"
                    }}
                ],
                "trending_skills": ["新兴技能1", "新兴技能2"],
                "recommended_learning_path": [
                    {{
                        "skill": "技能名",
                        "priority": "High/Medium/Low",
                        "learning_resources": ["资源1", "资源2"],
                        "estimated_learning_time": "学习时间估计"
                    }}
                ],
                "market_insights": {{
                    "average_salary": "平均薪资范围",
                    "job_growth": "就业增长趋势",
                    "top_companies": ["顶级雇主1", "顶级雇主2"],
                    "geographic_demand": ["高需求地区1", "高需求地区2"]
                }},
                "data_source": "基于2025年市场分析",
                "last_updated": "2025年最新数据"
            }}
            
            请确保数据基于最新的2025年就业市场信息。
            """
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            try:
                heatmap_data = json.loads(content)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    heatmap_data = json.loads(json_match.group())
                else:
                    raise ValueError("无法解析技能热点图数据")
            
            logger.info(f"Generated skill heatmap for: {job_title}")
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Skill heatmap generation failed: {e}")
            return {
                "job_title": job_title,
                "skills": [],
                "trending_skills": [],
                "recommended_learning_path": [],
                "market_insights": {},
                "error": str(e)
            }
    
    async def get_german_job_market_insights(self, query: str) -> str:
        """
        获取德国就业市场咨询 / Get German job market insights
        
        Args:
            query: 查询内容 / Query content
            
        Returns:
            市场洞察信息 / Market insights
        """
        try:
            prompt = f"""
            请基于德国就业市场的最新信息来回答以下问题：
            
            用户问题：{query}
            
            请提供详细、准确的德国就业市场咨询，包括：
            1. 当前市场状况
            2. 热门行业和职位
            3. 薪资水平
            4. 求职建议
            5. 签证和工作许可信息（如适用）
            
            请用中文、英文或德文回答，根据用户的语言偏好。
            """
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"German job market insights failed: {e}")
            return f"抱歉，获取德国就业市场信息时出现错误：{str(e)}" 