import request from './request'

export function listCycles(params = {}) {
  return request.get('/assessment-cycles', { params })
}

export function getCycleDetail(id) {
  return request.get(`/assessment-cycles/${id}`)
}

export function createCycle(data) {
  return request.post('/assessment-cycles', data)
}

export function updateCycle(id, data) {
  return request.put(`/assessment-cycles/${id}`, data)
}

export function deleteCycle(id) {
  return request.delete(`/assessment-cycles/${id}`)
}

export function launchCycle(data) {
  return request.post('/assessment-cycles/launch', data)
}

export function getCycleProgress(id) {
  return request.get(`/assessment-cycles/${id}/progress`)
}

export function publishCycle(id) {
  return request.post(`/assessment-cycles/${id}/publish`)
}

export function listCycleEmployees(cycleId) {
  return request.get(`/assessment-cycles/${cycleId}/employees`)
}
