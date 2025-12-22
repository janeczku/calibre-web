# AI模块UML类图和流程顺序图

## 1. UML类图

```mermaid
classDiagram
    direction LR
    
    %% 核心实体
    class AI_Book_Service {
        +service_id: String
        +api_endpoint: String
        +api_key: String
        +timeout: Integer
        +rate_limit: Integer
        +enabled: Boolean
        +last_used: DateTime
        +get_book_summary(book_id: Integer): String
        +get_related_books(book_id: Integer): List[Book]
        -_get_book_info(book_id: Integer): Dict
        -_call_deepseek_api(prompt: String): String
    }
    
    %% 关联实体
    class Book {
        +id: Integer
        +title: String
        +authors: List[Author]
        +tags: List[Tag]
        +series: List[Series]
        +comments: List[Comment]
        +isbn: String
    }
    
    class Author {
        +id: Integer
        +name: String
    }
    
    class Tag {
        +id: Integer
        +name: String
    }
    
    class Series {
        +id: Integer
        +name: String
    }
    
    class Comment {
        +id: Integer
        +text: String
    }
    
    class User {
        +id: Integer
        +username: String
        +email: String
    }
    
    %% AI响应缓存
    class AI_Response_Cache {
        +cache_id: String
        +book_id: Integer
        +request_type: String
        +response_data: Text
        +created_at: DateTime
        +expires_at: DateTime
        +get_cache(book_id: Integer, request_type: String): String
        +set_cache(book_id: Integer, request_type: String, data: String): void
    }
    
    %% 数据库访问类
    class calibre_db {
        +get_books(ids: List[Integer]): List[Dict]
        +get_book(book_id: Integer): Dict
        +get_book_authors(book_id: Integer): List[Dict]
        +get_book_tags(book_id: Integer): List[Dict]
        +get_book_series(book_id: Integer): List[Dict]
        +get_book_comments(book_id: Integer): List[Dict]
    }
    
    %% 关系定义
    AI_Book_Service --> Book : 使用
    AI_Book_Service --> AI_Response_Cache : 缓存结果
    AI_Book_Service --> calibre_db : 获取数据
    Book --> Author : 多对多
    Book --> Tag : 多对多
    Book --> Series : 多对多
    Book --> Comment : 一对多
    User --> Book : 阅读/收藏
```

## 2. 核心流程顺序图

### 2.1 书籍AI摘要生成流程

```mermaid
sequenceDiagram
    participant Frontend as 前端页面
    participant Web as Web服务器
    participant AIService as AI_Book_Service
    participant Cache as AI_Response_Cache
    participant DB as calibre_db
    participant DeepSeek as DeepSeek API
    
    Frontend->>Web: AJAX请求: /ajax/ai/book_summary/123
    Web->>AIService: 调用 get_book_summary(123)
    AIService->>Cache: 检查缓存是否存在
    
    alt 缓存存在且未过期
        Cache-->>AIService: 返回缓存的摘要
    else 缓存不存在或已过期
        AIService->>DB: 调用 _get_book_info(123)
        DB-->>AIService: 返回书籍元数据
        AIService->>AIService: 构建AI prompt
        AIService->>DeepSeek: 调用API发送prompt
        DeepSeek-->>AIService: 返回AI生成的摘要
        AIService->>Cache: 保存摘要到缓存
    end
    
    AIService-->>Web: 返回摘要结果
    Web-->>Frontend: 返回JSON响应
    Frontend->>Frontend: 展示AI摘要
```

### 2.2 相关书籍推荐流程

```mermaid
sequenceDiagram
    participant Frontend as 前端页面
    participant Web as Web服务器
    participant AIService as AI_Book_Service
    participant Cache as AI_Response_Cache
    participant DB as calibre_db
    participant DeepSeek as DeepSeek API
    
    Frontend->>Web: AJAX请求: /ajax/ai/book_recommendations/123
    Web->>AIService: 调用 get_related_books(123)
    AIService->>Cache: 检查缓存是否存在
    
    alt 缓存存在且未过期
        Cache-->>AIService: 返回缓存的推荐结果
    else 缓存不存在或已过期
        AIService->>DB: 调用 _get_book_info(123)
        DB-->>AIService: 返回书籍元数据
        AIService->>AIService: 构建AI推荐prompt
        AIService->>DeepSeek: 调用API发送prompt
        DeepSeek-->>AIService: 返回AI推荐的书籍列表
        AIService->>Cache: 保存推荐结果到缓存
    end
    
    AIService-->>Web: 返回推荐结果
    Web-->>Frontend: 返回JSON响应
    Frontend->>Frontend: 展示推荐书籍列表
```

## 3. 图表说明

### 3.1 UML类图说明

UML类图展示了AI模块的核心类及其关系：

1. **核心实体**：
   - `AI_Book_Service`：AI书籍服务的核心类，提供书籍摘要生成和相关书籍推荐功能

2. **关联实体**：
   - `Book`：书籍类，包含书籍的基本信息和关联关系
   - `Author`、`Tag`、`Series`、`Comment`：与书籍相关的实体类
   - `User`：用户类，与书籍有阅读/收藏关系

3. **辅助类**：
   - `AI_Response_Cache`：AI响应缓存类，用于缓存AI生成的结果，提高性能
   - `calibre_db`：数据库访问类，用于获取书籍元数据

4. **关系**：
   - `AI_Book_Service` 使用 `Book` 实体的数据
   - `AI_Book_Service` 与 `AI_Response_Cache` 交互以缓存结果
   - `AI_Book_Service` 通过 `calibre_db` 获取书籍元数据
   - `Book` 与 `Author`、`Tag`、`Series` 是多对多关系
   - `Book` 与 `Comment` 是一对多关系
   - `User` 与 `Book` 有阅读/收藏关系

### 3.2 核心流程顺序图说明

1. **书籍AI摘要生成流程**：
   - 前端发起AJAX请求获取书籍摘要
   - Web服务器调用AI服务的`get_book_summary`方法
   - AI服务先检查缓存，如果缓存存在且未过期则直接返回
   - 如果缓存不存在或已过期，则获取书籍元数据，构建prompt，调用DeepSeek API
   - 将API返回的摘要保存到缓存，然后返回给前端
   - 前端展示AI生成的摘要

2. **相关书籍推荐流程**：
   - 前端发起AJAX请求获取相关书籍推荐
   - Web服务器调用AI服务的`get_related_books`方法
   - AI服务先检查缓存，如果缓存存在且未过期则直接返回
   - 如果缓存不存在或已过期，则获取书籍元数据，构建推荐prompt，调用DeepSeek API
   - 将API返回的推荐结果保存到缓存，然后返回给前端
   - 前端展示推荐的书籍列表

这些图表清晰地展示了AI模块的类结构和核心流程，有助于理解AI模块的设计和工作原理。