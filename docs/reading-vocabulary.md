# 阅读单词学习

EPUB 阅读器支持在当前可见页面识别英文单词，并将学习上下文交给 `moon-well` 保存。

## 功能

- 当前页面中的英文单词会被批量识别。
- `moon-well` 根据用户历史返回陌生词和释义。
- 陌生词在阅读器中以波浪下划线标识，悬停或点击可查看释义及上次学习信息。
- 每次遇到单词都会保存：单词、句子、用户、书籍 ID/名称、章节、页码、EPUB CFI、学习时间和次数。
- 历史记录使用 Elasticsearch 的 `reading_vocabulary` 索引保存；原有 `vocabulary` 索引继续提供词汇释义。

## 配置

在 magicbook 进程配置：

```bash
MOON_WELL_READING_URL=https://moon-well.example.com
MOON_WELL_INTEGRATION_TOKEN=replace-with-a-long-random-token
```

在 moon-well 进程配置同一个令牌：

```bash
MAGICBOOK_INTEGRATION_TOKEN=replace-with-a-long-random-token
```

magicbook 通过自己的 Flask 登录会话确定用户，并在服务端代理请求；令牌不会下发到浏览器。moon-well 的 `/reading-vocabulary/**` 是集成接口，使用 `X-Magicbook-Token` 校验令牌。

## 当前范围

第一版接入 EPUB/KEPUB 阅读器，因为 epub.js 能直接访问当前章节 iframe 的 HTML 文本和 CFI 位置。PDF、TXT、漫画和音频阅读器尚未接入这套识词流程。

如果没有配置 moon-well 地址或令牌，阅读器保持原有行为，不显示错误弹窗。
