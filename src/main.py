# -*- coding: utf-8 -*-
import pygame
import sys
import os
import random
import math

pygame.init()

SCREEN_W = 640
SCREEN_H = 480
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()

# ---------------------------------------------------------
# ★ 調整可能な定数（演出パラメータ）
# ---------------------------------------------------------
FIXED_FPS = 60

# バトルメインウィンドウ（旧：黒帯）
BATTLE_MAIN_WINDOW_HEIGHT = 400
BATTLE_MAIN_WINDOW_ANIM_FRAMES = 10   # バトルメインウィンドウが開ききるまでのフレーム数

# ヒロイン演出パラメータ
BATTLE_HEROINE_FIRST_SCALE = 3.6    # 登場時の画像高さ（画面高さの何倍）
BATTLE_HEROINE_LAST_SCALE  = 1.2    # ズームアウト後の画像高さ（画面高さの何倍）
BATTLE_HEROINE_FIRST_FOCUS = 0.10   # 注視点：下端から高さの何倍の位置を画面中央に合わせるか

# バトルウィンドウが開いた後の静止 → ズームアウト
BATTLE_HEROINE_FOCUS_DELAY_FRAMES = 5  # 静止フレーム数
BATTLE_HEROINE_ZOOMOUT_FRAMES = 60      # ズームアウトに要するフレーム数
BATTLE_HEROINE_ZOOMOUT_ANCHOR = 0.625   # ヒロイン下端から高さの何倍がバトルウィンドウ下端に来るか

# バトルウィンドウ色
BATTLE_WINDOW_COLOR = (30, 80, 200)  # バトル中のウィンドウ色
RESULT_WINDOW_COLOR = (0, 0, 0)      # リザルト到達後のウィンドウ色

# リザルト演出
BATTLE_FLASHOUT_FRAMES    = 30  # バトルウィンドウが黒→白にフラッシュアウトするフレーム数
RESULT_WHITE_DELAY_FRAMES = 30  # 白ウィンドウ静止フレーム数
RESULT_SLIDEIN_FRAMES     = 30  # バストショットのスライドイン所要フレーム数
RESULT_TEXT_FRAMES_PER_CHAR = 10  # 勝利メッセージ1文字追加するのに要するフレーム数
RESULT_TEXT_DELAY_FRAMES   = 30  # スライドイン完了後、テキスト・ボイス開始までの待機フレーム数
RESULT_WIN_BGM_START_SEC   = 148.0  # 勝利演出開始時にbattle.mp3を再生開始する秒数

# 音量
BGM_BATTLE_VOLUME = 0.5  # バトルBGM音量（0.0～1.0）
VOICE_WIN_VOLUME  = 1.0  # 勝利ボイス音量（0.0～1.0）

# ズームアウト後の待機モーション（縦横逆位相スクワッシュ）
BATTLE_HEROINE_IDLE_PERIOD_FRAMES = 30  # 拡縮1周期のフレーム数
BATTLE_HEROINE_IDLE_SCALE_DELTA   = 0.02  # 縦横スケールの振れ幅（1.0 ± DELTA）

# ---------------------------------------------------------
# ゲーム状態
# ---------------------------------------------------------
STATE_FIELD = 0
STATE_BATTLE = 1
STATE_RESULT = 2
game_state = STATE_FIELD

battle_anim_frame = 0
heroine_focus_delay_frame = 0
heroine_zoomout_frame = 0
heroine_idle_frame       = 0
battle_flashout_frame    = 0
result_white_delay_frame = 0
result_slidein_frame     = 0
result_text_delay_frame  = 0
result_text_frame        = 0

# ----------------------------------------------------------
# フォント
# ----------------------------------------------------------
RESULT_TEXT_FONT_SIZE = 32  # リザルトセリフのフォントサイズ

font           = pygame.font.SysFont(None, 24)
font_result    = pygame.font.Font('C:/Windows/Fonts/meiryo.ttc', RESULT_TEXT_FONT_SIZE)

# ---------------------------------------------------------
# ズーム設定
# ---------------------------------------------------------
ZOOM_MIN = 0.5
ZOOM_MAX = 2.0
ZOOM_STEP = 0.1
zoom = 1.0

# ---------------------------------------------------------
# カメラオフセット
# ---------------------------------------------------------
CAMERA_Y_OFFSET_M = -0.25

# ---------------------------------------------------------
# コライダ設定
# ---------------------------------------------------------
PLAYER_COLLIDER_RADIUS = 0.25

# ---------------------------------------------------------
# ワールドスケール
# ---------------------------------------------------------
METER_TO_PIXEL = 64
CHARACTER_HEIGHT_M = 2.0
TILE_SIZE_M = 2.0

def character_height_px():
    return int(CHARACTER_HEIGHT_M * METER_TO_PIXEL * zoom)

def tile_size_px():
    return int(TILE_SIZE_M * METER_TO_PIXEL * zoom)

# ---------------------------------------------------------
# ワールド座標
# ---------------------------------------------------------
player_world_x = 0.0
player_world_y = 0.0

camera_world_x = 0.0
camera_world_y = 10.0

# ---------------------------------------------------------
# キャラ移動速度
# ---------------------------------------------------------
player_speed_mps = 2.0
player_speed = player_speed_mps / FIXED_FPS

# ---------------------------------------------------------
# タイルマップ
# ---------------------------------------------------------
TILE_MIN = -16
TILE_MAX = 16

TILE_TYPES = {
    "grass": (80, 200, 80),
    "sand": (210, 180, 80),
    "forest": (20, 120, 20),
    "mountain": (120, 120, 120),
}
TILE_LIST = list(TILE_TYPES.values())

tile_map = {}

# ---------------------------------------------------------
# キャラ画像読み込み
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WALK_DIR = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "bunny", "bunny_walk")
BACK_IMG_PATH = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "bunny", "bunny_back.png")
WIN_IMG_PATH  = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "bunny", "bunny_win.png")
VOICE_WIN_PATH  = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "bunny_win.mp3")
BGM_BATTLE_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "bgms", "battle.mp3")

def load_walk_images():
    files = [f for f in os.listdir(WALK_DIR)
             if f.lower().endswith(".png") and f.startswith("bunny_walk_")]

    def sort_key(fname):
        return int(os.path.splitext(fname)[0].split("_")[-1])

    files.sort(key=sort_key)

    images = []
    for fname in files:
        img = pygame.image.load(os.path.join(WALK_DIR, fname)).convert_alpha()
        w, h = img.get_size()
        scale = character_height_px() / h
        img = pygame.transform.smoothscale(img, (int(w * scale), character_height_px()))
        images.append(img)

    return images

walk_images = []
frame_index = 0
frame_timer = 0
FRAME_INTERVAL = 1
last_image = None

battle_back_img     = None  # 後ろ姿画像（スケール後）
battle_back_img_raw = None  # 後ろ姿画像（オリジナル）
result_win_img      = None  # 勝利バストショット画像（スケール後）
result_win_img_raw  = None  # 勝利バストショット画像（オリジナル）
voice_win           = None  # 勝利ボイス

# ---------------------------------------------------------
# ワールド座標 → スクリーン座標
# ---------------------------------------------------------
def world_to_screen(wx, wy):
    sx = (wx - camera_world_x) * METER_TO_PIXEL * zoom + SCREEN_W // 2
    sy = (wy - camera_world_y) * METER_TO_PIXEL * zoom + SCREEN_H // 2
    return int(sx), int(sy)

# ---------------------------------------------------------
# 周囲に山があるか
# ---------------------------------------------------------
def is_near_mountain(px, py):
    mx = math.floor(px / TILE_SIZE_M)
    my = math.floor(py / TILE_SIZE_M)

    for ty in range(my - 1, my + 2):
        for tx in range(mx - 1, mx + 2):
            if (tx, ty) in tile_map:
                if tile_map[(tx, ty)] == TILE_TYPES["mountain"]:
                    return True
    return False

# ---------------------------------------------------------
# 円 vs AABB 押し出し
# ---------------------------------------------------------
def resolve_collision(px, py):
    r = PLAYER_COLLIDER_RADIUS
    mx = math.floor(px / TILE_SIZE_M)
    my = math.floor(py / TILE_SIZE_M)

    for _ in range(4):
        collided = False

        for ty in range(my - 1, my + 2):
            for tx in range(mx - 1, mx + 2):
                if (tx, ty) not in tile_map:
                    continue
                if tile_map[(tx, ty)] != TILE_TYPES["mountain"]:
                    continue

                left   = tx * TILE_SIZE_M
                right  = left + TILE_SIZE_M
                top    = ty * TILE_SIZE_M
                bottom = top + TILE_SIZE_M

                cx = px
                cy = py

                circle_left   = cx - r
                circle_right  = cx + r
                circle_top    = cy - r
                circle_bottom = cy + r

                if circle_right <= left or circle_left >= right:
                    continue
                if circle_bottom <= top or circle_top >= bottom:
                    continue

                overlap_left   = circle_right - left
                overlap_right  = right - circle_left
                overlap_top    = circle_bottom - top
                overlap_bottom = bottom - circle_top

                min_overlap = min(overlap_left, overlap_right,
                                  overlap_top, overlap_bottom)

                if min_overlap == overlap_left:
                    px -= overlap_left
                elif min_overlap == overlap_right:
                    px += overlap_right
                elif min_overlap == overlap_top:
                    py -= overlap_top
                else:
                    py += overlap_bottom

                collided = True
                mx = math.floor(px / TILE_SIZE_M)
                my = math.floor(py / TILE_SIZE_M)

        if not collided:
            break

    return px, py

# ---------------------------------------------------------
# initialize()
# ---------------------------------------------------------
def initialize():
    global tile_map, walk_images, last_image, battle_back_img, battle_back_img_raw
    global result_win_img, result_win_img_raw, voice_win
    global player_world_x, player_world_y

    for my in range(TILE_MIN, TILE_MAX + 1):
        for mx in range(TILE_MIN, TILE_MAX + 1):
            tile_map[(mx, my)] = random.choice(TILE_LIST)

    walk_images = load_walk_images()
    last_image = walk_images[0]

    # ★ 後ろ姿画像を読み込み → スケール
    raw_img = pygame.image.load(BACK_IMG_PATH).convert_alpha()
    orig_w, orig_h = raw_img.get_size()

    battle_back_img_raw = raw_img  # オリジナルを保持

    target_h = int(SCREEN_H * BATTLE_HEROINE_FIRST_SCALE)
    scale = target_h / orig_h

    battle_back_img = pygame.transform.smoothscale(
        raw_img,
        (int(orig_w * scale), target_h)
    )

    # ★ 勝利バストショット画像を読み込み（等方スケーリングでウィンドウ高さに合わせる）
    win_raw = pygame.image.load(WIN_IMG_PATH).convert_alpha()
    win_orig_w, win_orig_h = win_raw.get_size()
    win_scale = BATTLE_MAIN_WINDOW_HEIGHT / win_orig_h
    win_img_w = max(1, int(win_orig_w * win_scale))
    result_win_img_raw = win_raw   # グローバル変数に保存
    result_win_img = pygame.transform.smoothscale(win_raw, (win_img_w, BATTLE_MAIN_WINDOW_HEIGHT))

    voice_win = pygame.mixer.Sound(VOICE_WIN_PATH)
    voice_win.set_volume(VOICE_WIN_VOLUME)

    player_world_x, player_world_y = resolve_collision(player_world_x, player_world_y)

# ---------------------------------------------------------
# process_input()
# ---------------------------------------------------------
def process_input():
    global zoom, walk_images, last_image
    global move_x, move_y
    global moving
    global game_state, battle_anim_frame
    global heroine_focus_delay_frame, heroine_zoomout_frame, heroine_idle_frame
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame

    moving = False
    move_x = 0.0
    move_y = 0.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                zoom -= ZOOM_STEP
            elif event.y < 0:
                zoom += ZOOM_STEP

            zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom))

            walk_images = load_walk_images()
            last_image = walk_images[frame_index]

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if game_state == STATE_FIELD:
                game_state = STATE_BATTLE
                battle_anim_frame = 0
                heroine_focus_delay_frame = 0
                heroine_zoomout_frame = 0
                heroine_idle_frame = 0
                battle_flashout_frame    = 0
                result_white_delay_frame = 0
                result_slidein_frame     = 0
                result_text_delay_frame  = 0
                result_text_frame        = 0
                pygame.mixer.music.load(BGM_BATTLE_PATH)
                pygame.mixer.music.set_volume(BGM_BATTLE_VOLUME)
                pygame.mixer.music.play()

        # [開発用] Fキー：敵を倒したことにしてリザルトへ
        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            if game_state == STATE_BATTLE:
                game_state = STATE_RESULT
                battle_flashout_frame    = 0
                result_white_delay_frame = 0
                result_slidein_frame     = 0
                result_text_delay_frame  = 0
                result_text_frame        = 0
                pygame.mixer.music.stop()

        # Enterキー：リザルト画面からフィールドへ
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            if game_state == STATE_RESULT:
                game_state = STATE_FIELD
                pygame.mixer.music.stop()

    if game_state in (STATE_BATTLE, STATE_RESULT):
        return

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        move_x -= player_speed
        moving = True
    if keys[pygame.K_RIGHT]:
        move_x += player_speed
        moving = True
    if keys[pygame.K_UP]:
        move_y -= player_speed
        moving = True
    if keys[pygame.K_DOWN]:
        move_y += player_speed
        moving = True

# ---------------------------------------------------------
# update(dt)
# ---------------------------------------------------------
def update(dt):
    global frame_timer, frame_index, last_image
    global player_world_x, player_world_y
    global game_state
    global battle_anim_frame, heroine_focus_delay_frame, heroine_zoomout_frame, heroine_idle_frame
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame

    if game_state == STATE_RESULT:
        # フェーズ①：フラッシュアウト（黒→白）
        if battle_flashout_frame < BATTLE_FLASHOUT_FRAMES:
            battle_flashout_frame += 1
            return
        # フェーズ②：白ウィンドウ静止
        if result_white_delay_frame < RESULT_WHITE_DELAY_FRAMES:
            result_white_delay_frame += 1
            return
        # フェーズ③：スライドイン
        if result_slidein_frame < RESULT_SLIDEIN_FRAMES:
            result_slidein_frame += 1
            return
        # フェーズ③.5：スライドイン後の待機（テキスト・ボイス開始前）
        if result_text_delay_frame < RESULT_TEXT_DELAY_FRAMES:
            result_text_delay_frame += 1
            return
        # フェーズ④：テキスト逐次表示
        if result_text_frame == 0:
            if voice_win:
                voice_win.play()
            pygame.mixer.music.play(start=RESULT_WIN_BGM_START_SEC)
        result_text_frame += 1
        return

    if game_state == STATE_BATTLE:

        # ① バトルメインウィンドウ開くアニメ
        if battle_anim_frame < BATTLE_MAIN_WINDOW_ANIM_FRAMES:
            battle_anim_frame += 1
            return

        # ② 静止フレーム
        if heroine_focus_delay_frame < BATTLE_HEROINE_FOCUS_DELAY_FRAMES:
            heroine_focus_delay_frame += 1
            return

        # ③ ズームアウト
        if heroine_zoomout_frame < BATTLE_HEROINE_ZOOMOUT_FRAMES:
            heroine_zoomout_frame += 1
            return

        # ④ 待機モーション（無限ループ）
        heroine_idle_frame += 1
        return

    # フィールド時のアニメ
    if moving:
        frame_timer += 1
        if frame_timer >= FRAME_INTERVAL:
            frame_timer = 0
            frame_index = (frame_index + 1) % len(walk_images)
            last_image = walk_images[frame_index]

    player_world_x += move_x
    player_world_y += move_y

    player_world_x, player_world_y = resolve_collision(player_world_x, player_world_y)

# ---------------------------------------------------------
# update_camera(dt)
# ---------------------------------------------------------
def update_camera(dt):
    global camera_world_x, camera_world_y
    camera_world_x = player_world_x
    camera_world_y = player_world_y + CAMERA_Y_OFFSET_M

# ---------------------------------------------------------
# render_field()
# ---------------------------------------------------------
def render_field():
    screen.fill((0, 0, 0))

    for (mx, my), color in tile_map.items():
        wx = mx * TILE_SIZE_M
        wy = my * TILE_SIZE_M
        sx = (wx - camera_world_x) * METER_TO_PIXEL * zoom + SCREEN_W // 2
        sy = (wy - camera_world_y) * METER_TO_PIXEL * zoom + SCREEN_H // 2
        rect = pygame.Rect(sx, sy, tile_size_px(), tile_size_px())
        pygame.draw.rect(screen, color, rect)

    sx, sy = world_to_screen(player_world_x, player_world_y)
    rect = last_image.get_rect(midbottom=(sx, sy))
    screen.blit(last_image, rect)

    screen.blit(font.render(f"Player: ({player_world_x:.2f}, {player_world_y:.2f})", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Camera: ({camera_world_x:.2f}, {camera_world_y:.2f})", True, (255, 255, 0)), (10, 30))
    screen.blit(font.render(f"Zoom: {zoom:.2f}", True, (0, 200, 255)), (10, 50))
    screen.blit(font.render(f"FPS: {clock.get_fps():.1f}", True, (255, 255, 255)), (10, 70))

    collider_px = int(PLAYER_COLLIDER_RADIUS * METER_TO_PIXEL * zoom)
    cx, cy = world_to_screen(player_world_x, player_world_y)

    if is_near_mountain(player_world_x, player_world_y):
        color = (255, 255, 0)
    else:
        color = (0, 128, 255)

    pygame.draw.circle(screen, color, (cx, cy), collider_px, 2)

# ---------------------------------------------------------
# render_battle()
# ---------------------------------------------------------
def render_battle():
    render_field()

    # ★ バトルメインウィンドウ開くアニメ進行度（0.0～1.0）
    progress = min(1.0, battle_anim_frame / BATTLE_MAIN_WINDOW_ANIM_FRAMES)
    current_height = int(BATTLE_MAIN_WINDOW_HEIGHT * progress)

    band_y = SCREEN_H//2 - current_height//2
    band_bottom = band_y + current_height

    # バトルメインウィンドウ
    overlay = pygame.Surface((SCREEN_W, current_height))
    overlay.fill(BATTLE_WINDOW_COLOR)
    screen.blit(overlay, (0, band_y))

    # ★ ヒロイン後ろ姿の描画
    if battle_back_img_raw:
        orig_w, orig_h = battle_back_img_raw.get_size()

        # ズームアウト進行度（0.0 → 1.0）
        t_zoom = min(1.0, heroine_zoomout_frame / BATTLE_HEROINE_ZOOMOUT_FRAMES) \
                 if BATTLE_HEROINE_ZOOMOUT_FRAMES > 0 else 1.0
        # ease-out
        t_eased = 1.0 - (1.0 - t_zoom) ** 2

        # 画像高さ：登場サイズ → ズームアウト後サイズ
        start_img_h = int(SCREEN_H * BATTLE_HEROINE_FIRST_SCALE)
        end_img_h   = int(SCREEN_H * BATTLE_HEROINE_LAST_SCALE)
        img_h = max(1, int(start_img_h + (end_img_h - start_img_h) * t_eased))

        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(battle_back_img_raw, (img_w, img_h))

        # bottom_y：注視点（FIRST_FOCUS）を画面中央に固定したままズームアウト後は
        # ANCHOR位置がバトルウィンドウ下端に来るよう補間
        bottom_y_start = SCREEN_H // 2 + int(start_img_h * BATTLE_HEROINE_FIRST_FOCUS)
        bottom_y_end   = band_bottom + int(end_img_h * BATTLE_HEROINE_ZOOMOUT_ANCHOR)
        bottom_y = int(bottom_y_start + (bottom_y_end - bottom_y_start) * t_eased)

        # ④ 待機モーション：縦横逆位相スクワッシュ（ズームアウト完了後のみ適用）
        if heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
            idle_t = math.sin(heroine_idle_frame / BATTLE_HEROINE_IDLE_PERIOD_FRAMES * 2 * math.pi)
            sx = 1.0 + BATTLE_HEROINE_IDLE_SCALE_DELTA * idle_t   # 横：+側で膨らむ
            sy = 1.0 - BATTLE_HEROINE_IDLE_SCALE_DELTA * idle_t   # 縦：横と逆位相
            idle_w = max(1, int(img.get_width()  * sx))
            idle_h = max(1, int(img.get_height() * sy))
            img = pygame.transform.smoothscale(img, (idle_w, idle_h))
            # スケーリング中心 = キャラ下端：bottom_y はそのまま維持

        img_rect = img.get_rect(midbottom=(SCREEN_W // 2, bottom_y))

        clip_rect = pygame.Rect(0, band_y, SCREEN_W, current_height)
        screen.set_clip(clip_rect)
        screen.blit(img, img_rect)
        screen.set_clip(None)

    # テキスト
    text = font.render("BATTLE MODE (Press E to return)", True, (255, 255, 255))
    screen.blit(text, (SCREEN_W//2 - text.get_width()//2, band_y + 10))

# ---------------------------------------------------------
# render()
# ---------------------------------------------------------
# ----------------------------------------------------------
# render_result()
# ----------------------------------------------------------
def render_result():
    band_y      = SCREEN_H // 2 - BATTLE_MAIN_WINDOW_HEIGHT // 2
    band_bottom = band_y + BATTLE_MAIN_WINDOW_HEIGHT

    render_field()

    # -------- フェーズ①：フラッシュアウト（バトルウィンドウ色→白） --------
    if battle_flashout_frame < BATTLE_FLASHOUT_FRAMES:
        t = battle_flashout_frame / BATTLE_FLASHOUT_FRAMES
        br, bg, bb = BATTLE_WINDOW_COLOR
        fc = (int(br + (255 - br) * t), int(bg + (255 - bg) * t), int(bb + (255 - bb) * t))
        overlay = pygame.Surface((SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
        overlay.fill(fc)
        screen.blit(overlay, (0, band_y))
        # ヒロイン後ろ姿をフェードアウト
        if battle_back_img_raw:
            orig_w, orig_h = battle_back_img_raw.get_size()
            h = int(SCREEN_H * BATTLE_HEROINE_LAST_SCALE)
            w = max(1, int(orig_w * h / orig_h))
            img = pygame.transform.smoothscale(battle_back_img_raw, (w, h))
            boty = band_bottom + int(h * BATTLE_HEROINE_ZOOMOUT_ANCHOR)
            alpha_img = img.copy()
            alpha_img.set_alpha(int(255 * (1.0 - t)))
            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(alpha_img, img.get_rect(midbottom=(SCREEN_W // 2, boty)))
            screen.set_clip(None)
        return

    # -------- フェーズ②：白ウィンドウ静止 --------
    overlay_white = pygame.Surface((SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
    overlay_white.fill((255, 255, 255))

    if result_white_delay_frame < RESULT_WHITE_DELAY_FRAMES:
        screen.blit(overlay_white, (0, band_y))
        return

    # -------- フェーズ③④：スライドイン（黒シルエット→通常） --------
    if result_win_img:
        win_w = result_win_img.get_width()

        # スライドイン進行度（0.0 → 1.0）
        t_slide = min(1.0, result_slidein_frame / RESULT_SLIDEIN_FRAMES) \
                  if RESULT_SLIDEIN_FRAMES > 0 else 1.0
        # ease-out
        t_eased = 1.0 - (1.0 - t_slide) ** 2

        # X 位置：画面外左端（-win_w/2）→ 画面中央
        start_cx = -win_w // 2
        end_cx   = SCREEN_W // 2
        cx = int(start_cx + (end_cx - start_cx) * t_eased)

        img_rect = result_win_img.get_rect(midtop=(cx, band_y))

        arrived = (result_slidein_frame >= RESULT_SLIDEIN_FRAMES)

        if arrived:
            # 到達後：RESULT_WINDOW_COLOR ウィンドウ + 通常表示
            overlay_result = pygame.Surface((SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            overlay_result.fill(RESULT_WINDOW_COLOR)
            screen.blit(overlay_result, (0, band_y))
            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(result_win_img, img_rect)
            screen.set_clip(None)
        else:
            # スライドイン中：白ウィンドウ + 黒シルエット
            screen.blit(overlay_white, (0, band_y))
            # 黒シルエット：画像と同サイズの Surface に黒を乗算合成
            silhouette = result_win_img.copy()
            black_fill = pygame.Surface(silhouette.get_size(), pygame.SRCALPHA)
            black_fill.fill((0, 0, 0, 255))
            silhouette.blit(black_fill, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(silhouette, img_rect)
            screen.set_clip(None)
    else:
        # 画像がない場合のフォールバック
        screen.blit(overlay_white, (0, band_y))

    # スライドイン後の待機を経てセリフを表示
    if result_text_delay_frame >= RESULT_TEXT_DELAY_FRAMES:
        text_full = 'もっと大きいのが欲しいの…'
        num_chars = min(len(text_full), result_text_frame // RESULT_TEXT_FRAMES_PER_CHAR + 1)
        full_surf = font_result.render(text_full, True, (255, 255, 255))
        left_x = SCREEN_W // 2 - full_surf.get_width() // 2
        serif = font_result.render(text_full[:num_chars], True, (255, 255, 255))
        screen.blit(serif, (left_x, SCREEN_H // 2 - serif.get_height() // 2))


def render():
    if game_state == STATE_FIELD:
        render_field()
    elif game_state == STATE_BATTLE:
        render_battle()
    else:  # STATE_RESULT
        render_result()

    pygame.display.flip()

# ---------------------------------------------------------
# main()
# ---------------------------------------------------------
def main():
    initialize()

    while True:
        dt = clock.tick(FIXED_FPS)
        process_input()
        update(dt)
        update_camera(dt)
        render()

if __name__ == "__main__":
    main()