---
name: robocopy-project
description: RoboCopy GUI 项目全记录 - 架构、踩坑、关键命令、用户偏好
---

# RoboCopy GUI 项目经验

## 用户偏好
- 中文界面，所有选项带中文说明
- 不要深色模式（之前做砸了，控件颜色错乱）
- 不要弹窗向导（之前滚轮绑定泄漏）
- 不要任务队列/文件监控/定时执行（功能臃肿且不稳定）
- 不要打包 exe（之前的 exe 启动有问题）
- 改代码只能增量添加，不能删改已有功能
- 改完后必须自己跑一次验证
- 涉及外部命令参数必须先查官方文档

## 最终架构

```
GUI 控件 → 参数字典 self.p → params_to_argv() → robocopy 命令行
                                                       ↓
主线程 poll() 100ms ← queue.Queue ← 子线程(二进制块读管道)
```

### 硬性约束
1. **线程永远不碰 tkinter API** — 工作线程只读写 `queue.Queue`
2. **参数集中管理** — 所有配置在 `self.p` 字典里，UI ↔ p ↔ 命令行
3. **布局只用 `pack()`** — 不混用 grid/place
4. **改代码只增量不加** — 不动已存在的代码行
5. **单文件结构** — `robocopy_gui.py`

## 全部弯路记录（按时间顺序）

### 1. 一上来就做了太多功能
一开始就加了 6 个选项卡、向导、任务队列、文件监控、定时执行……
结果每个功能都半残，bug 一堆，用户要求全部删掉重来。
**教训：先做核心功能（参数翻译 + 执行），稳定了再加别的。**

### 2. 线程里碰了 tkinter API
工作线程里直接调 `self.after(0, ...)` 和 `self._output.config(...)`。
**根因**：Python tkinter 的 `after()` 不是线程安全的，从非主线程调用会导致主事件循环卡死。
**修复**：工作线程只写 `queue.Queue`，主线程 100ms 轮询处理。

### 3. readline 阻塞导致界面卡死
用 `self._proc.stdout.readline()` 读 robocopy 输出。
**根因**：robocopy 用 `\r`（回车）做进度更新，但 `readline` 只认 `\n`，遇不到 `\n` 就一直阻塞。管道缓冲区满了之后 robocopy 自己也会卡住写输出。
**修复**：用 `os.read(fd, 65536)` 按块读二进制，自行按 `\r\n`、`\n`、`\r` 切分行。

### 4. 深色模式颜色错乱
做了亮色/深色切换，但递归遍历改控件颜色会漏改 tk.Checkbutton、tk.Button 等。
用户反馈「大量控件文字颜色相近看不清」。
**修复**：彻底移除深色模式，只保留亮色。

### 5. 向导滚轮绑定泄漏
`canvas.bind_all("<MouseWheel>", ...)` 全局绑定，关闭向导后不解除。
用户反馈「关掉向导后在其他窗口滚轮也会触发滚动」。
**修复**：改成 `canvas.bind()` 局部绑定，窗口关闭时 `unbind`。

### 6. 参数序列化乱存
`_get_all_vars()` 用 `dir(self)` 遍历所有 `tk.Variable`，把 `_preset_var`、`_cmd_var`、`_status_var` 等 UI 状态也存进了配置文件。
**修复**：用白名单 `CONFIG_VARS` 只保存配置相关变量。

### 7. 变量没初始化就使用
`self._stop_event` 在方法里定义但没在 `__init__` 初始化，调用 `self._stop_event.set()` 时报错。
**修复**：在 `__init__` 中初始化所有 `threading.Event`。

### 8. 没查 robocopy /? 就改参数映射
把 `/256` 映射成了 `/X`（ `X` 应该是「显示额外文件」）。
默认 `/R:3` 应该是 `/R:1`，默认 `/W:10` 应该是 `/W:30`。
**根因**：靠记忆写代码，没查官方文档。
**规则**：涉及外部命令参数时，先跑 `cmd /?` 逐条对照。

### 9. 重复参数键
params 字典里写了两次 `"x":False`，第二个覆盖了第一个。
**原因**：改代码时粗心，没检查 diff。

### 10. 构建产物误提交到 git
`.gitignore` 只写了 `__pycache__/`，漏了 `build/` `dist/` `*.spec`。
**修复**：补全 gitignore 并 `git rm --cached`。

### 11. 改了功能不更新文档
移除了深色模式，但 README 里还写着「深色模式切换」。
用户问「你改了功能为什么不改配套文档」。

### 12. dev-sidecar 证书问题
装好 dev-sidecar 后浏览器报 `ERR_CERT_AUTHORITY_INVALID`。
**修复**：手动安装 CA 证书：
```
certutil -addstore -user Root "%USERPROFILE%\.dev-sidecar\dev-sidecar.ca.crt"
```

### 13. 重写了太多次代码
整个项目重写了至少 4 次，每次都是因为前一个版本 bug 太多。
用户说「就这个版本！能用了！」的时候已经浪费了大量时间。
**教训**：不要动不动就重写，在一个能跑的基础上修 bug 比重写快。

## 关键命令

```bash
# 打包 exe
pyinstaller --onefile --noconsole --name "RoboCopy UI" robocopy_gui.py

# Git 推送（SSH 直连，无需 VPN）
git push

# 创建 Release
git tag v1.0.0 -f && git push origin v1.0.0 -f

# 安装 dev-sidecar CA 证书
certutil -addstore -user Root "%USERPROFILE%\.dev-sidecar\dev-sidecar.ca.crt"

# 同步 Git 代理到系统 VPN（换 VPN 节点后执行）
python setup_complete.py
```

## 关键凭据

- **GitHub Token**: 存在对话历史里，不要写进文件（GitHub 会封）
- **SSH 密钥**: `~/.ssh/github_he-lle`（配了 ssh.github.com:443）
- **SSH 配置**: `~/.ssh/config`
- **Git 远程**: `git@github.com:He-lle/RoboCopy-UI.git`
- **dev-sidecar**: `D:\Program Files\dev-sidecar\`

## 文件结构

```
D:\Program\RoboCopy UI\
├── robocopy_gui.py        # 主程序（全部功能）
├── test_all.py            # 测试
├── setup_complete.py      # VPN 代理同步
├── presets.json           # 预设方案
├── README.md              # 文档
├── .gitignore
└── .claude/
    ├── skills/
    │   └── robocopy-project.md
    └── memory/
```
