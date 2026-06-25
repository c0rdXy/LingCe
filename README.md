<h1 align="center">灵测 LingCe</h1>

<p align="center">灵测通用考试练习平台</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
  <a href="pyproject.toml"><img alt="Python 3.7+" src="https://img.shields.io/badge/Python-3.7%2B-brightgreen.svg"></a>
  <a href="tests/"><img alt="Tests" src="https://img.shields.io/badge/Tests-138%20passed-success.svg"></a>
</p>

灵测是一个本地优先的考试练习工具，使用 Python 和 Tkinter 构建。题库、练习记录、错题、收藏和考试历史默认都保存在本机；AI 相关能力是可选功能，只有在用户配置接口后才会发起网络请求。

项目目标很简单：让个人或小团队可以维护自己的题库，完成练习、考试、回顾、统计和题库整理，不需要额外部署服务端。

## 特性

- 练习模式：支持全部题目、收藏、错题复习、继续上次练习和按题型筛选。
- 考试模式：支持考试时长、题型数量、分值分布、自动评分和答题回顾。
- 题库生成：支持逐题录入、复制、删除、排序、模板、草稿保存和清空草稿。
- 资料导入：支持 TXT、Markdown、CSV、Word、Excel、PDF 的文本提取，可交给 AI 生成题库草稿。
- AI 复核：可在练习、考试回顾和题库生成中复核题目、答案与解析，也可以继续追问。
- 系统设置：支持系统名称、主题、考试规则、题型配置、AI 服务商和模型配置。
- 本地数据：自动保存收藏、错题、练习进度、考试历史和学习统计。

## 支持题型

| 类型 | 标识 | 说明 |
| --- | --- | --- |
| 单选题 | `single` | 选择一个正确答案 |
| 多选题 | `multiple` | 选择多个正确答案 |
| 判断题 | `judgement` | 判断正确或错误 |
| 填空题 | `fill` | 填写答案 |
| 简答题 | `short` | 开放式作答 |

## 快速开始

```bash
git clone https://github.com/c0rdXy/LingCe.git
cd LingCe
python app.py
```

要求 Python 3.7 或更高版本。Tkinter 通常随 Python 一起安装；如果你的发行版拆分了 Tkinter 包，需要单独安装对应组件。

练习、考试、题库编辑等核心功能只使用 Python 标准库。以下依赖是可选的：

```bash
pip install matplotlib pypdf
```

`matplotlib` 用于统计图表增强，`pypdf` 用于 PDF 文本提取增强。

## AI 接入

AI 默认关闭。需要在“系统设置”里选择接入方式、服务商、Base URL、模型和 API Key 后使用。

当前设置页支持按接入方式和服务商保存多个 Key。Key 会加密写入本地配置文件，界面中切换已保存配置时会还原明文显示，便于用户确认和修改。

支持普通 API、Coding Plan、Token Plan 和自定义地址。只要服务端兼容 OpenAI 风格的聊天接口，通常都可以通过自定义配置接入。

## 题库格式

题库文件是 JSON 数组。一个最小示例如下：

```json
[
  {
    "id": 1,
    "type": "single",
    "question": "题目内容？",
    "options": ["选项一", "选项二", "选项三", "选项四"],
    "answer": "A",
    "explanation": "解析说明",
    "is_collected": false
  }
]
```

字段说明：

- `type` 使用 `single`、`multiple`、`judgement`、`fill`、`short` 之一。
- `judge` 和 `essay` 是兼容旧数据的别名，建议新题库统一使用 `judgement` 和 `short`。
- 选择题答案使用 `A`、`B`、`C`、`D` 这类字母；多选题可使用 `ABCD` 或等价格式。
- 判断题推荐使用 `正确` 或 `错误`。
- `options` 对填空题和简答题可以为空。
- `is_collected` 表示是否收藏，省略时默认为 `false`。

题库读写会保留 `id`、`question`、`options`、`answer`、`explanation`、`is_collected` 这些字段。手工录入时通常只需要关心题型、题干、选项和答案。

项目自带的 `question_banks/题库.json` 是示例题库。用户新建和导出的题库默认也放在 `question_banks/` 下，除内置示例外不会提交到 Git。

## 本地数据

运行时会在 `data/` 下生成本地数据：

| 文件 | 用途 |
| --- | --- |
| `data/settings.json` | 系统设置、主题、考试规则、AI 配置 |
| `data/user_data.json` | 最近题库、练习进度、错题、收藏、统计 |
| `data/exam_history.db` | 考试历史记录 |
| `data/user_data.example.json` | 用户数据结构示例 |

除示例文件外，运行数据不会提交到仓库。

核心功能可离线使用。会主动访问网络的地方只有 AI 调用和首页 GitHub 链接。

## 项目结构

```text
LingCe/
├── app.py                         # 程序入口
├── core/                          # 配置、模型、题型和通用工具
├── services/                      # 题库、考试、设置、AI、导入等业务逻辑
├── ui/                            # Tkinter 界面
├── assets/                        # Logo 和图标资源
├── question_banks/                # 内置示例题库和本地生成题库
├── data/                          # 本地运行数据示例和运行时数据
├── scripts/release_check.py       # 发布前检查脚本
├── tests/                         # 单元测试
├── secure_build.py                # Windows 打包脚本
├── pyproject.toml                 # 项目元数据和开发依赖
└── requirements.txt               # 可选依赖说明
```

## 开发

安装开发依赖：

```bash
pip install -e ".[dev]"
```

运行测试：

```bash
pytest
```

发布前检查：

```bash
python scripts/release_check.py
```

检查脚本会验证版本号一致性、运行数据是否误提交、文件大小、疑似乱码、编译结果和测试结果。

## 打包

Windows 下可以使用项目内的打包脚本：

```bash
pip install pyinstaller
python secure_build.py
```

打包产物会输出到 `dist/` 或 `dist_secure/`，这些目录不会提交到仓库。

## 贡献

欢迎提交 Issue 或 Pull Request。提交前请至少运行：

```bash
pytest
python scripts/release_check.py
```

如果改动涉及界面流程，也建议手动运行 `python app.py` 走一遍练习、考试和设置页。

## 许可证

本项目使用 [MIT License](LICENSE)。
