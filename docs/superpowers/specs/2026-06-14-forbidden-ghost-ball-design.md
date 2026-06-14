# 非法首球时假想球（鬼球）显示禁止样式

## 背景

瞄准时，`renderer.draw_aim` 通过 `cue.predict_aim` 找到母球射线第一颗会撞上的球，并在接触点画出白色细圈"鬼球"，同时画出目标球去向路径。

当前无论瞄准的是哪颗球，鬼球样式都一样。玩家无法在出杆前直观看出自己瞄准的是否为合法首球（按美式8球规则）。

本功能：当瞄准的第一颗球不是合法首球时，把鬼球画成**红圈 + 对角斜杠**的禁止样式，提醒玩家这是犯规击球。

## 合法首球规则（复用 rules 现有判定）

合法性按当前实时游戏状态判定，与 `rules.evaluate_shot` 中的犯规判定保持一致：

- **开放球台**（尚未分组）：除 8 号外都合法；先碰 8 号非法。
- **打 8 阶段**（击球者已清完本组）：只有 8 号合法；碰其他球非法。
- **已分组**：只有本组球合法；对方组别球和 8 号非法。

注意：母球（0 号）不会作为首球被预测（`predict_aim` 跳过母球），无需特殊处理。

## 改动设计

### 1. `cue.py` — 预测带回球号

`AimPrediction` namedtuple **末尾**新增字段 `target_number: int`。
- 加在末尾，现有测试均按字段名访问，不受影响。
- `predict_aim` 返回时填入 `best_ball.number`。

### 2. `rules.py` — 抽出纯函数 `is_legal_first_contact`

新增：

```
def is_legal_first_contact(number, open_table, shooter_group, shooter_on_eight) -> bool
```

返回该球作为首个被母球碰到的球是否合法。把 `evaluate_shot` 中现有的首球合法性判断（开放台 / 打8 / 已分组三分支）改为调用此函数，消除重复逻辑，形成单一事实来源。`evaluate_shot` 对外行为不变。

### 3. `billiar_ball.py` — 把禁止判断传给渲染

`Game.draw` 在 `STATE_AIMING` 分支构造一个回调 `is_forbidden(number) -> bool`：

```
forbidden = lambda n: not rules.is_legal_first_contact(
    n, self.open_table, self.player_groups[self.current], self._shooter_on_eight())
```

传入 `renderer.draw_aim(..., is_forbidden=forbidden)`。

### 4. `renderer.py` — 画禁止样式

- `draw_aim` 新增可选参数 `is_forbidden=None`（`number→bool` 回调；为 None 时全部按合法处理，渲染层不直接依赖 rules）。
- `_draw_separation` 接收该回调与命中球号 `target_number`：
  - **合法**：维持现状——白色细圈鬼球（不变）。
  - **非法**：鬼球画成红圈（`COLOR_GHOST_FORBIDDEN`）+ 一条对角斜杠（禁止符）。
- 瞄准线、目标球去向路径**保持不变**（不隐藏、不变灰）。

`config.py` 新增颜色常量 `COLOR_GHOST_FORBIDDEN`（红色，建议 `(230, 60, 60)`）。

## 数据流

```
predict_aim  → AimPrediction(含 target_number)
                      │
Game.draw 构造 is_forbidden(n) ─┐
                      ▼         ▼
draw_aim(cue, aim_dir, balls, spin_v, is_forbidden)
                      │
              _draw_separation(pred, is_forbidden)
                      │
       合法 → 白色细圈      非法 → 红圈 + 斜杠
```

## 测试

- `tests/test_rules.py`：给 `is_legal_first_contact` 加单元测试，覆盖三种场景：
  - 开放球台：8 号非法、其它合法。
  - 已分组：本组合法、对方组非法、8 号非法。
  - 打 8 阶段：仅 8 号合法、其它非法。
- 验证 `evaluate_shot` 重构后现有测试全绿（36 个）。
- 渲染层（renderer）按项目惯例不写单元测试。

## 不做（YAGNI）

- 不改变出杆/犯规的实际判定逻辑（只是把已有逻辑抽成可复用函数）。
- 非法时不隐藏或变灰目标球路径。
- 不加音效、提示文字或其它反馈。
