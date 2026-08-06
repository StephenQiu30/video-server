import React from 'react';
import ReactDOM from 'react-dom/client';

import { App } from './app';
import './global.css';

const root = document.getElementById('root');
if (!root) {
  throw new Error('root_element_missing');
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
