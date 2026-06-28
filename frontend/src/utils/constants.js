// 角色枚举
export const ROLES = {
  ADMIN: 'admin',
  HR: 'hr',
  MANAGER: 'manager',
  EMPLOYEE: 'employee',
  PEER: 'peer'
}

// 考核状态枚举
export const ASSESSMENT_STATUS = {
  NOT_STARTED: 'not_started',
  PENDING_SELF: 'pending_self',
  PENDING_MANAGER: 'pending_manager',
  PENDING_PEER: 'pending_peer',
  PENDING_SUMMARY: 'pending_summary',
  PENDING_DISTRIBUTION: 'pending_distribution_review',
  PENDING_APPROVAL: 'pending_approval',
  PUBLISHED: 'published',
  ARCHIVED: 'archived',
  CANCELLED: 'cancelled'
}

// 考核状态显示文本
export const ASSESSMENT_STATUS_TEXT = {
  not_started: '未开始',
  pending_self: '自评中',
  pending_manager: '上级评分中',
  pending_peer: '协作评分中',
  pending_summary: '汇总中',
  pending_distribution_review: '强制分布处理中',
  pending_approval: '审批中',
  published: '已发布',
  archived: '已归档',
  cancelled: '已取消'
}

// 绩效等级枚举
export const GRADES = {
  A: 'A',
  B: 'B',
  C: 'C',
  D: 'D'
}

// 绩效等级显示文本
export const GRADE_TEXT = {
  A: '优秀',
  B: '良好',
  C: '合格',
  D: '待改进'
}

// 评分维度枚举
export const DIMENSIONS = {
  PERFORMANCE: 'performance',
  ABILITY: 'ability',
  ATTITUDE: 'attitude'
}

// 评分维度显示文本
export const DIMENSION_TEXT = {
  performance: '工作业绩',
  ability: '工作能力',
  attitude: '工作态度'
}

// 评分锚点说明
export const SCORE_ANCHORS = [
  { range: '90-100', label: '优秀', desc: '超出预期，表现卓越' },
  { range: '80-89', label: '良好', desc: '符合预期，表现稳定' },
  { range: '60-79', label: '合格', desc: '基本符合，仍有提升空间' },
  { range: '0-59', label: '待改进', desc: '明显不足，需制定改进计划' }
]

// 角色显示文本
export const ROLE_TEXT = {
  admin: '系统管理员',
  hr: 'HR/绩效专员',
  manager: '部门负责人',
  employee: '普通员工',
  peer: '协作评分人'
}

// 角色权限菜单
export const ROLE_MENU_ITEMS = {
  admin: [
    { path: '/dashboard', title: '首页', icon: 'HomeFilled' },
    { path: '/employees', title: '员工管理', icon: 'UserFilled' },
    { path: '/cycles', title: '考核周期', icon: 'Calendar' },
    { path: '/summary', title: '分数汇总', icon: 'Histogram' },
    { path: '/distribution-review', title: '强制分布', icon: 'WarningFilled' },
    { path: '/reports', title: '报表分析', icon: 'TrendCharts' },
    { path: '/admin', title: '系统配置', icon: 'Setting' }
  ],
  hr: [
    { path: '/dashboard', title: '首页', icon: 'HomeFilled' },
    { path: '/employees', title: '员工管理', icon: 'UserFilled' },
    { path: '/cycles', title: '考核周期', icon: 'Calendar' },
    { path: '/summary', title: '分数汇总', icon: 'Histogram' },
    { path: '/distribution-review', title: '强制分布', icon: 'WarningFilled' },
    { path: '/reports', title: '报表分析', icon: 'TrendCharts' },
    { path: '/appeal', title: '申诉处理', icon: 'ChatDotRound' }
  ],
  manager: [
    { path: '/dashboard', title: '首页', icon: 'HomeFilled' },
    { path: '/score-sheet', title: '评分', icon: 'EditPen' },
    { path: '/approval-workbench', title: '审批工作台', icon: 'Stamp' },
    { path: '/interview', title: '绩效面谈', icon: 'ChatRound' },
    { path: '/summary', title: '部门汇总', icon: 'Histogram' }
  ],
  employee: [
    { path: '/dashboard', title: '首页', icon: 'HomeFilled' },
    { path: '/score-sheet', title: '自评', icon: 'EditPen' },
    { path: '/my-performance', title: '我的绩效', icon: 'UserFilled' },
    { path: '/appeal', title: '申诉', icon: 'ChatDotRound' }
  ],
  peer: [
    { path: '/dashboard', title: '首页', icon: 'HomeFilled' },
    { path: '/score-sheet', title: '协作评分', icon: 'EditPen' }
  ]
}
