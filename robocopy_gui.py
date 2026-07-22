#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RoboCopy GUI — 微软 Robocopy 图形化操作软件
===============================================
纯 Python 标准库。把 GUI 选项翻译成 robocopy 命令行并执行。
"""

import os, sys, json, re, subprocess, threading, queue, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 启动自检
try:
    subprocess.run(["robocopy", "/?"], capture_output=True, timeout=5)
except:
    r = tk.Tk(); r.withdraw()
    messagebox.showerror("环境错误", "找不到 robocopy.exe，请确认是 Windows 10/11。")
    sys.exit(1)

# 颜色
C = {
    "bg": "#f1f5f9", "fg": "#0f172a",
    "card": "#ffffff", "cf": "#1e293b",
    "desc": "#64748b", "border": "#e2e8f0",
    "ok": "#059669", "err": "#dc2626",
    "obg": "#0f172a", "ofg": "#38bdf8",
}

# ────────────────────────────────────────
# 参数 → 命令行
# ────────────────────────────────────────
def params_to_argv(p):
    a = []
    # 源 + 目标
    src = p["src"]
    dst = p["dst"]
    if p.get("copy_folder") and src:
        dst = os.path.join(dst, os.path.basename(src.rstrip("\\/")))
    a.append(src if src else "\"\"")
    a.append(dst if dst else "\"\"")

    # 文件
    f = p["files"].strip()
    a.extend(f.split()) if f and f != "*.*" else a.append("*.*")

    if p.get("mirror"): a.append("/MIR")
    if p.get("subdirs_empty"): a.append("/E")
    if p.get("mov"): a.append("/MOV")
    if p.get("copyall"): a.append("/COPYALL")
    if p.get("j"): a.append("/J")
    if p.get("compress"): a.append("/COMPRESS")
    if p.get("xf","").strip():
        a.append("/XF"); a.extend(p["xf"].strip().split())
    if p.get("xd","").strip():
        a.append("/XD"); a.extend(p["xd"].strip().split())
    for flag in ["xo","xn"]:
        if p.get(flag): a.append(f"/{flag.upper()}")
    for flag in ["min","max","minage","maxage"]:
        if p.get(flag,"").strip(): a.append(f"/{flag.upper()}:{p[flag].strip()}")
    if p.get("xj"): a.append("/XJ")
    if p.get("retry",3) != 3: a.append(f"/R:{p['retry']}")
    if p.get("wait",10) != 10: a.append(f"/W:{p['wait']}")
    if p.get("mt",8) != 8: a.append(f"/MT:{p['mt']}")
    if p.get("ipg"): a.append(f"/IPG:{p['ipg']}")
    if p.get("v"): a.append("/V")
    if p.get("eta"): a.append("/ETA")
    if p.get("np"): a.append("/NP")
    if p.get("l"): a.append("/L")
    if p.get("njh"): a.append("/NJH")
    if p.get("njs"): a.append("/NJS")
    if p.get("x"): a.append("/X")
    if p.get("nooffload"): a.append("/NOOFFLOAD")
    if p.get("fft"): a.append("/FFT")
    if p.get("dst_"): a.append("/DST")
    if p.get("sl"): a.append("/SL")
    if p.get("sj"): a.append("/SJ")
    if p.get("xjd"): a.append("/XJD")
    if p.get("xjf"): a.append("/XJF")
    if p.get("create"): a.append("/CREATE")
    if p.get("fat"): a.append("/FAT")
    if p.get("zb"): a.append("/ZB")
    if p.get("efsraw"): a.append("/EFSRAW")
    for flag in ["xc","xx","xl","is_","it","im"]:
        if p.get(flag): a.append(f"/{flag.capitalize().rstrip('_')}")
    for flag in ["maxlad","minlad"]:
        if p.get(flag,"").strip(): a.append(f"/{flag.upper()}:{p[flag].strip()}")
    if p.get("reg"): a.append("/REG")
    if p.get("tbd"): a.append("/TBD")
    if p.get("lfsm"):
        v = p.get("lfsm_val","").strip()
        a.append(f"/LFSM:{v}" if v else "/LFSM")
    if p.get("log","").strip():
        tag = "/LOG+:" if p.get("log_append") else "/LOG:"
        a.append(f"{tag}{p['log'].strip()}")
    if p.get("ts"): a.append("/TS")
    if p.get("fp"): a.append("/FP")
    if p.get("bytes"): a.append("/BYTES")
    if p.get("nc"): a.append("/NC")
    if p.get("ns"): a.append("/NS")
    if p.get("nfl"): a.append("/NFL")
    if p.get("ndl"): a.append("/NDL")
    if p.get("tee"): a.append("/TEE")
    # 时间窗口 /RH
    if p.get("rh_start","").strip() and p.get("rh_end","").strip():
        a.append(f"/RH:{p['rh_start'].strip()}-{p['rh_end'].strip()}")
    if p.get("pf"): a.append("/PF")
    # 添加/删除属性
    if p.get("a_plus","").strip(): a.append(f"/A+:{p['a_plus'].strip()}")
    if p.get("a_minus","").strip(): a.append(f"/A-:{p['a_minus'].strip()}")
    # Job 文件
    if p.get("job","").strip(): a.append(f"/JOB:{p['job'].strip()}")
    if p.get("save","").strip(): a.append(f"/SAVE:{p['save'].strip()}")
    # 属性包含/排除
    ia = "".join(p.get(f"ia_{x}") for x in "RASHCNET" if p.get(f"ia_{x}"))
    if ia: a.append(f"/IA:{ia}")
    xa = "".join(p.get(f"xa_{x}") for x in "RASHCNET" if p.get(f"xa_{x}"))
    if xa: a.append(f"/XA:{xa}")
    return a

def cmd_str(p):
    argv = params_to_argv(p)
    q = []
    for x in argv:
        if " " in x and not x.startswith('"'): q.append(f'"{x}"')
        else: q.append(x)
    return "robocopy " + " ".join(q)


# ────────────────────────────────────────
# 主程序
# ────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RoboCopy GUI")
        self.geometry("1050x760")
        self.minsize(900, 650)
        self.configure(bg=C["bg"])

        # 参数
        self.p = {
            "src":"","dst":"","files":"*.*",
            "subdirs":False,"subdirs_empty":False,
            "mirror":False,"mov":False,
            "copyall":True,"copy_folder":True,
            "j":False,"compress":False,
            "xf":"","xd":"","xo":False,"xn":False,
            "min":"","max":"","minage":"","maxage":"",
            "xj":False,"retry":3,"wait":10,"mt":8,"ipg":0,
            "v":True,"eta":True,"l":False,
            "x":False,"nooffload":False,
            "fft":False,"dst_":False,
            "sl":False,"xjd":False,"xjf":False,"sj":False,
            "create":False,"fat":False,
            "zb":False,"efsraw":False,
            "xc":False,"xx":False,"xl":False,"is_":False,"it":False,"im":False,
            "maxlad":"","minlad":"",
            "reg":False,"tbd":False,
            "lfsm":False,"lfsm_val":"",
            "log":"","log_append":False,
            "ts":False,"fp":False,"bytes":False,
            "nc":False,"ns":False,"nfl":False,"ndl":False,"tee":False,
            "rh_start":"","rh_end":"","pf":False,
            "a_plus":"","a_minus":"",
            "job":"","save":"",
        }

        self._running = False
        self._proc = None
        self._stop_evt = threading.Event()
        self._q = queue.Queue()
        self._cmd_var = tk.StringVar()
        self._out_lines = 0

        self._build_styles()
        self._build_menu()
        self._build_ui()
        self._ui_from_p()
        self._bind_traces()
        self._update_cmd()

        self.bind("<F5>", lambda e: self._run())
        self.bind("<Control-Break>", lambda e: self._stop())
        self.bind("<Control-q>", lambda e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll)

    # ── 样式 ──────────────────────────
    def _build_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=C["bg"], foreground=C["fg"],
                   fieldbackground=C["card"], selectbackground="#3b82f6")
        s.configure("TNotebook.Tab", padding=[12,4], borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", C["card"])])
        s.configure("TEntry", fieldbackground=C["card"], foreground=C["fg"])
        s.configure("TSpinbox", fieldbackground=C["card"], foreground=C["fg"])

    # ── 菜单 ──────────────────────────
    def _build_menu(self):
        mb = tk.Menu(self); self.config(menu=mb)
        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="保存配置", command=self._save_config, accelerator="Ctrl+S")
        fm.add_command(label="加载配置", command=self._load_config, accelerator="Ctrl+O")
        fm.add_separator()
        fm.add_command(label="退出", command=self._on_close, accelerator="Ctrl+Q")
        mb.add_cascade(label="文件", menu=fm)
        rm = tk.Menu(mb, tearoff=0)
        rm.add_command(label="开始复制", command=self._run, accelerator="F5")
        rm.add_command(label="终止", command=self._stop, accelerator="Ctrl+Break")
        rm.add_separator()
        rm.add_command(label="清空输出", command=self._clear_out)
        mb.add_cascade(label="操作", menu=rm)

    # ── UI ────────────────────────────
    def _build_ui(self):
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        nb = ttk.Notebook(outer)
        nb.pack(fill=tk.BOTH, expand=True, pady=2)
        self._build_tab1(nb)
        self._build_tab2(nb)
        self._build_tab3(nb)
        self._build_tab4(nb)
        nb.add(self._t1, text="  源与目标  ")
        nb.add(self._t2, text="  复制模式  ")
        nb.add(self._t3, text="  筛选  ")
        nb.add(self._t4, text="  性能日志  ")

        # 底部
        bot = tk.Frame(outer, bg=C["bg"])
        bot.pack(fill=tk.X, pady=1)

        # 命令
        cf = tk.Frame(bot, bg=C["bg"])
        cf.pack(fill=tk.X, pady=1)
        tk.Label(cf, text="命令：", bg=C["bg"], fg=C["desc"]).pack(side=tk.LEFT)
        ttk.Entry(cf, textvariable=self._cmd_var, state="readonly",
                 font=("Consolas", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # 进度
        self._pbar = ttk.Progressbar(bot, mode="determinate")
        self._pbar.pack(fill=tk.X, pady=1)
        self._plab = tk.Label(bot, text="就绪", bg=C["bg"], fg=C["fg"], font=("Consolas", 9), anchor=tk.W)
        self._plab.pack(fill=tk.X)

        # 按钮
        bf = tk.Frame(bot, bg=C["bg"])
        bf.pack(fill=tk.X, pady=2)
        self._btn_run = tk.Button(bf, text="▶ 开始复制 (F5)", command=self._run,
                                 bg=C["ok"], fg="white",
                                 font=("Microsoft YaHei UI", 10, "bold"),
                                 padx=16, cursor="hand2", relief=tk.FLAT)
        self._btn_run.pack(side=tk.LEFT, padx=(0,4))
        self._btn_stop = tk.Button(bf, text="⏹ 终止", command=self._stop,
                                  bg=C["err"], fg="white", state=tk.DISABLED,
                                  padx=12, cursor="hand2", relief=tk.FLAT)
        self._btn_stop.pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="清空输出", command=self._clear_out).pack(side=tk.LEFT, padx=4)

        # 输出区域（Text + Scrollbar，不用 ScrolledText 避免滚动问题）
        of = tk.Frame(outer, bg=C["bg"])
        of.pack(fill=tk.BOTH, expand=True, pady=2)
        tk.Label(of, text="输出", bg=C["bg"], fg=C["desc"],
                font=("Microsoft YaHei UI", 8, "bold")).pack(anchor=tk.W)

        sw = tk.Frame(of)
        sw.pack(fill=tk.BOTH, expand=True)
        scroll = tk.Scrollbar(sw, orient=tk.VERTICAL)
        self._out = tk.Text(sw, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), bg=C["obg"], fg=C["ofg"],
            insertbackground=C["ofg"], yscrollcommand=scroll.set,
            relief=tk.FLAT, borderwidth=0)
        scroll.config(command=self._out.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 状态栏
        self._st = tk.StringVar(value="就绪")
        tk.Label(self, textvariable=self._st, bg="#e2e8f0", anchor=tk.W,
                padx=10).pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0,4))

    # ══════════════════════════════════
    # 选项卡
    # ══════════════════════════════════
    def _build_tab1(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=14, pady=10)
        self._hint(f, "设置要复制的文件夹（源目录）和目标位置。")
        self._src_var = self._entry(f, "源目录：", btn="浏览", cmd=lambda: self._br(self._src_var, True))
        self._dst_var = self._entry(f, "目标目录：", btn="浏览", cmd=lambda: self._br(self._dst_var, True))
        self._files_var = self._entry(f, "文件模式：", placeholder="*.*（全部文件）")
        self._folder_var = self._check(f, "复制文件夹本身（目标路径追加源文件夹名）",
                                       "勾选后：D:\\src → D:\\dst\\src，不勾选：D:\\src\\* → D:\\dst\\")
        self._t1 = f

    def _build_tab2(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=14, pady=10)
        self._hint(f, "选择复制方式。不勾选=只复制源目录根部的文件（不含子目录）。")
        self._mirror_var = self._check(f, "完全同步（删除多余文件）",
                                       "让目标和源一模一样，会删除目标中多余的文件")
        self._subdirs_e_var = self._check(f, "包含子目录",
                                          "连子目录一起复制（空目录也会创建）")
        self._copyall_var = self._check(f, "保留所有文件信息",
                                        "保留数据、属性、时间、权限等")
        self._mov_var = self._check(f, "移动（复制后删除源）",
                                    "相当于剪切，源文件会消失")
        # ── 新增选项 ──
        self._zb_var = self._check(f, "可重启+备份模式 /ZB", "先尝试重启，被拒则用备份")
        self._create_var = self._check(f, "仅创建目录和空文件", "/CREATE")
        self._sl_var = self._check(f, "符号链接保留为链接", "/SL")
        self._t2 = f

    def _build_tab3(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=14, pady=10)
        self._hint(f, "排除不要的文件，或按大小/时间筛选。留空=不筛选。")
        self._xf_var = self._entry(f, "排除文件：", placeholder="*.log *.tmp")
        self._xd_var = self._entry(f, "排除目录：", placeholder="temp cache")
        self._xo_var = self._check(f, "只复制较新的文件")
        self._xn_var = self._check(f, "只复制较旧的文件")
        self._min_s_var = self._entry(f, "最小大小：", placeholder="1024 或 1M")
        self._max_s_var = self._entry(f, "最大大小：", placeholder="10M")
        self._min_a_var = self._entry(f, "至少距今：", placeholder="天数或 YYYYMMDD")
        self._max_a_var = self._entry(f, "最多距今：", placeholder="天数或 YYYYMMDD")
        # ── 新增选项 ──
        self._minlad_var = self._entry(f, "最后访问 ≥：", placeholder="天数或 YYYYMMDD")
        self._maxlad_var = self._entry(f, "最后访问 ≤：", placeholder="天数或 YYYYMMDD")
        self._xc_var = self._check(f, "排除已更改文件", "/XC")
        self._im_var = self._check(f, "包含修改时间不同", "/IM")
        self._t3 = f

    def _build_tab4(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=14, pady=10)
        self._hint(f, "调整速度、重试和输出选项。")
        self._retry_var = self._spin(f, "重试次数：", 0, 100, 3)
        self._wait_var = self._spin(f, "重试间隔（秒）：", 1, 300, 10)
        self._mt_var = self._spin(f, "线程数：", 1, 128, 8)
        self._ipg_var = self._spin(f, "包间隔（ms）：", 0, 9999, 0)
        self._v_var = self._check(f, "详细输出（推荐）")
        self._eta_var = self._check(f, "显示预计完成时间")
        self._l_var = self._check(f, "仅列出不复制（安全预览）")
        # ── 新增选项 ──
        self._reg_var = self._check(f, "保存为注册表默认 /REG")
        self._tbd_var = self._check(f, "等待共享名可用 /TBD")
        self._lfsm_var = self._check(f, "低磁盘空间模式 /LFSM")
        self._ts_var = self._check(f, "显示文件时间 /TS")
        self._nc_var = self._check(f, "不显示文件类 /NC")
        self._ns_var = self._check(f, "不显示文件大小 /NS")
        self._nfl_var = self._check(f, "不显示文件列表 /NFL")
        self._ndl_var = self._check(f, "不显示目录列表 /NDL")
        self._t4 = f

    # ── 组件 ──────────────────────────
    def _hint(self, parent, text):
        f = tk.Frame(parent, bg="#fffbeb", padx=10, pady=5)
        f.pack(fill=tk.X, pady=4)
        tk.Label(f, text=text, bg="#fffbeb", fg="#b45309",
                font=("Microsoft YaHei UI", 9), wraplength=900, justify=tk.LEFT).pack(anchor=tk.W)

    def _entry(self, parent, label, placeholder="", btn="", cmd=None):
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, bg=C["card"], fg=C["cf"],
                font=("Microsoft YaHei UI", 9), width=16, anchor=tk.W).pack(side=tk.LEFT)
        var = tk.StringVar()
        e = ttk.Entry(row, textvariable=var)
        e.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        if btn and cmd:
            tk.Button(row, text=btn, command=cmd, padx=4).pack(side=tk.LEFT, padx=2)
        return var

    def _check(self, parent, text, desc=""):
        var = tk.BooleanVar()
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill=tk.X, pady=1)
        tk.Checkbutton(row, text=text, variable=var, bg=C["card"], fg=C["cf"],
                      anchor=tk.W, cursor="hand2").pack(side=tk.LEFT)
        if desc:
            tk.Label(row, text=desc, bg=C["card"], fg=C["desc"],
                    font=("Microsoft YaHei UI", 8)).pack(side=tk.LEFT, padx=6)
        return var

    def _spin(self, parent, label, min_, max_, default):
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, bg=C["card"], fg=C["cf"],
                font=("Microsoft YaHei UI", 9), width=16, anchor=tk.W).pack(side=tk.LEFT)
        var = tk.StringVar(value=str(default))
        ttk.Spinbox(row, from_=min_, to=max_, textvariable=var, width=6).pack(side=tk.LEFT, padx=4)
        return var

    # ── 浏览 ──────────────────────────
    def _br(self, var, is_dir):
        p = filedialog.askdirectory(title="选择目录") if is_dir else \
            filedialog.asksaveasfilename(title="选择文件")
        if p: var.set(p)

    # ── 参数同步 ──────────────────────
    VAR_MAP = [
        ("_src_var","src"),("_dst_var","dst"),("_files_var","files"),
        ("_folder_var","copy_folder"),
        ("_subdirs_e_var","subdirs_empty"),
        ("_mirror_var","mirror"),("_mov_var","mov"),
        ("_copyall_var","copyall"),
        ("_xf_var","xf"),("_xd_var","xd"),
        ("_xo_var","xo"),("_xn_var","xn"),
        ("_min_s_var","min"),("_max_s_var","max"),
        ("_min_a_var","minage"),("_max_a_var","maxage"),
        ("_retry_var","retry",int),("_wait_var","wait",int),
        ("_mt_var","mt",int),("_ipg_var","ipg",int),
        ("_v_var","v"),("_eta_var","eta"),("_l_var","l"),
        # 新增
        ("_zb_var","zb"),("_create_var","create"),
        ("_sl_var","sl"),
        ("_minlad_var","minlad"),("_maxlad_var","maxlad"),
        ("_xc_var","xc"),("_im_var","im"),
        ("_reg_var","reg"),("_tbd_var","tbd"),
        ("_lfsm_var","lfsm"),
        ("_ts_var","ts"),
        ("_nc_var","nc"),("_ns_var","ns"),
        ("_nfl_var","nfl"),("_ndl_var","ndl"),
    ]

    def _p_from_ui(self):
        for m in self.VAR_MAP:
            attr, key = m[0], m[1]
            conv = m[2] if len(m) > 2 else None
            v = getattr(self, attr).get()
            self.p[key] = conv(v) if conv else v

    def _ui_from_p(self):
        for m in self.VAR_MAP:
            attr, key = m[0], m[1]
            v = self.p[key]
            if isinstance(v, bool):
                getattr(self, attr).set(v)
            else:
                getattr(self, attr).set(str(v) if v is not None else "")

    def _update_cmd(self):
        self._p_from_ui()
        self._cmd_var.set(cmd_str(self.p))

    def _bind_traces(self):
        """给所有 UI 变量加 trace，变化时实时更新命令预览"""
        for attr in dir(self):
            if attr.endswith("_var") and isinstance(getattr(self, attr), tk.Variable):
                try:
                    getattr(self, attr).trace_add("write", lambda *_: self._update_cmd())
                except:
                    pass

    # ── 执行 ──────────────────────────
    def _run(self):
        if self._running:
            return
        self._p_from_ui()
        if not self.p["src"] or not self.p["dst"]:
            messagebox.showerror("错误", "请填写源目录和目标目录路径。")
            return

        cmd = cmd_str(self.p)
        if not messagebox.askyesno("确认", f"{cmd}\n\n确认执行？"):
            return

        self._clear_out()
        self._log(f"> {cmd}\n")
        self._pbar["value"] = 0
        self._plab.config(text="等待开始...")
        self._running = True
        self._btn_run.config(state=tk.DISABLED, bg="#9ca3af")
        self._btn_stop.config(state=tk.NORMAL)
        self._st.set("正在复制...")

        self._stop_evt.clear()
        argv = ["robocopy"] + params_to_argv(self.p)
        threading.Thread(target=self._run_thread, args=(argv,), daemon=True).start()

    def _run_thread(self, argv):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self._proc = subprocess.Popen(argv, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, startupinfo=si, bufsize=0)
            start = time.time(); fc = 0; last_up = 0; buf = b""

            while True:
                if self._stop_evt.is_set():
                    self._proc.terminate(); break
                chunk = os.read(self._proc.stdout.fileno(), 65536)
                if not chunk: break
                buf += chunk
                while b"\n" in buf or b"\r" in buf:
                    ni, ri = buf.find(b"\n"), buf.find(b"\r")
                    if ri >= 0 and (ni < 0 or ri < ni):
                        line, buf = buf[:ri], buf[ri+1:]
                        if buf and buf[0:1] == b"\n": buf = buf[1:]
                    elif ni >= 0:
                        line, buf = buf[:ni], buf[ni+1:]
                    else: break
                    s = line.decode("gbk", errors="replace").rstrip("\n\r")
                    self._q.put(s)
                    if "新文件" in s or "新目录" in s or "*EXTRA" in s:
                        fc += 1
                    m = re.match(r"\s*(\d{1,3})%", s)
                    if m:
                        self._q.put(f"!P:{m.group(1)}")
                    el = time.time() - start
                    if el - last_up >= 1.0:
                        last_up = el; sp = fc/el if el>0 else 0
                        self._q.put(f"!S:{fc}:{sp:.1f}:{el:.0f}")

            self._proc.stdout.close()
            ret = self._proc.wait()
            el = time.time() - start
            self._q.put(f"!D:{ret}:{el:.1f}:{fc}")
        except Exception as e:
            self._q.put(f"!E:{e}")
        finally:
            self._proc = None

    def _stop(self):
        if self._proc and self._running:
            self._stop_evt.set()
            try: self._proc.terminate()
            except: pass
            self._log("\n⏹ 已终止\n"); self._finish()

    def _finish(self):
        self._running = False
        self._btn_run.config(state=tk.NORMAL, bg=C["ok"])
        self._btn_stop.config(state=tk.DISABLED)

    # ── 队列轮询 ──────────────────────
    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                if msg.startswith("!P:"):
                    self._pbar["value"] = int(msg[3:])
                elif msg.startswith("!S:"):
                    p = msg[3:].split(":")
                    if len(p) >= 3:
                        self._plab.config(text=f"{int(self._pbar['value'])}% | {p[0]} 文件 | {p[1]} 文件/秒 | 已用 {p[2]}s")
                elif msg.startswith("!D:"):
                    p = msg[3:].split(":")
                    self._log(f"\n退出代码 {p[0]} | 耗时 {p[1]}s | {p[2]} 个文件\n")
                    if p[0] == "0": self._log("所有文件已是最新。\n")
                    elif p[0] == "1": self._log("✅ 复制成功！\n")
                    elif p[0] < "4": self._log("⚠ 完成。\n")
                    else: self._log(f"❌ 错误。\n")
                    self._finish(); self._st.set("就绪")
                elif msg.startswith("!E:"):
                    self._log(f"❌ {msg[3:]}\n"); self._finish()
                else:
                    self._log(msg + "\n")
        except queue.Empty:
            pass
        self._trim_out()
        self.after(100, self._poll)

    # ── 输出 ──────────────────────────
    def _log(self, text):
        self._out.config(state=tk.NORMAL)
        self._out.insert(tk.END, text)
        self._out_lines += text.count("\n") + 1
        # 自动滚动到底部
        self._out.see(tk.END)
        self._out.config(state=tk.DISABLED)

    def _trim_out(self):
        """行数超限时裁剪，只在 _poll 末尾调用"""
        if self._out_lines <= 500:
            return
        self._out.config(state=tk.NORMAL)
        n = int(self._out.index("end-1c").split(".")[0])
        if n > 500:
            self._out.delete("1.0", f"{n-500}.0")
            self._out_lines = 500
        self._out.config(state=tk.DISABLED)

    def _clear_out(self):
        self._out.config(state=tk.NORMAL)
        self._out.delete("1.0", tk.END)
        self._out.config(state=tk.DISABLED)
        self._out_lines = 0

    # ── 配置保存/加载 ──────────────────
    def _save_config(self):
        import json
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                           filetypes=[("JSON","*.json")])
        if not path: return
        self._p_from_ui()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.p, f, ensure_ascii=False, indent=2)
            self._st.set(f"配置已保存：{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _load_config(self):
        import json
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            for k in self.p:
                if k in d and isinstance(d[k], (bool,int,str)):
                    self.p[k] = d[k]
            self._ui_from_p()
            self._update_cmd()
            self._st.set(f"配置已加载：{os.path.basename(path)}")
        except json.JSONDecodeError:
            messagebox.showerror("加载失败", "配置文件格式错误。")
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    # ── 关闭 ──────────────────────────
    def _on_close(self):
        if self._running:
            if not messagebox.askyesno("确认", "正在复制，是否终止并退出？"):
                return
            self._stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
