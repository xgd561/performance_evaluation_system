import request from './request'
import axios from 'axios'

export function getDistribution(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/distribution`)
}

export function exportCycleReport(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/export`)
}

export function exportCycleReportExcel(cycleId) {
  const token = localStorage.getItem('token')
  return axios.get(`/api/reports/cycle/${cycleId}/export`, {
    responseType: 'blob',
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
}

export function getEmployeeTrend(employeeId) {
  return request.get(`/reports/employee/${employeeId}/trend`)
}
