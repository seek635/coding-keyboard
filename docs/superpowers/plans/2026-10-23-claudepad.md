# ClaudePad Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Ship a working ZMK shield and a Windows companion daemon for ClaudePad.

**Architecture:** ZMK devicetree-only shield implements key behaviors; a zero-dependency Python daemon listens for F14/F15/F16 and injects keystrokes, while Claude Code hooks exchange state through JSON files in `%LOCALAPPDATA%\ClaudePad`.

**Tech Stack:** ZMK / devicetree / GitHub Actions; Python 3.12 stdlib + ctypes; Claude Code hooks + statusLine.

**Spec:** `docs/superpowers/specs/2026-10-23-claudepad-design.md`

**Status:** Implemented inline on 2026-10-23. Main controller switched to Seeed XIAO nRF52840 (`xiao_ble`) because it has a physical RESET button. Verification: 15 unit tests pass, `tools/check_firmware.py` reports OK, hooks/statusline and daemon startup smoke-tested. Firmware compilation must still be confirmed by GitHub Actions.

**Change log 2026-10-25:** The approval lever, F13 auto-approve and power switch were removed at the user's request. The shield is now 11 keys / 11 diodes, the battery uses a JST pigtail, and the host no longer installs `hook_permission.py`. Details below that mention 11 positions, F13, `auto_approve`, or `hook_permission.py` are historical.

**Hardware addendum 2026-10-25:** A 4-layer 90×76mm KiCad PCB (`pcb/`) and a 3D-printed case/plate/keycap set (`cad/`) were added. PCB DRC: 0 violations / 0 unconnected. STL check: all six parts closed, 0 non-manifold edges. See `docs/pcb.md` and `docs/cad.md`.

**Change log 2026-10-26:** XIAO switched from SMD edge pads to **2×7 2.54mm through-hole headers** (14 × 1.0mm holes at the official Seeed DIP positions; header pins trimmed to ≤4mm after soldering); the battery window was removed and BAT1 moved beside the JST (x=70, y=17.5/19.5); the case USB-C slot/recess was raised to z≈10.5–14.3 for the 2.5mm header height. Diodes remain in the open bands between switch rows. Fresh DRC 0/0, BOM, 3D, renders, case STL and a JLCPCB-only Gerber zip were generated.

## Global Constraints

- 3×5 matrix: rows `xiao_d 0/1/2`, cols `xiao_d 6/7/8/9/10`; 11 used intersections.
- Toggle holds `F13`; reset signal `Ctrl+Alt+Shift+F15`; model signal `Ctrl+Alt+Shift+F14`. (Historical: the F13 toggle was removed on 2026-10-25; no auto-approve.)
- 12 keymap positions in the order defined in the spec.
- Python standard library only; no third-party runtime dependencies.
- All state writes are atomic (`temp` + `os.replace`).
- Do not restore or use the old CAD files in the recycle bin.
- No git repository exists; do not initialize one. Verification replaces commit steps.

## File Map

| Path | Responsibility |
|---|---|
| `build.yaml` | `xiao_ble` + `claudepad` build matrix |
| `.github/workflows/build.yml` | ZMK reusable build workflow |
| `config/west.yml` | ZMK manifest |
| `config/boards/shields/claudepad/claudepad.overlay` | kscan, transform, physical layout |
| `config/boards/shields/claudepad/claudepad.keymap` | behaviors, macros, keymap |
| `config/boards/shields/claudepad/claudepad.conf` | ZMK options |
| `config/boards/shields/claudepad/Kconfig.shield` | shield symbol |
| `config/boards/shields/claudepad/Kconfig.defconfig` | keyboard name |
| `host/claudepad_host/core.py` | paths, state, cycle/model logic |
| `host/claudepad_host/winapi.py` | SendInput / hotkeys / toggle / mutex |
| `host/claudepad_host/actions.py` | reset permissions, cycle model |
| `host/claudepad_host/daemon.py` | main loop |
| `host/claudepad_host/installer.py` | settings merge / install / uninstall |
| `host/claudepad_host/__main__.py` | CLI |
| `host/scripts/statusline.py` | statusLine writer |
| `host/scripts/hook_state.py` | mode/cwd state writer |
| `host/tests/test_core.py` | cycle/model/state tests |
| `host/tests/test_installer.py` | settings merge tests |
| `host/run.bat` | run daemon |
| `host/install.bat` | install hooks |
| `README.md` | project overview |
| `docs/wiring.md` | hand-wiring guide |
| `docs/keymap.md` | behavior reference |
| `host/README.md` | host usage/troubleshooting |
| `pcb/claudepad.kicad_pcb` | 4-layer PCB (90×76mm) |
| `pcb/output/gerbers/` | Gerber / drill / job files |
| `cad/params.scad` | PCB/case shared dimensions |
| `cad/output/stl/` | case, plate, keycaps, test coupon |

---

### Task 1: ZMK skeleton and shield overlay

**Files:**
- Create: `build.yaml`
- Create: `.github/workflows/build.yml`
- Create: `config/west.yml`
- Create: `config/boards/shields/claudepad/claudepad.overlay`
- Create: `config/boards/shields/claudepad/Kconfig.shield`
- Create: `config/boards/shields/claudepad/Kconfig.defconfig`
- Create: `config/boards/shields/claudepad/claudepad.conf`

**Interfaces:**
- Produces: kscan node `kscan0`, transform `default_transform`, physical layout `claudepad_layout`, 11 positions.

- [x] **Step 1: Write the overlay**

```dts
/* includes + chosen + transform + kscan + physical layout as in the spec */
```

- [x] **Step 2: Write shield Kconfig**

```kconfig
config SHIELD_CLAUDEPAD
    def_bool $(shields_list_contains,claudepad)
```

- [x] **Step 3: Write build files**

```yaml
# build.yaml
include:
  - board: xiao_ble
    shield: claudepad
```

- [x] **Step 4: Static check**

Run: `grep` for all 11 `RC(...)` entries and verify no duplicate rows/cols beyond the intended 11 points.

### Task 2: Keymap

**Files:**
- Create: `config/boards/shields/claudepad/claudepad.keymap`

**Interfaces:**
- Consumes: 11-position transform from Task 1.
- Produces: behaviors `perm_ht`, `model_ht`, `cmd_ht`, `space_ht`, `stop_td`, `enter_td`, `voice_td`; macros `mac_model`, `mac_voice`, `mac_stop_exit`.

- [x] **Step 1: Define macros**

```dts
mac_model: mac_model { compatible = "zmk,behavior-macro-one-param"; #binding-cells = <1>;
  wait-ms = <15>; tap-ms = <10>;
  bindings = <&kp SLASH>, <&kp M>, <&kp O>, <&kp D>, <&kp E>, <&kp L>, <&kp ENTER>; };
```

- [x] **Step 2: Define hold-taps and tap-dances** with the exact timing table.

- [x] **Step 3: Write 11-binding keymap** in the spec's position order.

- [x] **Step 4: Static check** that every `&label` referenced exists.

### Task 3: Host core and tests (TDD)

**Files:**
- Create: `host/claudepad_host/__init__.py`
- Create: `host/claudepad_host/core.py`
- Create: `host/tests/test_core.py`

**Interfaces:**
- `state_dir() -> Path`
- `read_json(path, default) -> dict`
- `write_json(path, data) -> None`
- `session_status_path(session_id) -> Path`
- `session_mode_path(session_id) -> Path`
- `write_status(payload) -> None`
- `write_mode(payload) -> None`
- `read_active_state() -> dict`
- `presses_to_default(current, cycle) -> int`
- `next_model(state_model_id, state_model_name, models) -> str`
- `auto_approve_enabled(now=None) -> bool`

- [x] **Step 1: Write failing tests** for presses (auto→1, plan→2, acceptEdits→3, default→0), model matching, active-session merge, heartbeat freshness.
- [x] **Step 2: Run tests; expect import/attribute failures.**
- [x] **Step 3: Implement core.**
- [x] **Step 4: Run tests; expect PASS.**
- [x] **Step 5: Verification instead of commit** (`python -m unittest ...`).

### Task 4: Windows input and daemon

**Files:**
- Create: `host/claudepad_host/winapi.py`
- Create: `host/claudepad_host/actions.py`
- Create: `host/claudepad_host/daemon.py`
- Create: `host/claudepad_host/__main__.py`

**Interfaces:**
- `class Injector`: `tap(vk)`, `combo(mods, vk)`, `type_text(text)`.
- `reset_permissions(injector, state) -> int`
- `cycle_model(injector, state) -> str`
- `run() -> int`, `status() -> int`

- [x] **Step 1: Implement `SendInput` structures and helpers.**
- [x] **Step 2: Implement hotkey registration + F13 polling fallback.**
- [x] **Step 3: Implement actions and optimistic state writes.**
- [x] **Step 4: Implement heartbeat, single-instance mutex, logging, shutdown.**
- [x] **Step 5: Smoke test** `python -m claudepad_host status` and `--help`.

### Task 5: Hooks and statusline

**Files:**
- Create: `host/scripts/statusline.py`
- Create: `host/scripts/hook_permission.py`
- Create: `host/scripts/hook_state.py`

**Interfaces:**
- Each script does `sys.path.insert(0, dirname(__file__)); from claudepad_core import ...`.
- `hook_permission.py` prints the allow JSON only when `auto_approve_enabled()`.
- `statusline.py` prints one status line and never raises.

- [x] **Step 1: Implement statusline writer.**
- [x] **Step 2: Implement state hook.**
- [x] **Step 3: Implement permission hook.**
- [x] **Step 4: Pipe sample JSON** through each script and verify exit 0/output.

### Task 6: Installer

**Files:**
- Create: `host/claudepad_host/installer.py`
- Create: `host/tests/test_installer.py`
- Create: `host/install.bat`, `host/run.bat`

**Interfaces:**
- `merge_settings(settings: dict, python_exe: str, scripts_dir: str) -> dict`
- `install(settings_path=None, scripts_dir=None, autostart=False) -> int`
- `uninstall(settings_path=None) -> int`

- [x] **Step 1: Write failing merge tests** (preserve unrelated hooks, replace our entries, idempotent, restore statusline).
- [x] **Step 2: Implement merge.**
- [x] **Step 3: Implement file copying, backup, autostart, uninstall.**
- [x] **Step 4: Run tests; PASS.**

### Task 7: Docs and final verification

**Files:**
- Create: `README.md`
- Create: `docs/wiring.md`
- Create: `docs/keymap.md`
- Create: `host/README.md`

- [x] **Step 1: Write wiring guide** matching `docs/BOM.md`.
- [x] **Step 2: Write behavior/configuration reference.**
- [x] **Step 3: Run all unit tests.**
- [x] **Step 4: Run import checks** for every Python module.
- [x] **Step 5: Sanity-check devicetree positions and macro references.**
