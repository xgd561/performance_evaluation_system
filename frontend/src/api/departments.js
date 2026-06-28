import request from './request'

export function listDepartments() {
  return request.get('/departments')
}

export function createDepartment(data) {
  return request.post('/departments', data)
}

export function updateDepartment(id, data) {
  return request.put(`/departments/${id}`, data)
}

export function deleteDepartment(id) {
  return request.delete(`/departments/${id}`)
}

export function listPositions(params) {
  return request.get('/positions', { params })
}

export function createPosition(data) {
  return request.post('/positions', data)
}

export function updatePosition(id, data) {
  return request.put(`/positions/${id}`, data)
}

export function deletePosition(id) {
  return request.delete(`/positions/${id}`)
}
