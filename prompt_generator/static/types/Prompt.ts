/**
 * 提示词数据结构定义
 */
export interface Prompt {
  /** 提示词ID */
  id: string;
  
  /** 所属项目ID */
  project_id: string;
  
  /** System Prompt 内容 */
  system_prompt: string;
  
  /** User Prompt 内容 */
  user_prompt?: string;
  
  /** 提示词内容 (向后兼容，映射到 system_prompt) */
  content?: string;
  
  /** 提示词中的变量列表 */
  variables: string[];
  
  /** 提示词版本号 */
  version: string | number;
  
  /** 创建时间 */
  created_at?: string;
  
  /** 最后更新时间 */
  updated_at?: string;
  
  /** 变更说明 */
  change_summary?: string;
} 