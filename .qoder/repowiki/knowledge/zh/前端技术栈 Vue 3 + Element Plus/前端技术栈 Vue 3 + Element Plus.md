---
kind: external_dependency
name: 前端技术栈 Vue 3 + Element Plus
slug: vue3-element-plus
category: external_dependency
category_hints:
    - framework_behavior
scope:
    - '**'
---

前端使用 Vue 3 + Element Plus 作为 UI 框架，Pinia 做状态管理，Vue Router 做路由，ECharts + vue-echarts 做图表展示，axios 调用后端 `/api/v1` 接口。开发期由 Vite 提供 dev server（端口 3000），代理到后端 8014；构建产物输出到 `frontend/dist`。