"""
数据库连接管理 / Database connection management
"""

import os
import sqlite3
from typing import Dict, List, Any
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


# 初始化OpenAI embedding模型 / Initialize OpenAI embedding model
def get_openai_embedding_client():
    """获取OpenAI embedding客户端 / Get OpenAI embedding client"""
    # 从settings配置获取API密钥 / Get API key from settings configuration
    api_key = settings.openai_api_key
    if not api_key or api_key == "sk-your_openai_api_key_here":
        raise ValueError("OPENAI_API_KEY is not properly configured in .env file")
    
    # 初始化OpenAI客户端 / Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    return client


def get_text_embedding(client: OpenAI, text: str) -> List[float]:
    """
    使用OpenAI text-embedding-3-small模型生成向量 / Generate embeddings using OpenAI text-embedding-3-small model
    
    Args:
        client: OpenAI客户端 / OpenAI client
        text: 要向量化的文本 / Text to embed
        
    Returns:
        向量列表 / List of embeddings
    """
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",  # 使用最新的text-embedding-3-small模型 / Use latest text-embedding-3-small model
            input=text,
            encoding_format="float"  # 返回浮点数格式 / Return float format
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"OpenAI embedding failed: {e}")


def get_text_embeddings_batch(client: OpenAI, texts: List[str]) -> List[List[float]]:
    """
    批量生成向量（提高效率）/ Generate embeddings in batch (for efficiency)
    
    Args:
        client: OpenAI客户端 / OpenAI client
        texts: 要向量化的文本列表 / List of texts to embed
        
    Returns:
        向量列表的列表 / List of embedding lists
    """
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
            encoding_format="float"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        raise Exception(f"OpenAI batch embedding failed: {e}")


# Chroma向量数据库配置 / Chroma vector database configuration
def get_chroma_client():
    """获取Chroma客户端 / Get Chroma client"""
    # 创建数据目录 / Create data directory
    os.makedirs("./data/chroma", exist_ok=True)
    
    # 初始化Chroma客户端 / Initialize Chroma client
    client = chromadb.PersistentClient(
        path="./data/chroma",
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    return client


# SQLite连接（用于用户session存储）/ SQLite connection (for user session storage)
def get_sqlite_db():
    """获取SQLite数据库连接 / Get SQLite database connection"""
    db_path = "./data/sessions.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    # 创建用户会话表 / Create user session table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建用户表 / Create user table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            picture TEXT,
            google_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    
    # 创建简历分析表 / Create resume analysis table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resume_analyses (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_content TEXT NOT NULL,
            analysis_result TEXT NOT NULL,
            skills TEXT NOT NULL,
            experience_years INTEGER,
            education_level TEXT,
            languages TEXT NOT NULL,
            preferred_location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # 创建聊天记录表 / Create chat history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            message_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    return conn


# 初始化所有数据库连接 / Initialize all database connections
async def init_databases():
    """初始化所有数据库连接 / Initialize all database connections"""
    try:
        # 初始化SQLite数据库 / Initialize SQLite database
        sqlite_conn = get_sqlite_db()
    
        # 初始化Chroma向量数据库 / Initialize Chroma vector database
        chroma_client = get_chroma_client()
    
        # 检查jobs集合是否存在，如果不存在则创建 / Check if jobs collection exists, create if not
        try:
            existing_collection = chroma_client.get_collection("jobs")
            logger.info("Found existing jobs collection, keeping existing data")
            jobs_collection = existing_collection
        except Exception as e:
            logger.info(f"No existing jobs collection found, creating new one: {e}")
            # 创建新的jobs集合，支持OpenAI text-embedding-3-small的1536维向量 / Create new jobs collection supporting 1536-dim vectors
            jobs_collection = chroma_client.create_collection(
                name="jobs",
                metadata={
                    "description": "Job postings with OpenAI text-embedding-3-small embeddings",
                    "embedding_model": "text-embedding-3-small",
                    "embedding_dimension": 1536
                }
            )
            logger.info("Created new jobs collection with 1536-dimension support")
        
        # 检查resumes集合是否存在，如果不存在则创建 / Check if resumes collection exists, create if not
        try:
            resumes_collection = chroma_client.get_collection("resumes")
            logger.info("Found existing resumes collection")
        except Exception as e:
            logger.info(f"No existing resumes collection found, creating new one: {e}")
            resumes_collection = chroma_client.create_collection(
                name="resumes",
                metadata={
                    "description": "Resume analysis vector store",
                    "embedding_model": "text-embedding-3-small",
                    "embedding_dimension": 1536
                }
            )
            logger.info("Created new resumes collection")
        
        # 初始化OpenAI客户端 / Initialize OpenAI client
        openai_client = get_openai_embedding_client()
        
        logger.info("All databases initialized successfully")
        
        return {
            'sqlite_conn': sqlite_conn,
            'chroma_client': chroma_client,
            'jobs_collection': jobs_collection,
            'resumes_collection': resumes_collection,
            'openai_client': openai_client  # 返回OpenAI客户端 / Return OpenAI client
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        raise 