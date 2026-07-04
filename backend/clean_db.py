import os
import sqlite3
import sys

def clean_database():
    db_path = os.path.join('..', 'data', 'db', 'performance_evaluation.db')

    # 保留的基本用户和员工ID
    keep_employee_ids = {1, 2, 3, 5, 7, 23}  # admin, hr001, mgr001, peer001, exec001, emp001
    keep_user_ids = {1, 2, 3, 4, 5, 8}  # admin, hr001, mgr001, emp001, peer001, exec001

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 关闭外键约束检查（SQLite 默认不开启，但为安全起见）
        cursor.execute("PRAGMA foreign_keys = OFF")

        # 1. 清空所有业务表
        business_tables = [
            'assessment_records',
            'cycle_employees',
            'peer_reviewers',
            'score_details',
            'kpi_adjustments',
            'approval_records',
            'operation_logs',
            'appeal_records',
            'interview_records',
            'kpi_templates',
            'assessment_cycles',
            'system_configs',
        ]

        for table in business_tables:
            cursor.execute(f"DELETE FROM {table}")
            print(f"OK 清空表: {table}")

        # 2. 删除不需要的 employees
        cursor.execute("SELECT id FROM employees WHERE id NOT IN (" + ",".join(map(str, keep_employee_ids)) + ")")
        to_delete_employees = [row[0] for row in cursor.fetchall()]
        if to_delete_employees:
            cursor.execute("DELETE FROM employees WHERE id NOT IN (" + ",".join(map(str, keep_employee_ids)) + ")")
            print(f"OK 删除 employees: {len(to_delete_employees)} 条")

        # 3. 删除不需要的 users
        cursor.execute("SELECT id FROM users WHERE id NOT IN (" + ",".join(map(str, keep_user_ids)) + ")")
        to_delete_users = [row[0] for row in cursor.fetchall()]
        if to_delete_users:
            cursor.execute("DELETE FROM users WHERE id NOT IN (" + ",".join(map(str, keep_user_ids)) + ")")
            print(f"OK 删除 users: {len(to_delete_users)} 条")

        # 4. 获取保留的 employees 关联的 department_id 和 position_id
        cursor.execute("SELECT DISTINCT department_id FROM employees WHERE id IN (" + ",".join(map(str, keep_employee_ids)) + ")")
        keep_dept_ids = {row[0] for row in cursor.fetchall() if row[0] is not None}

        cursor.execute("SELECT DISTINCT position_id FROM employees WHERE id IN (" + ",".join(map(str, keep_employee_ids)) + ")")
        keep_pos_ids = {row[0] for row in cursor.fetchall() if row[0] is not None}

        # 5. 删除不需要的 positions
        if keep_pos_ids:
            cursor.execute("SELECT id FROM positions WHERE id NOT IN (" + ",".join(map(str, keep_pos_ids)) + ")")
            to_delete_pos = [row[0] for row in cursor.fetchall()]
            if to_delete_pos:
                cursor.execute("DELETE FROM positions WHERE id NOT IN (" + ",".join(map(str, keep_pos_ids)) + ")")
                print(f"OK 删除 positions: {len(to_delete_pos)} 条")

        # 6. 删除不需要的 departments（注意：parent_id 可能引用自身，需要小心处理）
        if keep_dept_ids:
            # 保留的 departments 及其所有父部门
            all_keep_dept_ids = set(keep_dept_ids)
            for dept_id in list(keep_dept_ids):
                cursor.execute("SELECT parent_id FROM departments WHERE id = ?", (dept_id,))
                parent = cursor.fetchone()
                while parent and parent[0] is not None:
                    all_keep_dept_ids.add(parent[0])
                    cursor.execute("SELECT parent_id FROM departments WHERE id = ?", (parent[0],))
                    parent = cursor.fetchone()

            cursor.execute("SELECT id FROM departments WHERE id NOT IN (" + ",".join(map(str, all_keep_dept_ids)) + ")")
            to_delete_dept = [row[0] for row in cursor.fetchall()]
            if to_delete_dept:
                cursor.execute("DELETE FROM departments WHERE id NOT IN (" + ",".join(map(str, all_keep_dept_ids)) + ")")
                print(f"OK 删除 departments: {len(to_delete_dept)} 条")

        # 7. 更新保留的 departments 的 head_id（如果引用了已删除的 employee）
        cursor.execute("UPDATE departments SET head_id = NULL WHERE head_id NOT IN (" + ",".join(map(str, keep_employee_ids)) + ")")

        # 8. 更新保留的 employees 的 manager_id（如果引用了已删除的 employee）
        cursor.execute("UPDATE employees SET manager_id = NULL WHERE manager_id NOT IN (" + ",".join(map(str, keep_employee_ids)) + ")")

        conn.commit()
        print("\nOK 数据库清理完成")

        # 验证
        cursor.execute("SELECT id, username, role FROM users")
        print("\n保留的用户:")
        for row in cursor.fetchall():
            print(f"  {row}")

        cursor.execute("SELECT id, employee_no, name FROM employees")
        print("\n保留的员工:")
        for row in cursor.fetchall():
            print(f"  {row}")

        cursor.execute("SELECT id, name FROM departments")
        print("\n保留的部门:")
        for row in cursor.fetchall():
            print(f"  {row}")

        cursor.execute("SELECT id, name FROM positions")
        print("\n保留的岗位:")
        for row in cursor.fetchall():
            print(f"  {row}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    clean_database()
