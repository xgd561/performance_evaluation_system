import request from './request'

export function listEmployees(params) {
  return request.get('/employees', { params })
}

export function createEmployee(data) {
  return request.post('/employees', data)
}

export function updateEmployee(id, data) {
  return request.put(`/employees/${id}`, data)
}

export function deleteEmployee(id) {
  return request.delete(`/employees/${id}`)
}

export function importEmployees(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/employees/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function downloadTemplate(type = 'empty') {
  return request.get(`/employees/template?type=${type}`, { responseType: 'blob' })
}
