#!/usr/bin/env python3
"""
测试Zyte API连接 / Test Zyte API connection
"""

import asyncio
import os
import sys
from zyte_api import AsyncZyteAPI

# 添加app目录到Python路径 / Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_zyte_api():
    """测试Zyte API连接 / Test Zyte API connection"""
    
    # 从环境变量获取API密钥 / Get API key from environment variables
    api_key = "4f3ed429712943d2826c3e5b22e6a6d8"  # 直接使用.env中的密钥
    
    if not api_key:
        print("❌ Zyte API密钥未配置")
        return False
    
    try:
        print(f"🔑 使用API密钥: {api_key[:8]}...")
        
        # 初始化Zyte API客户端 / Initialize Zyte API client
        client = AsyncZyteAPI(api_key=api_key)
        
        # 执行一个简单的测试请求 / Execute a simple test request
        test_url = "https://de.indeed.com/jobs?q=test&l="
        
        print(f"🌐 测试URL: {test_url}")
        print("📡 正在发送测试请求...")
        
        api_response = await client.get({
            "url": test_url,
            "jobPostingNavigation": True,
            "jobPostingNavigationOptions": {"extractFrom": "httpResponseBody"},
        })
        
        print("✅ Zyte API连接成功!")
        print(f"📊 响应数据类型: {type(api_response)}")
        
        # 检查响应内容 / Check response content
        if "jobPostingNavigation" in api_response:
            job_navigation = api_response["jobPostingNavigation"]
            print(f"📋 找到jobPostingNavigation数据")
            
            if "items" in job_navigation:
                items_count = len(job_navigation["items"])
                print(f"📈 找到 {items_count} 个职位链接")
                
                # 显示前3个链接 / Show first 3 links
                for i, item in enumerate(job_navigation["items"][:3]):
                    if "url" in item:
                        print(f"   {i+1}. {item['url']}")
            else:
                print("⚠️  jobPostingNavigation中没有找到items字段")
                print(f"   可用字段: {list(job_navigation.keys())}")
        else:
            print("⚠️  响应中没有找到jobPostingNavigation字段")
            print(f"   可用字段: {list(api_response.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Zyte API连接失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        
        # 检查是否是认证错误 / Check if it's an authentication error
        if "401" in str(e) or "Unauthorized" in str(e):
            print("🔐 这是认证错误，请检查API密钥是否正确")
        elif "403" in str(e) or "Forbidden" in str(e):
            print("🚫 这是权限错误，请检查API密钥权限")
        elif "429" in str(e) or "rate limit" in str(e).lower():
            print("⏰ 这是频率限制错误，请稍后重试")
        
        return False

async def test_job_detail_extraction():
    """测试职位详情提取 / Test job detail extraction"""
    
    api_key = "4f3ed429712943d2826c3e5b22e6a6d8"
    
    try:
        client = AsyncZyteAPI(api_key=api_key)
        
        # 使用一个真实的Indeed职位URL进行测试 / Use a real Indeed job URL for testing
        test_job_url = "https://de.indeed.com/viewjob?jk=test"
        
        print(f"\n🔍 测试职位详情提取...")
        print(f"🌐 测试URL: {test_job_url}")
        
        api_response = await client.get({
            "url": test_job_url,
            "jobPosting": True,
            "jobPostingOptions": {"extractFrom": "httpResponseBody"},
        })
        
        print("✅ 职位详情提取成功!")
        
        if "jobPosting" in api_response:
            job_posting = api_response["jobPosting"]
            print(f"📋 职位数据字段: {list(job_posting.keys())}")
            
            # 显示主要字段 / Show main fields
            title = job_posting.get("jobTitle", "N/A")
            company = job_posting.get("hiringOrganization", {})
            location = job_posting.get("jobLocation", "N/A")
            
            print(f"   职位标题: {title}")
            print(f"   公司信息: {company}")
            print(f"   工作地点: {location}")
        else:
            print("⚠️  响应中没有找到jobPosting字段")
            print(f"   可用字段: {list(api_response.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 职位详情提取失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Zyte API连接测试工具")
    print("=" * 50)
    
    # 运行测试 / Run tests
    loop = asyncio.get_event_loop()
    
    print("\n1️⃣ 测试基本连接和职位列表提取...")
    success1 = loop.run_until_complete(test_zyte_api())
    
    print("\n2️⃣ 测试职位详情提取...")
    success2 = loop.run_until_complete(test_job_detail_extraction())
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ 所有测试通过！Zyte API工作正常")
    elif success1:
        print("⚠️  基本连接正常，但职位详情提取有问题")
    else:
        print("❌ Zyte API连接失败，请检查配置")
    
    print("🏁 测试完成!") 