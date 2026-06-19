import config


def test_window_and_table_are_consistent():
    assert config.WINDOW_WIDTH > 0 and config.WINDOW_HEIGHT > 0
    # 球台在窗口内且为横向长方形
    assert 0 < config.TABLE_LEFT < config.TABLE_RIGHT < config.WINDOW_WIDTH
    assert 0 < config.TABLE_TOP < config.TABLE_BOTTOM < config.WINDOW_HEIGHT
    assert (config.TABLE_RIGHT - config.TABLE_LEFT) > (config.TABLE_BOTTOM - config.TABLE_TOP)


def test_physics_params_in_sane_ranges():
    assert 0 < config.FRICTION < 1
    assert 0 < config.CUSHION_RESTITUTION <= 1
    assert 0 < config.BALL_RESTITUTION <= 1
    assert config.SUBSTEPS >= 1
    # 每个 substep 的最大位移要小于球直径，避免穿模
    assert config.MAX_SHOT_SPEED / config.SUBSTEPS < 2 * config.BALL_RADIUS


def test_ball_radius_smaller_than_pocket():
    assert config.BALL_RADIUS < config.POCKET_RADIUS


def test_spin_control_constants_present_and_sane():
    # 杆法图标与放大面板在窗口内、半径为正
    assert 0 < config.SPIN_ICON_R < config.SPIN_PANEL_R
    assert 0 < config.SPIN_ICON_X < config.WINDOW_WIDTH
    assert 0 < config.SPIN_ICON_Y < config.WINDOW_HEIGHT
    assert 0 < config.SPIN_PANEL_X < config.WINDOW_WIDTH
    assert 0 < config.SPIN_PANEL_Y < config.WINDOW_HEIGHT
    assert 0 < config.SPIN_DOT_R < config.SPIN_PANEL_R
    # 图标整体在球台上沿之上的背景带，不压球台
    assert config.SPIN_ICON_Y + config.SPIN_ICON_R < config.TABLE_TOP
    assert config.SPIN_PANEL_Y + config.SPIN_PANEL_R < config.TABLE_TOP
    # 物理强度为正且温和
    assert 0 < config.FOLLOW_DRAW_STRENGTH <= 1.5
    assert 0 < config.SIDE_ENGLISH_STRENGTH <= 1.0


def test_shot_clock_constants_present_and_sane():
    # 出杆计时器：45 秒，派生帧数 = 秒数 * FPS
    assert config.SHOT_CLOCK_SECONDS == 45
    assert config.SHOT_CLOCK_FRAMES == config.SHOT_CLOCK_SECONDS * config.FPS
    # 低于此剩余秒数 HUD 变红预警
    assert 0 < config.SHOT_CLOCK_WARN_SECONDS < config.SHOT_CLOCK_SECONDS


def test_menu_constants_present_and_sane():
    # 文案
    assert isinstance(config.MENU_TITLE, str) and config.MENU_TITLE
    # 按钮尺寸为正、按钮整体落在窗口内
    assert config.MENU_BTN_W > 0 and config.MENU_BTN_H > 0
    assert config.MENU_BTN_W <= config.WINDOW_WIDTH
    assert 0 < config.MENU_BTN_CY < config.WINDOW_HEIGHT
    assert config.MENU_BTN_CY + config.MENU_BTN_H // 2 <= config.WINDOW_HEIGHT
    # 遮罩为带 alpha 的 RGBA，其余为 RGB
    assert len(config.COLOR_MENU_OVERLAY) == 4 and 0 <= config.COLOR_MENU_OVERLAY[3] <= 255
    assert len(config.COLOR_MENU_BTN) == 3
    assert len(config.COLOR_MENU_BTN_TEXT) == 3
    assert len(config.COLOR_MENU_TITLE) == 3
    # 三按钮布局 + 提示
    assert config.MENU_BTN_GAP >= 0
    assert config.MENU_HINT_SECONDS > 0
    assert len(config.COLOR_MENU_HINT) == 3
