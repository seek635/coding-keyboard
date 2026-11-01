# ClaudePad 上位机（Windows）

监听键盘发出的 `Ctrl+Alt+Shift+F15`（权限复位）、`Ctrl+Alt+Shift+F14`（模型循环）、`F16`（PERM 档位同步），并通过 Claude Code 的 hooks 与 statusLine 交换状态。

> 审批/自动批准功能已取消。Claude Code 的权限提示仍由人工回答，上位机不再返回 `allow`。

- 系统：Windows 10/11
- Python：3.10+（已在 3.12 测试）
- 依赖：无第三方包

## 安装与运行

```bash
cd host
python -m claudepad_host install
python -m claudepad_host run
```

安装器会：

1. 把 `core.py`、`statusline.py`、`hook_state.py` 复制到 `~/.claude/claudepad/`。
2. 备份 `~/.claude/settings.json`。
3. 在 `PermissionRequest`、`UserPromptSubmit`、`Stop`、`SessionStart` 上注册状态 hook（只写权限档位，不做决策）。
4. 把 `statusLine` 指向 ClaudePad 的状态栏脚本。
5. 可选 `--autostart`：在启动文件夹创建隐藏运行的 `.vbs`。

卸载：

```bash
python -m claudepad_host uninstall
```

会移除本项目的 hooks / statusLine，并恢复安装前的 statusLine；设置文件会先备份。

查看状态：

```bash
python -m claudepad_host status
```

## 工作流程

### 权限复位（PERM 长按）

1. 固件发 `Ctrl+Alt+Shift+F15`。
2. 守护进程读当前档位（来自 hooks 写入的 mode 文件）。
3. 按官方循环 `default → acceptEdits → plan → auto → default` 计算需要按几次 `Shift+Tab`。
4. 注入 `Shift+Tab`，然后写入 `default` 状态。

PERM 单击会先发 `Shift+Tab`，再补一个 `F16` 同步信号。守护进程收到 F16 后把档位前进一格，这样即使 Claude Code 不暴露当前档位，复位次数也能保持准确。若 F16 热键注册失败，仍会靠 `PermissionRequest` / `UserPromptSubmit` / `Stop` hooks 在触发时校正。

如果状态文件里还没有档位，会使用 `config.json` 的 `assume_mode`（默认 `auto`，即按 1 次回 default）。

### 模型循环（MODEL 长按）

1. 固件发 `Ctrl+Alt+Shift+F14`。
2. 守护进程从 statusLine 状态里读 `model.id` / `display_name`。
3. 在 `config.json` 的 `models` 列表里找下一个别名。
4. 发送 `/model <alias>` + Enter。

注意：`/model <alias>` 会同时把这个模型保存为**新会话默认模型**。

### statusLine

终端底部会显示：

```
ClaudePad | Opus | coding keyboard | 12% ctx
```

同时把模型、cwd、会话 ID 写进状态目录。

## 状态文件

`%LOCALAPPDATA%\ClaudePad\`：

| 文件 | 内容 |
|---|---|
| `config.json` | 模型列表、权限循环、假设档位 |
| `sessions/<id>.status.json` | statusLine 写入的模型、cwd |
| `sessions/<id>.mode.json` | hooks 写入的权限档位、cwd |
| `daemon.log` | 守护进程日志 |
| `hooks.log` | hook/statusLine 异常日志 |
| `install.json` | 安装器保存的旧 statusLine 信息 |

所有写入都是“临时文件 + `os.replace`”，不会读到半截 JSON。

## 配置

`%LOCALAPPDATA%\ClaudePad\config.json`：

```json
{
  "models": ["opus", "sonnet", "haiku"],
  "permission_cycle": ["default", "acceptEdits", "plan", "auto"],
  "assume_mode": "auto"
}
```

- 如果会话启用了 `bypassPermissions`，按实际顺序加入 `permission_cycle`，例如
  `["default", "acceptEdits", "plan", "bypassPermissions", "auto"]`。
- 修改后重启 `python -m claudepad_host run`。

## 限制

- 注入按键发送到当前前台窗口；触发复位/模型循环时请保持 Claude Code 终端聚焦。
- 多会话时上位机选择“最近更新的会话”。
- 用普通键盘按 `Shift+Tab` 改档位不会发 `F16`，上位机的档位可能短暂过期；下一次 `PermissionRequest` / `UserPromptSubmit` / `Stop` hook 会用真实档位校正。用 ClaudePad 的 PERM 键换档则会即时同步。
- 更新本项目代码后，重新运行 `python -m claudepad_host install` 以刷新复制到 `~/.claude/claudepad/` 的脚本。
- 由于取消了电源开关，键盘依靠 ZMK 深度睡眠省电；长期存放时请拔掉 JST 电池插头。

## 排错

| 现象 | 检查 |
|---|---|
| PERM 长按后档位不对 | `config.json` 的 `permission_cycle` 是否与实际一致；终端是否在前台；`status` 里 `permission_mode` 是否过期（用 PERM 键换档可即时同步） |
| MODEL 长按无反应 | 当前模型是否在 `models` 列表里（不在则从第一个开始）；终端是否在前台 |
| statusLine 不显示 | 手动运行 `python "~/.claude/claudepad/statusline.py"` 并喂一段 JSON；检查 `settings.json` 的 `statusLine.command` |
| 热键没反应 | 是否有其他程序占用了 F14/F15/F16；`daemon.log` 会写 fallback；按 `Ctrl+Alt+Shift+F15` 时确保终端聚焦 |
| 中文用户名/路径问题 | hooks 使用 exec 形式，不经过 shell；statusLine 命令已加引号 |

## 手动验收清单

1. `python -m claudepad_host status` 能显示当前会话的模型与权限档位。
2. PERM 单击循环档位，`status` 里的 `permission_mode` 跟随变化。
3. PERM 长按后，终端权限档位回到 Manual/default。
4. MODEL 长按，模型切到列表中的下一个。
5. STOP 单击打断、双击 `Ctrl+C`、长按 1.2 秒退出。
6. ENTER 双击换行（`Shift+Enter`）。
7. SPACE 长按在输入框内不应误触 Tab；在其他键后快速按空格应输出空格。
8. VOICE 按住对讲，双击发送 `/voice`。
9. 关闭终端/守护进程后，键盘仍能正常输入（固件不依赖上位机）。
