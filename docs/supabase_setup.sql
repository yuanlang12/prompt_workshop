-- ============================================================
-- 提示词工坊 Supabase 建表脚本
--
-- 使用方法:
--   1. 在 https://supabase.com 创建一个免费项目
--   2. 打开左侧 SQL Editor，粘贴本文件全部内容并执行
--   3. 从 Project Settings -> API 页面获取三个配置值:
--        - Project URL        -> SUPABASE_URL
--        - anon public key    -> SUPABASE_KEY
--        - service_role key   -> SUPABASE_SERVICE_ROLE_KEY
--      填入 config/.env（参考 config/.env.example）
--
-- 说明:
--   应用的所有数据读写都通过后端使用 service_role 密钥完成，
--   因此这里只启用 RLS 而不开放任何客户端直连策略，
--   匿名/普通用户无法绕过后端直接读写这三张表。
-- ============================================================

-- ---------- 项目表 ----------
create table if not exists public.projects (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  description text,
  user_id     uuid not null references auth.users (id) on delete cascade,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz
);

-- ---------- 提示词表 ----------
create table if not exists public.prompts (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references public.projects (id) on delete cascade,
  title       text,
  description text,
  content     text not null default '',
  variables   jsonb default '{}'::jsonb,
  is_public   boolean not null default false,
  version     integer not null default 1,
  user_id     uuid not null references auth.users (id) on delete cascade,
  created_at  timestamptz not null default now()
);

-- ---------- 提示词版本历史表 ----------
create table if not exists public.prompt_history (
  id             uuid primary key default gen_random_uuid(),
  project_id     uuid not null references public.projects (id) on delete cascade,
  system_prompt  text not null default '',
  user_prompt    text not null default '',
  version        integer not null default 1,
  user_id        uuid not null references auth.users (id) on delete cascade,
  change_summary text,
  variables      jsonb default '{}'::jsonb,
  created_at     timestamptz not null default now()
);

-- ---------- 索引 ----------
create index if not exists idx_projects_user_id     on public.projects (user_id);
create index if not exists idx_prompts_project_id   on public.prompts (project_id);
create index if not exists idx_prompts_user_id      on public.prompts (user_id);
create index if not exists idx_prompt_history_project on public.prompt_history (project_id);

-- ---------- 行级安全 (RLS) ----------
-- 启用 RLS 且不添加任何策略: 客户端（anon / authenticated）一律拒绝，
-- 后端使用 service_role 密钥访问时不受 RLS 限制。
alter table public.projects       enable row level security;
alter table public.prompts        enable row level security;
alter table public.prompt_history enable row level security;

-- ---------- 注册登录说明 ----------
-- 用户体系使用 Supabase Auth（应用通过后端调用）。
-- 如需跳过邮箱验证方便本地试用: Authentication -> Providers -> Email
-- 中关闭 "Confirm email"；
-- 生产环境建议开启验证并配置自定义 SMTP。
