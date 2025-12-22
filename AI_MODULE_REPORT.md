# AI模块相关信息汇报

## 1. 核心实体：AI_Book_Service（AI书籍服务）
- **属性1**：service_id，数据类型：String，说明：AI服务唯一标识（由系统分配）
- **属性2**：api_endpoint，数据类型：String，说明：外部AI API端点（如DeepSeek API地址）
- **属性3**：api_key，数据类型：String，说明：外部AI API密钥（安全存储）
- **属性4**：timeout，数据类型：Integer，说明：API请求超时时间（毫秒）
- **属性5**：rate_limit，数据类型：Integer，说明：API请求速率限制（每分钟请求数）
- **属性6**：enabled，数据类型：Boolean，说明：服务启用状态（默认True）
- **属性7**：last_used，数据类型：DateTime，说明：服务最后使用时间（自动更新）

## 2. 关联实体：Book（书籍）
- **属性1**：id，数据类型：Integer，说明：书籍唯一标识（主键，自增，用于AI服务查询）
- **属性2**：title，数据类型：String，说明：书籍标题（用于AI摘要生成和推荐）
- **属性3**：authors，数据类型：Relationship，说明：书籍作者（多对多关系）
- **属性4**：tags，数据类型：Relationship，说明：书籍标签（多对多关系）
- **属性5**：series，数据类型：Relationship，说明：书籍系列（多对多关系）
- **属性6**：comments，数据类型：Relationship，说明：书籍评论（一对多关系）
- **属性7**：isbn，数据类型：String，说明：书籍ISBN编号（用于书籍识别）

## 3. 关联实体：AI_Response_Cache（AI响应缓存）
- **属性1**：cache_id，数据类型：String，说明：缓存唯一标识（主键，由系统生成）
- **属性2**：book_id，数据类型：Integer，说明：关联书籍ID（外键，非空）
- **属性3**：request_type，数据类型：String(50)，说明：请求类型（如"summary"或"recommendation"，非空）
- **属性4**：response_data，数据类型：Text，说明：AI响应数据（非空）
- **属性5**：created_at，数据类型：DateTime，说明：缓存创建时间（默认当前UTC时间）
- **属性6**：expires_at，数据类型：DateTime，说明：缓存过期时间（默认创建后7天）

## 4. AI模块功能说明

### 4.1 书籍AI摘要生成
- **功能描述**：根据书籍元数据生成AI摘要
- **调用方式**：通过`/ajax/ai/book_summary/<int:book_id>` API端点
- **数据来源**：书籍标题、作者、标签、系列、评论等元数据
- **响应格式**：JSON格式的AI生成摘要

### 4.2 相关书籍推荐
- **功能描述**：根据当前书籍元数据推荐相关书籍
- **调用方式**：通过`/ajax/ai/book_recommendations/<int:book_id>` API端点
- **数据来源**：当前书籍元数据及系统内其他书籍元数据
- **响应格式**：JSON格式的推荐书籍列表

## 5. 技术实现细节

### 5.1 核心文件
- `cps/services/deepseek_ai.py`：AI服务的主要实现
- `cps/services/__init__.py`：AI服务的导入配置
- `cps/web.py`：AI功能的API路由定义
- `cps/templates/detail.html`：前端AI功能的UI界面

### 5.2 关键函数
- `get_book_summary(book_id)`：获取书籍AI摘要
- `get_related_books(book_id)`：获取相关书籍推荐
- `_get_book_info(book_id)`：获取书籍元数据信息
- `_call_deepseek_api(prompt)`：调用DeepSeek AI API

### 5.3 数据流向
1. 前端发起AJAX请求
2. Web服务器路由到对应的AI服务函数
3. 服务函数获取书籍元数据
4. 构建prompt并调用外部AI API
5. 处理API响应并返回给前端
6. 前端展示AI生成的结果