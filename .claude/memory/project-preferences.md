---
name: project-preferences
description: RoboCopy GUI 项目约束和用户偏好
metadata:
  type: project
---

- 不要深色模式（之前做砸了）
- 不要弹窗向导、任务队列、文件监控、定时执行
- 不要打包 exe（之前的 exe 不启动）
- 改代码只能增量添加，不动现有行
- 改完后必须自己验证（跑一次 python robocopy_gui.py）
- 涉及 robocopy 参数必须查 `robocopy /?` 对照
- 工作线程绝不碰 tkinter API
