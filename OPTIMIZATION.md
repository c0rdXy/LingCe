# 灵测 LingCe V0.0.1 — 开源优化计划

> 记录项目向可持续开源方向演进的优化进度。
---

## 一、开源基础设施

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 1 | `pyproject.toml` | ✅ 已完成 | 现代打包配置，定义元数据、依赖、入口 |
| 2 | `LICENSE` | ✅ 已完成 | MIT 许可证 |
| 3 | `.gitignore` | ✅ 已完成 | 排除缓存、构建产物、IDE、OS 文件 |
| 4 | `requirements.txt` | ✅ 已完成 | 零外部依赖，matplotlib 可选 |
| 5 | 重写 `README.md` | ✅ 已完成 | 含中英简介、项目结构、贡献指南、更新日志 |

## 二、项目结构重组

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 6 | 源码提升到根目录 | ✅ 已完成 | 消除 `1-源码版本/` 嵌套 |
| 7 | 删除打包产物目录 | ✅ 已完成 | `2-安全打包版本/` 已移除 |
| 8 | 题库目录重命名 | ✅ 已完成 | `3-题库文件/` → `data/`，脚本移入 `scripts/` |
| 9 | 清理冗余文档 | ✅ 已完成 | 删除旧更新日志和统计报告，合并入 README |
| 10 | 版本重置为 0.0.1 | ✅ 已完成 | pyproject.toml + config.py |

## 三、代码拆分与架构

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 11 | 新增 `ui/widgets.py` | ✅ 已完成 | 增强版共享渲染组件 QuestionWidget |
| 12 | 重构 `exam_mode.py` | ✅ 已完成 | 1307行 → 558行 (减少57%) |
| 13 | 优化 `practice_mode.py` | ✅ 已完成 | 使用共享 get_question_type_name |

## 四、跨平台兼容

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 14 | 字体 fallback | ✅ 已完成 | get_font() 自动检测 (Win/Mac/Linux) |
| 15 | 硬编码字体清理 | ✅ 已完成 | 22处全部替换为 get_font() |
| 16 | 路径改用 pathlib | ✅ 已完成 | file_service + edit_functions |
| 17 | 编码统一 UTF-8 | ✅ 已完成 | 所有 open() 均带 encoding 参数 |

## 五、功能增强

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 18 | 主题/深色模式 | ✅ 已完成 | config.py THEMES + 菜单切换 + 持久化 |
| 19 | 练习进度持久化 | ✅ 已完成 | services/user_data_service.py (JSON) |
| 20 | 题目收藏/标签 | ✅ 已完成 | 练习模式收藏按钮 + UserDataService |
| 21 | 统计面板图表 | ✅ 已完成 | ui/stats_chart.py (matplotlib可选/Canvas fallback) |

## 六、测试体系

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 22 | `tests/test_models.py` | ✅ 已完成 | 32 个测试：Question/QuestionBank/ExamSession/PracticeSession |
| 23 | `tests/test_utils.py` | ✅ 已完成 | 27 个测试：加载保存/答案验证/时间格式化/题型映射/题目生成 |
| 24 | `tests/test_services.py` | ✅ 已完成 | 33 个测试：ExamService/UserDataService 完整覆盖 |

> **测试结果：92 passed, 0 failed (0.44s)**

---

## 变更日志

### v0.0.1 (2026-06-01) — 项目开源重构

**基础设施**
- 标准开源项目目录结构 + pyproject.toml + MIT 许可证
- 版本从 v5.0 重置为 v0.0.1

**代码架构**
- 新增 `ui/widgets.py`：共享题目渲染组件
- 重构 `exam_mode.py`：1307行 → 558行（减少57%）

**跨平台兼容**
- `get_font()` 自动检测系统可用中文字体 (Win/Mac/Linux)
- 22处硬编码字体全部替换、os.path → pathlib、编码统一 UTF-8

**功能增强**
- 主题/深色模式（config.py THEMES + 持久化）
- `services/user_data_service.py`（JSON 持久化：进度/错题/收藏/统计）
- 收藏功能（练习模式收藏按钮）
- 统计图表面板 `ui/stats_chart.py`（matplotlib 可选 / Canvas fallback）

**测试体系**
- 92 个单元测试全覆盖（models 32 + utils 27 + services 33）
- pytest 框架，`pip install -e ".[dev]"` 即可运行
