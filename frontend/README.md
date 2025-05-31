# JobCatcher Frontend

## 概述

JobCatcher前端是一个基于现代Web技术构建的智能职位搜索平台，提供直观的用户界面和流畅的交互体验。

## 技术栈

- **HTML5** - 语义化文档结构
- **CSS3** - 现代样式设计，包含Grid/Flexbox布局
- **JavaScript ES6+** - 模块化应用逻辑
- **Font Awesome** - 图标库
- **Google OAuth** - 用户认证

## 项目结构

```
frontend/
├── index.html          # 主页面文件
├── css/
│   └── styles.css      # 主样式文件
├── js/
│   ├── app.js          # 主应用逻辑
│   ├── auth.js         # 认证管理
│   ├── chat.js         # AI聊天功能
│   └── jobs.js         # 职位搜索和展示
└── assets/
    └── default-avatar.svg  # 默认用户头像
```

## 核心功能

### 1. 用户认证
- Google OAuth 2.0 登录
- 自动会话管理
- 用户状态保持

### 2. 职位搜索
- 实时职位搜索
- 地点和关键词过滤
- 搜索历史记录
- 职位详情展示

### 3. AI聊天助手
- 基于Claude 4 Sonnet的智能对话
- 简历上传和分析
- 流式消息输出
- 多语言支持（中/英/德）

### 4. 响应式设计
- 桌面端优化（>1024px）
- 平板端适配（768-1024px）
- 移动端优化（<768px）

## 页面布局

### 登录页面
- 艺术化渐变背景
- 简洁的登录界面
- Google OAuth集成
- 产品特性展示

### 主应用界面
- **Header**: Logo、用户信息、退出按钮
- **左侧面板（50%）**: 职位搜索和展示
  - 搜索栏（职位+地点）
  - 职位卡片列表
  - 职位详情模态框
- **右侧面板（50%）**: AI聊天助手
  - 聊天消息区域
  - 文件上传区域
  - 消息输入框

## JavaScript架构

### app.js - 主应用管理器
```javascript
class JobCatcherApp {
    // 应用初始化
    // 状态管理
    // 页面路由
    // 全局事件处理
}
```

### auth.js - 认证管理器
```javascript
class AuthManager {
    // Google OAuth处理
    // 会话管理
    // 用户状态检查
    // 自动刷新机制
}
```

### chat.js - 聊天管理器
```javascript
class ChatManager {
    // 消息发送和接收
    // 流式输出处理
    // 文件上传管理
    // 简历分析展示
}
```

### jobs.js - 职位管理器
```javascript
class JobsManager {
    // 职位搜索功能
    // 职位展示逻辑
    // 详情模态框
    // 职位保存功能
}
```

## CSS设计系统

### 颜色方案
```css
:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    --bg-primary: #f8fafc;
    --text-primary: #2d3748;
    --border-color: #e2e8f0;
}
```

### 响应式断点
- 大屏幕: >1024px
- 平板: 768px-1024px
- 手机: <768px

### 动画效果
- 浮动动画（登录页面）
- 卡片悬浮效果
- 页面切换过渡
- 打字指示器
- 模态框滑入

## API集成

### 认证API
```javascript
// 检查登录状态
GET /api/auth/me

// Google OAuth登录
GET /api/auth/google

// 退出登录
POST /api/auth/logout
```

### 职位API
```javascript
// 搜索职位
POST /api/jobs/search
{
    "query": "软件工程师",
    "location": "柏林",
    "limit": 25
}

// 获取热门职位
GET /api/jobs/trending

// 保存职位
POST /api/jobs/save
```

### 聊天API
```javascript
// 发送消息
POST /api/chat/message
{
    "message": "用户消息",
    "history": [...]
}

// 简历分析
POST /api/chat/analyze-resume

// 文件上传
POST /api/upload/resume
```

## 部署说明

### 开发环境
1. 确保后端服务运行在 `http://localhost:8000`
2. 直接打开 `index.html` 或使用本地服务器
3. 配置Google OAuth客户端ID

### 生产环境
1. 配置Web服务器（Nginx推荐）
2. 设置HTTPS证书
3. 更新API基础URL
4. 配置CDN（可选）

### 环境变量
在 `index.html` 中配置：
```html
<meta name="google-signin-client_id" content="YOUR_GOOGLE_CLIENT_ID">
```

## 浏览器兼容性

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## 性能优化

- CSS/JS文件压缩
- 图片优化
- 懒加载实现
- 缓存策略
- CDN加速

## 无障碍访问

- ARIA标签支持
- 键盘导航
- 屏幕阅读器兼容
- 高对比度模式
- 焦点管理

## 开发指南

### 代码规范
- 使用ES6+语法
- 模块化架构
- 事件委托
- 错误处理
- 注释规范

### 调试工具
- 浏览器开发者工具
- Console日志
- 网络监控
- 性能分析

### 测试建议
- 跨浏览器测试
- 响应式测试
- 功能测试
- 性能测试
- 无障碍测试

## 许可证

本项目为JobCatcher智能职位搜索平台的前端部分，请遵循项目整体许可证。 