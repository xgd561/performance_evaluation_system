import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue'), meta: { roles: ['admin', 'hr', 'manager', 'employee', 'peer', 'executive'] } },
      { path: 'employees', name: 'Employees', component: () => import('@/views/employees/EmployeeList.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'departments', name: 'Departments', component: () => import('@/views/departments/DepartmentList.vue'), meta: { roles: ['admin'] } },
      { path: 'cycles', name: 'Cycles', component: () => import('@/views/cycles/CycleList.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'kpi-templates', name: 'KpiTemplates', component: () => import('@/views/kpi-templates/KpiTemplateList.vue'), meta: { roles: ['admin'] } },
      { path: 'kpi-templates/create', name: 'KpiTemplateCreate', component: () => import('@/views/kpi-templates/KpiTemplateEdit.vue'), meta: { roles: ['admin'] } },
      { path: 'kpi-templates/:id/edit', name: 'KpiTemplateEdit', component: () => import('@/views/kpi-templates/KpiTemplateEdit.vue'), meta: { roles: ['admin'] } },
      { path: 'config', name: 'Config', component: () => import('@/views/config/ConfigView.vue'), meta: { roles: ['admin'] } },
      { path: 'audit-logs', name: 'AuditLogs', component: () => import('@/views/audit/OperationLog.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'appeals', name: 'Appeals', component: () => import('@/views/appeal/AppealList.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'summary', name: 'Summary', component: () => import('@/views/summary/SummaryDashboard.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'reports', name: 'Reports', component: () => import('@/views/reports/ReportExport.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'distribution-review', name: 'DistributionReview', component: () => import('@/views/distribution-review/DistributionReview.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'kpi-adjustment-request', name: 'KpiAdjustmentRequest', component: () => import('@/views/kpi-adjustment/KpiAdjustmentRequest.vue'), meta: { roles: ['manager'] } },
      { path: 'kpi-adjustment-approval', name: 'KpiAdjustmentApproval', component: () => import('@/views/kpi-adjustment/KpiAdjustmentApproval.vue'), meta: { roles: ['admin', 'hr', 'executive', 'manager'] } },
      { path: 'score-sheet', name: 'ScoreSheet', component: () => import('@/views/score-sheet/ScoreSheetView.vue'), meta: { roles: ['manager'] } },
      { path: 'score-sheet-list', name: 'ScoreSheetList', component: () => import('@/views/score-sheet/ScoreSheetList.vue'), meta: { roles: ['manager'] } },
      { path: 'approval-workbench', name: 'ApprovalWorkbench', component: () => import('@/views/approval-workbench/ApprovalWorkbench.vue'), meta: { roles: ['manager', 'hr', 'admin'] } },
      { path: 'approval-detail', name: 'ApprovalDetail', component: () => import('@/views/approval-workbench/ApprovalDetail.vue'), meta: { roles: ['manager', 'hr', 'admin'] } },
      { path: 'interviews', name: 'Interviews', component: () => import('@/views/interview/InterviewList.vue'), meta: { roles: ['manager'] } },
      { path: 'interview-form', name: 'InterviewForm', component: () => import('@/views/interview/InterviewForm.vue'), meta: { roles: ['manager'] } },
      { path: 'peer-review', name: 'PeerReview', component: () => import('@/views/peer-review/PeerReviewList.vue'), meta: { roles: ['peer'] } },
      { path: 'peer-review/:taskId', name: 'PeerReviewScore', component: () => import('@/views/peer-review/PeerReviewScore.vue'), meta: { roles: ['peer'] } },
      { path: 'my-performance', name: 'MyPerformance', component: () => import('@/views/my-performance/MyPerformance.vue'), meta: { roles: ['employee'] } },
      { path: 'self-assessment', name: 'SelfAssessment', component: () => import('@/views/self-assessment/SelfAssessment.vue'), meta: { roles: ['employee'] } },
      { path: 'appeal', name: 'Appeal', component: () => import('@/views/appeal/AppealView.vue'), meta: { roles: ['employee'] } },
      { path: 'organization-chart', name: 'OrganizationChart', component: () => import('@/views/departments/OrganizationChart.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'positions', name: 'Positions', component: () => import('@/views/positions/PositionList.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'employees/edit', name: 'EmployeeEdit', component: () => import('@/views/employees/EmployeeEdit.vue'), meta: { roles: ['admin', 'hr'] } },
      { path: 'cycles/edit', name: 'CycleEdit', component: () => import('@/views/cycles/CycleEdit.vue'), meta: { roles: ['admin', 'hr'] } },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/403',
  },
]

export function beforeEachGuard(to, from, next) {
  const authStore = useAuthStore()
  if (!to.meta.public && !authStore.token) {
    next('/login')
    return
  }
  // 路由权限校验
  if (to.meta.roles && authStore.role) {
    if (!to.meta.roles.includes(authStore.role)) {
      next('/403')
      return
    }
  }
  next()
}

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(beforeEachGuard)

export default router
