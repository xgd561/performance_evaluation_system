import request from './request'

export function listAppeals(params) {
  return request.get('/appeals', { params })
}

export function getAppeal(id) {
  return request.get(`/appeals/${id}`)
}

export function createAppeal(data) {
  return request.post('/appeals', data)
}

export function reviewAppeal(id, data) {
  return request.post(`/appeals/${id}/review`, data)
}
