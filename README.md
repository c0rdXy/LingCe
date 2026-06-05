# 灵测 LingCe

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-brightgreen.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-92%20passed-success.svg)](tests/)

**灵测 LingCe** 是一个轻量、通用的开源考试练习系统，基于 Python + Tkinter 构建，零外部依赖即可运行。

支持自定义 JSON 题库、练习与考试双模式、错题集管理、学习统计，适用于各类考试备考场景。

**English** | [简体中文](#)

---

## ✨ 功能特性

- 📚 **题库管理** — 导入 JSON 题库，支持创建示例题库
- 🎯 **练习模式** — 逐题练习，即时反馈，按题型筛选，支持在线编辑
- 📝 **考试模式** — 模拟考试，限时作答，自动评分，答题回顾
- ❌ **错题集** — 自动记录错题，支持导出复习
- 📊 **学习统计** — 答题数据统计与可视化（matplotlib 可选）
- 🌙 **主题切换** — 浅色 / 深色模式
- ⌨️ **快捷键** — 全键盘操作，高效刷题

## 📋 支持题型

| 类型 | 标识 | 说明 |
|------|------|------|
| 单选题 | `single` | 选择一个正确答案 |
| 多选题 | `multiple` | 选择多个正确答案 |
| 判断题 | `judgement` | 判断对错 |
| 填空题 | `fill` | 填写答案 |
| 简答题 | `short` | 开放式作答 |

## 🚀 快速开始

### 运行

`ash
git clone https://github.com/<your-username>/LingCe.git
cd LingCe
python app.py
`

> 需要 Python 3.7+，tkinter 通常随 Python 自带。

### 开发安装

`ash
pip install -e ".[dev]"
pytest
`

### 打包构建

`ash
pip install pyinstaller
python secure_build.py
`

## 📁 项目结构

`
LingCe/
├── app.py                  # 主程序入口
├── core/
│   ├── config.py           # 配置与主题管理
│   ├── models.py           # 数据模型
│   └── utils.py            # 工具函数
├── services/
│   ├── exam_service.py     # 考试业务逻辑
│   ├── file_service.py     # 文件导入导出
│   ├── question_service.py # 题目管理
│   └── user_data_service.py# 用户数据持久化
├── ui/
│   ├── main_window.py      # 主窗口
│   ├── practice_mode.py    # 练习模式
│   ├── exam_mode.py        # 考试模式
│   ├── components.py       # 通用 UI 组件
│   ├── widgets.py          # 增强组件
│   ├── edit_functions.py   # 编辑功能
│   └── stats_chart.py      # 统计图表
├── data/                   # 题库数据
├── scripts/                # 辅助脚本
├── tests/                  # 单元测试（92 个）
├── pyproject.toml          # 项目配置
└── requirements.txt        # 依赖声明
`

## ⌨️ 快捷键

| 模式 | 按键 | 功能 |
|------|------|------|
| 练习 | `←` / `→` | 上一题 / 下一题 |
| 练习 | `R` | 随机跳题 |
| 练习 | `Enter` | 提交答案 |
| 练习 | `Space` | 显示 / 隐藏答案 |
| 考试 | `Enter` | 提交答案 |
| 考试 | 数字键 | 快速跳转题目 |

## 📝 题库格式

题库为标准 JSON 数组格式，示例：

``json
[
  {
    "id": 1,
    "type": "single",
    "question": "题目内容？",
    "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
    "answer": "A",
    "explanation": "解析说明"
  }
]
``

支持 `single` / `multiple` / `judgement` / `fill` / `short` 五种题型。

## 🛠️ 技术栈

- **Python 3.7+** — 无外部运行时依赖
- **Tkinter** — 跨平台 GUI
- **matplotlib** — 可选，统计图表增强
- **pytest** — 开发依赖，单元测试

## 🤝 参与贡献

欢迎贡献！请遵循以下流程：

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feature/your-feature`）
3. 提交更改（`git commit -m 'Add your feature'`）
4. 推送到分支（`git push origin feature/your-feature`）
5. 创建 Pull Request

提交前请确保通过全部测试：

`ash
pytest
`

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。