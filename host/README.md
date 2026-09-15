# ClaudePad 宿主程序

审批拨杆的宿主侧实现。**让键盘侧边拨杆真正能自动批准 Claude Code 的操作。**

设计依据与实测数据见 `docs/审批拨杆技术验证.md`。

---

## 它解决什么问题

Claude Code 跑长任务时会反复弹审批：「是否允许执行 rm」「是否允许写入配置」。
用户此时可能在做别的事，每次都要切回终端按回车。

把键盘拨杆拨到 ON，这些审批自动通过。拨回 OFF，恢复原样。

**拨杆 OFF 时，这个程序对 Claude Code 完全没有影响**——不改变任何既有行为。

---

## 目录

```
host/
├── claudepad_core.py       决策核心（危险命令识别 / 受保护路径 / 状态读写）
├── claudepad_daemon.py     ★ 常驻守护进程：HTTP hook 服务 + 键盘监听
├── claudepad_hook.py       command 模式 hook（降级方案）
├── switchctl.py            命令行控制（手动开关 / 状态 / 日志 / 守护模式）
├── install_hook.py         一键安装卸载 hook 配置
└── test_hook.py            测试台（31 个用例）
```

---

## 快速开始

### 1. 先跑测试（不需要键盘，不需要 Claude Code）

```bash
python test_hook.py
```

应该输出「31 个用例全部通过」。这一步验证审批逻辑本身是对的。

### 2. 安装 hook

```bash
python install_hook.py              # 预览要写入的配置（不改文件）
python install_hook.py --apply      # 确认后真正写入（自动备份原文件）
```

安装脚本会自动填好路径和访问令牌。**不要手改 `settings.json`**——路径里的反斜杠和空格最容易在这里出错。

### 3. 启动守护进程

```bash
python claudepad_daemon.py
```

保持运行。它会：
- 在 `127.0.0.1:8787` 提供 hook 应答服务
- 监听全局按键，捕捉键盘发来的 F13/F14

> 需要 `pynput` 才能监听键盘：`pip install pynput`
> 没装也能用，只是要手动控制拨杆。

### 4. 验证

```bash
python switchctl.py on     # 打开拨杆
# 回到 Claude Code，做一件需要授权的事 → 应该不再询问
python switchctl.py off    # 关掉，恢复询问
```

---

## 常用命令

```bash
python switchctl.py status      # 查看拨杆状态
python switchctl.py on          # 打开（模拟拨杆 ON）
python switchctl.py off         # 关闭
python switchctl.py toggle      # 切换
python switchctl.py watch       # 守护模式（不带 HTTP 服务）
python switchctl.py log 30      # 查看最近 30 条审批记录
python switchctl.py reset-log   # 清空日志
```

---

## 行为规则

拨杆 ON 时：

| 操作类型 | 行为 |
|---|---|
| 读文件（`Read` / `Glob` / `Grep`） | ✅ 自动批准 |
| 编辑/新建文件（`Edit` / `Write`） | ✅ 自动批准 |
| 常规命令（`ls` / `git status` / `npm test`） | ✅ 自动批准 |
| 联网（`WebFetch` / `WebSearch`） | ✅ 自动批准 |
| **危险命令** | ⚠️ **不自动批准**，交回原生流程询问 |
| **写受保护路径** | ⚠️ **不自动批准** |
| **`AskUserQuestion`** | ⚠️ **永不代答**（需要用户本人判断） |

### 被拦截的危险命令

删除类：`rm -rf`、`rm -r`、`rmdir`、`del /s`、`rd /s`、`Remove-Item -Recurse`
权限类：`sudo`、`runas`、`chmod 777`、`chown`
磁盘系统：`dd`、`mkfs`、`format`、写 `/dev/sd*`、`shutdown`、`reboot`
Git 破坏性：`git push --force`、`git push -f`、`git reset --hard`、`git clean -f`
远程执行：`curl | sh`、`wget | bash`
其他：`kill -9`、fork bomb、`npm publish`

### 受保护路径

`/etc/`、`/usr/`、`/bin/`、`/boot/`、`C:\Windows`、`C:\Program Files`、
`~/.ssh/`、`~/.aws/`、`~/.gnupg/`、`~/.bashrc`、`~/.zshrc`、
`~/.claude/settings.json`（防止自我修改配置）、`.git/config`

> 想调整规则？改 `claudepad_core.py` 里的 `DANGEROUS_CMD_PATTERNS` 和
> `PROTECTED_PATH_PATTERNS`，然后重跑 `test_hook.py`。

---

## 为什么用 HTTP 模式而不是 command 模式

hooks 支持两种执行方式，实测延迟差 34 倍：

| 模式 | 延迟 | 说明 |
|---|---|---|
| `command` | **510 ms/次** | 每次工具调用起一个 Python 进程 |
| `http` | **15 ms/次** | 常驻进程直接应答 |

`command` 模式下每个工具调用都多等半秒，不可接受。所以默认装 HTTP 模式。

如果不想常驻进程，可以装 command 模式：

```bash
python install_hook.py --mode command --apply
```

逻辑完全一样（共用 `claudepad_core.py`），只是慢。

---

## 安全设计

### 失效安全：任何故障都退化为「正常询问」

| 故障 | 结果 |
|---|---|
| 守护进程没跑 | 连接失败 → **正常询问** |
| 访问令牌不匹配 | HTTP 403 → **正常询问** |
| hook 脚本异常 | 返回空 → **正常询问** |
| 输入 JSON 损坏 | 返回空 → **正常询问** |
| 状态文件丢失 | 视为拨杆 OFF → **正常询问** |

**绝不会出现「因为程序 bug 而全部自动批准」。**

### 只升不降

hook 只返回 `allow`，从不返回 `ask` 或 `deny`。

危险命令一律**静默放行**给 Claude Code 原生流程判断，而不是强制弹窗。

好处：不会出现「本来在 `acceptEdits` 模式，因为拨杆 ON 反而被强制弹窗」这种反直觉行为。

### 访问令牌

守护进程监听在 `127.0.0.1`，理论上本机任何程序都能调它。所以加了令牌校验：
令牌存在 `~/.claudepad/token`，由安装脚本写进 hook 配置的请求头。
令牌不对直接 403，Claude Code 会退化为正常询问。

### 审计日志

所有决策记录在 `~/.claudepad/approvals.jsonl`：

```
✅ 2026-09-14T19:40:12  Bash      allow   常规 shell 命令              git status
⏭️ 2026-09-14T19:40:15  Bash      skipped 危险命令特征: rm -rf          rm -rf /tmp/x
```

用 `python switchctl.py log` 查看。

---

## 卸载

```bash
python install_hook.py --uninstall --apply
```

会把 ClaudePad 的条目从 `settings.json` 移除，**保留你其他所有 hook 和设置**。

---

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 拨杆 ON 但仍弹审批 | 守护进程没跑 | 检查守护进程是否在运行 |
| 同上 | hook 没装上 | `python install_hook.py` 看预览，再 `--apply` |
| 同上 | 令牌不匹配 | 重跑 `install_hook.py --apply` 重新写入令牌 |
| 危险命令被拦下了 | **这是设计如此** | 危险命令不自动批，属预期行为 |
| 守护进程起不来 | 端口被占 | `--port 8788` 换端口，同时重装 hook 指定同一端口 |
| 键盘拨杆无反应 | 没装 pynput | `pip install pynput` |
| 键盘拨杆无反应 | F13 被拦截 | 换 F14/F15（改固件 + `claudepad_daemon.py` 的 `VK_F13`） |

---

## 关于「未在真实 Claude Code 上跑通」

本机没有安装 Claude Code CLI，所以验证是在**协议层**完成的：按官方文档构造 hook 的
输入 JSON、检查脚本的输出、验证失效路径。逻辑和协议格式都已确认，但
「Claude Code 真的会按文档所述处理这个响应」这一步没有实测。

接入真机后按上面的「快速开始」走一遍，第 4 步「不再询问」即验证通过。

详见 `docs/审批拨杆技术验证.md` §7。
