export const accessPolicyLabel: Record<API.ProviderAccessPolicy, string> = {
  public: '公开无会话',
  public_session: '公开访客会话',
  operator_public: '部署者公开会话',
  personal_entitled: '个人授权会话',
};

export function routeCooldownLabel(retryAt: string): string {
  return `最早重试时间：${new Date(retryAt).toLocaleString('zh-CN')}；到期仍需验证恢复。`;
}
