import request from '@/api/request'

export function getLogs(params) {
  return request.get('/logs', { params })
}

export function getLogActions() {
  return request.get('/logs/actions')
}
