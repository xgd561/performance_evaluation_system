from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, Date, DateTime, ForeignKey, DECIMAL, UniqueConstraint, JSON
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from datetime import datetime
import json

Base = declarative_base()

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    head_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", foreign_keys="Employee.department_id", back_populates="department")
    positions = relationship("Position", back_populates="department")

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="positions")
    employees = relationship("Employee", foreign_keys="Employee.position_id", back_populates="position")
    kpi_templates = relationship("KpiTemplate", back_populates="position")

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_no = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_department_head = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", foreign_keys=[department_id], back_populates="employees")
    position = relationship("Position", foreign_keys=[position_id], back_populates="employees")
    manager = relationship("Employee", remote_side=[id], foreign_keys=[manager_id])
    subordinates = relationship("Employee", foreign_keys=[manager_id], back_populates="manager")
    user = relationship("User", uselist=False, back_populates="employee")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_first_login = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="user")

class AssessmentCycle(Base):
    __tablename__ = "assessment_cycles"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    self_due_date = Column(Date, nullable=True)
    manager_due_date = Column(Date, nullable=True)
    peer_due_date = Column(Date, nullable=True)
    status = Column(String(50), default="not_started")
    # 权重列默认值与 config_service.get_dimension_weights / get_reviewer_weights 保持同值（60/20/20；
    # 业绩 30/70/0、能力 20/60/20、态度 10/50/40），仅为直接创建模型（脚本/测试）时的兜底；
    # 运行时权威口径以 config_service 为准（含 POST /assessment-cycles 创建周期）。
    dimension_weights = Column(JSON, nullable=False, default={"performance": 0.6, "ability": 0.2, "attitude": 0.2})
    reviewer_weights = Column(JSON, nullable=False, default={"performance": {"self": 0.3, "manager": 0.7, "peer": 0.0}, "ability": {"self": 0.2, "manager": 0.6, "peer": 0.2}, "attitude": {"self": 0.1, "manager": 0.5, "peer": 0.4}})
    grade_rules = Column(JSON, nullable=False, default={"A": {"min": 90, "max": 100, "ratio_limit": 0.2}, "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5}, "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25}, "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}})
    is_distribution_enabled = Column(Boolean, default=True)
    small_dept_exemption = Column(Boolean, default=True)
    peer_review_enabled = Column(Boolean, default=True)
    approval_chain_config = Column(JSON, nullable=True)
    is_locked = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KpiTemplate(Base):
    __tablename__ = "kpi_templates"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    name = Column(String(200), nullable=False)
    weight = Column(DECIMAL(5,2), nullable=False)
    target_value = Column(String(255), nullable=True)
    scoring_method = Column(String(50), default="percentage")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    position = relationship("Position", back_populates="kpi_templates")

class AssessmentRecord(Base):
    __tablename__ = "assessment_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cycle_id = Column(Integer, ForeignKey("assessment_cycles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    kpi_snapshot = Column(JSON, nullable=True)
    self_scores = Column(JSON, nullable=True)
    manager_scores = Column(JSON, nullable=True)
    peer_scores = Column(JSON, nullable=True)
    weighted_performance = Column(DECIMAL(5,2), nullable=True)
    weighted_ability = Column(DECIMAL(5,2), nullable=True)
    weighted_attitude = Column(DECIMAL(5,2), nullable=True)
    total_score = Column(DECIMAL(5,2), nullable=True)
    grade = Column(String(10), nullable=True)
    original_grade = Column(String(10), nullable=True)
    is_distribution_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    manager_comment = Column(Text, nullable=True)
    manager_draft_scores = Column(JSON, nullable=True)
    self_draft_scores = Column(JSON, nullable=True)
    peer_draft_scores = Column(JSON, nullable=True)
    manager_submitted = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    interview_record = Column(JSON, nullable=True)
    appeal_record = Column(JSON, nullable=True)
    archive_pdf_path = Column(String(255), nullable=True)
    status = Column(String(50), default="pending_self")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    drafts = relationship("ScoreDraft", back_populates="record", cascade="all, delete-orphan")

class ScoreDetail(Base):
    __tablename__ = "score_details"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    kpi_template_id = Column(Integer, ForeignKey("kpi_templates.id"), nullable=True)
    kpi_name = Column(String(200), nullable=True)
    weight = Column(DECIMAL(5,2), nullable=True)
    self_score = Column(DECIMAL(5,2), nullable=True)
    manager_score = Column(DECIMAL(5,2), nullable=True)
    target_value = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class KpiAdjustment(Base):
    __tablename__ = "kpi_adjustments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    original_kpi = Column(Text, nullable=False)
    adjusted_kpi = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    approver_role = Column(String(50), nullable=True)
    step_index = Column(Integer, default=1)
    approval_type = Column(String(50), default="normal")
    action = Column(String(50), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CycleEmployee(Base):
    __tablename__ = "cycle_employees"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cycle_id = Column(Integer, ForeignKey("assessment_cycles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String(50), default="pending")
    added_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('cycle_id', 'employee_id', name='_cycle_employee_uc'),)

class PeerReviewer(Base):
    __tablename__ = "peer_reviewers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cycle_id = Column(Integer, ForeignKey("assessment_cycles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reviewer_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    status = Column(String(50), default="pending")
    __table_args__ = (UniqueConstraint('cycle_id', 'employee_id', 'reviewer_id', name='_peer_reviewer_uc'),)

class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AppealRecord(Base):
    __tablename__ = "appeal_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reason = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    reviewer_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    review_result = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class InterviewRecord(Base):
    __tablename__ = "interview_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    interviewer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    interview_time = Column(DateTime, nullable=True)
    location = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    improvement_plan = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemConfig(Base):
    __tablename__ = "system_configs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScoreDraft(Base):
    __tablename__ = "score_drafts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    draft_type = Column(String(50), nullable=False)
    draft_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("record_id", "draft_type", name="uq_record_draft_type"),)

    record = relationship("AssessmentRecord", back_populates="drafts")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PeerReviewTask(Base):
    __tablename__ = "peer_review_tasks"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("assessment_records.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    ability_score = Column(DECIMAL(5, 2), nullable=True)
    comment = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

