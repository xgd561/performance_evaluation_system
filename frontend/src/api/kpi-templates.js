import request from './request'

export function listKpiTemplates() {
  return request.get('/kpi-templates')
}

export function createKpiTemplate(data) {
  return request.post('/kpi-templates', data)
}

export function updateKpiTemplate(id, data) {
  return request.put(`/kpi-templates/${id}`, data)
}
