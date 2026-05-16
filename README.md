# AI Chat Demo

一个基于 Streamlit 构建的 AI 聊天演示项目，支持本地回显模式和 OpenAI 兼容接口调用。项目默认适配 DeepSeek 的 OpenAI 兼容接口，也可以通过环境变量或页面输入框切换到其他兼容服务。

## 功能特性

- 基于 Streamlit 的简洁聊天界面
- 支持多会话创建、切换、重命名、删除和导出
- 支持 PostgreSQL 持久化保存会话、系统提示词和聊天消息
- 支持自定义系统提示词
- 支持 Prompt 模板库，可保存、编辑、复制和应用模板，并支持 `{{变量名}}` 占位符渲染
- 支持保存多个模型配置，并在页面中自由切换当前提问使用的模型
- 支持模型服务商预设与连接测试，减少手动配置成本
- 支持按模型配置保存 API Key、Base URL、模型名、temperature、最大输出 Token、上下文消息数、请求超时和自动重试
- 支持使用 `APP_SECRET_KEY` 对已保存的模型 API Key 进行应用层对称加密
- 支持 OpenAI SDK 流式输出
- 支持 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_CHAT_MODEL` 等环境变量
- 未启用接口或未安装依赖时，可使用本地回显模式

## 项目结构

```text
.
├── app.py              # Streamlit 应用入口和页面编排
├── config.py           # 默认配置和环境变量读取
├── services/
│   ├── llm.py          # 模型调用、本地回显和消息清洗
│   ├── model_config.py # 模型配置数据库读写
│   ├── prompt_template.py # Prompt 模板库持久化和变量渲染
│   └── session.py      # 会话与消息的 PostgreSQL 持久化读写
├── ui/
│   └── components.py   # 页面组件渲染函数
├── docs/
│   └── remaining-optimizations.md # 剩余优化与功能拓展清单
├── requirements.txt    # Python 依赖
└── README.md           # 项目说明
```

## 环境要求

- Python 3.9 或更高版本
- pip
- PostgreSQL

## 安装依赖

建议先创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装项目依赖：

```bash
pip install -r requirements.txt
```

如需运行测试和代码检查，建议额外安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

## 运行项目

先确认 PostgreSQL 数据库已创建，例如：

```bash
createdb ai_chat_demo
export APP_DATABASE_URL="postgresql://你的用户:你的密码@localhost:5432/ai_chat_demo"
```

```bash
streamlit run app.py
```

启动后，终端会显示本地访问地址，通常是：

```text
http://localhost:8501
```

## 使用本地回显模式

当当前模型配置被停用，或未填写 API Key 时，应用不会请求外部模型接口，而是返回本地回显内容，适合快速验证页面是否正常运行。

## 使用模型接口

如需调用 OpenAI 或 OpenAI 兼容接口，请先在页面右上角的“设置”弹窗中创建或编辑模型配置。当前应用支持保存多个模型配置，并通过“当前模型配置”下拉框切换下一次提问使用的模型。

模型配置会保存到 PostgreSQL。请先准备数据库，并配置连接串：

```bash
export APP_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_chat_demo"
```

也可以使用常见的 `DATABASE_URL`：

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_chat_demo"
```

如果两个变量都未设置，应用会默认尝试连接：

```text
postgresql://postgres:postgres@localhost:5432/ai_chat_demo
```

如需把保存到 PostgreSQL 的模型 API Key 以密文形式持久化，请额外配置：

```bash
export APP_SECRET_KEY="请替换成足够长的随机字符串"
```

首次启动时，应用会使用现有环境变量创建一条默认模型配置。

方式一：通过环境变量配置：

```bash
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_CHAT_MODEL="deepseek-chat"
export OPENAI_MAX_TOKENS="2048"
export OPENAI_CONTEXT_MESSAGES="20"
export OPENAI_TIMEOUT_SECONDS="60"
export OPENAI_MAX_RETRIES="2"
streamlit run app.py
```

方式二：在页面右上角“设置”弹窗中维护模型配置：

- `配置名称`
- `服务商预设`
- `服务商`
- `API Key`
- `Base URL`
- `模型`
- `temperature`
- 最大输出 Token、上下文消息数、请求超时、自动重试次数
- `测试连接`

配置停用或未填写 API Key 时，应用会自动使用本地回显模式。

> 注意：从当前版本开始，填写了 `APP_SECRET_KEY` 后，新保存的 API Key 会以密文形式写入 PostgreSQL；历史明文数据会在下次编辑保存时平滑迁移。正式部署仍建议结合环境变量注入或服务端密钥管理。

## 使用 Prompt 模板库

在页面右上角“设置”弹窗中，进入“提示词 > 模板库”可以：

- 浏览内置模板和自定义模板
- 使用 `{{变量名}}` 占位符定义变量
- 填写变量后预览渲染结果
- 一键应用到当前会话提示词，或设为全局默认提示词
- 保存、编辑、复制、删除模板

## 常用配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 模型接口密钥 | 空 |
| `OPENAI_BASE_URL` | OpenAI 兼容接口地址 | `https://api.deepseek.com` |
| `OPENAI_CHAT_MODEL` | 聊天模型名称 | `deepseek-chat` |
| `OPENAI_MAX_TOKENS` | 单次回复最大输出 Token | `2048` |
| `OPENAI_CONTEXT_MESSAGES` | 发送给模型的最近上下文消息数，不含系统提示词 | `20` |
| `OPENAI_TIMEOUT_SECONDS` | 模型请求超时时间，单位秒 | `60` |
| `OPENAI_MAX_RETRIES` | SDK 自动重试次数 | `2` |
| `APP_DATABASE_URL` | PostgreSQL 连接串 | `postgresql://postgres:postgres@localhost:5432/ai_chat_demo` |
| `DATABASE_URL` | PostgreSQL 连接串，未设置 `APP_DATABASE_URL` 时使用 | 同上 |
| `APP_SECRET_KEY` | API Key 加密主密钥 | 空 |

## 常见问题

### 未配置 API Key 能运行吗？

可以。未勾选“使用 OpenAI 接口”时，应用会使用本地回显模式，不需要 API Key。

### 为什么勾选接口后返回鉴权失败？

通常是 API Key 无效、Base URL 不正确，或者模型名称与服务商不匹配。请检查“设置”弹窗中的模型配置、服务商预设或环境变量；也可以先使用“测试连接”按钮快速验证。

### 聊天记录会保存吗？

会。当前版本会把会话、系统提示词和聊天消息保存到 PostgreSQL，刷新页面或重启服务后仍可继续查看。你也可以在左侧会话栏导出当前会话的 Markdown 或 JSON 文件。

## 开发建议

后续优化和功能拓展已整理到 `docs/remaining-optimizations.md`。

## 开发命令

项目根目录已提供 `Makefile`，常用命令如下：

```bash
make dev
make test
make lint
make format
```

如果你更习惯直接执行命令，也可以使用：

```bash
python -m pytest
python -m ruff check .
python -m ruff format .
```

## 本地启动与测试流程

推荐按下面顺序进行本地开发：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

然后根据你的本地 PostgreSQL 环境修改 `.env` 中的 `APP_DATABASE_URL`，并按需填写模型接口配置。

数据库准备完成后，可以直接启动应用：

```bash
make dev
```

提交代码前，建议至少执行下面两步：

```bash
make test
make lint
```

如果你只想快速验证某个配置模块，也可以直接运行：

```bash
.venv/bin/python -m unittest tests.test_config -v
```
