import request from './request'

export function listKpiTemplates() {
  return request.get('/kpi-templates')
}

export function createKpiTemplate(data) {
  return request.post('/kpi-templates/single', data)
}

export function updateKpiTemplate(id, data) {
  return request.put(`/kpi-templates/single/${id}`, data)
}

export function deleteKpiTemplate(id) {
  return request.delete(`/kpi-templates/${id}`)
}
