import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getWsUrl = (path: string): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = API_BASE_URL || window.location.host;
  const cleanHost = host.replace(/^https?:\/\//, '');
  return `${protocol}//${cleanHost}${path}`;
};
