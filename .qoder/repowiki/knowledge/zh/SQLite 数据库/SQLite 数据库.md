---
kind: external_dependency
name: SQLite 数据库
slug: sqlite
category: external_dependency
category_hints:
    - client_constraint
scope:
    - '**'
---

生产/开发统一使用 SQLite 文件 `data/db/performance_evaluation.db`，通过 SQLAlchemy 2.0 访问。由于是文件型数据库且配置缓存、登录失败计数等状态驻留进程内存，当前版本默认单 worker 部署；多 worker 需要迁移到共享数据库和集中式缓存/限流后才可行。备份脚本 `scripts/backup.bat` 仅手工复制 `.db` 文件，无在线恢复能力。