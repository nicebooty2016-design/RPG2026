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

# ズームアウト後の待機モーション（縦横逆位相スクワッシュ）
BATTLE_HEROINE_IDLE_PERIOD_FRAMES = 30  # 拡縮1周期のフレーム数
BATTLE_HEROINE_IDLE_SCALE_DELTA   = 0.02  # 縦横スケールの振れ幅（1.0 ± DELTA）

# ---------------------------------------------------------
# ゲーム状態
# ---------------------------------------------------------
STATE_FIELD = 0
STATE_BATTLE = 1
game_state = STATE_FIELD

battle_anim_frame = 0
heroine_focus_delay_frame = 0
heroine_zoomout_frame = 0
heroine_idle_frame = 0

# ---------------------------------------------------------
# フォント
# ---------------------------------------------------------
font = pygame.font.SysFont(None, 24)

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

battle_back_img = None  # 後ろ姿画像（スケール後）
battle_back_img_raw = None  # 後ろ姿画像（オリジナル）

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
            else:
                game_state = STATE_FIELD

    if game_state == STATE_BATTLE:
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
    overlay.fill((0, 0, 0))
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
def render():
    if game_state == STATE_FIELD:
        render_field()
    else:
        render_battle()

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