import request from './request'
import axios from 'axios'

export function getDistribution(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/distribution`)
}

export function exportCycleReport(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/export`)
}

export function exportCycleReportExcel(cycleId, departmentIds = []) {
  const token = localStorage.getItem('token')
  const params = new URLSearchParams()
  if (departmentIds.length > 0) {
    departmentIds.forEach(id => params.append('department_id', id))
  }
  return axios.get(`/api/v1/assessment-cycles/${cycleId}/export-excel?${params.toString()}`, {
    responseType: 'blob',
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
}

export function exportCycleReportPdf(cycleId, departmentIds = []) {
  const token = localStorage.getItem('token')
  const params = new URLSearchParams()
  if (departmentIds.length > 0) {
    departmentIds.forEach(id => params.append('department_id', id))
  }
  return axios.get(`/api/v1/assessment-cycles/${cycleId}/archive-pdf?${params.toString()}`, {
    responseType: 'blob',
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
}

export function getEmployeeTrend(employeeId, params = {}) {
  return request.get(`/reports/employee/${employeeId}/trend`, { params })
}
