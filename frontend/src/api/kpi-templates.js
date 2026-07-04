import request from './request'

export function listKpiTemplates() {
  return request.get('/kpi-templates')
}

export function getKpiTemplate(id) {
  return request.get(`/kpi-templates/${id}`)
}

export function createKpiTemplate(data) {
  return request.post('/kpi-templates/single', data)
}

export function createKpiTemplatesBatch(data) {
  return request.post('/kpi-templates', data)
}

export function updateKpiTemplate(id, data) {
  return request.put(`/kpi-templates/single/${id}`, data)
}

export function updateKpiTemplatesBatch(id, data) {
  return request.put(`/kpi-templates/${id}`, data)
}

export function deleteKpiTemplate(id) {
  return request.delete(`/kpi-templates/${id}`)
}

export function copyKpiTemplate(id) {
  return request.post(`/kpi-templates/${id}/copy`)
}
