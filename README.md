# 轻便签

一个 Windows 桌面悬浮便签：永远浮在最上层，随手记一笔，带待办勾选。绿色轻量，装好就一个图标。

[**⬇ 下载最新版**](../../releases/latest)

---

## 它长什么样

一个无边框的小窗，贴在屏幕角落，不挡事也不碍眼：

```
┌────────────────────────────┐
│ ● 今日待办        ▼  —  ✕  ⋮ │
├────────────────────────────┤
│  1  2  +                    │
│                             │
│  ☐ 检查 K8s 节点状态         │
│  ☑ 备份 etcd 快照            │
│  ☐ 写周报                    │
│                             │
│  随手记：RocketMQ 消费堆积，  │
│  原因是消费者组没订阅新 topic │
├────────────────────────────┤
│ 3 项待办 · 完成 1     58 字  │
└────────────────────────────┘
```

## 装起来

下载 [Releases](../../releases/latest) 里的 `StickyNotes-v1.0.0-win64.zip`，解压后二选一：

| 方式 | 做法 | 适合 |
| --- | --- | --- |
| **安装** | 双击 `安装.bat` | 装到 `%LOCALAPPDATA%\StickyNotes`，自动建桌面图标、设开机自启 |
| **绿色** | 直接双击 `轻便签.exe` | 放哪都能跑，数据存在 exe 同级的 `data` 目录 |

卸载跑同目录的 `卸载.bat`，会问你要不要保留便签内容。

系统要求：Windows 10 / 11 x64，**不需要装 Python 或任何运行时**。

## 能干什么

- **真·悬浮**：无边框、置顶、半透明，能看见底下的内容
- **待办勾选**：点行首方框就勾上，完成的行自动变灰划掉，底部实时统计
- **随手记**：正文区想写什么写什么，和待办混排也认
- **多张便签**：顶部数字切换，`+` 新建，右键改名/删除
- **两种收起**：`▼` 折叠成一条（只剩标题栏），`—` 最小化到任务栏
- **换皮**：5 套配色（奶黄/薄荷/淡蓝/淡粉/夜间）、字号、透明度随便调
- **自动保存**：改完 0.7 秒落盘，关掉也不丢

## 快捷键

| 操作 | 快捷键 |
| --- | --- |
| 新建便签 | `Ctrl+N` |
| 当前行变待办 | `Ctrl+D` |
| 调字号 | `Ctrl` + `+` / `-`，或 `Ctrl` + 滚轮 |
| 立即保存 | `Ctrl+S` |
| 折叠 / 展开 | 双击标题栏 |

## 数据在哪

`data/notes.json`，纯文本，人眼可读。不联网、不上传、不留后门。

安装版在 `%LOCALAPPDATA%\StickyNotes\data\`，绿色版在 exe 同级 `data\`。

## 自己构建

需要 Python 3.9+。

```bash
pip install pyinstaller pillow
python tools/make_icon.py
pyinstaller --noconfirm --onedir --windowed --name StickyNotes \
  --icon assets/note.ico --add-data "assets/note.ico;." src/sticky.py
python tools/package.py v1.0.0
```

产物在 `release/`。推 tag 或往 `main` 提交时，GitHub Actions 会自动构建并更新 Release。

> **注意**：必须用 `--onedir`。`--onefile` + `--windowed` 在部分环境（如 200% 缩放的多显示器机器）会导致 tkinter 窗口压根不出现——进程活着、窗口不存在，很难查。

## 一些实现细节

- 用系统级拖动（`WM_NCLBUTTONDOWN`）搬窗口，而不是每帧 `geometry()`，否则高 DPI 下半透明窗口会撕裂
- 去边框靠 `SetWindowLongPtrW` 摘掉 `WS_CAPTION`，保留 `WS_MINIMIZEBOX`，这样任务栏有按钮也能最小化（`overrideredirect` 做不到）
- tk 会在窗口显示后把样式改回去，所以得在 `after(200)` 和 `<Map>` 里重复应用
- 所有尺寸按 `winfo_fpixels('1i')/96` 换算，适配任意 DPI 缩放

## License

[MIT](LICENSE)
