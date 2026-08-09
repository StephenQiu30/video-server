import type { ProLayoutProps } from '@ant-design/pro-components';

/**
 * @name
 */
const Settings: ProLayoutProps & {
  logo?: string;
} = {
  navTheme: 'light',
  colorPrimary: '#1677FF',
  layout: 'top',
  contentWidth: 'Fixed',
  fixedHeader: false,
  colorWeak: false,
  title: '帧取',
  logo: '/logo.png',
  iconfontUrl: '',
  token: {
    bgLayout: '#fff',
    header: {
      colorBgHeader: '#fff',
      colorBgScrollHeader: '#fff',
    },
    pageContainer: {
      colorBgPageContainer: '#fff',
      colorBgPageContainerFixed: '#fff',
    },
  },
};

export default Settings;
