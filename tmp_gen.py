import os

BASE = 'D:/cc_project/performance_evaluation_system/frontend'
SRC = os.path.join(BASE, 'src')

os.makedirs(os.path.join(SRC, 'views/login'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'views/dashboard'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'views/employees'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'views/departments'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'views/cycles'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'views/kpi-templates'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'views/config'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'components'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'router'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'stores'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'api'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'utils'), exist_ok=True)
os.makedirs(os.path.join(SRC, 'styles'), exist_ok=True)

files = {}

files['src/App.vue'] = '<template>\n  <router-view />\n</template>\n\n<script setup>\n</script>\n\n<style>\nhtml, body, #app {\n  height: 100%;\n  margin: 0;\n  padding: 0;\n}\n</style>\n'

files['src/router/index.js'] = """import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },
      { path: 'employees', name: 'Employees', component: () => import('@/views/employees/EmployeeList.vue') },
      { path: 'departments', name: 'Departments', component: () => import('@/views/departments/DepartmentList.vue') },
      { path: 'cycles', name: 'Cycles', component: () => import('@/views/cycles/CycleList.vue') },
      { path: 'kpi-templates', name: 'KpiTemplates', component: () => import('@/views/kpi-templates/KpiTemplateList.vue') },
      { path: 'config', name: 'Config', component: () => import('@/views/config/ConfigView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (!to.meta.public && !authStore.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
"""

files['src/stores/auth.js'] = """import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role || '')

  async function doLogin(credentials) {
    const res = await login(credentials)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    user.value = res.user
    return res
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await getMe()
      user.value = res
    } catch (e) {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, role, doLogin, fetchUser, logout }
})
"""

files['src/api/request.js'] = """import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code !== undefined && data.code !== 200 && data.code !== 201) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  (error) => {
    const msg = error.response?.data?.message || error.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default request
"""

files['src/api/auth.js'] = """import request from './request'

export function login(data) {
  return request.post('/auth/login', data)
}

export function getMe() {
  return request.get('/auth/me')
}

export function changePassword(data) {
  return request.post('/auth/change-password', data)
}
"""

files['src/api/employees.js'] = """import request from './request'

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
"""

files['src/api/departments.js'] = """import request from './request'

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
"""

files['src/api/cycles.js'] = """import request from './request'

export function listCycles() {
  return request.get('/assessment-cycles')
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
"""

files['src/api/kpi-templates.js'] = """import request from './request'

export function listKpiTemplates() {
  return request.get('/kpi-templates')
}

export function createKpiTemplate(data) {
  return request.post('/kpi-templates', data)
}

export function updateKpiTemplate(id, data) {
  return request.put(`/kpi-templates/${id}`, data)
}
"""

files['src/api/config.js'] = """import request from './request'

export function getGradeRules() {
  return request.get('/config/grade-rules')
}

export function updateGradeRules(data) {
  return request.put('/config/grade-rules', data)
}

export function getDimensionWeights() {
  return request.get('/config/dimension-weights')
}

export function updateDimensionWeights(data) {
  return request.put('/config/dimension-weights', data)
}

export function getReviewerWeights() {
  return request.get('/config/reviewer-weights')
}

export function updateReviewerWeights(data) {
  return request.put('/config/reviewer-weights', data)
}

export function getSmallDeptExemption() {
  return request.get('/config/small-dept-exemption')
}

export function updateSmallDeptExemption(data) {
  return request.put('/config/small-dept-exemption', data)
}
"""

for rel_path, content in files.items():
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Created {rel_path}')

print('Done')
