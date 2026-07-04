from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime

# ------------------ Common ------------------
class StandardResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None

# ------------------ Auth ------------------
class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: Optional[bool] = False

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ------------------ Department ------------------
class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None
    parent_id: Optional[int] = None
    head_id: Optional[int] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[int] = None
    head_id: Optional[int] = None

class DepartmentOut(BaseModel):
    id: int
    name: str
    code: Optional[str]
    parent_id: Optional[int]
    head_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ------------------ Position ------------------
class PositionCreate(BaseModel):
    name: str
    department_id: Optional[int] = None

class PositionUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[int] = None

class PositionOut(BaseModel):
    id: int
    name: str
    department_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ------------------ Employee ------------------
class EmployeeCreate(BaseModel):
    employee_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    manager_id: Optional[int] = None
    manager_employee_no: Optional[str] = None
    is_department_head: Optional[bool] = False
    is_active: Optional[bool] = True

class EmployeeUpdate(BaseModel):
    employee_no: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    manager_id: Optional[int] = None
    manager_employee_no: Optional[str] = None
    is_department_head: Optional[bool] = None
    is_active: Optional[bool] = None

class EmployeeOut(BaseModel):
    id: int
    employee_no: str
    name: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    position_id: Optional[int]
    position_name: Optional[str] = None
    manager_id: Optional[int]
    manager_name: Optional[str] = None
    manager_employee_no: Optional[str] = None
    is_department_head: bool
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class EmployeeListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[EmployeeOut]

# ------------------ KPI Template ------------------
class KpiItemCreate(BaseModel):
    name: str
    weight: Decimal
    target_value: Optional[str] = None
    scoring_method: Optional[str] = "percentage"
    description: Optional[str] = None

class KpiTemplateCreate(BaseModel):
    position_id: int
    items: List[KpiItemCreate]

    @field_validator('items')
    @classmethod
    def check_weight_sum(cls, v):
        total = sum(item.weight for item in v)
        if total != 100:
            raise ValueError(f"KPI模板权重总和必须等于100%，当前为{total}%")
        return v

class KpiTemplateSingleCreate(BaseModel):
    position_id: int
    name: str
    weight: Decimal
    target_value: Optional[str] = None
    scoring_method: Optional[str] = "percentage"
    description: Optional[str] = None

class KpiTemplateSingleUpdate(BaseModel):
    position_id: Optional[int] = None
    name: Optional[str] = None
    weight: Optional[Decimal] = None
    target_value: Optional[str] = None
    scoring_method: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class KpiTemplateUpdate(BaseModel):
    items: List[KpiItemCreate]

    @field_validator('items')
    @classmethod
    def check_weight_sum(cls, v):
        total = sum(item.weight for item in v)
        if total != 100:
            raise ValueError(f"KPI模板权重总和必须等于100%，当前为{total}%")
        return v

class KpiTemplateOut(BaseModel):
    id: int
    position_id: int
    position_name: Optional[str] = None
    name: str
    weight: Decimal
    target_value: Optional[str]
    scoring_method: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class KpiTemplateGroupOut(BaseModel):
    position_id: int
    items: List[KpiTemplateOut]

# ------------------ Assessment Cycle ------------------
class AssessmentCycleCreate(BaseModel):
    name: str
    type: str
    start_date: date
    end_date: date
    self_due_date: Optional[date] = None
    manager_due_date: Optional[date] = None
    peer_due_date: Optional[date] = None
    weights: Dict[str, int]
    grade_rules: Dict[str, Any]
    small_dept_exemption: Optional[bool] = True
    peer_review_enabled: Optional[bool] = True

    @field_validator('weights')
    @classmethod
    def check_weights_sum(cls, v):
        total = sum(v.values())
        if total != 100:
            raise ValueError(f"维度权重总和必须等于100，当前为{total}%")
        return v

    @field_validator('end_date')
    @classmethod
    def check_dates(cls, v, info):
        start = info.data.get('start_date')
        if start and v and v < start:
            raise ValueError("结束日期不能早于开始日期")
        return v

    @field_validator('grade_rules')
    @classmethod
    def check_grade_rules(cls, v):
        # Accept both simple {"A": 90} and detailed {"A": {"min": 90, "max": 100}}
        if not v:
            raise ValueError("等级规则不能为空")
        return v

class AssessmentCycleUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    self_due_date: Optional[date] = None
    manager_due_date: Optional[date] = None
    peer_due_date: Optional[date] = None
    weights: Optional[Dict[str, int]] = None
    grade_rules: Optional[Dict[str, Any]] = None
    small_dept_exemption: Optional[bool] = None
    peer_review_enabled: Optional[bool] = None

class AssessmentCycleOut(BaseModel):
    id: int
    name: str
    type: str
    start_date: date
    end_date: date
    self_due_date: Optional[date]
    manager_due_date: Optional[date]
    peer_due_date: Optional[date]
    status: str
    weights: Optional[Dict[str, Any]]
    grade_rules: Optional[Dict[str, Any]]
    is_distribution_enabled: bool
    small_dept_exemption: bool
    peer_review_enabled: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class LaunchCycleRequest(BaseModel):
    cycle_id: int
    employee_ids: List[int]

class AddEmployeesToCycleRequest(BaseModel):
    cycle_id: int
    employee_ids: List[int]


class CycleEmployeeOut(BaseModel):
    id: int
    cycle_id: int
    employee_id: int
    employee_no: str
    name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    status: str
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ------------------ Operation Log ------------------
class OperationLogOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OperationLogListResponse(BaseModel):
    total: int
    items: List[OperationLogOut]


# ------------------ Assessment Record ------------------
class AssessmentRecordOut(BaseModel):
    id: int
    cycle_id: int
    employee_id: int
    position_id: Optional[int]
    department_id: Optional[int]
    status: str
    total_score: Optional[Decimal]
    grade: Optional[str]
    created_at: Optional[datetime]

    @model_validator(mode='after')
    def mask_unpublished_scores(self):
        """未发布状态的考核记录不返回 total_score 和 grade。"""
        if self.status not in ("published", "archived"):
            self.total_score = None
            self.grade = None
        return self

    class Config:
        from_attributes = True

# ------------------ KPI Adjustment ------------------
class KpiAdjustmentCreate(BaseModel):
    kpi_id: int
    new_target: str
    reason: str

class KpiAdjustmentOut(BaseModel):
    id: int
    record_id: int
    original_kpi: str
    adjusted_kpi: str
    reason: str
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ------------------ System Config ------------------
class GradeRuleEntry(BaseModel):
    min: float = Field(..., ge=0, le=100, description="等级最低分")
    max: float = Field(..., ge=0, le=100, description="等级最高分")
    ratio_limit: float = Field(..., ge=0, le=1, description="等级人数上限比例，0-1之间")

    @model_validator(mode='after')
    def check_min_less_than_max(self):
        if self.min >= self.max:
            raise ValueError(f"min({self.min})必须小于max({self.max})")
        return self


class GradeRulesSchema(BaseModel):
    A: GradeRuleEntry
    B: GradeRuleEntry
    C: GradeRuleEntry
    D: GradeRuleEntry

    @model_validator(mode='after')
    def check_intervals(self):
        entries = [("A", self.A), ("B", self.B), ("C", self.C), ("D", self.D)]
        sorted_entries = sorted(entries, key=lambda x: x[1].min)

        # Check full coverage
        lowest_min = min(entry.min for _, entry in entries)
        highest_max = max(entry.max for _, entry in entries)
        if lowest_min > 0:
            raise ValueError("最低等级min必须等于0")
        if highest_max < 100:
            raise ValueError("最高等级max必须等于100")

        # Check no overlap and continuity
        for i in range(len(sorted_entries) - 1):
            curr_name, curr = sorted_entries[i]
            next_name, next_ = sorted_entries[i + 1]
            if curr.max > next_.min:
                raise ValueError(f"区间重叠: {curr_name} 与 {next_name}")
            # Allow small gap up to 1.0 for integer/decimal boundaries
            if next_.min > curr.max + 1:
                raise ValueError(f"区间不连续: {curr_name}({curr.max}) 与 {next_name}({next_.min})")

        return self

    @model_validator(mode='after')
    def check_ratio_limit(self):
        total = sum(entry.ratio_limit for _, entry in [("A", self.A), ("B", self.B), ("C", self.C), ("D", self.D)])
        if total > 1.0:
            raise ValueError(f"ratio_limit合计不能超过100%，当前为{total * 100:.0f}%")
        return self


class GradeRulesConfig(GradeRulesSchema):
    pass

class DimensionWeightsConfig(BaseModel):
    performance: Optional[int] = None
    ability: Optional[int] = None
    attitude: Optional[int] = None
    业绩: Optional[int] = None
    能力: Optional[int] = None
    态度: Optional[int] = None

    @field_validator('*')
    @classmethod
    def check_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("权重不能为负数")
        return v

class ReviewerWeightEntry(BaseModel):
    self: int = Field(..., ge=0, le=100, description="自评权重")
    manager: int = Field(..., ge=0, le=100, description="上级权重")
    peer: int = Field(..., ge=0, le=100, description="协作权重")

    @model_validator(mode='after')
    def check_sum(self):
        total = self.self + self.manager + self.peer
        if total != 100:
            raise ValueError(f"评分人权重总和必须等于100%，当前为{total}%")
        return self

class ReviewerWeightsConfig(BaseModel):
    performance: Optional[ReviewerWeightEntry] = None
    ability: Optional[ReviewerWeightEntry] = None
    attitude: Optional[ReviewerWeightEntry] = None

    @model_validator(mode='after')
    def check_all_dimensions_present(self):
        for dim in ['performance', 'ability', 'attitude']:
            if getattr(self, dim) is None:
                raise ValueError(f"缺少维度: {dim}")
        return self

class SmallDeptExemptionConfig(BaseModel):
    enabled: bool
    threshold: int = 5

# ------------------ Dashboard ------------------
class DashboardOut(BaseModel):
    stats: Dict[str, Any]
    recent_cycles: List[Dict[str, Any]]
    pending_tasks: List[Dict[str, Any]]

