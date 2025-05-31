#!/usr/bin/env python3
"""
检查Chroma数据库中的数据量 / Check data count in Chroma database
"""

import os
import sys
import chromadb
from chromadb.config import Settings
from datetime import datetime, timedelta
import json

# 添加app目录到Python路径 / Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def check_chroma_data():
    """检查Chroma数据库中的数据 / Check data in Chroma database"""
    
    # 初始化Chroma客户端 / Initialize Chroma client
    chroma_path = "./data/chroma"
    if not os.path.exists(chroma_path):
        print(f"❌ Chroma数据库路径不存在: {chroma_path}")
        return
    
    try:
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        print("🔍 正在检查Chroma数据库...")
        print(f"📁 数据库路径: {os.path.abspath(chroma_path)}")
        
        # 获取所有集合 / Get all collections
        collections = client.list_collections()
        print(f"\n📊 找到 {len(collections)} 个集合:")
        
        total_documents = 0
        
        for collection in collections:
            print(f"\n📋 集合名称: {collection.name}")
            
            # 获取集合详情 / Get collection details
            try:
                coll = client.get_collection(collection.name)
                count = coll.count()
                total_documents += count
                
                print(f"   📈 文档数量: {count}")
                
                # 获取集合元数据 / Get collection metadata
                if hasattr(collection, 'metadata') and collection.metadata:
                    print(f"   📝 元数据: {collection.metadata}")
                
                # 如果是jobs集合，获取一些样本数据 / If it's jobs collection, get some sample data
                if collection.name == "jobs" and count > 0:
                    print(f"   🔍 正在获取最新的5条数据样本...")
                    
                    # 获取最新的几条数据 / Get latest few records
                    try:
                        results = coll.get(
                            limit=5,
                            include=['metadatas', 'documents']
                        )
                        
                        if results['metadatas']:
                            print(f"   📅 最新数据样本:")
                            for i, metadata in enumerate(results['metadatas'][:5]):
                                if metadata:
                                    title = metadata.get('title', 'N/A')
                                    company = metadata.get('company', 'N/A')
                                    location = metadata.get('location', 'N/A')
                                    crawl_time = metadata.get('crawl_time', 'N/A')
                                    source = metadata.get('source', 'N/A')
                                    
                                    print(f"      {i+1}. 职位: {title}")
                                    print(f"         公司: {company}")
                                    print(f"         地点: {location}")
                                    print(f"         来源: {source}")
                                    print(f"         爬取时间: {crawl_time}")
                                    print()
                    except Exception as e:
                        print(f"   ⚠️  获取样本数据时出错: {e}")
                
                # 尝试获取最近24小时的数据 / Try to get data from last 24 hours
                if collection.name == "jobs" and count > 0:
                    print(f"   🕐 检查最近24小时的数据...")
                    try:
                        # 获取所有数据的元数据 / Get all metadata
                        all_results = coll.get(include=['metadatas'])
                        
                        # 统计最近24小时的数据 / Count data from last 24 hours
                        now = datetime.now()
                        yesterday = now - timedelta(hours=24)
                        
                        recent_count = 0
                        today_count = 0
                        
                        for metadata in all_results['metadatas']:
                            if metadata and 'crawl_time' in metadata:
                                try:
                                    # 尝试解析时间 / Try to parse time
                                    crawl_time_str = metadata['crawl_time']
                                    # 支持多种时间格式 / Support multiple time formats
                                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                                        try:
                                            crawl_time = datetime.strptime(crawl_time_str.split('.')[0], fmt)
                                            break
                                        except ValueError:
                                            continue
                                    else:
                                        continue
                                    
                                    if crawl_time >= yesterday:
                                        recent_count += 1
                                    
                                    if crawl_time.date() == now.date():
                                        today_count += 1
                                        
                                except Exception as e:
                                    continue
                        
                        print(f"   📊 最近24小时新增: {recent_count} 条")
                        print(f"   📊 今天新增: {today_count} 条")
                        
                    except Exception as e:
                        print(f"   ⚠️  统计最近数据时出错: {e}")
                        
            except Exception as e:
                print(f"   ❌ 获取集合 {collection.name} 信息时出错: {e}")
        
        print(f"\n📈 总计文档数量: {total_documents}")
        
        # 检查数据库文件大小 / Check database file size
        db_file = os.path.join(chroma_path, "chroma.sqlite3")
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            file_size_mb = file_size / (1024 * 1024)
            print(f"💾 数据库文件大小: {file_size_mb:.2f} MB")
        
    except Exception as e:
        print(f"❌ 连接Chroma数据库时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 切换到backend目录 / Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    print("🚀 JobCatcher Chroma数据库检查工具")
    print("=" * 50)
    
    check_chroma_data()
    
    print("\n✅ 检查完成!") 