---
name: robocopy-project
description: RoboCopy GUI 项目架构规范和工作原则
---

# RoboCopy GUI 开发规范

## 用户偏好
- 中文界面，所有选项带中文说明
- 不要深色模式
- 不要弹窗向导、任务队列、文件监控、定时执行
- 不要打包 exe（用户自己决定）
- 代码修改只能增量添加，不能删改已有功能
- 改完后必须自己跑一次验证
- 涉及外部命令参数必须先查官方文档（`robocopy /?`）

## 核心架构

```
GUI 控件 → 参数字典 self.p → params_to_argv() → robocopy 命令行
                                                       ↓
主线程 poll() 100ms ← queue.Queue ← 子线程(二进制块读管道)
```

## 代码规范

### 线程安全
- **工作线程绝对不碰 tkinter API**（包括 `self.after()`、`widget.config()`、`tk.Variable.set()`）
- 工作线程唯一做的事：读管道 → 写 `queue.Queue`
- 主线程唯一做的事：轮询 `queue.Queue` → 更新 UI

### 子进程管道读写
- 用 `os.read(fd, 65536)` 按块读二进制，不用 `readline()`
- 自行按 `\r\n`、`\n`、`\r` 切分行
- 原因：`readline()` 在 `\r`（回车）上会阻塞，robocopy 用 `\r` 做进度刷新

### 参数管理
- 所有配置集中在 `self.p` 字典里
- 参数映射在 `params_to_argv()` 函数里统一处理
- 序列化用白名单 `CONFIG_VARS`，只保存配置相关变量
- 不要用 `dir(self)` 遍历所有变量

### UI 布局
- 只用 `pack()` 布局，不用 grid/place
- 保持单文件结构

### Git 管理
- `.gitignore` 必须包含：`build/` `dist/` `*.spec` `__pycache__/` `*.pyc`
- 不要将 GitHub Token、密码等凭据写入文件
- 构建产物（exe、安装包）不要提交到仓库

### 联调与验证
- 写完代码后必须运行一次：`python robocopy_gui.py`
- 涉及参数映射改动时：先查 `robocopy /?` 逐条对照
- 配置默认值以 robocopy 官方文档为准

## 关键命令

```bash
# 运行
python robocopy_gui.py

# Git 推送（SSH 直连）
git push

# 创建 Release
git tag v1.0.0 -f && git push origin v1.0.0 -f

# 安装 dev-sidecar CA 证书
certutil -addstore -user Root "%USERPROFILE%\.dev-sidecar\dev-sidecar.ca.crt"

# 同步 Git 代理到系统 VPN（换 VPN 节点后）
python setup_complete.py
```

## 关键凭据
- **SSH 密钥**: `~/.ssh/github_he-lle`（配了 ssh.github.com:443）
- **SSH 配置**: `~/.ssh/config`
- **Git 远程**: `git@github.com:He-lle/RoboCopy-UI.git`
- **dev-sidecar**: `D:\Program Files\dev-sidecar\`
