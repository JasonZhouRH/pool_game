# 2D 美式8球台球游戏

Python + pygame 实现的双人同屏美式8球。手写台球物理，物理/规则/渲染/输入分离。

## 环境

本机 Python 为 Homebrew 管理（externally-managed，PEP 668），需用虚拟环境。
官方 `pygame` 在 Python 3.14 上无预编译 wheel 且源码编译失败，故使用社区版 `pygame-ce`（导入名仍为 `pygame`）。

## 安装

```bash
cd pool_game
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

## 运行

```bash
venv/bin/python billiar_ball.py
```

## 操作

- **瞄准/击球**：在母球后方按住鼠标左键向后拉，拉得越远力度越大，松开击球。
- **自由球（对手犯规后）**：移动鼠标放置母球到合法位置，点击确定。
- **重新开始**：分出胜负后按 `R`。

## 规则要点（美式8球，不叫袋）

- 进球后继续打本方组别；未进本组球或犯规则交换。
- 犯规：母球落袋 / 母球未碰任何球 / 先碰错误组别 / 空杆（无进球且无球碰库）。犯规后对手获自由球。
- 清完本方组别后合法打进 8 号获胜；提前打进 8 号或打 8 号时母球落袋判负。

## 测试

```bash
cd ..
pool_game/venv/bin/python -m pytest pool_game/tests -v
```

纯逻辑模块（config/table/balls/physics/cue/rules）不依赖 pygame，可独立测试（共 129 个单元测试）。

## 架构

| 模块 | 职责 | 依赖 pygame |
|------|------|:-----------:|
| `config.py` | 常量（窗口/球台/物理参数/颜色） | 否 |
| `table.py` | 球台几何（袋口/球架/开球点） | 否 |
| `balls.py` | 球数据、分组、颜色、摆球 | 否 |
| `physics.py` | 物理逐帧推进，输出事件 | 否 |
| `cue.py` | 拉杆 → 击球向量 | 否 |
| `rules.py` | 8球判定（犯规/分组/胜负） | 否 |
| `renderer.py` | 绘制 | 是 |
| `billiar_ball.py` | 游戏循环 + 状态机（入口） | 是 |

物理引擎每帧返回事件列表（进袋/球碰/碰库），规则引擎消费事件做判定，二者互不计算对方领域。

## 后续里程碑

M2：旋转/加塞（跟杆、缩杆、侧旋）。Ball 已预留 `spin` 字段。
