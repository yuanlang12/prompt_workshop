/**
 * 获取授权请求头
 * 
 * 从localStorage获取访问令牌并构建授权头
 * @returns 包含Authorization的请求头对象
 */
export function getAuthHeaders(): Record<string, string> {
  // 尝试从localStorage获取令牌
  const token = localStorage.getItem('access_token');
  if (token) {
      return { 'Authorization': `Bearer ${token}` };
  }
  
  // 使用Cookie认证时无需添加其他头
  // 浏览器会自动在请求中包含Cookie
  return {}; 
} 