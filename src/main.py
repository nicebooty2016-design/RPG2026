# -*- coding: utf-8 -*-
import pygame
import sys
import os
import random

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
CAMERA_Y_OFFSET_M = 1.0

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
    "mountain": (120, 120, 120),
}
TILE_LIST = list(TILE_TYPES.values())

tile_map = {}
for my in range(TILE_MIN, TILE_MAX + 1):
    for mx in range(TILE_MIN, TILE_MAX + 1):
        tile_map[(mx, my)] = random.choice(TILE_LIST)

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

walk_images = load_walk_images()
frame_index = 0
frame_timer = 0
FRAME_INTERVAL = 12
last_image = walk_images[0]

# ---------------------------------------------------------
# ワールド座標 → スクリーン座標（ズーム対応）
# ---------------------------------------------------------
def world_to_screen(wx, wy):
    sx = (wx - camera_world_x) * METER_TO_PIXEL * zoom + SCREEN_W // 2
    sy = (wy - camera_world_y) * METER_TO_PIXEL * zoom + SCREEN_H // 2
    return int(sx), int(sy)

# ---------------------------------------------------------
# メインループ
# ---------------------------------------------------------
def main():
    global player_world_x, player_world_y
    global camera_world_x, camera_world_y
    global zoom, walk_images, last_image
    global frame_index, frame_timer

    while True:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # -------------------------------
            # マウスホイールでズーム
            # -------------------------------
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    zoom -= ZOOM_STEP
                elif event.y < 0:
                    zoom += ZOOM_STEP

                zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom))

                walk_images = load_walk_images()
                last_image = walk_images[frame_index]

        keys = pygame.key.get_pressed()
        moving = False

        # -------------------------------
        # キャラ移動（ワールド座標）
        # -------------------------------
        if keys[pygame.K_UP]:
            player_world_y -= player_speed
            moving = True
        if keys[pygame.K_DOWN]:
            player_world_y += player_speed
            moving = True
        if keys[pygame.K_LEFT]:
            player_world_x -= player_speed
            moving = True
        if keys[pygame.K_RIGHT]:
            player_world_x += player_speed
            moving = True

        # -------------------------------
        # カメラ追従（キャラより +1m）
        # -------------------------------
        camera_world_x = player_world_x
        camera_world_y = player_world_y + CAMERA_Y_OFFSET_M

        # -------------------------------
        # マップ描画（ワールド座標 -16～16）
        # -------------------------------
        screen.fill((0, 0, 0))

        for (mx, my), color in tile_map.items():
            wx = mx * TILE_SIZE_M
            wy = my * TILE_SIZE_M
            sx, sy = world_to_screen(wx, wy)
            rect = pygame.Rect(sx, sy, tile_size_px(), tile_size_px())
            pygame.draw.rect(screen, color, rect)

        # -------------------------------
        # 歩行アニメ
        # -------------------------------
        if moving:
            frame_timer += dt
            if frame_timer >= FRAME_INTERVAL:
                frame_timer = 0
                frame_index = (frame_index + 1) % len(walk_images)
            img = walk_images[frame_index]
            last_image = img
        else:
            img = last_image

        # -------------------------------
        # キャラ描画（足元＝ワールド座標）
        # -------------------------------
        sx, sy = world_to_screen(player_world_x, player_world_y)
        rect = img.get_rect(midbottom=(sx, sy))
        screen.blit(img, rect)

        # -------------------------------
        # デバッグ表示（キャラ足元）
        # -------------------------------
        text = f"({player_world_x:.1f}, {player_world_y:.1f})"
        img_text = font.render(text, True, (255, 255, 255))
        screen.blit(img_text, (sx - img_text.get_width() // 2, sy - 10))

        # -------------------------------
        # デバッグ表示（カメラ座標）
        # -------------------------------
        cam_text = f"Camera: ({camera_world_x:.1f}, {camera_world_y:.1f})"
        cam_img = font.render(cam_text, True, (255, 255, 0))
        screen.blit(cam_img, (10, 10))

        # -------------------------------
        # デバッグ表示（ズーム倍率）
        # -------------------------------
        zoom_text = f"Zoom: {zoom:.2f}"
        zoom_img = font.render(zoom_text, True, (0, 200, 255))
        screen.blit(zoom_img, (10, 30))

        pygame.display.flip()

if __name__ == "__main__":
    main()
