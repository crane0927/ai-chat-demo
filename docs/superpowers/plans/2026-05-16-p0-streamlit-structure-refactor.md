# P0 Streamlit 结构重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变现有聊天功能的前提下，拆分 `app.py` 中的工具函数、状态同步逻辑、侧边栏和设置弹窗，让入口文件只保留页面编排职责。

**Architecture:** 先把纯函数提取到 `utils/` 和 `state/`，用单元测试锁定导出、标签和状态同步行为；再把侧边栏与设置弹窗迁移到 `pages/` 模块，最后让 `app.py` 负责初始化数据、调用页面模块和聊天主流程。

**Tech Stack:** Python、Streamlit、unittest、PostgreSQL 服务模块

---

### Task 1: 抽离纯函数与状态同步逻辑

**Files:**
- Create: `utils/exporters.py`
- Create: `utils/view_helpers.py`
- Create: `state/session_state.py`
- Create: `tests/test_exporters.py`
- Create: `tests/test_view_helpers.py`
- Create: `tests/test_session_state.py`
- Modify: `app.py`

- [ ] 写失败测试，覆盖导出内容、文件名、展示标签和状态同步
- [ ] 运行 `python -m unittest tests.test_exporters tests.test_view_helpers tests.test_session_state -v`，确认先红灯
- [ ] 实现最小工具模块和状态模块
- [ ] 再次运行同一命令，确认转绿

### Task 2: 抽离侧边栏和设置弹窗

**Files:**
- Create: `pages/sidebar.py`
- Create: `pages/settings_dialog.py`
- Create: `ui/styles.py`
- Modify: `app.py`

- [ ] 迁移样式注入、侧边栏渲染和设置弹窗逻辑
- [ ] 保持现有数据库调用与页面行为不变
- [ ] 运行 `python -m py_compile app.py pages/sidebar.py pages/settings_dialog.py state/session_state.py utils/exporters.py utils/view_helpers.py ui/styles.py`

### Task 3: 最终验证

**Files:**
- Modify: `app.py`

- [ ] 运行 `python -m unittest tests.test_exporters tests.test_view_helpers tests.test_session_state -v`
- [ ] 运行 `python -m py_compile app.py pages/sidebar.py pages/settings_dialog.py state/session_state.py utils/exporters.py utils/view_helpers.py ui/styles.py`
- [ ] 记录未覆盖的风险点，例如 Streamlit 交互需要人工页面回归
