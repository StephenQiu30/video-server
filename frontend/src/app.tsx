import type { RequestConfig, RunTimeLayoutConfig } from '@umijs/max';
import defaultSettings from '../config/defaultSettings';
import { requestErrorConfig } from './requestErrorConfig';

export const layout: RunTimeLayoutConfig = () => ({
  ...defaultSettings,
  actionsRender: () => [],
  footerRender: () => null,
});

export const request: RequestConfig = requestErrorConfig;
