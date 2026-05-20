import client from './client'

export const register = (name, email, password) =>
  client.post('/api/auth/register', { name, email, password })

export const login = (email, password) =>
  client.post('/api/auth/login', { email, password })

export const getMe = () =>
  client.get('/api/auth/me')

export const saveReport = (reportData) =>
  client.post('/api/reports/save', reportData)

export const getHistory = (limit=20, skip=0) =>
  client.get(`/api/reports/history?limit=${limit}&skip=${skip}`)

export const getReportDetail = (reportId) =>
  client.get(`/api/reports/history/${reportId}`)

export const getSummary = () =>
  client.get('/api/reports/summary')

export const deleteReport = (reportId) =>
  client.delete(`/api/reports/history/${reportId}`)
