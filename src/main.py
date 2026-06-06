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
# ワールドスケール
# ---------------------------------------------------------
METER_TO_PIXEL = 64
CHARACTER_HEIGHT_M = 2.0
CHARACTER_HEIGHT_PX = int(CHARACTER_HEIGHT_M * METER_TO_PIXEL)

TILE_SIZE_M = 2.0
TILE_SIZE_PX = int(TILE_SIZE_M * METER_TO_PIXEL)

# ---------------------------------------------------------
# ワールド座標
# ---------------------------------------------------------
player_world_x = 0.0
player_world_y = 0.0

camera_world_x = 0.0
camera_world_y = 10.0   # カメラはキャラの10m上にいるイメージ

# ---------------------------------------------------------
# キャラ移動速度（秒速2m）
# ---------------------------------------------------------
player_speed_mps = 2.0
player_speed = player_speed_mps / 60.0   # 1フレームあたりの移動量（m）

# ---------------------------------------------------------
# タイルマップ（ワールド座標で扱う）
# ---------------------------------------------------------
MAP_W = 50
MAP_H = 50

TILE_TYPES = {
    "grass": (80, 200, 80),
    "sand": (210, 180, 80),
    "forest": (20, 120, 20),
    "mountain": (120, 120, 120)
}
TILE_LIST = list(TILE_TYPES.values())

tile_map = [[random.choice(TILE_LIST) for _ in range(MAP_W)] for _ in range(MAP_H)]

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
        scale = CHARACTER_HEIGHT_PX / h
        img = pygame.transform.smoothscale(img, (int(w * scale), CHARACTER_HEIGHT_PX))
        images.append(img)

    return images

walk_images = load_walk_images()
frame_index = 0
frame_timer = 0
FRAME_INTERVAL = 12
last_image = walk_images[0]

# ---------------------------------------------------------
# ワールド座標 → スクリーン座標変換
# ---------------------------------------------------------
def world_to_screen(wx, wy):
    sx = (wx - camera_world_x) * METER_TO_PIXEL + SCREEN_W // 2
    sy = (wy - camera_world_y) * METER_TO_PIXEL + SCREEN_H // 2
    return int(sx), int(sy)

# ---------------------------------------------------------
# メインループ
# ---------------------------------------------------------
def main():
    global player_world_x, player_world_y
    global camera_world_x, camera_world_y
    global frame_index, frame_timer, last_image

    while True:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        moving = False

        # ---------------------------------------------------------
        # キャラはワールド座標で移動する
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # カメラはキャラを追従（ワールド座標）
        # ---------------------------------------------------------
        camera_world_x = player_world_x
        camera_world_y = player_world_y

        # ---------------------------------------------------------
        # マップ描画（ワールド座標 → スクリーン座標）
        # ---------------------------------------------------------
        screen.fill((0, 0, 0))

        for my in range(MAP_H):
            for mx in range(MAP_W):
                wx = mx * TILE_SIZE_M
                wy = my * TILE_SIZE_M
                sx, sy = world_to_screen(wx, wy)
                rect = pygame.Rect(sx, sy, TILE_SIZE_PX, TILE_SIZE_PX)
                pygame.draw.rect(screen, tile_map[my][mx], rect)

        # ---------------------------------------------------------
        # 歩行アニメ or 静止
        # ---------------------------------------------------------
        if moving:
            frame_timer += dt
            if frame_timer >= FRAME_INTERVAL:
                frame_timer = 0
                frame_index = (frame_index + 1) % len(walk_images)
            img = walk_images[frame_index]
            last_image = img
        else:
            img = last_image

        # ---------------------------------------------------------
        # キャラ描画（ワールド座標 → スクリーン座標）
        # ---------------------------------------------------------
        sx, sy = world_to_screen(player_world_x, player_world_y)
        rect = img.get_rect(center=(sx, sy))
        screen.blit(img, rect)

        pygame.display.flip()

if __name__ == "__main__":
    main()
