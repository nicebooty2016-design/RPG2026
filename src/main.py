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
# フォント（デバッグ表示用）
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
# カメラオフセット（キャラより何m上に置くか）
# ---------------------------------------------------------
CAMERA_Y_OFFSET_M = -0.25

# ---------------------------------------------------------
# コライダ設定（キャラ足元の円）
# ---------------------------------------------------------
PLAYER_COLLIDER_RADIUS = 0.25  # 0.25m

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
# ワールド座標（キャラ & カメラ）
# ---------------------------------------------------------
player_world_x = 0.0
player_world_y = 0.0

camera_world_x = 0.0
camera_world_y = 10.0

# ---------------------------------------------------------
# キャラ移動速度（秒速2m）
# ---------------------------------------------------------
player_speed_mps = 2.0
player_speed = player_speed_mps / 60.0

# ---------------------------------------------------------
# タイルマップ（ワールド座標 -16 ～ +16）
# ---------------------------------------------------------
TILE_MIN = -16
TILE_MAX = 16

TILE_TYPES = {
    "grass": (80, 200, 80),
    "sand": (210, 180, 80),
    "forest": (20, 120, 20),
    "mountain": (120, 120, 120),  # 衝突対象
}
TILE_LIST = list(TILE_TYPES.values())

tile_map = {}

# ---------------------------------------------------------
# キャラ画像読み込み
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WALK_DIR = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "bunny", "bunny_walk")

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
FRAME_INTERVAL = 12
last_image = None

# ---------------------------------------------------------
# ワールド座標 → スクリーン座標（ズーム対応）
# ---------------------------------------------------------
def world_to_screen(wx, wy):
    sx = (wx - camera_world_x) * METER_TO_PIXEL * zoom + SCREEN_W // 2
    sy = (wy - camera_world_y) * METER_TO_PIXEL * zoom + SCREEN_H // 2
    return int(sx), int(sy)

# ---------------------------------------------------------
# 周囲8タイルに山があるかチェック（コライダ色用）
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
# 円 vs AABB 押し出し（depenetration）
# ---------------------------------------------------------
def resolve_collision(px, py):
    r = PLAYER_COLLIDER_RADIUS
    mx = math.floor(px / TILE_SIZE_M)
    my = math.floor(py / TILE_SIZE_M)

    # 複数タイルと重なっている可能性があるので、数回繰り返して解消
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

                # 円のAABB（近似）
                circle_left   = cx - r
                circle_right  = cx + r
                circle_top    = cy - r
                circle_bottom = cy + r

                # AABB同士の重なりチェック
                if circle_right <= left or circle_left >= right:
                    continue
                if circle_bottom <= top or circle_top >= bottom:
                    continue

                # 各方向のめり込み量
                overlap_left   = circle_right - left      # 左側から押し返される量
                overlap_right  = right - circle_left      # 右側から押し返される量
                overlap_top    = circle_bottom - top      # 上から
                overlap_bottom = bottom - circle_top      # 下から

                # 最小のめり込み方向に押し出す
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

                # 押し出したので、次のループでは新しい位置で再判定
                mx = math.floor(px / TILE_SIZE_M)
                my = math.floor(py / TILE_SIZE_M)

        if not collided:
            break

    return px, py

# ---------------------------------------------------------
# initialize()
# ---------------------------------------------------------
def initialize():
    global tile_map, walk_images, last_image
    global player_world_x, player_world_y

    for my in range(TILE_MIN, TILE_MAX + 1):
        for mx in range(TILE_MIN, TILE_MAX + 1):
            tile_map[(mx, my)] = random.choice(TILE_LIST)

    walk_images = load_walk_images()
    last_image = walk_images[0]

    # 初期位置が山にめり込んでいても押し出す
    player_world_x, player_world_y = resolve_collision(player_world_x, player_world_y)

# ---------------------------------------------------------
# process_input()
# ---------------------------------------------------------
def process_input():
    global zoom, walk_images, last_image
    global move_x, move_y
    global moving

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

    # アニメーション更新
    if moving:
        frame_timer += dt
        if frame_timer >= FRAME_INTERVAL:
            frame_timer = 0
            frame_index = (frame_index + 1) % len(walk_images)
            last_image = walk_images[frame_index]

    # まず X/Y 同時に移動
    player_world_x += move_x
    player_world_y += move_y

    # その後、山タイルから押し出す
    player_world_x, player_world_y = resolve_collision(player_world_x, player_world_y)

# ---------------------------------------------------------
# update_camera(dt)
# ---------------------------------------------------------
def update_camera(dt):
    global camera_world_x, camera_world_y
    camera_world_x = player_world_x
    camera_world_y = player_world_y + CAMERA_Y_OFFSET_M

# ---------------------------------------------------------
# render()
# ---------------------------------------------------------
def render():
    screen.fill((0, 0, 0))

    for (mx, my), color in tile_map.items():
        wx = mx * TILE_SIZE_M
        wy = my * TILE_SIZE_M
        sx, sy = world_to_screen(wx, wy)
        rect = pygame.Rect(sx, sy, tile_size_px(), tile_size_px())
        pygame.draw.rect(screen, color, rect)

    sx, sy = world_to_screen(player_world_x, player_world_y)
    rect = last_image.get_rect(midbottom=(sx, sy))
    screen.blit(last_image, rect)

    text = f"({player_world_x:.1f}, {player_world_y:.1f})"
    img_text = font.render(text, True, (255, 255, 255))
    screen.blit(img_text, (sx - img_text.get_width() // 2, sy - 10))

    cam_text = f"Camera: ({camera_world_x:.1f}, {camera_world_y:.1f})"
    cam_img = font.render(cam_text, True, (255, 255, 0))
    screen.blit(cam_img, (10, 10))

    zoom_text = f"Zoom: {zoom:.2f}"
    zoom_img = font.render(zoom_text, True, (0, 200, 255))
    screen.blit(zoom_img, (10, 30))

    # コライダ可視化（周囲に山があれば黄色、なければ青）
    collider_px = int(PLAYER_COLLIDER_RADIUS * METER_TO_PIXEL * zoom)
    cx, cy = world_to_screen(player_world_x, player_world_y)

    if is_near_mountain(player_world_x, player_world_y):
        color = (255, 255, 0)  # 黄色
    else:
        color = (0, 128, 255)  # 青

    pygame.draw.circle(screen, color, (cx, cy), collider_px, 2)

    pygame.display.flip()

# ---------------------------------------------------------
# main() test
# ---------------------------------------------------------
def main():
    initialize()

    while True:
        dt = clock.tick(60)
        process_input()
        update(dt)
        update_camera(dt)
        render()

if __name__ == "__main__":
    main()
