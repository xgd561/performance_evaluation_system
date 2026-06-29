import request from './request'

export function getMyAppeals() {
  return request.get('/appeals/my-appeals')
}

export function createAppeal(data) {
  return request.post('/appeals', data)
}

export function listAppeals(params) {
  return request.get('/appeals', { params })
}

export function getAppeal(appealId) {
  return request.get(`/appeals/${appealId}`)
}

export function reviewAppeal(appealId, data) {
  return request.post(`/appeals/${appealId}/review`, data)
}
