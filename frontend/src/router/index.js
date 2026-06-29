import { createRouter, createWebHistory } from 'vue-router'
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
      { path: 'appeals', name: 'Appeals', component: () => import('@/views/appeal/AppealList.vue') },
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
