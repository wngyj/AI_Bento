# AI_Bento 🐋

AI_Bento 是以 DeepSeek V4 Pro 二创形象「鲸鱼娘·大肥鱼」为主角的透明桌面宠物。

基于三视图素材（正面 / 侧面 / 背面），使用 **Python + PySide6** 实现的无边框透明置顶窗口。大肥鱼会在桌面上散步、蹦跳、吐泡泡，还能显示 DeepSeek 余额与 Codex 剩余用量、陪你聊天、播报天气。

## ✨ 功能亮点

- **三视图行走**：左右走用侧面（自动镜像）、向上走用背面、向下走用正面，转向带交叉淡化
- **脚下显示对象**：可同时显示 DeepSeek 账户余额与 Codex 剩余用量
- **中键对话**：鼠标中键单击即可与桌宠聊天（DeepSeek API）
- **三种模式**：自由散步 / 跟随鼠标 / 原地待着
- **丰富互动**：拖拽、单击回嘴、双击喂食、右键菜单、托盘控制
- **天气 & 系统监控**：气泡播报天气，CPU / 内存 / GPU 过载提醒
- **可打包 exe**：内置 PyInstaller 配置，一键打成单文件独立程序

## 🎮 互动操作

| 操作 | 效果 |
| --- | --- |
| 左键按住 | 拖拽（侧身朝向拖动方向，松手会说话） |
| 左键单击 | 蹦跳 + 回嘴 + 手动刷新余额 |
| 中键单击 | 与桌宠对话（弹出聊天输入框） |
| 单击 Codex 用量标签 | 切换显示 5 小时 / 一周剩余用量 |
| 中键单击 Codex 用量标签 | 独立详情窗口显示 5 小时与一周的剩余比例、重置倒计时 |
| 双击 | 喂食面板（小鱼干 / 蛋糕 / 棒棒糖 / 团子 / 钻石） |
| 右键 | 完整菜单（模式 / 大小 / 余额显示对象 / 设置 Key / 查看天气 / 显示隐藏 / 回到屏幕内 / 鼠标穿透 / 窗口置顶 / 开机自启 / 退出） |
| 托盘左键 | 显示 / 隐藏 |
| 托盘右键 | 同款完整菜单（鼠标穿透后可用托盘恢复交互） |

## 💰 余额显示

- 鱼脚边**常驻余额标签**，数据来自 DeepSeek 官方接口 `GET https://api.deepseek.com/user/balance`（取 `balance_infos[0]` 的 `total_balance` + `currency`）
- **每 30 秒自动静默刷新**，不打断其他互动；左键单击可手动刷新（标签短暂显示「余额刷新中…」）
- **时段颜色提示**：余额标签背景色随时段变化——每天 9:00–12:00、14:00–18:00 为高峰，红底；其余时间为低谷，绿底；标签文字只显示余额。
- 错误提示：Key 无效 / 余额不足 / 超时 / 网络失败都会在标签和气泡中给出
- 功能移植自 [DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget)

## 🤖 Codex 剩余用量

- 读取本机 Codex 会话日志中的限额窗口；不读取会话正文，不发送任何数据，也不需要额外 Key。
- 右键「余额显示对象」可独立勾选 **DeepSeek 余额**、**Codex 剩余用量**，两项可以同时显示。
- Codex 标签左键切换 5 小时 / 一周的剩余比例；中键显示两个窗口的重置倒计时。
- 用量每分钟从本机日志静默刷新。首次使用前，先完成一次 Codex 对话以生成限额记录。
- 解析逻辑参考 [Corread8/codex-usage-monitor](https://github.com/Corread8/codex-usage-monitor)（MIT）。

## 💬 AI 对话

- **鼠标中键单击**弹出聊天输入框
- 调用 DeepSeek API（`deepseek-chat` 模型），每句话不超过 25 字，风格贱兮兮但可爱
- 对话历史保留最近 40 条（自动记忆上下文）
- 聊天期间鱼会暂停移动，但呼吸 / 摇摆 / 小动作照常

## 🌦️ 天气查询

- 右键菜单「查看天气」→ 调用 `wttr.in` 获取当前城市天气，气泡播报
- 城市默认从 `config.json` 读取，可手动修改 `"city"` 字段

## 🖥️ 系统状态监控

- **CPU**：超过 90% 时冒泡提醒
- **内存**：超过 95% 时冒泡提醒
- **显卡（NVIDIA）**：温度超过 80°C 时冒泡提醒
- 检测间隔 10 秒，不频繁打扰

## 🚀 运行

需要 **Python 3.11+**。

```bash
pip install -r requirements.txt
python 桌宠.py
```

或直接双击 `启动桌宠.bat`（自动使用 `.venv` 或系统 Python）。

首次运行请右键桌宠 → **设置 Key**，输入 DeepSeek API Key（在 [platform.deepseek.com](https://platform.deepseek.com) 获取）。Key 保存在本地 `config.json`（已加入 `.gitignore`，不会提交到仓库）。

## 📦 打包成独立 exe

```bash
pip install pyinstaller
pyinstaller --noconfirm 桌宠.spec
```

产物在 `dist/桌宠.exe`（单文件、免安装 Python，双击即用）。

> 杀毒软件可能对 PyInstaller 产物误报，加信任即可。

## 📁 项目结构

| 文件 | 说明 |
| --- | --- |
| `桌宠.py` | 主程序（全部逻辑） |
| `桌宠.spec` | PyInstaller 打包配置（含依赖收集） |
| `启动桌宠.bat` | 一键启动脚本 |
| `requirements.txt` | Python 依赖 |
| `sprites/` | 三视图精灵图（正面 / 侧面 / 背面各尺寸 + 图标） |
| `icon.ico` | 程序 / 托盘图标 |
| `preprocess.py` | 白底三视图抠图脚本 |
| `preprocess2.py` | 精灵边缘去污 + 多尺寸生成脚本 |
| `config.json` | 本地配置（运行后自动生成，不入仓库） |

## ⚙️ 配置说明

`config.json` 字段：

| 字段 | 说明 | 默认值 |
| --- | --- | --- |
| `mode` | 模式：`wander` / `follow` / `still` | `wander` |
| `size` | 大小倍率 | `0.7` |
| `topmost` | 窗口置顶 | `true` |
| `passthrough` | 鼠标穿透 | `false` |
| `autostart` | 开机自启 | `false` |
| `x` / `y` | 窗口位置（退出时记忆） | 屏幕右下角 |
| `ds_api_key` | DeepSeek API Key | 空 |
| `city` | 天气查询城市 | `汕头` |
| `display_objects` | 脚下显示对象，可包含 `deepseek_balance` / `codex_usage` | 两项均显示 |
| `codex_usage_view` | Codex 标签当前显示窗口：`primary`（5 小时）/ `secondary`（一周） | `primary` |

所有设置（Key / 模式 / 大小 / 城市 / 穿透 / 置顶 / 自启）修改后**立即保存**到 `config.json`，无需退出程序，非正常关闭也不会丢失。

## 🎨 更换形象

把新的三视图（白底）放到程序目录：

1. 准备 `正面.png` / `侧面.png` / `背面.png`（原图）
2. 运行 `python preprocess.py` —— 白底抠图 + 统一高度
3. 运行 `python preprocess2.py` —— 边缘去污 + 预乘 alpha 缩放出各尺寸精灵

## 🤝 致谢

- **AI 对话 / 天气查询 / 系统监控 / PyInstaller 打包配置**：由 [Cpanoe](https://github.com/Cpanoe) 通过 [PR#3](https://github.com/1190fasheqi/dafeiyu-pet/pull/3) 贡献
- **桌面宠物朝向修复**：由 [B-A-A-GE](https://github.com/B-A-A-GE) 通过 [PR#1](https://github.com/1190fasheqi/dafeiyu-pet/pull/1) 提交
- **余额显示功能**：移植自 [MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget)
- **Codex 用量读取逻辑**：参考 [Corread8/codex-usage-monitor](https://github.com/Corread8/codex-usage-monitor)（MIT）

## 📄 开源协议

本项目以 [MIT License](LICENSE) 开源。
