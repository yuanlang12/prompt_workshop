# 提示词系统升级实施计划

## ✅ 已完成的任务

### Task 1: 数据库架构升级 ✅
- 创建了迁移脚本 `migrations/001_add_user_prompt.sql`
- 将 `content` 字段重命名为 `system_prompt`
- 添加了 `user_prompt` 字段
- 更新了 Supabase schema 定义

### Task 2: 后端 API 更新 ✅
- 更新了 `SavePromptRequest` 模型，支持 `system_prompt` 和 `user_prompt`
- 修改了 `/api/prompts` 接口
- 更新了 `supabase_db.create_prompt_history()` 方法
- 添加了向后兼容性支持

### Task 3: TypeScript 类型定义更新 ✅
- 更新了 `Prompt` 接口
- 添加了 `system_prompt` 和 `user_prompt` 字段
- 保留了 `content` 字段以向后兼容

## 📋 待完成的任务

### Task 4: UI 组件统一化
需要修改的文件：
- `static/js/main.js` - 更新提示词显示逻辑
- `static/components/PromptCard.tsx` - 支持显示两个 prompts
- `static/css/style.css` - 添加统一的编辑器样式

关键改动：
```javascript
// 在 main.js 中
function displayPrompt(prompt) {
    // 显示 system prompt
    systemPromptDisplay.innerHTML = `<pre>${escapeHtml(prompt.system_prompt || prompt.content)}</pre>`;
    
    // 显示 user prompt
    userPromptDisplay.innerHTML = `<pre>${escapeHtml(prompt.user_prompt || '')}</pre>`;
}
```

### Task 5: 版本管理优化
需要修改的文件：
- `static/components/PromptVersions.tsx`
- `static/components/VersionTabs.tsx`
- `server.py` - 确保 API 返回完整数据

关键改动：
- 确保 `/api/projects/{id}/prompts` 返回 `system_prompt` 和 `user_prompt`
- 更新前端展示逻辑

### Task 6: UX 改进
功能列表：
1. **实时预览** - 编辑时即时显示效果
2. **自动保存提示** - 检测到修改时提示保存
3. **字符计数** - 显示 prompt 长度
4. **快捷键支持** - Ctrl+S 保存等

### Task 7: 测试功能集成
需要修改的文件：
- `static/js/main.js` - 测试界面逻辑
- `templates/index.html` - UI 结构

关键改动：
```javascript
// 使用保存的 user_prompt 作为测试默认值
function updateTestArea(prompt) {
    // 设置 system prompt
    testSystemPrompt.value = prompt.system_prompt || prompt.content;
    
    // 设置 user prompt (如果有保存的)
    testUserPrompt.value = prompt.user_prompt || '';
}
```

### Task 8: 数据迁移
执行步骤：
1. 在 Supabase SQL Editor 中运行 `migrations/001_add_user_prompt.sql`
2. 验证字段添加成功
3. 为现有数据设置默认值（如需要）

## 🎯 执行建议

### 方案 A: 分步执行（推荐）
1. **首先**: 执行数据库迁移（Task 8）
2. **然后**: 完成 UI 组件修改（Task 4-5）
3. **最后**: 添加 UX 改进（Task 6-7）

### 方案 B: 一次性完成
继续修改所有剩余文件，一次性部署

## 📝 关键注意事项

1. **向后兼容性**
   - 保留 `content` 字段的支持
   - API 同时支持新旧格式

2. **数据一致性**
   - 确保所有 API 返回统一格式
   - 前端统一使用 `system_prompt` 和 `user_prompt`

3. **测试清单**
   - [ ] 创建新提示词
   - [ ] 查看历史版本
   - [ ] 切换版本
   - [ ] 编辑提示词
   - [ ] 测试功能
   - [ ] 优化功能

## 🚀 下一步行动

当前已完成核心架构升级（数据库+后端+类型定义）。

**建议下一步**：
1. 先在 Supabase 后台执行数据库迁移
2. 重启服务器
3. 继续完成前端组件修改

需要我继续完成剩余任务吗？
