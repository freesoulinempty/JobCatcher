# JobCatcher 前后端开发文档

## 项目概述

JobCatcher 是一个基于Claude 4 Sonnet驱动的智能职位搜索和匹配平台，专注于德国就业市场，充分利用AI原生能力，最小化代码开发。

## 技术架构

### 核心AI引擎
- **Claude 4 Sonnet** - 主要AI模型
  - 混合推理模式（即时响应 + 深度思考）
  - 先进的编程能力
  - 增强的工具使用和并行处理
  - 改进的指令遵循和记忆能力
  - 原生WebSearch

### 后端技术栈
- **FastAPI** (0.115.0+) - 高性能Web框架
- **LangChain** (0.3.25+) - LLM应用开发框架
- **Pydantic** (2.7.0+) - 数据验证
- **RAG** - 向量检索
- **SQLite** - 用户session存储
- **Chroma** - 向量存储职位数据

### 前端技术栈
- **HTML5** - 语义化结构
- **CSS3** - 现代样式设计(Grid/Flexbox布局)
- **JavaScript ES6+** - 交互逻辑和API调用
- **响应式设计** - 支持桌面/平板/移动端
- **Google OAuth** - 用户认证

## 前端开发规范

### 界面布局设计

#### 主界面结构
- **Google OAuth 2.0登录页**: 首页登录后进入主界面
- **左右分栏设计(50%:50%)**:
  - **左侧职位展示区域**:
    - 职位搜索栏,城市搜索栏(都在同一行)
    - 下方职位数据展示区域(岗位卡片)，支持上下滚动
    - 显示职位基本信息(岗位名称、公司名称、工作地点、办公形式、岗位详情链接、岗位详情)
    - 点击"show detail"当前岗位卡片展开展示详细信息
    - 点击职位可跳转到对应的外部职位详情链接
  - **右侧AI聊天区域**:
    - 智能聊天框,支持简历上传和AI对话(流式输出)
    - 实时显示简历分析结果和优化建议
    - 支持技能热点图生成和职位咨询

#### UI设计要求
- **界面语言**: 所有界面语言为英语
- **设计风格**: 简洁清爽的界面风格
- **视觉效果**: 艺术化渐变和动画效果，浮动效果
- **响应式设计**: 适配各种设备

### 前端功能实现

#### 用户认证
- 集成Google OAuth 2.0登录
- 用户会话管理
- 登录状态维护

#### 职位搜索界面
- 职位搜索栏和城市搜索栏布局(同一行)
- 职位卡片展示组件
- 职位详情展开/收起功能
- 外部链接跳转处理
- 上下滚动加载

#### AI聊天界面
- 文件上传组件(支持PDF/DOC/TXT)
- 流式对话输出
- 消息历史记录
- 技能热点图展示

## 后端开发规范

### API架构设计

#### 核心接口
1. **用户认证接口**
   - Google OAuth验证
   - 用户会话管理
   - 登录状态检查

2. **职位搜索接口**
   - 职位关键词+城市进行搜索
   - 搜索结果返回

3. **简历处理接口**
   - 文件上传处理
   - 简历解析
   - 向量化存储

4. **AI对话接口**
   - 流式对话响应
   - Claude 4 Sonnet集成
   - 技能热点图生成

### 数据源集成

#### Apify LinkedIn爬虫
- **Actor ID**: `valig/linkedin-jobs-scraper`
- **支持网站**: LinkedIn.de
- **定时爬取**: 每日定时爬取预设岗位的数据,只根据岗位名称爬取,城市名称为空,每个岗位25条(按照相关性)(发布时间7天内)
- **预设岗位**: "engineer","manager","IT","Finance","Sales","Nurse","Consultant","software developer"
- **成本**: €0.005/次调用(25个岗位) ; 定时爬取成本: €0.005 * 8 * 30 = €1.2 /月
- **最新开发文档**: https://docs.apify.com/api/client/python/docs/overview/introduction
- **input格式**:
```python
{
  "limit": 10,
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
- **output格式**:
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

#### Zyte API爬虫
- **支持网站**: Indeed.de
- **定时爬取**: 每天定时爬取,只根据岗位名称爬取,城市名称为空,每个岗位25条数据
- **预设岗位名称**: "Web","cloud","AI","Data","software"
- **成本**: €0.001/次调用,€0.001 * 26 * 5 * 30 = €4 /月
- **注意**: 先爬取岗位列表,再爬取岗位详情,速度很慢,需要留够等待时间或者异步处理
- **最新开发文档**: https://docs.zyte.com/zyte-api/usage/reference.html
- **Indeed URL构造示例**: https://de.indeed.com/jobs?q=software+developer&l=Stuttgart
- **爬取岗位列表调用方式**:
```python
import asyncio
from base64 import b64decode

from zyte_api import AsyncZyteAPI

async def main():
    client = AsyncZyteAPI()
    api_response = await client.get(
        {
            "url": "https://de.indeed.com/jobs?q=software&l=",
            "jobPostingNavigation": True,
            "jobPostingNavigationOptions": {"extractFrom":"httpResponseBody"},
        }
    )
    jobPostingNavigation = api_response["jobPostingNavigation"]

asyncio.run(main())
```
- **爬取岗位详情调用方式**:
```python
import asyncio
from base64 import b64decode

from zyte_api import AsyncZyteAPI

async def main():
    client = AsyncZyteAPI()
    api_response = await client.get(
        {
            "url": "https://de.indeed.com/jobs?q=software&l=&fromage=last&from=searchOnDesktopSerp&cf-turnstile-response=0.d7PCWf2oXUbeuMc_fSgUX3f701T9Pn7Yi97XI4er_M2KsCXLqTuraU3Zoi6F1feiY6530y3OD5EbxHT68QAvDDE-g7Ks7LaZgCV9PrM-aGnMRAqkY1Ztfq6OTj8Eunbs3iQu5x2zMtw_9iD1W3hu19NfjdyCzXG2CU9AIwvtoZLS0SgQFyBzLNx6vjsjQDmuLEsc_wPPkUtCMKg8TE9xgb_Uw0L2PcBZA33_k5Ei-sv0jo9pkqMkZeOxOz4QS3sCj4k0jneFmHNfKOX74QZh1QVlywJMjWa1up3T97kIViBhpOpl-Km0Z9YvEAmTd0qeJeLl9itSNBHWqUlLkTlBJ6RIgtePEIOWcIrzMSTCVCmXuEGGkmh6E_S_itOfmbaGd9W0d4SCJ1bEsvN0Bdk0kW5QhSyTz0M78xrcbodaM1lPdE_W_t28aMcUDLKpoXk9GLKHp5xjt5UVIXwsRLSz5bq-HtbfMaprvk6XE-kptJyrkczZNAh92sXwwphmAYrttOKsAs_EhQ4X6TE6obdbe2B8PNz5rxrTx3s8BXeempE-a4PeVf7PZEXp7OCy-CIPIl0JqfF3BPJdHqSO6uHsLAwxTU6ueK4kKH8jRiWLRI32-bN71MyQZDMcBcyCoTh78MjAl88MtVln3RFQk1IofIJpQ_oymH_t5C2i6-vhbSu46gvbPEBC8y4MKUCn2mXfCGlO7gF35r_7e5fZn2X5GWgq8BacWO7MunW8tz-awudxANAGVnWDCVl7FSspT6ilqKIhxdIVz6GkaWeIsP-txWH6q-yyCh-0IipyQwaR2d4r1OP-ndyT71UFCn5YquwYVRkWDpdFKww1qyl7UTLEMDPBqB83t4GqjqvSAArqViVVlAUQbrh5JxAsSAwi3lmU.HYULdYkJ8y3XoOkuEfLeZQ.49867fd49bfc083e8d2f287f31fa250c5d917c21655884fcfaf9db8c59f24303&vjk=f8d2fead4ba0e20d&advn=3267287698366588",
            "jobPosting": True,
            "jobPostingOptions": {"extractFrom":"httpResponseBody"},
        }
    )
    jobPosting = api_response["jobPosting"]

asyncio.run(main())

```

### 数据存储方案

#### SQLite
- 用户session存储
- 用户认证信息管理

#### Chroma向量数据库
- 向量存储和检索职位数据
- 简历向量化存储
- 相似度匹配查询
- text-embedding-3-small

#### 数据清理机制
- **定时清理**: 每天定时访问Chroma中所有岗位URL,如果URL失效则清理
- **僵尸岗位清理**: 清理14天之前的岗位数据,防止僵尸岗位

## 核心业务流程

### 用户搜索流程
1. 用户在主页搜索栏搜索"岗位名称"+"地点"
2. 后端把"岗位名称"+"地点"向量信息作为查询,检索Chroma最相似岗位
3. 发送给前端并展示(岗位名称,公司名称,工作地点,办公方式,岗位详情链接,岗位描述)

### 职位推荐流程
1. 用户在对话框上传简历 → 前端接受 → 后端接收发送给agent
2. agent使用claude4原生能力解析pdf,提取关键信息(地点,技能,学历,经历,语言等)
3. embedding向量化 → 存入Chroma(存入时去重,避免Chroma内有重复岗位)
4. 用户简历向量信息(地点,技能,学历,经历,语言)作为查询,检索Chroma最相似岗位(返回岗位数量25个)
5. 后端把Claude4生成的用户简历分析结果+Chroma匹配到的岗位数据拼接为一个prompt
6. 后端把prompt发送给claude进行分析岗位和排序
7. 前端bot聊天机器人发送信息
8. 后端获取claude4排序后的岗位数据 → 后端把岗位数据发送给前端(岗位名称、公司名称、工作地点、办公形式、岗位详情链接、岗位详情描述)
9. 前端把岗位放在左侧岗位展示区(按照匹配度从上到下)

### 简历和岗位匹配机制
- **匹配主导者**: RAG根据简历向量信息进行初匹配,claude4采纳"匹配要素"进行深度思考(thinking)进行匹配
- **匹配要素**: 
  - 地点(中等重要)
  - 技能(重要)
  - 学历(不是很重要)
  - 经历(重要)
  - 语言(中等重要)

## Claude 4 Sonnet Agent系统

### 统一Agent处理功能
- 利用Claude 4的原生文档理解能力深度分析简历
- 提供简历优化建议、技术栈建议、学习建议
- 基于简历分析结果推荐最匹配的25个岗位
- 推荐岗位按匹配度排序显示在左侧展示区域
- 生成岗位技能热点图(claude4原生WebSearch功能搜索岗位热点技能并进行深度思考(thinking),后调用Artifacts工具生成技能热点图片)
- 生成技能热点图和个性化学习建议
- 提供德国就业市场咨询和职业指导(claude4原生WebSearch功能搜索就业市场信息)
- 支持中文和德语和英语三语交流
- 回答岗位技术栈和要求相关问题

### AI驱动的个性化服务
- **智能简历分析**: 
  - Claude 4原生PDF/DOC/TXT文档处理能力
  - 分析后通过聊天框返回详细分析结果
  - 提供优化建议和技术栈建议
- **精准职位匹配**: 基于语义理解的匹配度评分
- **技能差距分析**: AI驱动的技能评估和热点图生成
- **学习路径推荐**: 个性化职业发展建议(claude4原生WebSearch功能搜索岗位技能以及此职业当前火热的学习路线)
- **职位技术栈分析**: 针对特定岗位生成技能要求热点图(claude4原生WebSearch功能搜索岗位技能以及此职业当前火热的要求以及技术栈)

## 安全与隐私

### 安全认证
- Google OAuth 2.0 登录
- 用户会话管理
- 数据隐私保护

### 数据安全
- 用户简历数据加密存储
- 向量数据去重机制
- 定时数据清理机制

## 部署要求

### 本地化部署
- 方便快捷的部署方案
- SQLite本地数据库
- 向量数据库本地存储

### 成本控制
- **Apify成本**: 定时爬取 €0.9/月 + 实时爬取(按需)
- **Zyte成本**: €4/月
- **总估算**: 约€5/月的数据抓取成本

### requirements.txt

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.0.0
langchain>=0.3.25
langchain-anthropic>=0.1.0
chromadb>=0.5.0
aiosqlite>=0.20.0
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
apify-client>=1.7.0
aiohttp>=3.10.0
aiofiles>=24.0.0
python-multipart>=0.0.9
apscheduler>=3.10.0
numpy>=1.24.0
pandas>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```