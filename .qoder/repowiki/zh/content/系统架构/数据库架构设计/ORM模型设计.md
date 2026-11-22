# ORM模型设计

<cite>
**本文引用的文件**   
- [models.py](file://backend/app/models.py)
- [database.py](file://backend/app/database.py)
- [main.py](file://backend/app/main.py)
- [employees.py](file://backend/app/routers/employees.py)
- [scores.py](file://backend/app/routers/scores.py)
- [config_service.py](file://backend/app/services/config_service.py)
- [test_level_field.py](file://backend/tests/test_level_field.py)
- [test_migration_autofill.py](file://backend/tests/test_migration_autofill.py)
</cite>

## 更新摘要
**变更内容**   
- 新增位置/员工级别字段（level）的P/M职级验证逻辑
- 增强权重验证系统，支持评分人权重和维度权重的双重校验
- 改进数据库迁移系统，使用SQLAlchemy元数据检查实现自动列补齐
- 更新模型关系图以反映新的级别字段配置

## 目录
1. [引言](#引言)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能与查询优化](#性能与查询优化)
8. [模型验证与业务逻辑](#模型验证与业务逻辑)
9. [使用示例：实例化、查询、更新](#使用示例实例化查询更新)
10. [故障排查指南](#故障排查指南)
11. [结论](#结论)

## 引言
本文面向 SQLAlchemy ORM 模型层，系统性梳理本项目的 Base 继承体系、模型基类设计、relationship 配置策略（back_populates、foreign_keys、remote_side 等）、关联查询优化方法（懒加载、立即加载、选择加载），以及模型层的验证规则与业务逻辑边界。同时给出基于现有路由代码的实例化、查询、更新示例路径，帮助读者快速理解并安全扩展模型。

**更新** 本次更新重点增强了模型schema的复杂性，包括 sophisticated weight validation logic supporting reviewer-based and dimension-based weights，position/employee level field with P/M rank validation，以及 improved database migration system using SQLAlchemy metadata inspection。

## 项目结构
本项目后端采用 FastAPI + SQLAlchemy ORM。ORM 相关代码集中在以下位置：
- 数据库连接与会话管理：backend/app/database.py
- ORM 模型定义：backend/app/models.py
- 数据库迁移系统：backend/app/main.py
- 使用模型的 API 路由：backend/app/routers/employees.py、backend/app/routers/scores.py
- 配置服务：backend/app/services/config_service.py

```mermaid
graph TB
subgraph "后端应用"
DB["数据库连接与会话<br/>database.py"]
Models["ORM 模型定义<br/>models.py"]
Migration["数据库迁移系统<br/>main.py"]
R_Employees["员工相关路由<br/>routers/employees.py"]
R_Scores["评分相关路由<br/>routers/scores.py"]
ConfigService["配置服务<br/>services/config_service.py"]
end
DB --> Models
Migration --> Models
R_Employees --> Models
R_Scores --> Models
ConfigService --> Models
```

图表来源
- [database.py:13-30](file://backend/app/database.py#L13-L30)
- [models.py:1-6](file://backend/app/models.py#L1-L6)
- [main.py:120-164](file://backend/app/main.py#L120-L164)
- [employees.py:1-32](file://backend/app/routers/employees.py#L1-L32)
- [scores.py:1-21](file://backend/app/routers/scores.py#L1-L21)
- [config_service.py:1-100](file://backend/app/services/config_service.py#L1-L100)

章节来源
- [database.py:1-31](file://backend/app/database.py#L1-L31)
- [models.py:1-6](file://backend/app/models.py#L1-L6)

## 核心组件
- Base 与 declarative_base：所有模型均继承自 Base，用于统一声明表结构与元数据。
- 基础实体模型：Department、Position、Employee、User。
- 考核域模型：AssessmentCycle、AssessmentRecord、ScoreDetail、KpiTemplate、KpiAdjustment。
- 流程与协作模型：ApprovalRecord、PeerReviewer、PeerReviewTask、AppealRecord、InterviewRecord。
- 辅助与系统模型：OperationLog、SystemConfig、Notification、ScoreDraft。

这些模型通过 relationship 建立双向或单向关联，支撑组织人事、绩效考核、审批申诉、协作评价等业务场景。

**更新** 新增了 Position.level 和 Employee.level 字段，用于存储P/M职级信息，支持前端岗位表单和员工表单的职级展示与筛选功能。

章节来源
- [models.py:8-273](file://backend/app/models.py#L8-L273)

## 架构总览
下图展示核心模型之间的主要关系，包括部门-岗位-员工、用户-员工一对一、考核记录与草稿一对多、上级-下属递归关系等。

```mermaid
classDiagram
class Department {
+int id
+string name
+string code
+int parent_id
+int head_id
+datetime created_at
}
class Position {
+int id
+string name
+string level
+int department_id
+datetime created_at
}
class Employee {
+int id
+string employee_no
+string name
+string level
+int department_id
+int position_id
+int manager_id
+bool is_department_head
+bool is_active
+datetime created_at
}
class User {
+int id
+string username
+string password_hash
+string role
+int employee_id
+bool is_active
+bool is_first_login
+datetime created_at
}
class AssessmentCycle {
+int id
+string name
+string type
+date start_date
+date end_date
+string status
+json dimension_weights
+json reviewer_weights
+json grade_rules
+bool is_distribution_enabled
+bool small_dept_exemption
+bool peer_review_enabled
+json approval_chain_config
+bool is_locked
+datetime archived_at
+datetime created_at
+datetime updated_at
}
class AssessmentRecord {
+int id
+int cycle_id
+int employee_id
+int position_id
+int department_id
+json kpi_snapshot
+json self_scores
+json manager_scores
+json peer_scores
+decimal weighted_performance
+decimal weighted_ability
+decimal weighted_attitude
+decimal total_score
+string grade
+string original_grade
+bool is_distribution_override
+text override_reason
+text manager_comment
+json manager_draft_scores
+json self_draft_scores
+json peer_draft_scores
+bool manager_submitted
+bool is_locked
+json interview_record
+json appeal_record
+string archive_pdf_path
+string status
+datetime created_at
+datetime updated_at
}
class ScoreDetail {
+int id
+int record_id
+int kpi_template_id
+string kpi_name
+decimal weight
+decimal self_score
+decimal manager_score
+string target_value
+datetime created_at
}
class KpiTemplate {
+int id
+int position_id
+string name
+decimal weight
+string target_value
+string scoring_method
+text description
+bool is_active
+datetime created_at
}
class ScoreDraft {
+int id
+int record_id
+string draft_type
+json draft_data
+datetime created_at
+datetime updated_at
}
Department "1" --> "many" Position : "positions"
Department "1" --> "many" Employee : "employees"
Position "1" --> "many" Employee : "employees"
Position "1" --> "many" KpiTemplate : "kpi_templates"
Employee "1" --> "1" User : "user (uselist=False)"
Employee "1" --> "many" Employee : "subordinates"
AssessmentRecord "1" --> "many" ScoreDetail : "details"
AssessmentRecord "1" --> "many" ScoreDraft : "drafts (cascade all, delete-orphan)"
AssessmentCycle "1" --> "many" AssessmentRecord : "records"
```

图表来源
- [models.py:8-273](file://backend/app/models.py#L8-L273)

## 详细组件分析

### Base 与模型基类设计
- Base 由 declarative_base() 创建，作为所有模型的基类，集中管理表元数据。
- 所有模型通过 __tablename__ 指定表名，并通过 Column 定义字段类型、约束、默认值、索引等。
- 时间戳字段普遍使用 default=datetime.utcnow，部分更新字段使用 onupdate=datetime.utcnow。
- JSON 字段用于存储复杂配置与快照数据，如维度权重、评分人权重、等级规则、KPI 快照、草稿数据等。

**更新** 新增了 Position.level 和 Employee.level 字段，类型为 String(20)，nullable=True，用于存储P/M职级信息。

章节来源
- [models.py:1-6](file://backend/app/models.py#L1-L6)
- [models.py:20-31](file://backend/app/models.py#L20-L31)
- [models.py:33-52](file://backend/app/models.py#L33-L52)
- [models.py:66-91](file://backend/app/models.py#L66-L91)
- [models.py:237-248](file://backend/app/models.py#L237-L248)

### relationship 定义与参数说明

#### back_populates：双向关系一致性
- 在两个模型上分别定义 relationship，并使用相同的 back_populates 名称，确保访问时双向同步。
- 典型用法：
  - Department.employees 与 Employee.department
  - Position.employees 与 Employee.position
  - Position.kpi_templates 与 KpiTemplate.position
  - AssessmentRecord.drafts 与 ScoreDraft.record

这种配置避免 N+1 查询时的歧义，并让对象图保持一致性。

章节来源
- [models.py:17-18](file://backend/app/models.py#L17-L18)
- [models.py:29-31](file://backend/app/models.py#L29-L31)
- [models.py:47-51](file://backend/app/models.py#L47-L51)
- [models.py:104](file://backend/app/models.py#L104)
- [models.py:138](file://backend/app/models.py#L138)
- [models.py:248](file://backend/app/models.py#L248)

#### foreign_keys：明确外键归属
- 当同一模型存在多个外键指向同一目标模型时，必须用 foreign_keys 指明具体列，避免歧义。
- 典型用法：
  - Department.employees 使用 foreign_keys="Employee.department_id"
  - Position.employees 使用 foreign_keys="Employee.position_id"
  - Employee.department 使用 foreign_keys=[department_id]
  - Employee.position 使用 foreign_keys=[position_id]

章节来源
- [models.py:17](file://backend/app/models.py#L17)
- [models.py:30](file://backend/app/models.py#L30)
- [models.py:47-48](file://backend/app/models.py#L47-L48)

#### remote_side：自引用关系的远端侧
- 自引用关系需要指定 remote_side，以表明"远端"是哪一侧的主键。
- 典型用法：
  - Employee.manager 使用 remote_side=[id]，表示 manager 指向的是另一个 Employee 的 id。
  - Employee.subordinates 通过 back_populates="manager" 与 manager 形成双向关系。

章节来源
- [models.py:49-50](file://backend/app/models.py#L49-L50)

#### uselist=False：一对一关系
- Employee.user 使用 uselist=False，表示一个员工对应一个用户账户，返回单个对象而非列表。
- User.employee 通过 back_populates="employee" 与之配对。

章节来源
- [models.py:51](file://backend/app/models.py#L51)
- [models.py:64](file://backend/app/models.py#L64)

#### cascade：级联删除孤儿
- AssessmentRecord.drafts 使用 cascade="all, delete-orphan"，当父记录删除时，子草稿自动清理，避免孤儿数据。

章节来源
- [models.py:138](file://backend/app/models.py#L138)

### 关键模型职责与复杂度

- Department：部门主数据，支持层级结构（parent_id）与负责人（head_id）。
- Position：岗位主数据，隶属于部门，承载 KPI 模板，新增 level 字段支持P/M职级。
- Employee：员工主数据，包含部门、岗位、直属上级、是否部门负责人、是否在职等属性；新增 level 字段；提供 manager/subordinates 自引用关系。
- User：认证账户，与 Employee 一对一绑定。
- AssessmentCycle：考核周期配置，包含维度权重、评分人权重、等级规则、强制分布开关、协作评分开关、审批链配置等。
- AssessmentRecord：考核记录，聚合自评、上级评、协作评、加权得分、等级、状态机状态、归档路径等。
- ScoreDetail：KPI 明细评分，按记录维度展开。
- KpiTemplate：岗位 KPI 模板，含权重、目标值、评分方式等。
- ScoreDraft：评分草稿，支持自评、上级评、协作评等多类型草稿。
- ApprovalRecord、PeerReviewer、PeerReviewTask、AppealRecord、InterviewRecord：流程与协作相关实体。
- OperationLog、SystemConfig、Notification：审计、系统配置、通知。

复杂度分析要点：
- 自引用关系（Employee.manager/subordinates）适合树形遍历，但深度过大时需限制递归深度以避免性能问题。
- JSON 字段承载大量业务配置与快照，读取时需进行解析与校验，建议在服务层做缓存与校验。
- AssessmentRecord 与 ScoreDetail、ScoreDraft 是一对多关系，批量操作时应注意事务边界与级联行为。
- **新增** Position.level 和 Employee.level 字段为业务展示和筛选提供支持，不参与评分计算。

章节来源
- [models.py:8-273](file://backend/app/models.py#L8-L273)

## 依赖关系分析
- database.py 负责引擎创建、会话工厂、初始化建表，并提供 get_db 依赖注入函数。
- models.py 定义所有模型，Base.metadata.create_all 会依据模型生成表结构。
- main.py 实现了增强的数据库迁移系统，使用 SQLAlchemy 元数据检查自动补齐缺失列。
- routers/employees.py 与 routers/scores.py 通过 Session 访问模型，执行 CRUD 与业务逻辑。

```mermaid
graph LR
Engine["Engine<br/>create_engine"] --> SessionLocal["SessionLocal<br/>sessionmaker"]
SessionLocal --> GetDB["get_db()"]
Models["models.py 模型"] --> Metadata["Base.metadata"]
InitDB["init_db()"] --> Metadata
Migration["_migrate_db()<br/>metadata inspection"] --> Metadata
R_Employees["routers/employees.py"] --> SessionLocal
R_Scores["routers/scores.py"] --> SessionLocal
```

图表来源
- [database.py:13-30](file://backend/app/database.py#L13-L30)
- [models.py:1-6](file://backend/app/models.py#L1-L6)
- [main.py:120-164](file://backend/app/main.py#L120-L164)

章节来源
- [database.py:1-31](file://backend/app/database.py#L1-L31)
- [models.py:1-6](file://backend/app/models.py#L1-L6)

## 性能与查询优化

### 懒加载（默认）
- 未显式配置 eager loading 时，relationship 默认懒加载。
- 优点：按需加载，减少初始查询负载。
- 风险：在循环中访问关联对象可能产生 N+1 查询。

适用场景：
- 列表页仅展示主表字段，不频繁访问关联对象。
- 单条详情页面按需加载关联数据。

### 立即加载（joinedload）
- 使用 joinedload 在一次 SQL 中 JOIN 获取关联数据，避免 N+1。
- 当前路由中已引入 joinedload，可用于后续优化。

建议用法：
- 在需要一次性获取员工及其部门、岗位、上级信息的接口中使用 joinedload。
- 在评分汇总、审批详情等涉及多表关联的场景中优先使用。

章节来源
- [employees.py:1-3](file://backend/app/routers/employees.py#L1-L3)

### 选择加载（selectinload）
- selectinload 通过 IN 查询批量加载关联集合，适合一对多关系且子集较大的场景。
- 适用于 AssessmentRecord.drafts、ScoreDetail 等一对多关系的大列表场景。

建议用法：
- 批量获取考核记录的草稿或 KPI 明细时，使用 selectinload 降低往返次数。

### 查询优化实践建议
- 在列表接口中尽量只 SELECT 必要字段，避免 SELECT *。
- 对高频关联字段使用 joinedload/selectinload，避免 N+1。
- 对大结果集使用分页（limit/offset）与索引（Column(index=True)）。
- 对 JSON 字段进行结构化校验与缓存，避免重复解析。

章节来源
- [models.py:10-15](file://backend/app/models.py#L10-L15)
- [models.py:33-41](file://backend/app/models.py#L33-L41)
- [models.py:66-91](file://backend/app/models.py#L66-L91)

## 模型验证与业务逻辑

### 模型层验证
- 字段约束：nullable、unique、default、onupdate 等约束在模型层保证数据完整性。
- 唯一约束：表级 UniqueConstraint 用于组合唯一性（如 cycle_employees、peer_reviewers、score_drafts）。
- JSON 校验：在路由与服务层对 JSON 字段进行合法性校验（如维度权重之和为 1.0 或 100%）。

**更新** 新增了 sophisticated weight validation logic：
- 维度权重验证：确保 dimension_weights 总和为 1.0 或 100%
- 评分人权重验证：确保每个维度的 reviewer_weights 总和为 1.0 或 100%
- 位置/员工级别验证：支持 P/M 职级格式验证

章节来源
- [models.py:174-184](file://backend/app/models.py#L174-L184)
- [models.py:239](file://backend/app/models.py#L239)
- [scores.py:183-200](file://backend/app/routers/scores.py#L183-L200)
- [config_service.py:55-81](file://backend/app/services/config_service.py#L55-L81)

### 业务逻辑在模型层的边界
- 模型层主要负责数据结构与关系映射，不建议承载复杂业务规则。
- 复杂业务逻辑（评分计算、强制分布、状态机流转、通知发送、审计日志）放在服务层与路由层。
- 模型层可通过 cascade、事件钩子（如 @event.listens_for）实现简单的级联与触发，但应保持轻量。

**更新** 数据库迁移系统现在使用 SQLAlchemy 元数据检查，自动检测并补齐缺失的列，支持幂等操作。

章节来源
- [scores.py:165-331](file://backend/app/routers/scores.py#L165-L331)
- [models.py:138](file://backend/app/models.py#L138)
- [main.py:120-164](file://backend/app/main.py#L120-L164)

### 数据库迁移系统增强

**新增** 改进了数据库迁移系统，使用 SQLAlchemy 元数据检查实现自动列补齐：

- 自动检测缺失列：通过 inspector.get_columns() 检查现有表结构
- 智能类型转换：根据 Column 类型自动生成合适的 DDL 语句
- 默认值处理：支持标量默认值的内联添加
- 幂等性保证：重复执行不会产生错误
- NOT NULL 保护：跳过无法自动处理的 NOT NULL 列

章节来源
- [main.py:120-164](file://backend/app/main.py#L120-L164)
- [test_migration_autofill.py:17-42](file://backend/tests/test_migration_autofill.py#L17-L42)

## 使用示例：实例化、查询、更新

以下示例基于现有路由代码，给出常见操作的参考路径。为避免直接粘贴代码，仅提供精确的文件与行号定位。

### 实例化模型
- 创建员工：参考创建员工的 POST 接口，构造 Employee 实例并添加到会话后提交。
  - 参考路径：[employees.py:484-557](file://backend/app/routers/employees.py#L484-L557)
- 创建考核记录：通常在周期启动或分配阶段创建 AssessmentRecord，并写入 employee_id、cycle_id 等关键字段。
  - 参考路径：[scores.py:348-419](file://backend/app/routers/scores.py#L348-L419)

**更新** 创建员工时现在支持 level 字段，用于设置P/M职级信息。

### 查询模型
- 查询员工列表：支持分页、关键词、部门筛选、排序，并进行数据隔离。
  - 参考路径：[employees.py:233-312](file://backend/app/routers/employees.py#L233-L312)
- 查询我的考核记录：根据当前用户角色过滤可见数据，组装响应。
  - 参考路径：[scores.py:636-737](file://backend/app/routers/scores.py#L636-L737)
- 查询待评列表：根据经理下属范围与状态筛选 AssessmentRecord。
  - 参考路径：[scores.py:348-419](file://backend/app/routers/scores.py#L348-L419)

### 更新模型
- 更新员工信息：校验工号唯一性与外键有效性，处理 manager_employee_no 到 manager_id 的解析。
  - 参考路径：[employees.py:560-636](file://backend/app/routers/employees.py#L560-L636)
- 提交上级评分：校验分数范围、评语长度，更新 manager_scores 与状态机状态，必要时创建协作任务。
  - 参考路径：[scores.py:434-554](file://backend/app/routers/scores.py#L434-L554)
- 提交协作评分：校验权限与分数，更新 peer_scores 与 PeerReviewTask。
  - 参考路径：[scores.py:561-626](file://backend/app/routers/scores.py#L561-L626)

### 关联查询优化示例
- 在需要一次性获取员工及其部门、岗位、上级信息的接口中，建议使用 joinedload。
  - 导入位置：[employees.py:1-3](file://backend/app/routers/employees.py#L1-L3)
- 在批量获取考核记录的草稿或 KPI 明细时，建议使用 selectinload。
  - 参考路径：[scores.py:680-690](file://backend/app/routers/scores.py#L680-L690)

### 权重验证示例

**新增** 权重验证逻辑的使用示例：

- 维度权重验证：确保 dimension_weights 总和为 1.0 或 100%
  - 参考路径：[scores.py:183-189](file://backend/app/routers/scores.py#L183-L189)
- 评分人权重验证：确保每个维度的 reviewer_weights 总和为 1.0 或 100%
  - 参考路径：[scores.py:191-200](file://backend/app/routers/scores.py#L191-L200)
- 配置服务中的权重获取：从 SystemConfig 中获取并缓存权重配置
  - 参考路径：[config_service.py:55-81](file://backend/app/services/config_service.py#L55-L81)

章节来源
- [employees.py:233-312](file://backend/app/routers/employees.py#L233-L312)
- [employees.py:484-557](file://backend/app/routers/employees.py#L484-L557)
- [employees.py:560-636](file://backend/app/routers/employees.py#L560-L636)
- [scores.py:348-419](file://backend/app/routers/scores.py#L348-L419)
- [scores.py:434-554](file://backend/app/routers/scores.py#L434-L554)
- [scores.py:561-626](file://backend/app/routers/scores.py#L561-L626)
- [scores.py:636-737](file://backend/app/routers/scores.py#L636-L737)
- [scores.py:183-200](file://backend/app/routers/scores.py#L183-L200)
- [config_service.py:55-81](file://backend/app/services/config_service.py#L55-L81)

## 故障排查指南

### 常见问题与定位
- N+1 查询导致性能退化：检查是否在循环中访问 relationship 而未使用 eager loading。
  - 排查建议：在列表接口中为常用关联字段添加 joinedload/selectinload。
  - 参考路径：[employees.py:1-3](file://backend/app/routers/employees.py#L1-L3)
- 自引用关系死循环：Employee.manager/subordinates 递归过深可能导致栈溢出或超时。
  - 排查建议：限制递归深度，或在路由中使用迭代方式收集下属 ID。
  - 参考路径：[employees.py:457-470](file://backend/app/routers/employees.py#L457-L470)
- JSON 字段校验失败：维度权重或评分人权重之和不为 1.0/100%。
  - 排查建议：在服务层增加严格校验并返回明确错误信息。
  - 参考路径：[scores.py:183-200](file://backend/app/routers/scores.py#L183-L200)
- 级联删除未生效：ScoreDraft 应随 AssessmentRecord 删除而清理。
  - 排查建议：确认 cascade="all, delete-orphan" 配置正确。
  - 参考路径：[models.py:138](file://backend/app/models.py#L138)

**新增** 数据库迁移相关问题：
- 迁移脚本重复执行报错：确认 _migrate_db() 函数的幂等性实现
  - 参考路径：[main.py:120-164](file://backend/app/main.py#L120-L164)
- 新列添加失败：检查 NOT NULL 列是否有默认值
  - 参考路径：[main.py:149-151](file://backend/app/main.py#L149-L151)
- 位置/员工级别字段缺失：确认迁移脚本是否正确添加了 level 列
  - 参考路径：[test_migration_autofill.py:17-42](file://backend/tests/test_migration_autofill.py#L17-L42)

章节来源
- [employees.py:457-470](file://backend/app/routers/employees.py#L457-L470)
- [scores.py:183-200](file://backend/app/routers/scores.py#L183-L200)
- [models.py:138](file://backend/app/models.py#L138)
- [main.py:120-164](file://backend/app/main.py#L120-L164)
- [test_migration_autofill.py:17-42](file://backend/tests/test_migration_autofill.py#L17-L42)

## 结论
本项目的 ORM 模型设计以 Base 为统一基类，围绕组织人事与绩效考核构建清晰的实体关系。relationship 的配置遵循 back_populates、foreign_keys、remote_side、uselist、cascade 等最佳实践，确保数据一致性与可维护性。在查询层面，应结合懒加载、joinedload、selectinload 的策略，平衡性能与可读性。模型层保持轻量，复杂业务逻辑下沉至服务层与路由层，便于测试与演进。

**更新总结** 本次更新显著增强了系统的健壮性和可维护性：
- 引入了 sophisticated weight validation logic，确保评分数据的准确性
- 添加了 position/employee level field with P/M rank validation，支持更精细的组织结构管理
- 改进了 database migration system using SQLAlchemy metadata inspection，实现自动化的数据库版本管理
- 保持了向后兼容性，确保现有功能不受影响

这些改进使得系统在保持简洁性的同时，具备了更强的业务适应性和运维便利性。