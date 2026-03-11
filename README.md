# <img src="./public/logo.png" alt="示例图片" width="32" height="32"> resource2code：基于 AI 大模型的代码生成工具

**resource2code**是一款利用 AI 大模型和本地资源生成业务代码的生产力工具。它的原理很简单：

**资源 + 规则 + LLM = 代码**

- **资源**: 可以是任何生成代码依赖的东西：数据库表，API 文档，代码文件，配置文档等，resource2code 帮你将各种资源转换成 LLM 易于理解的格式
- **规则**: 是你对生成代码的要求，比如：代码规范，代码风格，代码示例等，使用 markdown 格式编写，你可以自由的管理维护各种规则，同时在各个项目中复用你的规则
- **LLM**: 支持接入自定义的 AI 大模型，目前支持 OpenAI 兼容格式以及 Ollama 两种格式的 API

和其它类似的代码助手相比，它的核心优势在于不依赖 IDE 独立工作，可以自由管理和复用规则，不必每次重复编写提示词，灵活的整合各种外部资源，不用手动复制和编辑

![示例图片](./public/readme/main.png)

# 快速开始

1. 下载预编译的可执行文件(暂时只提供 windows 版本)或者下载源码自行编译；
2. 在 LLM 配置中配置你的 AI 大模型；
3. 在右侧资源栏配置数据库连接信息和项目工程目录（项目工程目录请选择实际的源码目录 src，不要包含过多的无关目录，避免影响 LLM 判断代码的生成目录）
4. 管理你的代码规则（系统提供了一些默认规则作为参考）
5. 选择任务需要用到的额外的资源，开始生成代码

# 本地编译

整个项目是基于 tauri 框架的，请首先确保安装 rust 和 pnpm 环境。
然后在源码根目录执行以下命令：

```bash
pnpm install
pnpm tauri build
```

欢迎大家关注我的公众号（飞空之羽的技术手札），我会在上面定期分享一些关于技术的经验和感悟~

![二维码](https://github.com/davidfantasy/mybatis-plus-generator-ui/blob/master/imgs/wechat.jpg)


## Python 后端版本（前端不变）

仓库中新增了 `backend-python` 目录，用于提供与前端 `invoke(...)` 对齐的 Python 后端实现（FastAPI）。

### 启动方式

1. 启动 Python 后端：

```bash
cd backend-python
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

2. 在项目根目录启动前端：

Linux / macOS：

```bash
pnpm install
VITE_BACKEND_URL=http://127.0.0.1:8000 pnpm dev
```

Windows PowerShell：

```powershell
pnpm install
$env:VITE_BACKEND_URL='http://127.0.0.1:8000'
pnpm dev
```

Windows CMD：

```cmd
pnpm install
set VITE_BACKEND_URL=http://127.0.0.1:8000
pnpm dev
```

### 说明

- 前端程序语言保持为 TypeScript + Vue。
- 新增了 `src/api/invoke.ts`，将原本 `@tauri-apps/api/core` 的 `invoke` 调用改为 HTTP 调用 Python 后端。
- Python 后端包含配置、数据源、规则、任务、文件树与文件保存等基础命令；`get_tables` 目前返回空列表，可按你的数据库协议继续扩展。

### 在 PyCharm 中使用（推荐）

下面给出一种最顺手的方式：**PyCharm 跑 Python 后端，终端跑前端**。

1. 用 PyCharm 打开项目根目录 `ai_code`。
2. 在 PyCharm 中进入 `backend-python` 目录，创建并选择项目解释器（建议虚拟环境 `.venv`）。
3. 在 PyCharm Terminal 执行：

```bash
cd backend-python
pip install -r requirements.txt
```

4. 新建 Run/Debug Configuration：
   - 类型：`Python`
   - Name：`backend-python`
   - Script path：选择 `-m` module 模式，模块名填写 `uvicorn`
   - Parameters：`app:app --host 127.0.0.1 --port 8000 --reload`
   - Working directory：`$ProjectFileDir$/backend-python`
5. 运行该配置，确认 `http://127.0.0.1:8000/health` 返回 `{"status":"ok"}`。
6. 再打开一个终端（可用 PyCharm Terminal 或系统终端）启动前端：

Linux / macOS：

```bash
pnpm install
VITE_BACKEND_URL=http://127.0.0.1:8000 pnpm dev
```

Windows PowerShell：

```powershell
pnpm install
$env:VITE_BACKEND_URL='http://127.0.0.1:8000'
pnpm dev
```

7. 浏览器打开前端地址（通常是 `http://127.0.0.1:1420`）。


### 常见问题（Windows / PowerShell）

- 报错：`pmpm : 无法将“pmpm”项识别...`
  - 原因：命令拼写错误，正确命令是 **`pnpm`**，不是 `pmpm`。
  - 正确执行：

```powershell
pnpm install
```

- 报错：`VITE_BACKEND_URL=http://127.0.0.1:8000 : 无法将...识别为 cmdlet`
  - 原因：这是 Linux/macOS 的“临时环境变量 + 命令”写法，PowerShell 不支持这种语法。
  - PowerShell 正确写法：

```powershell
$env:VITE_BACKEND_URL='http://127.0.0.1:8000'
pnpm dev
```

- 报错：`pnpm` 也无法识别
  - 说明本机未安装 pnpm，可用以下任一方式安装：

```powershell
npm install -g pnpm
# 或（Node.js 16.13+ 推荐）
corepack enable
corepack prepare pnpm@latest --activate
```

- 安装后验证：

```powershell
pnpm -v
```
