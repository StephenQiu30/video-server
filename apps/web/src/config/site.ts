export const siteConfig = {
  name: import.meta.env.VITE_SITE_NAME || "Stephen视频下载器",
  description: "专业级 AI 视频下载与智能分析平台",
  url: import.meta.env.VITE_SITE_URL || "http://localhost:3000",
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  links: {
    github: "https://github.com/StephenQiu30/stephen-video",
  },
  currentYear: new Date().getFullYear(),
};

export type SiteConfig = typeof siteConfig;
