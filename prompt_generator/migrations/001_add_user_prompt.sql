-- 数据库迁移脚本: 添加 user_prompt 字段到 prompt_history 表
-- 日期: 2025-09-30
-- 描述: 支持同时保存 system prompt 和 user prompt

-- 1. 重命名现有的 content 字段为 system_prompt (保持向后兼容)
ALTER TABLE prompt_history 
  RENAME COLUMN content TO system_prompt;

-- 2. 添加 user_prompt 字段
ALTER TABLE prompt_history
  ADD COLUMN IF NOT EXISTS user_prompt TEXT DEFAULT '';

-- 3. 为新字段添加注释
COMMENT ON COLUMN prompt_history.system_prompt IS 'System Prompt 内容 (原 content 字段)';
COMMENT ON COLUMN prompt_history.user_prompt IS 'User Prompt 内容';

-- 4. 为现有数据设置默认的 user_prompt (如果需要)
-- UPDATE prompt_history 
-- SET user_prompt = '' 
-- WHERE user_prompt IS NULL;
