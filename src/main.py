# -*- coding: utf-8 -*-
import pygame
import sys
import os
import random
import math
import array
import ctypes

pygame.init()

SCREEN_W = 640
SCREEN_H = 480
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()

# ウィンドウタイトル：[開発用] システムポーズ中はタイトルバーの表示（文字列・背景色）を切り替えて、
# ゲーム画面自体には影響を与えずに「ポーズ中」であることを開発者に分かりやすく伝える
WINDOW_TITLE               = "RPG2026"
WINDOW_TITLE_PAUSED_SUFFIX = " - [システムポーズ中]"
WINDOW_TITLE_PAUSED_COLOR  = (255, 0, 0)  # ポーズ中のタイトルバー背景色（赤）
pygame.display.set_caption(WINDOW_TITLE)

# ---------------------------------------------------------
# set_titlebar_color()：タイトルバーの背景色を変更する（Windows 11 の DWM API を使用）。
#                       rgb=None で既定の色に戻す。非対応環境では何もしない
# ---------------------------------------------------------
DWMWA_CAPTION_COLOR = 35
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF

def set_titlebar_color(rgb):
    try:
        hwnd = pygame.display.get_wm_info()["window"]
        if rgb is None:
            colorref = DWMWA_COLOR_DEFAULT
        else:
            r, g, b = rgb
            colorref = (b << 16) | (g << 8) | r
        value = ctypes.c_int(colorref)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass

# ---------------------------------------------------------
# ★ 調整可能な定数（演出パラメータ）
# ---------------------------------------------------------
FIXED_FPS = 60

# バトルメインウィンドウ（旧：黒帯）
BATTLE_MAIN_WINDOW_HEIGHT = 400
BATTLE_MAIN_WINDOW_ANIM_FRAMES = 10   # バトルメインウィンドウが開ききるまでのフレーム数

# ヒロイン演出パラメータ
BATTLE_HEROINE_FIRST_SCALE = 3.6    # 登場時の画像高さ（画面高さの何倍）
BATTLE_HEROINE_LAST_SCALE  = 0.9    # ズームアウト後の画像高さ（画面高さの何倍）
BATTLE_HEROINE_FIRST_FOCUS = 0.10   # 注視点：下端から高さの何倍の位置を画面中央に合わせるか

# バトルウィンドウが開いた後の静止 → ズームアウト
BATTLE_HEROINE_FOCUS_DELAY_FRAMES = 20  # 静止フレーム数
BATTLE_HEROINE_ZOOMOUT_FRAMES = 60      # ズームアウトに要するフレーム数
BATTLE_HEROINE_ZOOMOUT_ANCHOR = 0.625   # ヒロイン下端から高さの何倍がバトルウィンドウ下端に来るか

# バトルウィンドウ色
BATTLE_WINDOW_COLOR = (30, 80, 200)  # バトル中のウィンドウ色
RESULT_WINDOW_COLOR = (0, 0, 0)      # リザルト到達後のウィンドウ色

# リザルト演出
BATTLE_FLASHOUT_FRAMES    = 40  # バトルウィンドウが黒→白にフラッシュアウトするフレーム数
RESULT_WHITE_DELAY_FRAMES = 30  # 白ウィンドウ静止フレーム数
RESULT_SLIDEIN_FRAMES     = 30  # バストショットのスライドイン所要フレーム数

# 勝利ボイス（bunny_win_<番号>.mp3）ごとに対応する勝利メッセージ本文。
# リザルト開始時にボイスをランダム選択し、対応するメッセージを表示する
RESULT_VICTORY_MESSAGES = {
    0: 'もっと大きいのが欲しいの…',
    1: 'こんなの、初めて…',
    2: 'もうイっちゃったの？',
}
VOICE_WIN_SPEED = 1.5  # 勝利ボイスの再生速度倍率（候補とも一律。この倍率に合わせて勝利メッセージの表示速度も変化する）
# 再生速度変更時のピッチ維持（OLA法による時間伸縮）パラメータ
VOICE_TIME_STRETCH_FRAME_SIZE = 1024  # 解析フレーム長（サンプル数）。大きいほど低音域の質が安定するが処理が重くなる
VOICE_TIME_STRETCH_OVERLAP    = 0.5   # フレーム間のオーバーラップ率（0.0～1.0）。大きいほど滑らかだが処理が重くなる
RESULT_TEXT_FRAMES_PER_CHAR_BASE = 12  # 勝利メッセージ1文字追加するのに要するフレーム数（等速=1.0倍時の基準値）
RESULT_TEXT_FRAMES_PER_CHAR = max(1, round(RESULT_TEXT_FRAMES_PER_CHAR_BASE / VOICE_WIN_SPEED))  # 実際に使用する値（ボイス速度倍率を反映）
RESULT_TEXT_DELAY_FRAMES   = 0  # スライドイン完了後、テキスト・ボイス開始までの待機フレーム数
RESULT_WIN_BGM_DELAY_FRAMES = 30  # メッセージ表示完了後、勝利BGM再生開始までの待機フレーム数
RESULT_WIN_BGM_START_SEC   = 151.4  # 勝利BGM代用：再生開始時にbattle.mp3を再生開始する秒数

# 音量
BGM_BATTLE_VOLUME = 0.30  # バトルBGM音量（0.0～1.0）
VOICE_WIN_VOLUME  = 1.0  # 勝利ボイス音量（0.0～1.0）
VOICE_BATTLE_START_VOLUME = 1.0  # エンカウント時かけ声の音量（0.0～1.0）
VOICE_ATTACK_VOLUME = 1.0  # 攻撃ボイス音量（0.0～1.0）
VOICE_GOBLIN_DAMAGED_VOLUME = 1.0  # 敵（ゴブリン）被弾やられボイスの音量（0.0～1.0）

# 攻撃ボイス（ムチ最接近時に再生。ピッチを維持したまま再生速度を変更する）
VOICE_ATTACK_SPEED = 1.5  # 攻撃ボイスの再生速度倍率

BGM_FIELD_RETURN_FADEOUT_MS = 1200  # フィールドへ戻る際のBGMフェードアウト時間（ミリ秒）

# ズームアウト後の待機モーション（縦横逆位相スクワッシュ）
BATTLE_HEROINE_IDLE_PERIOD_FRAMES = 30  # 拡縮1周期のフレーム数
BATTLE_HEROINE_IDLE_SCALE_DELTA   = 0.02  # 縦横スケールの振れ幅（1.0 ± DELTA）

# 敵キャラクター演出パラメータ
ENEMY_GOBLIN_FIRST_SCALE = 3.0  # 登場時の画像高さ（画面高さの何倍）
ENEMY_GOBLIN_LAST_SCALE  = 0.3  # ヒロインのズームアウト完了時点での画像高さ（画面高さの何倍）
ENEMY_GROUND_Y_FROM_BOTTOM_RATIO = 0.3  # 敵の足元（接地位置）：画面下端から画面高さの何倍の位置か
ENEMY_X_RATIOS = [0.25, 0.5, 0.75]  # 敵を並べる横位置（画面左端から画面幅の何倍か）を1体ずつ指定
ENEMY_SILHOUETTE_RELEASE_FRAMES = 15  # 黒シルエットが解除され通常表示になるまでのフレーム数（ズームアウト完了直後から進行）
ENEMY_IDLE_PERIOD_FRAMES = 30   # 待機モーション：拡縮1周期のフレーム数
ENEMY_IDLE_SCALE_DELTA   = 0.02  # 待機モーション：縦横スケールの振れ幅（1.0 ± DELTA）

# 攻撃選択サブウィンドウ
BATTLE_MENU_OPTIONS = ["ムチ", "ドレイン", "炎"]  # 攻撃手段の選択肢（上から順に表示）

BATTLE_MENU_WIDTH  = 180  # サブウィンドウの幅（px）
BATTLE_MENU_HEIGHT = 140  # サブウィンドウの高さ（px）
BATTLE_MENU_MARGIN = 20   # 画面端からの余白（右上に寄せて配置）

BATTLE_MENU_BORDER_COLOR  = (255, 255, 255)  # 枠線の色（白）
BATTLE_MENU_BORDER_WIDTH  = 4                # 枠線の太さ（px）
BATTLE_MENU_BORDER_RADIUS = 16               # 枠の角の丸み（px）。0で角ばった矩形
BATTLE_MENU_BG_COLOR  = (0, 0, 0)  # ウィンドウ内背景の色
BATTLE_MENU_BG_ALPHA  = 150        # ウィンドウ内背景の不透明度（0=透明 ～ 255=不透明）

BATTLE_MENU_FONT_SIZE = 24  # 選択肢テキストのフォントサイズ（メイリオ使用、文字化け対策）

BATTLE_MENU_TEXT_PADDING_X = 20  # 選択肢テキストの左余白（px）
BATTLE_MENU_TEXT_PADDING_Y = 16  # 選択肢テキストの上余白（px）
BATTLE_MENU_LINE_HEIGHT    = 36  # 選択肢1行あたりの高さ（px）

BATTLE_MENU_SELECTED_COLOR   = (255, 255, 255)  # 選択中の文字色（真っ白）
BATTLE_MENU_UNSELECTED_COLOR = (120, 120, 120)  # 非選択時の文字色（グレーアウト）

# 攻防ステート（コマンド実行後、専用の演出を行う期間。コマンドウィンドウは非表示）
BATTLE_EXCHANGE_FRAMES = 30  # 攻防ステートが継続するフレーム数（未実装の攻撃手段で使用。経過後はコマンド選択ステートへ戻る）

BATTLE_MENU_INDEX_WHIP  = 0  # BATTLE_MENU_OPTIONS内の「ムチ」のインデックス
BATTLE_MENU_INDEX_FLAME = 2  # BATTLE_MENU_OPTIONS内の「炎」のインデックス

# 攻撃手段ごとの攻撃ボイス再生候補：bunny_attack_<番号>.mp3 の番号で指定する（再生時にこの中からランダムに選ぶ）
BATTLE_WHIP_ATTACK_VOICE_NUMBERS  = (1, 1)  # ムチ攻撃時に再生するボイス候補
BATTLE_FLAME_ATTACK_VOICE_NUMBERS = (0, 0)  # 炎攻撃時に再生するボイス候補

# ムチ（近接攻撃）演出パラメータ：敵に接近 → 最接近で停止 → 元の位置へ後退
# （接近対象の敵はコマンドウィンドウ上で左右キーにより選択する。battle_target_enemy_index を参照）
BATTLE_WHIP_APPROACH_FRAMES = 15      # 敵に接近するまでのフレーム数（後退も同じフレーム数で行う）
BATTLE_WHIP_TARGET_SCALE    = 0.5     # 最接近時の画像高さ（画面高さの何倍。元のBATTLE_HEROINE_LAST_SCALEより小さい値を指定）
BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO = 0.1  # 最接近時のヒロインの足元位置：画面下端から画面高さの何倍の位置か（敵とは独立して指定）

# ムチ：接近・後退中の残像（モーションブラー風の演出。数フレーム前のヒロイン画像を半透明で重ねて表示する）
BATTLE_WHIP_TRAIL_OFFSET_1 = 5         # 残像(A)：何フレーム前の位置を表示するか
BATTLE_WHIP_TRAIL_OFFSET_2 = 10         # 残像(B)：何フレーム前の位置を表示するか
BATTLE_WHIP_TRAIL_ALPHA_1 = 0.7        # 残像(A)の不透明度
BATTLE_WHIP_TRAIL_ALPHA_2 = 0.3        # 残像(B)の不透明度
BATTLE_WHIP_TRAIL_MIN_OFFSET_PX = 2    # 残像を表示する最小の位置差（ピクセル）。これ未満なら現在位置とほぼ同じとみなして表示しない

# ムチ：最接近直後のダメージ演出（攻撃ボイス再生 → 数フレーム後に敵を白色点滅 → 点滅終了直後に後退開始）
BATTLE_WHIP_DAMAGE_DELAY_FRAMES = 10        # 最接近（攻撃ボイス再生開始）から敵の白色点滅開始までのフレーム数
BATTLE_WHIP_FLASH_FRAMES = 10               # 敵の白色点滅の継続フレーム数（経過後、即座に後退を開始する）
BATTLE_WHIP_FLASH_BLINK_PERIOD_FRAMES = 4   # 点滅1周期のフレーム数
BATTLE_WHIP_FLASH_COLOR = (255, 255, 255)   # 点滅時に重ねる色（白）
BATTLE_ANNIHILATE_FRAMES = 15               # 撃破した敵の殲滅演出（アルファ値を下げて消滅させる）にかけるフレーム数（ムチ・炎共通）

# 炎（全体攻撃）演出パラメータ：その場で詠唱（攻撃ボイス再生 → 待機） → 敵全体を同時に赤色点滅
BATTLE_FLAME_CAST_DELAY_FRAMES = 60         # 攻撃ボイス再生から敵全体への赤色点滅開始までの待機フレーム数
BATTLE_FLAME_FLASH_COLOR = (255, 0, 0)      # 炎の点滅時に重ねる色（赤。ムチの白色点滅と区別するため）

# 敵の攻撃演出パラメータ：ヒロインに接近 → 最接近で停止 → 元の位置へ後退（流れはムチ演出と同じ4ステート構成を共有する）
BATTLE_ENEMY_ATTACK_TARGET_SCALE = 0.4      # 最接近時の敵の画像高さ（画面高さの何倍）
BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO = 0.0  # 最接近時の敵の足元位置：バトルウィンドウ下端からのオフセット（画面高さの何倍。0でウィンドウ下端と一致）

# HP関連パラメータ：最大HPと、各攻撃手段で増減するダメージ量の範囲（ランダム抽選はrandom.randint(MIN, MAX)で行う）
HEROINE_MAX_HP = 200   # ヒロインの最大HP（現在HPは戦闘をまたいで引き継ぐ。回復はしない）
GOBLIN_MAX_HP  = 30    # ゴブリン1体の最大HP（敵はエンカウント毎に最大HPへリセットされる）

BATTLE_WHIP_DAMAGE_MIN  = 20   # ムチで敵に与えるダメージの最小値
BATTLE_WHIP_DAMAGE_MAX  = 50   # ムチで敵に与えるダメージの最大値
BATTLE_FLAME_DAMAGE_MIN = 10   # 炎で敵1体ごとに与えるダメージの最小値（全体攻撃だが各々個別に抽選する）
BATTLE_FLAME_DAMAGE_MAX = 40   # 炎で敵1体ごとに与えるダメージの最大値
BATTLE_ENEMY_ATTACK_DAMAGE_MIN = 10   # 敵の攻撃でヒロインが受けるダメージの最小値
BATTLE_ENEMY_ATTACK_DAMAGE_MAX = 30   # 敵の攻撃でヒロインが受けるダメージの最大値

# 攻撃対象選択カーソル（ムチ選択中、対象の敵の頭上に点滅表示する下向き三角カーソル。左右キーで対象変更）
BATTLE_TARGET_CURSOR_COLOR  = (255, 255, 255)  # カーソルの色（白）
BATTLE_TARGET_CURSOR_WIDTH  = 24    # 三角カーソルの幅（px）
BATTLE_TARGET_CURSOR_HEIGHT = 16    # 三角カーソルの高さ（px）
BATTLE_TARGET_CURSOR_MARGIN_Y = 6   # 敵の頭上とカーソル下端との間隔（px）
BATTLE_TARGET_CURSOR_BLINK_PERIOD_FRAMES = 30  # 点滅1周期のフレーム数

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
heroine_idle_phase_offset = 0  # 待機モーションの位相ずらし（フレーム数。エンカウント毎にランダム決定）
enemy_silhouette_frame   = 0
enemy_idle_frame         = 0
enemy_idle_phase_offsets = [0, 0, 0]  # 敵1体ごとの待機モーション位相ずらし（フレーム数。エンカウント毎にランダム決定）
battle_flashout_frame    = 0
result_white_delay_frame = 0
result_slidein_frame     = 0
result_text_delay_frame  = 0
result_text_frame        = 0
result_flashout_heroine_override = None  # フラッシュアウト中のヒロイン表示位置・スケールの上書き指定（(x, 足元y, 画像高さ) または None）

battle_menu_selected_index = 0
battle_target_enemy_index  = 0  # ムチ選択中に左右キーで選べる攻撃対象（ENEMY_X_RATIOSのインデックス）
battle_target_cursor_frame = 0  # 攻撃対象カーソルの点滅用フレームカウンタ

# HP：ヒロインの現在HPは戦闘をまたいで引き継ぐ（回復しない）。敵の現在HPはエンカウント毎に最大HPへリセットされる
heroine_hp = HEROINE_MAX_HP
enemy_hp   = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)

# 敵の撃破状態：True の敵は殲滅済み（選択対象・通常表示の対象外となる）
enemy_defeated = [False] * len(ENEMY_X_RATIOS)
battle_annihilate_targets = []  # 殲滅演出（アルファ値を下げて消滅）中の敵のインデックスのリスト（[] = 演出なし。ムチは1体、炎は複数を同時に格納）
battle_annihilate_frame   = 0   # 殲滅演出の経過フレーム数（共通カウンタ）

# 戦闘内ステート：コマンド選択 ⇔ 攻防演出
BATTLE_PHASE_COMMAND  = 0  # ヒロインの行動選択中（コマンドウィンドウ表示）
BATTLE_PHASE_EXCHANGE = 1  # 攻防演出中（コマンドウィンドウ非表示）
battle_phase = BATTLE_PHASE_COMMAND
battle_exchange_frame = 0

# ムチ（近接攻撃）演出ステート：接近 → ダメージ待機 → 白色点滅 → 後退
BATTLE_WHIP_PHASE_APPROACH    = 0  # 敵に接近中
BATTLE_WHIP_PHASE_DAMAGE_WAIT = 1  # 最接近後、攻撃ボイス再生から白色点滅開始までの待機中
BATTLE_WHIP_PHASE_FLASH       = 2  # ダメージ演出（敵の白色点滅）中
BATTLE_WHIP_PHASE_RETURN      = 3  # 元の位置へ後退中
battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
battle_whip_frame = 0

# 炎（全体攻撃）演出ステート：その場で詠唱（待機） → 敵全体に同時に赤色点滅
BATTLE_FLAME_PHASE_CAST  = 0  # 攻撃ボイス再生後、白色点滅開始までの待機中（その場にとどまる）
BATTLE_FLAME_PHASE_FLASH = 1  # ダメージ演出（敵全体の白色点滅）中
battle_flame_phase = BATTLE_FLAME_PHASE_CAST
battle_flame_frame = 0

# 攻防ステート内の行動順：ヒロインのムチ選択時に、生存している敵全体とヒロインを含めてランダムに決定する
# （-1 = ヒロイン、0以上 = 敵のインデックス。一巡したらコマンド選択ステートへ戻る）
battle_turn_order = []
battle_turn_index = 0

# 敵の攻撃演出ステート：接近 → ダメージ待機 → 白色点滅 → 後退（ムチ演出と同じ4ステートをそのまま流用する）
battle_enemy_attack_phase = BATTLE_WHIP_PHASE_APPROACH
battle_enemy_attack_frame = 0
battle_attacking_enemy_index = -1  # 現在攻撃中の敵のインデックス（-1 = 攻撃側はヒロイン）

# ムチ：接近・後退中の残像履歴（直近 BATTLE_WHIP_TRAIL_OFFSET_2 フレーム分の (x, 足元y, 画像高さ) を保持。古い順）
heroine_whip_trail = []
heroine_whip_trail_key = None  # 最後に記録したフレームの識別キー（(phase, frame)）。重複登録の防止用

# [開発用] システムポーズ：Pキーでフレーム処理を停止／再開（描画は継続）。
# ポーズ中はSpaceキーで1フレームだけ処理を進められる。
# また、Spaceキーを押し続けた場合はキーリピートで連続して1フレームずつ進める
# （最初は PAUSE_STEP_REPEAT_DELAY_SEC 秒後に1回、以後は PAUSE_STEP_REPEAT_INTERVAL_SEC 秒間隔で繰り返す）
PAUSE_STEP_REPEAT_DELAY_SEC    = 0.5  # 押し続けてから最初のリピートが発生するまでの秒数
PAUSE_STEP_REPEAT_INTERVAL_SEC = 0.05  # 2回目以降のリピート間隔（秒）
PAUSE_STEP_REPEAT_DELAY_FRAMES    = max(1, round(PAUSE_STEP_REPEAT_DELAY_SEC * FIXED_FPS))
PAUSE_STEP_REPEAT_INTERVAL_FRAMES = max(1, round(PAUSE_STEP_REPEAT_INTERVAL_SEC * FIXED_FPS))

is_paused = False
pause_step_requested = False
pause_step_key_held       = False  # Spaceキーが押され続けているか（リピート判定用）
pause_step_key_hold_frame = 0      # Spaceキーを押し続けているフレーム数（リピート判定用カウンタ）
pause_step_key_repeated   = False  # 押し続けている間に既に1回以上リピートが発生したか（遅延／間隔の切り替え用）

# ----------------------------------------------------------
# フォント
# ----------------------------------------------------------
RESULT_TEXT_FONT_SIZE = 32  # リザルトセリフのフォントサイズ

font           = pygame.font.SysFont(None, 24)
font_result    = pygame.font.Font('C:/Windows/Fonts/meiryo.ttc', RESULT_TEXT_FONT_SIZE)
font_battle_menu = pygame.font.Font('C:/Windows/Fonts/meiryo.ttc', BATTLE_MENU_FONT_SIZE)

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
ENEMY_GOBLIN_IMG_PATH = os.path.join(BASE_DIR, "..", "assets", "images", "enemies", "goblin", "goblin_idle.png")
VOICES_DIR = os.path.join(BASE_DIR, "..", "assets", "sound", "voices")
VOICE_GOBLIN_DAMAGED_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "goblin_damaged.wav")
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
enemy_img_raw       = None  # 敵（goblin）画像（オリジナル）
voice_win_by_number = {}  # 勝利ボイス（{番号: Sound}。bunny_win_<番号>.mp3 の番号をキーとし、リザルト開始時にランダム選択する）
result_win_voice         = None  # リザルト開始時に選ばれた勝利ボイス（再生・長さ判定用）
result_victory_message        = ''  # 選ばれた勝利ボイスに対応する勝利メッセージ本文
result_message_complete_frame = 0  # 勝利メッセージが全文表示し終わるフレーム（= 最後の文字が追加される瞬間）
result_win_bgm_start_frame    = 0  # 勝利BGMの再生を開始するフレーム（= メッセージ表示完了から指定フレーム経過した瞬間）
voice_battle_start_list = []  # エンカウント時かけ声候補（bunny_battle_start_<番号>.mp3 を全て読み込み、再生時にランダム選択する）
voice_attack_by_number = {}  # 攻撃ボイス（{番号: Sound}。bunny_attack_<番号>.mp3 の番号をキーとし、攻撃手段ごとに候補番号を選んで再生する）
voice_goblin_damaged = None  # 敵（ゴブリン）被弾やられボイス

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
# time_stretch_pcm()：OLA法（重複加算）によりピッチを維持したまま
#                     再生速度のみを変更する（16bit PCM専用）
# ---------------------------------------------------------
def time_stretch_pcm(raw, channels, speed, frame_size, overlap):
    samples = array.array('h')
    samples.frombytes(raw)
    n_frames_total = len(samples) // channels
    frame_size = min(frame_size, n_frames_total)

    hop_in  = max(1, int(frame_size * (1.0 - overlap)))
    hop_out = max(1, int(hop_in / speed))

    # ハン窓：フレームの継ぎ目をクロスフェードして滑らかにする
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / (frame_size - 1)) for i in range(frame_size)]

    out_capacity  = int(n_frames_total / speed) + frame_size
    out_buffer    = [0.0] * (out_capacity * channels)
    weight_buffer = [0.0] * out_capacity

    in_pos = 0
    out_pos = 0
    while in_pos + frame_size <= n_frames_total:
        for i in range(frame_size):
            w = window[i]
            src = (in_pos + i) * channels
            dst = (out_pos + i) * channels
            for ch in range(channels):
                out_buffer[dst + ch] += samples[src + ch] * w
            weight_buffer[out_pos + i] += w
        in_pos  += hop_in
        out_pos += hop_out

    result = array.array('h', [0] * (out_pos * channels))
    for i in range(out_pos):
        w = weight_buffer[i] if weight_buffer[i] > 1e-6 else 1.0
        for ch in range(channels):
            idx = i * channels + ch
            result[idx] = max(-32768, min(32767, int(out_buffer[idx] / w)))

    return result.tobytes()

# ---------------------------------------------------------
# load_sound_at_speed()：再生速度を変更したSoundを生成する
#                        （ピッチはtime_stretch_pcmにより維持される）
# ---------------------------------------------------------
def load_sound_at_speed(path, speed):
    sound = pygame.mixer.Sound(path)
    if speed == 1.0:
        return sound

    _, _, mixer_channels = pygame.mixer.get_init()
    stretched_raw = time_stretch_pcm(
        sound.get_raw(), mixer_channels, speed,
        VOICE_TIME_STRETCH_FRAME_SIZE, VOICE_TIME_STRETCH_OVERLAP
    )
    return pygame.mixer.Sound(buffer=stretched_raw)

# ---------------------------------------------------------
# load_win_voices()：bunny_win_<番号>.mp3 を全て検出して読み込み、
#                    再生速度変更後のSoundを {番号: Sound} の辞書として返す
#                    （リザルト開始時にランダム選択し、対応する勝利メッセージ RESULT_VICTORY_MESSAGES と組み合わせて使う）
# ---------------------------------------------------------
def load_win_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("bunny_win_")]

    def voice_number(fname):
        return int(os.path.splitext(fname)[0].split("_")[-1])

    voices_by_number = {}
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_WIN_SPEED)
        voice.set_volume(VOICE_WIN_VOLUME)
        voices_by_number[voice_number(fname)] = voice

    return voices_by_number

# ---------------------------------------------------------
# load_battle_start_voices()：bunny_battle_start_<番号>.mp3 を全て検出して読み込み、
#                             Soundのリストとして返す（エンカウントのたびランダムに選んで再生する）
# ---------------------------------------------------------
def load_battle_start_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("bunny_battle_start_")]

    voices = []
    for fname in files:
        voice = pygame.mixer.Sound(os.path.join(VOICES_DIR, fname))
        voice.set_volume(VOICE_BATTLE_START_VOLUME)
        voices.append(voice)

    return voices

# ---------------------------------------------------------
# play_battle_start_voice()：エンカウント時のかけ声候補の中からランダムに選んで再生する
# ---------------------------------------------------------
def play_battle_start_voice():
    if voice_battle_start_list:
        random.choice(voice_battle_start_list).play()

# ---------------------------------------------------------
# load_attack_voices()：bunny_attack_<番号>.mp3 を全て検出して読み込み、
#                       再生速度変更後のSoundを {番号: Sound} の辞書として返す
#                       （攻撃手段ごとに BATTLE_*_ATTACK_VOICE_NUMBERS で候補番号を指定し、再生時にランダム選択する）
# ---------------------------------------------------------
def load_attack_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("bunny_attack_")]

    def voice_number(fname):
        return int(os.path.splitext(fname)[0].split("_")[-1])

    voices_by_number = {}
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_ATTACK_SPEED)
        voice.set_volume(VOICE_ATTACK_VOLUME)
        voices_by_number[voice_number(fname)] = voice

    return voices_by_number

# ---------------------------------------------------------
# play_attack_voice()：選択中のコマンド（ムチ／炎）に応じたボイス候補番号の中から、
#                      実際に読み込めたものをランダムに選んで再生する
# ---------------------------------------------------------
def play_attack_voice():
    numbers = (BATTLE_FLAME_ATTACK_VOICE_NUMBERS if battle_menu_selected_index == BATTLE_MENU_INDEX_FLAME
               else BATTLE_WHIP_ATTACK_VOICE_NUMBERS)
    candidates = [voice_attack_by_number[n] for n in numbers if n in voice_attack_by_number]
    if candidates:
        random.choice(candidates).play()

# ---------------------------------------------------------
# find_alive_enemy_index(start_index, step)：撃破済みでない敵を探して、そのインデックスを返す
# start_index から step（+1 または -1）方向へ巡回的に探索する。全滅している場合は start_index を返す
# ---------------------------------------------------------
def find_alive_enemy_index(start_index, step):
    n = len(enemy_defeated)
    idx = start_index
    for _ in range(n):
        idx = (idx + step) % n
        if not enemy_defeated[idx]:
            return idx
    return start_index

# ---------------------------------------------------------
# start_battle_turn()：行動順（battle_turn_order）の現在の番のキャラクターについて、
#                      接近・攻撃演出ステートを初期化する（ヒロインの番なら攻撃ボイスもここで再生する）
# ---------------------------------------------------------
def start_battle_turn():
    global battle_whip_phase, battle_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_enemy_attack_phase, battle_enemy_attack_frame, battle_attacking_enemy_index

    attacker = battle_turn_order[battle_turn_index]
    if attacker == -1:
        battle_attacking_enemy_index = -1
        if battle_menu_selected_index == BATTLE_MENU_INDEX_FLAME:
            battle_flame_phase = BATTLE_FLAME_PHASE_CAST
            battle_flame_frame = 0
        else:
            battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
            battle_whip_frame = 0
        play_attack_voice()
    else:
        battle_attacking_enemy_index = attacker
        battle_enemy_attack_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_enemy_attack_frame = 0

# ---------------------------------------------------------
# advance_battle_turn()：現在の番の演出が完了したあと、次の番へ進める
# （途中で撃破された敵の番はスキップする。全員の番が終わったらコマンド選択ステートへ戻る）
# ---------------------------------------------------------
def advance_battle_turn():
    global battle_turn_index, battle_phase
    global battle_whip_phase, battle_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_attacking_enemy_index

    battle_attacking_enemy_index = -1

    battle_turn_index += 1
    while battle_turn_index < len(battle_turn_order):
        attacker = battle_turn_order[battle_turn_index]
        if attacker != -1 and enemy_defeated[attacker]:
            battle_turn_index += 1
            continue
        break

    if battle_turn_index >= len(battle_turn_order):
        battle_phase = BATTLE_PHASE_COMMAND
        battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_whip_frame = 0
        battle_flame_phase = BATTLE_FLAME_PHASE_CAST
        battle_flame_frame = 0
    else:
        start_battle_turn()

# ---------------------------------------------------------
# initialize()
# ---------------------------------------------------------
def initialize():
    global tile_map, walk_images, last_image, battle_back_img, battle_back_img_raw
    global result_win_img, result_win_img_raw, enemy_img_raw, voice_win_by_number
    global voice_battle_start_list, voice_attack_by_number, voice_goblin_damaged
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

    # ★ 敵（goblin）画像を読み込み（描画時にスケールするためオリジナルのみ保持）
    enemy_img_raw = pygame.image.load(ENEMY_GOBLIN_IMG_PATH).convert_alpha()

    voice_win_by_number = load_win_voices()

    voice_battle_start_list = load_battle_start_voices()

    voice_attack_by_number = load_attack_voices()

    voice_goblin_damaged = pygame.mixer.Sound(VOICE_GOBLIN_DAMAGED_PATH)
    voice_goblin_damaged.set_volume(VOICE_GOBLIN_DAMAGED_VOLUME)

    player_world_x, player_world_y = resolve_collision(player_world_x, player_world_y)

# ---------------------------------------------------------
# enter_result_state()：バトルからリザルトへ遷移する
# ---------------------------------------------------------
def enter_result_state(heroine_override=None):
    global game_state
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame
    global result_flashout_heroine_override
    global result_win_voice
    global result_victory_message, result_message_complete_frame, result_win_bgm_start_frame

    game_state = STATE_RESULT
    battle_flashout_frame    = 0
    result_white_delay_frame = 0
    result_slidein_frame     = 0
    result_text_delay_frame  = 0
    result_text_frame        = 0
    # フラッシュアウト中のヒロイン表示位置・スケールの上書き指定（(x, 足元y, 画像高さ) のタプル、または None＝通常位置）
    # ムチで最後の敵を倒した直後にリザルトへ遷移した場合などに、表示位置が瞬間的にスナップして見えるのを防ぐために使う
    result_flashout_heroine_override = heroine_override

    # 勝利ボイスを候補からランダムに選び、対応する勝利メッセージ・タイミング関連の値を算出する
    # （メッセージ文字数は候補ごとに異なるため、ここで毎回算出し直す）
    win_voice_number = random.choice(list(voice_win_by_number.keys()))
    result_win_voice = voice_win_by_number[win_voice_number]
    result_victory_message = RESULT_VICTORY_MESSAGES.get(win_voice_number, '')
    result_message_complete_frame = (len(result_victory_message) - 1) * RESULT_TEXT_FRAMES_PER_CHAR
    result_win_bgm_start_frame = result_message_complete_frame + RESULT_WIN_BGM_DELAY_FRAMES

    pygame.mixer.music.stop()

    # 勝利BGM代用（battle.mp3の指定秒数からの再生）の「先読みシーク」をここで済ませておく。
    # MP3は途中の再生位置へシークする際に先頭からのデコードが必要で処理時間がかかり、
    # 本来の再生開始タイミング（result_win_bgm_start_frame）で行うと一瞬処理落ちして
    # 「ひっかかる」ように感じられてしまう。そのため、まだ何も始まっていないこの時点で
    # 無音・一時停止の状態でシークだけ先に終わらせ、本番では unpause するだけにする
    pygame.mixer.music.load(BGM_BATTLE_PATH)
    pygame.mixer.music.set_volume(0.0)
    pygame.mixer.music.play(start=RESULT_WIN_BGM_START_SEC)
    pygame.mixer.music.pause()

# ---------------------------------------------------------
# process_input()
# ---------------------------------------------------------
def process_input():
    global zoom, walk_images, last_image
    global move_x, move_y
    global moving
    global game_state, battle_anim_frame
    global heroine_focus_delay_frame, heroine_zoomout_frame, heroine_idle_frame
    global heroine_idle_phase_offset
    global enemy_silhouette_frame, enemy_idle_frame, enemy_idle_phase_offsets
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame
    global battle_menu_selected_index
    global battle_target_enemy_index, battle_target_cursor_frame
    global battle_phase, battle_exchange_frame
    global battle_whip_phase, battle_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_turn_order, battle_turn_index
    global battle_enemy_attack_phase, battle_enemy_attack_frame, battle_attacking_enemy_index
    global enemy_defeated, enemy_hp, battle_annihilate_targets, battle_annihilate_frame
    global is_paused, pause_step_requested
    global pause_step_key_held, pause_step_key_hold_frame, pause_step_key_repeated

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
                heroine_idle_phase_offset = random.randint(0, BATTLE_HEROINE_IDLE_PERIOD_FRAMES - 1)
                enemy_silhouette_frame   = 0
                enemy_idle_frame         = 0
                enemy_idle_phase_offsets = [random.randint(0, ENEMY_IDLE_PERIOD_FRAMES - 1)
                                            for _ in range(len(ENEMY_X_RATIOS))]
                battle_flashout_frame    = 0
                result_white_delay_frame = 0
                result_slidein_frame     = 0
                result_text_delay_frame  = 0
                result_text_frame        = 0
                battle_menu_selected_index = 0
                battle_target_enemy_index  = 0
                battle_target_cursor_frame = 0
                battle_phase = BATTLE_PHASE_COMMAND
                battle_exchange_frame = 0
                battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
                battle_whip_frame = 0
                battle_flame_phase = BATTLE_FLAME_PHASE_CAST
                battle_flame_frame = 0
                battle_turn_order = []
                battle_turn_index = 0
                battle_enemy_attack_phase = BATTLE_WHIP_PHASE_APPROACH
                battle_enemy_attack_frame = 0
                battle_attacking_enemy_index = -1
                enemy_defeated = [False] * len(ENEMY_X_RATIOS)
                enemy_hp = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)
                battle_annihilate_targets = []
                battle_annihilate_frame   = 0
                pygame.mixer.music.load(BGM_BATTLE_PATH)
                pygame.mixer.music.set_volume(BGM_BATTLE_VOLUME)
                pygame.mixer.music.play()

        # [開発用] Pキー：システムポーズの切り替え（フレーム処理を停止／再開。描画は継続。BGM/SEも連動して一時停止／再開）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            is_paused = not is_paused
            pause_step_requested = False
            pause_step_key_held       = False
            pause_step_key_hold_frame = 0
            pause_step_key_repeated   = False
            if is_paused:
                pygame.mixer.pause()
                pygame.mixer.music.pause()
                pygame.display.set_caption(WINDOW_TITLE + WINDOW_TITLE_PAUSED_SUFFIX)
                set_titlebar_color(WINDOW_TITLE_PAUSED_COLOR)
            else:
                pygame.mixer.unpause()
                pygame.mixer.music.unpause()
                pygame.display.set_caption(WINDOW_TITLE)
                set_titlebar_color(None)

        # [開発用] Fキー：敵を倒したことにしてリザルトへ
        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            if game_state == STATE_BATTLE:
                enter_result_state()

        # 攻撃選択サブウィンドウ：上下キーで選択位置を変更（ズームアウト完了後・コマンド選択中のみ）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase == BATTLE_PHASE_COMMAND):
                battle_menu_selected_index = (battle_menu_selected_index - 1) % len(BATTLE_MENU_OPTIONS)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase == BATTLE_PHASE_COMMAND):
                battle_menu_selected_index = (battle_menu_selected_index + 1) % len(BATTLE_MENU_OPTIONS)

        # ムチ選択中：左右キーで攻撃対象の敵を変更（ズームアウト完了後・コマンド選択中のみ。撃破済みの敵は選択をスキップする）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase == BATTLE_PHASE_COMMAND and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP):
                battle_target_enemy_index = find_alive_enemy_index(battle_target_enemy_index, -1)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase == BATTLE_PHASE_COMMAND and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP):
                battle_target_enemy_index = find_alive_enemy_index(battle_target_enemy_index, 1)

        # Enterキー：攻撃選択サブウィンドウで実行 → 攻防ステートへ遷移（コマンドウィンドウは非表示）／リザルト画面からフィールドへ
        # （システムポーズ中は意図しない進行を防ぐため無効）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and not is_paused:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase == BATTLE_PHASE_COMMAND):
                battle_phase = BATTLE_PHASE_EXCHANGE
                battle_exchange_frame = 0
                if battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME):
                    # 行動順を決定する：生存している敵全体とヒロイン（-1）を含めてランダムにシャッフルする
                    alive_indices = [i for i in range(len(enemy_defeated)) if not enemy_defeated[i]]
                    battle_turn_order = [-1] + alive_indices
                    random.shuffle(battle_turn_order)
                    battle_turn_index = 0
                    start_battle_turn()
            elif game_state == STATE_RESULT:
                game_state = STATE_FIELD
                pygame.mixer.music.fadeout(BGM_FIELD_RETURN_FADEOUT_MS)

        # Spaceキー：ポーズ中は1フレームだけ処理を進める（押し続けるとキーリピートでも進む）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if is_paused:
                pause_step_requested = True
                pause_step_key_held       = True
                pause_step_key_hold_frame = 0
                pause_step_key_repeated   = False

        # Spaceキーを離した瞬間：キーリピートの判定状態をリセットする
        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            pause_step_key_held       = False
            pause_step_key_hold_frame = 0
            pause_step_key_repeated   = False

    # ポーズ中、Spaceキーを押し続けている間のキーリピート処理
    # （最初は PAUSE_STEP_REPEAT_DELAY_FRAMES 経過後に1回、以後は PAUSE_STEP_REPEAT_INTERVAL_FRAMES ごとに1フレームずつ進める）
    if is_paused and pause_step_key_held:
        pause_step_key_hold_frame += 1
        repeat_threshold = (PAUSE_STEP_REPEAT_INTERVAL_FRAMES if pause_step_key_repeated
                            else PAUSE_STEP_REPEAT_DELAY_FRAMES)
        if pause_step_key_hold_frame >= repeat_threshold:
            pause_step_requested = True
            pause_step_key_hold_frame = 0
            pause_step_key_repeated = True

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
    global enemy_silhouette_frame, enemy_idle_frame
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame
    global battle_phase, battle_exchange_frame
    global battle_whip_phase, battle_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_enemy_attack_phase, battle_enemy_attack_frame
    global battle_target_cursor_frame
    global battle_target_enemy_index
    global enemy_defeated, enemy_hp, battle_annihilate_targets, battle_annihilate_frame
    global heroine_hp

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
        if result_text_frame == 0 and result_win_voice:
            result_win_voice.play()
        # 勝利セリフが全文表示し終わってから指定フレーム経過した瞬間に勝利BGM（battle.mp3の指定秒数）を再生
        # ※ シークは enter_result_state() で先読み済みのため、ここでは音量を戻して再開するだけ
        #   （その場で play(start=...) すると、シークによる処理落ちで「ひっかかる」ように感じられる）
        if result_text_frame == result_win_bgm_start_frame:
            pygame.mixer.music.set_volume(BGM_BATTLE_VOLUME)
            pygame.mixer.music.unpause()
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

        # ③ ズームアウト：静止が完了した瞬間にかけ声をランダムに選んで再生
        if heroine_zoomout_frame == 0:
            play_battle_start_voice()
        if heroine_zoomout_frame < BATTLE_HEROINE_ZOOMOUT_FRAMES:
            heroine_zoomout_frame += 1
            return

        # ④ 待機モーション（無限ループ）／敵の黒シルエット解除と待機モーション／攻撃対象カーソルの点滅
        heroine_idle_frame += 1
        if enemy_silhouette_frame < ENEMY_SILHOUETTE_RELEASE_FRAMES:
            enemy_silhouette_frame += 1
        enemy_idle_frame += 1
        battle_target_cursor_frame += 1

        # 殲滅演出（アルファ値を下げて消滅）の経過フレームを進める
        # ステート（攻防／コマンド選択）に関わらず必ず完了まで進めることで、半透明のまま表示され続けるのを防ぐ
        if (battle_annihilate_targets
                and battle_annihilate_frame < BATTLE_ANNIHILATE_FRAMES):
            battle_annihilate_frame += 1

        # ④.5 攻防ステート：コマンド実行後、専用の演出を行いコマンド選択ステートへ戻る
        if battle_phase == BATTLE_PHASE_EXCHANGE:
            if battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME):
                # 攻防ステート（ムチ・炎選択時）：ヒロインと生存中の敵全体が、ランダムに決定された行動順（battle_turn_order）に
                # 従って1体ずつ「接近 → 攻撃」を行う。一巡したらコマンド選択ステートへ戻る
                if battle_attacking_enemy_index == -1:
                    # ヒロインの番：選択中のコマンドに応じてムチ（単体攻撃）／炎（全体攻撃）の演出を行う
                    if battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP:
                        # ムチ：攻撃対象（battle_target_enemy_index）を攻撃する
                        # （接近 → 最接近（攻撃ボイス再生） → ダメージ待機 → 白色点滅 → 元の位置へ後退）
                        if battle_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            battle_whip_frame += 1
                            if battle_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                battle_whip_frame = 0
                        elif battle_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                            battle_whip_frame += 1
                            if battle_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                battle_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                battle_whip_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                            battle_whip_frame += 1
                            if battle_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                # ダメージ演出完了の瞬間にHPを更新する（0未満にはならない。0になっていたら撃破扱い）
                                target = battle_target_enemy_index
                                damage = random.randint(BATTLE_WHIP_DAMAGE_MIN, BATTLE_WHIP_DAMAGE_MAX)
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)

                                if enemy_hp[target] <= 0:
                                    # 撃破：殲滅演出（アルファ値を下げて消滅）を開始する
                                    # （対象インデックスはこの時点では変更しない：後退アニメは「撃破した敵の位置」を基準に行うため、
                                    #   後退が完了するまでは battle_target_enemy_index を維持する）
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0

                                if all(enemy_defeated):
                                    # 最後の敵を撃破：後退はせず、ダメージ演出完了直後に既存の戦闘終了演出（リザルトへの遷移）を行う
                                    # （行動順が一巡する前でも、その時点で戦闘を終了する）
                                    whip_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                    whip_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                    whip_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE)
                                    enter_result_state(heroine_override=(whip_target_x, whip_target_bottom_y, whip_target_img_h))
                                else:
                                    # 敵が残っている場合は今まで通り元の位置へ後退する
                                    battle_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                    battle_whip_frame = 0
                        elif battle_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            battle_whip_frame += 1
                            if battle_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                # 元の位置に戻り終えたら、撃破した敵の次に生存している敵を選択し、次の番へ進める
                                # （後退アニメ完了後に変更することで、後退中に対象が別の敵の位置に切り替わって見える不具合を防ぐ）
                                battle_target_enemy_index = find_alive_enemy_index(battle_target_enemy_index, 1)
                                advance_battle_turn()
                    else:
                        # 炎：その場にとどまったまま詠唱し（攻撃ボイスは番開始時に再生済み）、
                        # 一定フレーム待機後、生存中の敵全体に同時に赤色点滅ダメージを与える
                        if battle_flame_phase == BATTLE_FLAME_PHASE_CAST:
                            battle_flame_frame += 1
                            if battle_flame_frame >= BATTLE_FLAME_CAST_DELAY_FRAMES:
                                battle_flame_phase = BATTLE_FLAME_PHASE_FLASH
                                battle_flame_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_flame_phase == BATTLE_FLAME_PHASE_FLASH:
                            battle_flame_frame += 1
                            if battle_flame_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                # ダメージ演出完了の瞬間に、生存中の敵全体へ個別にランダムダメージを与えてHPを更新する
                                # （0未満にはならない。0になった敵はその場で撃破扱いとなり、同時に殲滅演出を開始する）
                                newly_defeated = []
                                for i in range(len(enemy_defeated)):
                                    if enemy_defeated[i]:
                                        continue
                                    damage = random.randint(BATTLE_FLAME_DAMAGE_MIN, BATTLE_FLAME_DAMAGE_MAX)
                                    enemy_hp[i] = max(0, enemy_hp[i] - damage)
                                    if enemy_hp[i] <= 0:
                                        enemy_defeated[i] = True
                                        newly_defeated.append(i)

                                if newly_defeated:
                                    battle_annihilate_targets = newly_defeated
                                    battle_annihilate_frame   = 0

                                if all(enemy_defeated):
                                    # 全滅：ヒロインは接近していないため、後退や表示位置の上書きは不要
                                    enter_result_state()
                                else:
                                    advance_battle_turn()
                else:
                    # 敵の番：battle_attacking_enemy_index の敵がヒロインに接近して攻撃する（流れはムチと同じ4ステート）
                    # 敵の攻撃ボイス・ヒロインのやられボイスは未実装のため再生しない
                    if battle_enemy_attack_phase == BATTLE_WHIP_PHASE_APPROACH:
                        battle_enemy_attack_frame += 1
                        if battle_enemy_attack_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                            battle_enemy_attack_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                            battle_enemy_attack_frame = 0
                    elif battle_enemy_attack_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                        battle_enemy_attack_frame += 1
                        if battle_enemy_attack_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                            battle_enemy_attack_phase = BATTLE_WHIP_PHASE_FLASH
                            battle_enemy_attack_frame = 0
                    elif battle_enemy_attack_phase == BATTLE_WHIP_PHASE_FLASH:
                        battle_enemy_attack_frame += 1
                        if battle_enemy_attack_frame >= BATTLE_WHIP_FLASH_FRAMES:
                            # ダメージ演出完了の瞬間にヒロインのHPを更新する（0未満にはならない。0になっても現状は何も起きない）
                            damage = random.randint(BATTLE_ENEMY_ATTACK_DAMAGE_MIN, BATTLE_ENEMY_ATTACK_DAMAGE_MAX)
                            heroine_hp = max(0, heroine_hp - damage)
                            battle_enemy_attack_phase = BATTLE_WHIP_PHASE_RETURN
                            battle_enemy_attack_frame = 0
                    elif battle_enemy_attack_phase == BATTLE_WHIP_PHASE_RETURN:
                        battle_enemy_attack_frame += 1
                        if battle_enemy_attack_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                            # 元の位置に戻り終えたら次の番へ進める（ヒロインが力尽きることはないため、そのまま進行する）
                            advance_battle_turn()
            else:
                # 未実装の攻撃手段：仮の経過フレーム数でコマンド選択ステートへ戻る
                battle_exchange_frame += 1
                if battle_exchange_frame >= BATTLE_EXCHANGE_FRAMES:
                    battle_phase = BATTLE_PHASE_COMMAND
                    battle_exchange_frame = 0

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

    screen.blit(font.render(f"FPS: {clock.get_fps():.1f}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Player: ({player_world_x:.2f}, {player_world_y:.2f})", True, (255, 255, 255)), (10, 30))
    screen.blit(font.render(f"Camera: ({camera_world_x:.2f}, {camera_world_y:.2f})", True, (255, 255, 0)), (10, 50))
    screen.blit(font.render(f"Zoom: {zoom:.2f}", True, (0, 200, 255)), (10, 70))

    collider_px = int(PLAYER_COLLIDER_RADIUS * METER_TO_PIXEL * zoom)
    cx, cy = world_to_screen(player_world_x, player_world_y)

    if is_near_mountain(player_world_x, player_world_y):
        color = (255, 255, 0)
    else:
        color = (0, 128, 255)

    pygame.draw.circle(screen, color, (cx, cy), collider_px, 2)

# ---------------------------------------------------------
# blit_heroine_trail_image(raw_img, pos, alpha)：残像（直近フレームの位置・スケールのヒロイン画像）を半透明で描画する
# pos は (x, 足元y, 画像高さ) のタプル。alpha は不透明度（0.0～1.0）
# ---------------------------------------------------------
def blit_heroine_trail_image(raw_img, pos, alpha):
    x, boty, h = pos
    orig_w, orig_h = raw_img.get_size()
    w = max(1, int(orig_w * h / orig_h))
    trail_img = pygame.transform.smoothscale(raw_img, (w, h))
    trail_img.set_alpha(int(255 * alpha))
    screen.blit(trail_img, trail_img.get_rect(midbottom=(x, boty)))

# ---------------------------------------------------------
# render_battle()
# ---------------------------------------------------------
def render_battle():
    global heroine_whip_trail_key

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

    # ★ 敵（goblin）の描画：黒シルエット → 通常表示への解除（ヒロインの奥＝先に描画）
    if enemy_img_raw:
        enemy_orig_w, enemy_orig_h = enemy_img_raw.get_size()

        # ズームアウト進行度（0.0 → 1.0）：ヒロインと同じタイミングで指定スケールへ収束
        enemy_t_zoom = min(1.0, heroine_zoomout_frame / BATTLE_HEROINE_ZOOMOUT_FRAMES) \
                       if BATTLE_HEROINE_ZOOMOUT_FRAMES > 0 else 1.0
        enemy_t_eased = 1.0 - (1.0 - enemy_t_zoom) ** 2

        enemy_start_img_h = int(SCREEN_H * ENEMY_GOBLIN_FIRST_SCALE)
        enemy_end_img_h   = int(SCREEN_H * ENEMY_GOBLIN_LAST_SCALE)
        enemy_img_h = max(1, int(enemy_start_img_h + (enemy_end_img_h - enemy_start_img_h) * enemy_t_eased))

        enemy_img_w = max(1, int(enemy_orig_w * enemy_img_h / enemy_orig_h))
        enemy_base_img = pygame.transform.smoothscale(enemy_img_raw, (enemy_img_w, enemy_img_h))

        # 黒シルエット → 通常表示：ズームアウト完了直後から数フレームかけて解除
        reveal_t = min(1.0, enemy_silhouette_frame / ENEMY_SILHOUETTE_RELEASE_FRAMES) \
                   if ENEMY_SILHOUETTE_RELEASE_FRAMES > 0 else 1.0
        if reveal_t < 1.0:
            gray = int(255 * reveal_t)
            tint = pygame.Surface(enemy_base_img.get_size(), pygame.SRCALPHA)
            tint.fill((gray, gray, gray, 255))
            enemy_base_img = enemy_base_img.copy()
            enemy_base_img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # 足元位置は登場時から変えない（ENEMY_GROUND_Y_FROM_BOTTOM_RATIO基準で固定）
        enemy_bottom_y = SCREEN_H - int(SCREEN_H * ENEMY_GROUND_Y_FROM_BOTTOM_RATIO)

        # ★ ムチ被弾時の白色点滅（ダメージ表現）：対象の敵にBLEND_RGB_ADDで白を加算し、点滅させる
        # BLEND_RGB_ADDはアルファ値を変えずRGBのみ加算するため、シルエットや透過部分を保ったまま白っぽく光らせられる
        whip_flash_active = (battle_phase == BATTLE_PHASE_EXCHANGE
                             and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP
                             and battle_attacking_enemy_index == -1
                             and battle_whip_phase == BATTLE_WHIP_PHASE_FLASH)
        flash_blink_on = False
        if whip_flash_active:
            blink_half = max(1, BATTLE_WHIP_FLASH_BLINK_PERIOD_FRAMES // 2)
            flash_blink_on = (battle_whip_frame // blink_half) % 2 == 0

        # ★ 炎（全体攻撃）の赤色点滅：ムチと同じ点滅周期パラメータを流用し、生存中の敵全体を同時に赤く光らせる
        flame_flash_active = (battle_phase == BATTLE_PHASE_EXCHANGE
                              and battle_menu_selected_index == BATTLE_MENU_INDEX_FLAME
                              and battle_attacking_enemy_index == -1
                              and battle_flame_phase == BATTLE_FLAME_PHASE_FLASH)
        flame_flash_blink_on = False
        if flame_flash_active:
            flame_blink_half = max(1, BATTLE_WHIP_FLASH_BLINK_PERIOD_FRAMES // 2)
            flame_flash_blink_on = (battle_flame_frame // flame_blink_half) % 2 == 0

        # ★ 敵の攻撃演出（ヒロインに接近 → 最接近で停止 → 元の位置へ後退）の進行度
        enemy_attack_active = (battle_phase == BATTLE_PHASE_EXCHANGE
                               and battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME)
                               and battle_attacking_enemy_index >= 0)
        enemy_attack_t = 0.0
        if enemy_attack_active:
            if battle_enemy_attack_phase == BATTLE_WHIP_PHASE_APPROACH:
                raw_t = (battle_enemy_attack_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                enemy_attack_t = 1.0 - (1.0 - raw_t) ** 2          # ヒロインに近づくほど減速
            elif battle_enemy_attack_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                enemy_attack_t = 1.0
            else:  # BATTLE_WHIP_PHASE_RETURN
                raw_t = (battle_enemy_attack_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                enemy_attack_t = (1.0 - raw_t) ** 2                # 元の位置に近づくほど減速
            enemy_attack_t = max(0.0, min(1.0, enemy_attack_t))

        # ENEMY_X_RATIOSで指定した横位置に1体ずつ並べて表示
        enemy_rects = []
        clip_rect = pygame.Rect(0, band_y, SCREEN_W, current_height)
        screen.set_clip(clip_rect)
        for i, x_ratio in enumerate(ENEMY_X_RATIOS):
            enemy_img = enemy_base_img
            enemy_x = int(SCREEN_W * x_ratio)
            enemy_img_bottom_y = enemy_bottom_y
            is_attacking = enemy_attack_active and i == battle_attacking_enemy_index

            if is_attacking:
                # ★ 敵の攻撃：ヒロインに接近 → 指定スケール・位置で最接近 → 元の位置へ後退
                # 接近・後退とも、目的地に近づくほど減速する ease-out 補間（ムチ演出と同じ手法）を用いる
                # （攻撃中は待機モーションを適用しない＝スケール変化と競合させないため）
                attack_target_x = SCREEN_W // 2
                attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE)

                enemy_x = int(enemy_x + (attack_target_x - enemy_x) * enemy_attack_t)
                enemy_img_bottom_y = int(enemy_bottom_y + (attack_target_bottom_y - enemy_bottom_y) * enemy_attack_t)
                target_img_h = max(1, int(enemy_img_h + (attack_target_img_h - enemy_img_h) * enemy_attack_t))
                target_img_w = max(1, int(enemy_img.get_width() * target_img_h / enemy_img.get_height()))
                enemy_img = pygame.transform.smoothscale(enemy_img, (target_img_w, target_img_h))
            elif heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
                # 待機モーション：縦横逆位相スクワッシュ（ズームアウト完了後・攻撃中以外のみ適用）
                # 個体ごとに位相をランダムにずらし、3体が同期して動かないようにする（周期はENEMY_IDLE_PERIOD_FRAMESで共通）
                phase = enemy_idle_phase_offsets[i] if i < len(enemy_idle_phase_offsets) else 0
                enemy_idle_t = math.sin((enemy_idle_frame + phase) / ENEMY_IDLE_PERIOD_FRAMES * 2 * math.pi)
                enemy_sx = 1.0 + ENEMY_IDLE_SCALE_DELTA * enemy_idle_t
                enemy_sy = 1.0 - ENEMY_IDLE_SCALE_DELTA * enemy_idle_t
                enemy_idle_w = max(1, int(enemy_img.get_width()  * enemy_sx))
                enemy_idle_h = max(1, int(enemy_img.get_height() * enemy_sy))
                enemy_img = pygame.transform.smoothscale(enemy_img, (enemy_idle_w, enemy_idle_h))
                # スケーリング中心 = 敵の足元：enemy_bottom_y はそのまま維持

            # 攻撃対象の敵をダメージ演出として点滅させる（ムチ＝対象の敵のみを白色点滅／炎＝生存中の敵全体を赤色点滅）
            whip_flashing  = whip_flash_active and flash_blink_on and i == battle_target_enemy_index
            flame_flashing = flame_flash_active and flame_flash_blink_on and not enemy_defeated[i]
            if whip_flashing or flame_flashing:
                flash_color = BATTLE_FLAME_FLASH_COLOR if flame_flashing else BATTLE_WHIP_FLASH_COLOR
                enemy_img = enemy_img.copy()
                enemy_img.fill(flash_color, special_flags=pygame.BLEND_RGB_ADD)

            enemy_rect = enemy_img.get_rect(midbottom=(enemy_x, enemy_img_bottom_y))

            # ★ 撃破演出：殲滅対象の敵は数フレームかけてアルファ値を下げ、完全に消滅させる（消滅後は描画しない）
            if i in battle_annihilate_targets:
                annihilate_t = min(1.0, battle_annihilate_frame / BATTLE_ANNIHILATE_FRAMES) \
                               if BATTLE_ANNIHILATE_FRAMES > 0 else 1.0
                alpha = int(255 * (1.0 - annihilate_t))
                if alpha > 0:
                    enemy_img = enemy_img.copy()
                    enemy_img.set_alpha(alpha)
                    screen.blit(enemy_img, enemy_rect)
            elif not enemy_defeated[i]:
                screen.blit(enemy_img, enemy_rect)

            # [デバッグ表示] 敵のHPを「現在HP/最大HP」の文字列で頭上に表示する（生存中のみ）
            if not enemy_defeated[i]:
                enemy_hp_text = font.render(f"{enemy_hp[i]}/{GOBLIN_MAX_HP}", True, (255, 255, 255))
                enemy_hp_rect = enemy_hp_text.get_rect(midbottom=(enemy_rect.centerx, enemy_rect.top - 4))
                screen.blit(enemy_hp_text, enemy_hp_rect)

            enemy_rects.append(enemy_rect)

        # ★ 攻撃対象選択カーソル（対象の敵の頭上に点滅表示する下向き三角カーソル）
        # ムチ選択中：左右キーで選んだ対象1体のみ／炎選択中：全体攻撃のため生存中の敵全体に表示する
        # HPデバッグ表示と被らないよう、頭上のクリアランスにテキスト分の高さも加味して上方へ表示する
        if (battle_phase == BATTLE_PHASE_COMMAND and battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME)
                and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES):
            if battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP:
                cursor_target_indices = [battle_target_enemy_index] if 0 <= battle_target_enemy_index < len(enemy_rects) else []
            else:
                cursor_target_indices = [i for i in range(len(enemy_rects)) if not enemy_defeated[i]]

            blink_half_period = max(1, BATTLE_TARGET_CURSOR_BLINK_PERIOD_FRAMES // 2)
            if cursor_target_indices and (battle_target_cursor_frame // blink_half_period) % 2 == 0:
                hp_text_clearance = font.get_height() + 4
                half_w = BATTLE_TARGET_CURSOR_WIDTH // 2
                for idx in cursor_target_indices:
                    target_rect = enemy_rects[idx]
                    cursor_cx = target_rect.centerx
                    cursor_top = target_rect.top - hp_text_clearance - BATTLE_TARGET_CURSOR_MARGIN_Y - BATTLE_TARGET_CURSOR_HEIGHT
                    points = [
                        (cursor_cx - half_w, cursor_top),
                        (cursor_cx + half_w, cursor_top),
                        (cursor_cx, cursor_top + BATTLE_TARGET_CURSOR_HEIGHT),
                    ]
                    pygame.draw.polygon(screen, BATTLE_TARGET_CURSOR_COLOR, points)
        screen.set_clip(None)

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

        # bottom_y：注視点（FIRST_FOCUS）を画面中央に固定したままズームアウト後は
        # ANCHOR位置がバトルウィンドウ下端に来るよう補間
        bottom_y_start = SCREEN_H // 2 + int(start_img_h * BATTLE_HEROINE_FIRST_FOCUS)
        bottom_y_end   = band_bottom + int(end_img_h * BATTLE_HEROINE_ZOOMOUT_ANCHOR)
        bottom_y = int(bottom_y_start + (bottom_y_end - bottom_y_start) * t_eased)

        heroine_x = SCREEN_W // 2

        # ★ ムチ（近接攻撃）：敵に接近 → 最接近で停止 → 元の位置へ後退
        # 接近・後退とも、進行方向の目的地に近づくほど減速する ease-out 補間（行きと帰りで共通の式 = ヒロインのズームアウト等と同じ手法）を用いる
        whip_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP
                       and battle_attacking_enemy_index == -1)
        if whip_active:
            if battle_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                raw_t = (battle_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                whip_t = 1.0 - (1.0 - raw_t) ** 2          # 敵に近づくほど減速
            elif battle_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                whip_t = 1.0
            else:  # BATTLE_WHIP_PHASE_RETURN
                raw_t = (battle_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                whip_t = (1.0 - raw_t) ** 2                # 元の位置に近づくほど減速
            whip_t = max(0.0, min(1.0, whip_t))

            whip_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_target_enemy_index])
            # 最接近時のヒロインの足元位置：横方向は敵に合わせるが、縦方向（接地ライン）は敵とは別の比率で指定する
            whip_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
            whip_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE)

            heroine_x = int(SCREEN_W // 2 + (whip_target_x - SCREEN_W // 2) * whip_t)
            bottom_y  = int(bottom_y + (whip_target_bottom_y - bottom_y) * whip_t)
            img_h     = max(1, int(img_h + (whip_target_img_h - img_h) * whip_t))

        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(battle_back_img_raw, (img_w, img_h))

        # ④ 待機モーション：縦横逆位相スクワッシュ（ズームアウト完了後・ムチ演出中以外で適用、エンカウント毎に位相をランダムにずらす）
        if heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES and not whip_active:
            idle_t = math.sin((heroine_idle_frame + heroine_idle_phase_offset) / BATTLE_HEROINE_IDLE_PERIOD_FRAMES * 2 * math.pi)
            sx = 1.0 + BATTLE_HEROINE_IDLE_SCALE_DELTA * idle_t   # 横：+側で膨らむ
            sy = 1.0 - BATTLE_HEROINE_IDLE_SCALE_DELTA * idle_t   # 縦：横と逆位相
            idle_w = max(1, int(img.get_width()  * sx))
            idle_h = max(1, int(img.get_height() * sy))
            img = pygame.transform.smoothscale(img, (idle_w, idle_h))
            # スケーリング中心 = キャラ下端：bottom_y はそのまま維持

        # ★ 敵の攻撃を受けた際の白色点滅（ダメージ表現。ムチ被弾時の敵の点滅と同じ手法）
        heroine_flash_active = (battle_phase == BATTLE_PHASE_EXCHANGE
                                and battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME)
                                and battle_attacking_enemy_index >= 0
                                and battle_enemy_attack_phase == BATTLE_WHIP_PHASE_FLASH)
        if heroine_flash_active:
            blink_half = max(1, BATTLE_WHIP_FLASH_BLINK_PERIOD_FRAMES // 2)
            if (battle_enemy_attack_frame // blink_half) % 2 == 0:
                img = img.copy()
                img.fill(BATTLE_WHIP_FLASH_COLOR, special_flags=pygame.BLEND_RGB_ADD)

        img_rect = img.get_rect(midbottom=(heroine_x, bottom_y))

        # ★ 残像（接近・後退中のみ）：BATTLE_WHIP_TRAIL_OFFSET_1/2 フレーム前の位置に半透明のヒロイン画像を重ねて表示する
        # （現在位置とほとんど同じ場合は表示しない。描画順は接近時＝現在→A→B、後退時＝B→A→現在）
        whip_moving = whip_active and battle_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
        current_pos = (heroine_x, bottom_y, img_h)
        trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

        def find_trail_pos(offset):
            if offset <= 0 or len(heroine_whip_trail) < offset:
                return None
            px, py, _ = heroine_whip_trail[-offset]
            min_offset_sq = BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2
            if (px - heroine_x) ** 2 + (py - bottom_y) ** 2 < min_offset_sq:
                return None
            return heroine_whip_trail[-offset]

        trail_a = None
        trail_b = None
        if whip_moving:
            trail_a = find_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1)
            trail_b = find_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2)

        clip_rect = pygame.Rect(0, band_y, SCREEN_W, current_height)
        screen.set_clip(clip_rect)
        if whip_active and battle_whip_phase == BATTLE_WHIP_PHASE_RETURN:
            # 戻るとき：B → A → 現在画像 の順で重ねる
            if trail_b is not None:
                blit_heroine_trail_image(battle_back_img_raw, trail_b, BATTLE_WHIP_TRAIL_ALPHA_2)
            if trail_a is not None:
                blit_heroine_trail_image(battle_back_img_raw, trail_a, BATTLE_WHIP_TRAIL_ALPHA_1)
            screen.blit(img, img_rect)
        else:
            # 近づくとき（および通常時）：現在画像 → A → B の順で重ねる
            screen.blit(img, img_rect)
            if trail_a is not None:
                blit_heroine_trail_image(battle_back_img_raw, trail_a, BATTLE_WHIP_TRAIL_ALPHA_1)
            if trail_b is not None:
                blit_heroine_trail_image(battle_back_img_raw, trail_b, BATTLE_WHIP_TRAIL_ALPHA_2)
        screen.set_clip(None)

        # [デバッグ表示] ヒロインのHPを「現在HP/最大HP」の文字列で頭上に表示する
        heroine_hp_text = font.render(f"{heroine_hp}/{HEROINE_MAX_HP}", True, (255, 255, 255))
        heroine_hp_rect = heroine_hp_text.get_rect(midbottom=(img_rect.centerx, img_rect.top - 4))
        screen.blit(heroine_hp_text, heroine_hp_rect)

        # 残像履歴を更新する（実際にフレームが進んだときのみ記録し、ポーズ中の再描画で重複登録しないようにする）
        if whip_moving:
            trail_key = (battle_whip_phase, battle_whip_frame)
            if heroine_whip_trail_key != trail_key:
                heroine_whip_trail_key = trail_key
                heroine_whip_trail.append(current_pos)
                if len(heroine_whip_trail) > trail_history_size:
                    heroine_whip_trail.pop(0)
        else:
            heroine_whip_trail.clear()
            heroine_whip_trail_key = None

    # テキスト
    text = font.render("BATTLE MODE (Press E to return)", True, (255, 255, 255))
    screen.blit(text, (SCREEN_W//2 - text.get_width()//2, band_y + 10))

    # ★ 攻撃選択サブウィンドウ（ズームアウト完了後・コマンド選択中のみ表示。攻防ステート中は非表示）
    if heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES and battle_phase == BATTLE_PHASE_COMMAND:
        render_battle_menu()

# ---------------------------------------------------------
# render_battle_menu()：攻撃選択サブウィンドウの描画
# ---------------------------------------------------------
def render_battle_menu():
    menu_x = SCREEN_W - BATTLE_MENU_WIDTH - BATTLE_MENU_MARGIN
    menu_y = BATTLE_MENU_MARGIN

    # 半透明黒の背景（角丸）
    bg = pygame.Surface((BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(
        bg, (*BATTLE_MENU_BG_COLOR, BATTLE_MENU_BG_ALPHA),
        bg.get_rect(),
        border_radius=BATTLE_MENU_BORDER_RADIUS
    )
    screen.blit(bg, (menu_x, menu_y))

    # 白い太線の枠（角丸）
    pygame.draw.rect(
        screen, BATTLE_MENU_BORDER_COLOR,
        pygame.Rect(menu_x, menu_y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT),
        BATTLE_MENU_BORDER_WIDTH,
        border_radius=BATTLE_MENU_BORDER_RADIUS
    )

    # 選択肢（上から左寄せで表示。選択中は白、それ以外はグレーアウト。文字化け対策でメイリオを使用）
    for i, label in enumerate(BATTLE_MENU_OPTIONS):
        color = BATTLE_MENU_SELECTED_COLOR if i == battle_menu_selected_index else BATTLE_MENU_UNSELECTED_COLOR
        option_text = font_battle_menu.render(label, True, color)
        text_x = menu_x + BATTLE_MENU_TEXT_PADDING_X
        text_y = menu_y + BATTLE_MENU_TEXT_PADDING_Y + i * BATTLE_MENU_LINE_HEIGHT
        screen.blit(option_text, (text_x, text_y))

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
        # （result_flashout_heroine_override が指定されている場合は、戦闘終了直前の表示位置・スケールをそのまま引き継ぐ。
        #   通常位置にスナップして見える違和感を防ぐため。例：ムチで最後の敵を倒した直後はリザルトの最接近位置を維持する）
        if battle_back_img_raw:
            orig_w, orig_h = battle_back_img_raw.get_size()
            if result_flashout_heroine_override:
                heroine_x, boty, h = result_flashout_heroine_override
            else:
                h = int(SCREEN_H * BATTLE_HEROINE_LAST_SCALE)
                heroine_x = SCREEN_W // 2
                boty = band_bottom + int(h * BATTLE_HEROINE_ZOOMOUT_ANCHOR)
            w = max(1, int(orig_w * h / orig_h))
            img = pygame.transform.smoothscale(battle_back_img_raw, (w, h))
            alpha_img = img.copy()
            alpha_img.set_alpha(int(255 * (1.0 - t)))
            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(alpha_img, img.get_rect(midbottom=(heroine_x, boty)))
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

    # スライドイン完了後、待機を経てセリフを表示
    if arrived and result_text_delay_frame >= RESULT_TEXT_DELAY_FRAMES:
        text_full = result_victory_message
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
    global pause_step_requested
    initialize()

    while True:
        dt = clock.tick(FIXED_FPS)
        process_input()

        # システムポーズ中はフレーム処理を止める（描画は継続）。
        # Enterキーで1フレームだけ処理を進める要求があった場合のみ、その回だけ処理する。
        if not is_paused:
            update(dt)
            update_camera(dt)
        elif pause_step_requested:
            pause_step_requested = False
            update(dt)
            update_camera(dt)

        render()

if __name__ == "__main__":
    main()