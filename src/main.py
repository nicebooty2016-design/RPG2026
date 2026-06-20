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
SCREEN_ASPECT_RATIO = (4, 3)  # 画面の横：縦比率（例：(4, 3) や (16, 9)）。SCREEN_HはSCREEN_Wとこの比率から自動算出される
SCREEN_H = SCREEN_W * SCREEN_ASPECT_RATIO[1] // SCREEN_ASPECT_RATIO[0]
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()

SCREEN_W_BASE = 640  # フォントサイズの基準とする画面幅（SCREEN_Wがこの値からどれだけ変化したかでフォントサイズを拡縮する）
FONT_SCALE = SCREEN_W / SCREEN_W_BASE

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
BATTLE_MAIN_WINDOW_HEIGHT_RATIO = 5 / 6  # ゲームウィンドウ高さ（SCREEN_H）の何倍かで指定する
BATTLE_MAIN_WINDOW_HEIGHT = int(SCREEN_H * BATTLE_MAIN_WINDOW_HEIGHT_RATIO)
BATTLE_MAIN_WINDOW_ANIM_FRAMES = 10   # バトルメインウィンドウが開ききるまでのフレーム数

# ヒロイン演出パラメータ：登場時／ズームアウト後それぞれについて、
# バトルウィンドウ幅（=SCREEN_W）がワールド座標系で何mに相当するかを指定する
# （この値が小さいほど、ヒロインの身長(HEROINE_HEIGHT_M)に対して画像が大きく＝ズームインして表示される）
BATTLE_HEROINE_FIRST_WINDOW_WIDTH_M = 20 / 27  # 登場時（ズームイン状態）
BATTLE_HEROINE_LAST_WINDOW_WIDTH_M  = 95 / 27  # ズームアウト後
BATTLE_HEROINE_FIRST_METER_TO_PIXEL = SCREEN_W / BATTLE_HEROINE_FIRST_WINDOW_WIDTH_M
BATTLE_HEROINE_LAST_METER_TO_PIXEL  = SCREEN_W / BATTLE_HEROINE_LAST_WINDOW_WIDTH_M

# バトルウィンドウが開いた後の静止 → ズームアウト
BATTLE_HEROINE_FOCUS_DELAY_FRAMES = 20  # 静止フレーム数
BATTLE_HEROINE_ZOOMOUT_FRAMES = 60      # ズームアウトに要するフレーム数
# 注視点：ヒロインの足元から何m上の位置（＝ワールド座標系の高さ。結果的に体の特定の部位を指す）が
# バトルウィンドウ下端に来るか。登場直後／ズームアウト完了直後それぞれで指定する
BATTLE_HEROINE_FIRST_FOCUS_M = 0  # 登場直後
BATTLE_HEROINE_LAST_FOCUS_M  = 1.1    # ズームアウト完了直後

# バトルウィンドウ色
BATTLE_WINDOW_COLOR = (30, 80, 200)  # バトル中のウィンドウ色
RESULT_WINDOW_COLOR = (0, 0, 0)      # リザルト到達後のウィンドウ色

# リザルト演出
BATTLE_FLASHOUT_FRAMES    = 40  # バトルウィンドウが黒→白にフラッシュアウトするフレーム数
RESULT_WHITE_DELAY_FRAMES = 30  # 白ウィンドウ静止フレーム数
RESULT_SLIDEIN_FRAMES     = 30  # バストショットのスライドイン所要フレーム数

# ヒロインの勝利バストショット（bunny_front.png）：ゲームウィンドウ幅(SCREEN_W)がワールド座標値で
# 何mに該当するかを指定する。ここから算出したHEROINE_HEIGHT_M分の高さに一度だけスケールし、
# 以後リザルト中の追加の拡縮（待機モーションの拡縮等）は行わない
RESULT_HEROINE_WIN_WIDTH_M = 1.0
# 表示位置：バストショット画像の上端から何mの位置を、ゲームウィンドウ上端に一致させるか
RESULT_HEROINE_WIN_TOP_MARGIN_M = 0.15

# サムライの勝利バストショット（samurai_front.png）：ゲームウィンドウ幅(SCREEN_W)がワールド座標値で
# 何mに該当するかを指定する。ここから算出したSAMURAI_HEIGHT_M分の高さに一度だけスケールし、
# 以後リザルト中の追加の拡縮（待機モーションの拡縮等）は行わない
RESULT_SAMURAI_WIN_WIDTH_M = 1.0
# 表示位置：バストショット画像の上端から何mの位置を、ゲームウィンドウ上端に一致させるか
RESULT_SAMURAI_WIN_TOP_MARGIN_M = 0.05

# 女戦士の勝利バストショット（warrior_front.png）：サムライと同様に算出する
RESULT_WARRIOR_WIN_WIDTH_M = 1.0
# 表示位置：バストショット画像の上端から何mの位置を、ゲームウィンドウ上端に一致させるか
RESULT_WARRIOR_WIN_TOP_MARGIN_M = 0.20

# シスター・くノ一・魔法使い・武道家の勝利バストショット（各自のfront.png）
RESULT_SISTER_WIN_WIDTH_M   = 1.0
RESULT_SISTER_WIN_TOP_MARGIN_M = 0.15
RESULT_KUNOICHI_WIN_WIDTH_M = 1.0
RESULT_KUNOICHI_WIN_TOP_MARGIN_M = 0.15
RESULT_WIZARD_WIN_WIDTH_M   = 1.0
RESULT_WIZARD_WIN_TOP_MARGIN_M = 0.15
RESULT_FIGHTER_WIN_WIDTH_M  = 1.0
RESULT_FIGHTER_WIN_TOP_MARGIN_M = 0.15

# 勝利ボイス（bunny_win_<番号>.mp3）ごとに対応する勝利メッセージ本文。
# リザルト開始時にボイスをランダム選択し、対応するメッセージを表示する
RESULT_VICTORY_MESSAGES = {
    0: 'もっと大きいのが欲しいの…',
    1: '凄い、こんなの初めて…',
    2: 'もうイっちゃったの？',
}
# サムライがトドメを刺した場合の勝利ボイス（samurai_win_<番号>.mp3）ごとに対応する勝利メッセージ本文
RESULT_SAMURAI_VICTORY_MESSAGES = {
    0: '皆さん、ご無事ですか・・・？',
}
# 女戦士がトドメを刺した場合の勝利ボイス（warrior_win_<番号>.mp3）ごとに対応する勝利メッセージ本文
RESULT_WARRIOR_VICTORY_MESSAGES = {
    0: '家に帰って、シコってろ！',
    1: 'もうイっちゃったのかぁ？',
}
# 新キャラがトドメを刺した場合の勝利メッセージ（ダミー。ボイスは未用意のため空dictで対応）
RESULT_SISTER_VICTORY_MESSAGES   = {0: 'ダミー'}
RESULT_KUNOICHI_VICTORY_MESSAGES = {0: 'ダミー'}
RESULT_WIZARD_VICTORY_MESSAGES   = {0: 'ダミー'}
RESULT_FIGHTER_VICTORY_MESSAGES  = {0: 'ダミー'}
VOICE_WIN_SPEED = 1.5  # 勝利ボイスの再生速度倍率（候補とも一律。この倍率に合わせて勝利メッセージの表示速度も変化する）
# 再生速度変更時のピッチ維持（OLA法による時間伸縮）パラメータ
VOICE_TIME_STRETCH_FRAME_SIZE = 1024  # 解析フレーム長（サンプル数）。大きいほど低音域の質が安定するが処理が重くなる
VOICE_TIME_STRETCH_OVERLAP    = 0.5   # フレーム間のオーバーラップ率（0.0～1.0）。大きいほど滑らかだが処理が重くなる
RESULT_TEXT_FRAMES_PER_CHAR_BASE = 12  # 勝利メッセージ1文字追加するのに要するフレーム数（等速=1.0倍時の基準値）
RESULT_TEXT_FRAMES_PER_CHAR = max(1, round(RESULT_TEXT_FRAMES_PER_CHAR_BASE / VOICE_WIN_SPEED))  # 実際に使用する値（ボイス速度倍率を反映）
RESULT_TEXT_DELAY_FRAMES   = 0  # スライドイン完了後、テキスト・ボイス開始までの待機フレーム数
RESULT_WIN_BGM_DELAY_FRAMES = 30  # メッセージ表示完了後、勝利BGM再生開始までの待機フレーム数
RESULT_WIN_BGM_START_SEC   = 157.6  # 勝利BGM代用：再生開始時にbattle.mp3を再生開始する秒数

# 音量
BGM_BATTLE_VOLUME = 0.30  # バトルBGM音量（0.0～1.0）
BGM_BATTLE2_VOLUME = 0.15  # 戦闘曲（battle2.mp3）の音量（0.0～1.0）
VOICE_WIN_VOLUME  = 1.0  # 勝利ボイス音量（0.0～1.0）
VOICE_BATTLE_START_VOLUME = 1.0  # エンカウント時かけ声の音量（0.0～1.0）
VOICE_BATTLE_START_SPEED = 1.3  # エンカウント時かけ声の再生速度倍率（候補とも一律）
VOICE_SAMURAI_BATTLE_START_VOLUME = 1.0  # エンカウント時（サムライ注視）かけ声の音量（0.0～1.0）
VOICE_WARRIOR_BATTLE_START_VOLUME = 1.0  # エンカウント時（女戦士注視）かけ声の音量（0.0～1.0）
VOICE_ATTACK_VOLUME = 1.0  # 攻撃ボイス音量（0.0～1.0）
VOICE_SAMURAI_ATTACK_VOLUME = 1.0  # サムライ攻撃時のかけ声音量（0.0～1.0）
VOICE_WARRIOR_ATTACK_VOLUME = 1.0  # 女戦士攻撃時のかけ声音量（0.0～1.0）
VOICE_GOBLIN_DAMAGED_VOLUME = 1.0  # 敵（ゴブリン）被弾やられボイスの音量（0.0～1.0）
VOICE_HEROINE_DAMAGED_VOLUME = 1.0  # ヒロイン被弾やられボイスの音量（0.0～1.0）
VOICE_SAMURAI_DAMAGED_VOLUME = 1.0  # サムライ被弾やられボイスの音量（0.0～1.0）
VOICE_WARRIOR_DAMAGED_VOLUME = 1.0  # 女戦士被弾やられボイスの音量（0.0～1.0）
VOICE_DANCE_VOLUME = 1.0  # マカダンスかけ声の音量（0.0～1.0）
VOICE_KATANA_SLASH_VOLUME = 1.0  # サムライの刀の斬撃エフェクト開始時に再生するSEの音量（0.0～1.0）
VOICE_SHINGANKEN_VOLUME = 1.0  # 心眼剣のかけ声（shinganken_0/1.mp3）の音量（0.0～1.0）

# 攻撃ボイス（ムチ最接近時に再生。ピッチを維持したまま再生速度を変更する）
VOICE_ATTACK_SPEED = 1.5  # 攻撃ボイスの再生速度倍率

# マカダンスかけ声（ピッチを維持したまま再生速度を変更する）
VOICE_DANCE_SPEED = 1.0  # マカダンスかけ声の再生速度倍率

BGM_FIELD_RETURN_FADEOUT_MS = 1200  # フィールドへ戻る際のBGMフェードアウト時間（ミリ秒）

# AIユーザモード（Aキーでトグル。実際のユーザ操作を模してコマンド選択を自動操作する）
AI_CURSOR_MOVE_FRAMES  = 30  # カーソルを1段階移動する（移動不要な場合もこの間待ってから決定する）のに要するフレーム数
AI_RESULT_ENTER_FRAMES = 60  # リザルト画面：勝利BGM再生開始からEnterキー相当の入力を行うまでのフレーム数
AI_FIELD_BATTLE_START_FRAMES = 90  # フィールドモード：経過後にEキー相当の入力を行いバトルを開始するまでのフレーム数

# ズームアウト後の待機モーション（縦横逆位相スクワッシュ）
BATTLE_HEROINE_IDLE_PERIOD_FRAMES = 30  # 拡縮1周期のフレーム数
BATTLE_HEROINE_IDLE_SCALE_DELTA   = 0.02  # 縦横スケールの振れ幅（1.0 ± DELTA）

# 敵キャラクター演出パラメータ：登場時／ズームアウト後それぞれについて、
# 敵位置にて、バトルウィンドウ幅（=SCREEN_W）がワールド座標系で何mに相当するかを指定する
# （この値が小さいほど、敵の身長(ENEMY_GOBLIN_HEIGHT_M)に対して画像が大きく＝ズームインして表示される）
ENEMY_GOBLIN_FIRST_WINDOW_WIDTH_M = 8 / 15  # 登場時（ズームイン状態）
ENEMY_GOBLIN_LAST_WINDOW_WIDTH_M  = 16 / 3  # ヒロインのズームアウト完了時点
ENEMY_GOBLIN_FIRST_METER_TO_PIXEL = SCREEN_W / ENEMY_GOBLIN_FIRST_WINDOW_WIDTH_M
ENEMY_GOBLIN_LAST_METER_TO_PIXEL  = SCREEN_W / ENEMY_GOBLIN_LAST_WINDOW_WIDTH_M
ENEMY_GROUND_Y_FROM_BOTTOM_RATIO = 0.3  # 敵の足元（接地位置）：画面下端から画面高さの何倍の位置か
ENEMY_X_RATIOS = [0.25, 0.5, 0.75]  # 敵を並べる横位置（画面左端から画面幅の何倍か）を1体ずつ指定
ENEMY_SILHOUETTE_RELEASE_FRAMES = 15  # 黒シルエットが解除され通常表示になるまでのフレーム数（ズームアウト完了直後から進行）
ENEMY_IDLE_PERIOD_FRAMES = 30   # 待機モーション：拡縮1周期のフレーム数
ENEMY_IDLE_SCALE_DELTA   = 0.02  # 待機モーション：縦横スケールの振れ幅（1.0 ± DELTA）

# 攻撃選択サブウィンドウ
BATTLE_MENU_OPTIONS = ["ムチ", "炎", "マカダンス"]  # 攻撃手段の選択肢（上から順に表示）

# サイズ・余白・枠線太さ・行間はSCREEN_W_BASEを基準に設定されているため、SCREEN_Wに応じてFONT_SCALEで拡縮する
BATTLE_MENU_WIDTH  = int(180 * FONT_SCALE)  # サブウィンドウの幅（px）
BATTLE_MENU_HEIGHT = int(176 * FONT_SCALE)  # サブウィンドウの高さ（px）
BATTLE_MENU_MARGIN = int(20 * FONT_SCALE)   # 画面端からの余白（右上に寄せて配置）

BATTLE_MENU_BORDER_COLOR  = (255, 255, 255)            # 枠線の色（白）
BATTLE_MENU_BORDER_WIDTH  = max(1, int(4 * FONT_SCALE))  # 枠線の太さ（px）
BATTLE_MENU_BORDER_RADIUS = int(16 * FONT_SCALE)       # 枠の角の丸み（px）。0で角ばった矩形
BATTLE_MENU_BG_COLOR  = (0, 0, 0)  # ウィンドウ内背景の色
BATTLE_MENU_BG_ALPHA  = 150        # ウィンドウ内背景の不透明度（0=透明 ～ 255=不透明）

BATTLE_MENU_FONT_SIZE = 24  # 選択肢テキストのフォントサイズ（メイリオ使用、文字化け対策）

BATTLE_MENU_TEXT_PADDING_X = int(20 * FONT_SCALE)  # 選択肢テキストの左余白（px）
BATTLE_MENU_TEXT_PADDING_Y = int(16 * FONT_SCALE)  # 選択肢テキストの上余白（px）
BATTLE_MENU_LINE_HEIGHT    = int(36 * FONT_SCALE)  # 選択肢1行あたりの高さ（px）

BATTLE_MENU_SELECTED_COLOR   = (255, 255, 255)  # 選択中の文字色（真っ白）
BATTLE_MENU_UNSELECTED_COLOR = (120, 120, 120)  # 非選択時の文字色（グレーアウト）

# 攻防ステート（コマンド実行後、専用の演出を行う期間。コマンドウィンドウは非表示）
BATTLE_EXCHANGE_FRAMES = 30  # 攻防ステートが継続するフレーム数（未実装の攻撃手段で使用。経過後はコマンド選択ステートへ戻る）

BATTLE_MENU_INDEX_WHIP  = 0  # BATTLE_MENU_OPTIONS内の「ムチ」のインデックス
BATTLE_MENU_INDEX_FLAME = 1  # BATTLE_MENU_OPTIONS内の「炎」のインデックス
BATTLE_MENU_INDEX_DANCE = 2  # BATTLE_MENU_OPTIONS内の「マカダンス」のインデックス

# サムライの行動選択肢（ヒロインの選択後に表示）
# マカダンスでバフがかかる前は「刀」のみ、バフがかかった後は「心眼剣」のみを選択可能とする
SAMURAI_MENU_OPTIONS_NORMAL = ["刀"]
SAMURAI_MENU_OPTIONS_POWERED_UP = ["心眼剣"]
SAMURAI_MENU_INDEX_SWORD = 0
SAMURAI_MENU_INDEX_SHINGANKEN = 0

# 女戦士の行動選択肢（サムライの選択後に表示）
WARRIOR_MENU_OPTIONS = ["斧"]
WARRIOR_MENU_INDEX_AXE = 0

# シスター・くノ一・魔法使い・武道家の行動選択肢（いずれも全てヒロインのムチと同じ挙動）
SISTER_MENU_OPTIONS   = ["ツララ落とし", "生命の雫"]
KUNOICHI_MENU_OPTIONS = ["手裏剣", "華火"]
WIZARD_MENU_OPTIONS   = ["火炎放射", "火竜変化"]
FIGHTER_MENU_OPTIONS  = ["拳脚", "百裂拳"]

# 攻撃手段ごとの攻撃ボイス再生候補：bunny_attack_<番号>.mp3 の番号で指定する（再生時にこの中からランダムに選ぶ）
BATTLE_WHIP_ATTACK_VOICE_NUMBERS  = (1, 1)  # ムチ攻撃時に再生するボイス候補
BATTLE_FLAME_ATTACK_VOICE_NUMBERS = (0, 0)  # 炎攻撃時に再生するボイス候補

# ムチ（近接攻撃）演出パラメータ：敵に接近 → 最接近で停止 → 元の位置へ後退
# （接近対象の敵はコマンドウィンドウ上で左右キーにより選択する。battle_target_enemy_index を参照）
BATTLE_WHIP_APPROACH_FRAMES = 15      # 敵に接近するまでのフレーム数（後退も同じフレーム数で行う）
BATTLE_WHIP_TARGET_SCALE    = 0.5     # 最接近時の画像高さ（画面高さの何倍。ズームアウト後のヒロイン画像高さより小さい値を指定）
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
BATTLE_ANNIHILATE_FRAMES = 15               # 撃破した敵の殲滅演出（アルファ値を下げて消滅させる）にかけるフレーム数（ムチ・炎共通）

# サムライの刀による斬撃エフェクト：敵への接近完了直後から、敵画像に重ねて水色の細い二等辺三角形の軌跡を表示する
# （敵画像の下端・右端・左端と、緑線表示位置（実際の絵の上端）を結んだ矩形の右上から左下へ向かう方向を
#   軸（対称線）とし、軌跡の先端側を底辺、末尾側を頂点とする二等辺三角形を描画する。
#   ダメージ表現アニメーションとは独立して進行する）
BATTLE_SLASH_COLOR = (0, 255, 255)   # 軌跡の基本色（水色。パラメータ調整可）
BATTLE_SLASH_FLASH_COLOR = (255, 255, 255)  # 点滅時に基本色と交互に表示する色（白。パラメータ調整可）
BATTLE_SLASH_BLINK_PERIOD_FRAMES = 4  # 基本色と点滅色の点滅1周期のフレーム数
BATTLE_SLASH_BASE_WIDTH_M = 0.03     # 二等辺三角形の底辺（軌跡の先端側）の長さ（ワールド座標系メートル。エフェクト発生時の敵の表示スケールに合わせてENEMY_GOBLIN_LAST_METER_TO_PIXELでピクセル変換する）
BATTLE_SLASH_DRAW_FRAMES  = 3        # 右上から左下まで軌跡が伸びるフレーム数
BATTLE_SLASH_HOLD_FRAMES  = 6        # 軌跡を維持するフレーム数
BATTLE_SLASH_ERASE_FRAMES = 12        # 右上から左下に向かって軌跡が消えるフレーム数
BATTLE_SLASH_TOTAL_FRAMES = BATTLE_SLASH_DRAW_FRAMES + BATTLE_SLASH_HOLD_FRAMES + BATTLE_SLASH_ERASE_FRAMES

# 炎（全体攻撃）演出パラメータ：その場で詠唱（攻撃ボイス再生 → 待機） → 敵全体に同時にダメージ表現アニメーションを適用
BATTLE_FLAME_CAST_DELAY_FRAMES = 60         # 攻撃ボイス再生から敵全体へのダメージ表現開始までの待機フレーム数

# マカダンス（味方バフ）演出パラメータ：ヒロインが画面下に消える → バトルウィンドウがピンクに染まりセクシーダンスを再生
# （仲間がいない現状はバフ対象が存在しないため、演出終了後はそのまま次の番へ進む）
BATTLE_DANCE_SINK_FRAMES = 10                # 待機モーションのヒロインが画面下に消えるまでのフレーム数
BATTLE_DANCE_WINDOW_COLOR = (0, 0, 0)        # ダンス中のバトルウィンドウ色（黒）
BATTLE_DANCE_SAMURAI_FLASH_COLOR = (252, 15, 192)  # ダンス中のサムライの点滅色（ショッキングピンク。黒背景に映えるようにする）
BATTLE_DANCE_IMAGE_INTERVAL_FRAMES = 1.0       # ダンス画像（bunny_dance_0フォルダ）が切り替わる間隔のフレーム数（ループ再生）
BATTLE_DANCE_SCROLL_FRAMES = 118             # ダンス画像の表示位置が移動するのに要するフレーム数
BATTLE_DANCE_ANCHOR_RATIO = 0.77              # 終了判定位置：ダンス画像下端から画像高さの何倍の位置か（この位置がバトルウィンドウ上端に一致したら終了）
BATTLE_DANCE_START_RATIO = 0.28               # 開始位置：ダンス画像下端から画像高さの何倍の位置か（この位置がバトルウィンドウ下端に一致した状態から開始。0なら画像下端＝従来通り）
BATTLE_DANCE_BODY_WIDTH_RATIO = 0.15          # ダンス画像の幅に対する彼女の体の幅の比率（この体の幅がバトルウィンドウ幅に一致するよう拡大スケーリングする）
BATTLE_DANCE_BGM_START_SEC = 153.4           # マカダンスBGM代用：開始時にbattle.mp3を再生開始する秒数（完了時に停止する）

# 敵の攻撃演出パラメータ：ヒロインに接近 → 最接近で停止 → 元の位置へ後退（流れはムチ演出と同じ4ステート構成を共有する）
BATTLE_ENEMY_ATTACK_TARGET_SCALE = 0.4      # 最接近時の敵の画像高さ（画面高さの何倍）
BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO = 0.0  # 最接近時の敵の足元位置：バトルウィンドウ下端からのオフセット（画面高さの何倍。0でウィンドウ下端と一致）

# HP関連パラメータ：最大HPと、各攻撃手段で増減するダメージ量の範囲（ランダム抽選はrandom.randint(MIN, MAX)で行う）
HEROINE_MAX_HP  = 200   # ヒロインの最大HP（現在HPは戦闘をまたいで引き継ぐ。回復はしない）
SAMURAI_MAX_HP  = 150   # サムライの最大HP
WARRIOR_MAX_HP  = 180   # 女戦士の最大HP
SISTER_MAX_HP   = 150   # シスターの最大HP
KUNOICHI_MAX_HP = 130   # くノ一の最大HP
WIZARD_MAX_HP   = 120   # 魔法使いの最大HP
FIGHTER_MAX_HP  = 200   # 武道家の最大HP
GOBLIN_MAX_HP   = 100   # ゴブリン1体の最大HP（敵はエンカウント毎に最大HPへリセットされる）

BATTLE_WHIP_DAMAGE_MIN  = 20   # ムチで敵に与えるダメージの最小値
BATTLE_WHIP_DAMAGE_MAX  = 50   # ムチで敵に与えるダメージの最大値
BATTLE_SWORD_DAMAGE_MIN = 20   # サムライの剣で敵に与えるダメージの最小値（ムチと同じ範囲）
BATTLE_SWORD_DAMAGE_MAX = 50   # サムライの剣で敵に与えるダメージの最大値（ムチと同じ範囲）
BATTLE_AXE_DAMAGE       = 100  # 女戦士の斧で敵に与えるダメージ（固定値）

# 心眼剣（サムライの特殊攻撃）パラメータ：接近せずその場にとどまり、待機後に方向ランダムな斬撃を連続で発生させる
SHINGANKEN_SLASH_COUNT = 5             # 斬撃の総数
SHINGANKEN_DARKEN_FRAMES = 30          # 開始時の暗転、および最後の斬撃時の暗転解除にかけるフレーム数
SHINGANKEN_ATTACK_VOICE_WAIT_FRAMES = 60  # 暗転完了後、攻撃発生のかけ声・1回目の斬撃開始までの待機フレーム数
SHINGANKEN_WAIT_FRAMES = SHINGANKEN_DARKEN_FRAMES + SHINGANKEN_ATTACK_VOICE_WAIT_FRAMES  # 開始から1回目の斬撃が始まるまでのフレーム数（その場で待機）
SHINGANKEN_SLASH_INTERVAL_FRAMES = 8   # 各斬撃の開始間隔フレーム数
SHINGANKEN_END_DELAY_FRAMES = SHINGANKEN_DARKEN_FRAMES  # 最後の斬撃開始から攻撃終了までのフレーム数（暗転解除が完了するのに合わせる）
SHINGANKEN_DAMAGE = 500                # 与えるダメージ（最後の斬撃の軌跡先端到達時に一括適用）
SHINGANKEN_DARKEN_MAX_ALPHA = 255      # 暗転時の最大アルファ値（255=完全に黒で覆う）
BATTLE_FLAME_DAMAGE_MIN = 10   # 炎で敵1体ごとに与えるダメージの最小値（全体攻撃だが各々個別に抽選する）
BATTLE_FLAME_DAMAGE_MAX = 40   # 炎で敵1体ごとに与えるダメージの最大値
BATTLE_ENEMY_ATTACK_DAMAGE_MIN = 10   # 敵の攻撃でヒロイン／サムライが受けるダメージの最小値
BATTLE_ENEMY_ATTACK_DAMAGE_MAX = 30   # 敵の攻撃でヒロイン／サムライが受けるダメージの最大値

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
STATE_STATUS = 3
game_state = STATE_FIELD

# ステータスウィンドウ：開閉アニメ（バトルメインウィンドウと同じサイズ・速度を流用）
STATUS_PHASE_OPENING = 0  # 開いている途中
STATUS_PHASE_OPEN    = 1  # 開ききって表示中（Enter／Spaceで閉じ始める）
STATUS_PHASE_CLOSING = 2  # 閉じている途中
status_phase      = STATUS_PHASE_OPENING
status_anim_frame = 0

# ステータスウィンドウ：表示する姿（上下キーで切り替え。デフォルトは後ろ姿）
STATUS_VIEW_BACK  = 0
STATUS_VIEW_FRONT = 1
status_view = STATUS_VIEW_BACK

# ステータスウィンドウ内の表示スケール：ウィンドウ幅（=SCREEN_W）がワールド座標系で何mに相当するか
# （SCREEN_Wが変わってもステータスウィンドウの表示内容（拡縮）が変わらないよう、ここから1mあたりのピクセル数を算出する）
STATUS_WINDOW_WIDTH_M = 4.0
STATUS_METER_TO_PIXEL = SCREEN_W / STATUS_WINDOW_WIDTH_M
# 隣り合うキャラの足元中心の横方向の間隔（ワールド座標・メートル）
# N人均等配置時の端のキャラ位置：画面中央 ± (N-1)/2 * spacing_px
# 7人の場合：cx ± 3s（s=spacing_px）。端キャラが画面内に収まるよう調整する
STATUS_CHARACTER_SPACING_M = 0.5

battle_anim_frame = 0
heroine_focus_delay_frame = 0
heroine_zoomout_frame = 0
battle_focus_character = -1  # ズームアウトで注視するキャラクター（-1=ヒロイン, -2=サムライ, -3=女戦士。エンカウント毎にランダム決定）
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
result_flashout_samurai_override = None  # フラッシュアウト中のサムライ表示位置・スケールの上書き指定（(x, 足元y, 画像高さ) または None）
result_flashout_is_samurai = False  # フラッシュアウトでヒロインの代わりにサムライを表示するか（サムライがトドメを刺した場合）
result_flashout_warrior_override = None  # フラッシュアウト中の女戦士表示位置・スケールの上書き指定（(x, 足元y, 画像高さ) または None）
result_flashout_is_warrior = False  # フラッシュアウトでヒロインの代わりに女戦士（または新キャラ）を表示するか
result_flashout_active_char = -1  # トドメを刺したキャラのID（-1=ヒロイン, -2=サムライ, -3=女戦士, -4〜-7=新キャラ）

battle_menu_selected_index = 0
battle_target_enemy_index  = 0  # ムチ選択中に左右キーで選べる攻撃対象（ENEMY_X_RATIOSのインデックス）
battle_target_cursor_frame = 0  # 攻撃対象カーソルの点滅用フレームカウンタ

# サムライの行動選択（ヒロインの選択後に行う）
battle_samurai_menu_selected_index = 0
battle_samurai_target_enemy_index  = 0  # 剣選択中に左右キーで選べる攻撃対象（ENEMY_X_RATIOSのインデックス）

# 女戦士の行動選択（サムライの選択後に行う）
battle_warrior_menu_selected_index = 0
battle_warrior_target_enemy_index  = 0  # 斧選択中に左右キーで選べる攻撃対象（ENEMY_X_RATIOSのインデックス）

# シスター・くノ一・魔法使い・武道家の行動選択
battle_sister_menu_selected_index   = 0
battle_sister_target_enemy_index    = 0
battle_kunoichi_menu_selected_index = 0
battle_kunoichi_target_enemy_index  = 0
battle_wizard_menu_selected_index   = 0
battle_wizard_target_enemy_index    = 0
battle_fighter_menu_selected_index  = 0
battle_fighter_target_enemy_index   = 0

# AIユーザモード：ON時はコマンド選択・リザルト画面の進行を自動操作する（process_ai_battle_input()）
ai_mode_active = True

# AIユーザモード：コマンド選択（行動メニュー → 必要なら攻撃対象）の自動操作の進行状態
AI_COMMAND_STEP_DECIDE        = 0  # 行動・対象をまだ決定していない（このフェーズに入った直後）
AI_COMMAND_STEP_MENU_CURSOR   = 1  # 行動メニューのカーソルを目標位置へ合わせている最中
AI_COMMAND_STEP_TARGET_CURSOR = 2  # 攻撃対象（敵）のカーソルを目標位置へ合わせている最中
ai_command_step       = AI_COMMAND_STEP_DECIDE
ai_command_wait_frame = 0  # 現在のカーソル移動／待機ステップの経過フレーム数
ai_menu_target_index  = 0  # AIが決定した行動メニューの目標インデックス
ai_menu_step_dir      = 1  # 行動メニューのカーソルを動かす方向（+1=下, -1=上）
ai_enemy_target_index = 0  # AIが決定した攻撃対象の敵の目標インデックス（ENEMY_X_RATIOSのインデックス）
ai_enemy_step_dir     = 1  # 攻撃対象カーソルを動かす方向（+1=右, -1=左）

# AIユーザモード：リザルト画面で勝利BGMの再生開始から経過したフレーム数
ai_result_wait_frame = 0

# AIユーザモード：フィールドモードで経過したフレーム数（一定時間経過でEキー相当の入力を行いバトルを開始する）
ai_field_wait_frame = 0

# AIユーザモード：ヒロインの行動選択 → マカダンスはそのバトル中1回のみ選択可能（使用済みなら以後は選択肢から除外する）
heroine_macadance_used = False

# HP：ヒロイン・サムライ他の現在HPは戦闘終了時に全回復する。敵の現在HPはエンカウント毎に最大HPへリセットされる
heroine_hp  = HEROINE_MAX_HP
samurai_hp  = SAMURAI_MAX_HP
warrior_hp  = WARRIOR_MAX_HP
sister_hp   = SISTER_MAX_HP
kunoichi_hp = KUNOICHI_MAX_HP
wizard_hp   = WIZARD_MAX_HP
fighter_hp  = FIGHTER_MAX_HP
enemy_hp    = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)

# ダメージ表現アニメーション：HP更新時、見た目への反映を2段階に分けて行う
# ①DAMAGE_FLASH_FRAMES：表示HPは更新前のまま、更新前→更新後の差分範囲を白く点滅させる
# ②DAMAGE_TRANSITION_FRAMES：表示HPを更新前→更新後へ線形に追従させる（グレースケール範囲が滑らかに広がる）
DAMAGE_FLASH_FRAMES = 16
DAMAGE_TRANSITION_FRAMES = 8
DAMAGE_FLASH_BLINK_PERIOD_FRAMES = 4  # ①の点滅周期（既存の被弾点滅と合わせる）

# ダメージ表現アニメーション：①の点滅色を行動ごとに指定する（行動ごとに調整できるようパラメータ化）
DAMAGE_FLASH_COLOR_WHIP         = (255, 255, 255)  # ムチによるダメージの点滅色（白）
DAMAGE_FLASH_COLOR_SWORD        = (255, 255, 255)  # 剣によるダメージの点滅色（白）
DAMAGE_FLASH_COLOR_AXE          = (255, 255, 255)  # 斧によるダメージの点滅色（白）
DAMAGE_FLASH_COLOR_FLAME        = (255, 0, 0)      # 炎によるダメージの点滅色（赤）
DAMAGE_FLASH_COLOR_ENEMY_ATTACK = (255, 255, 255)  # 敵の攻撃によるダメージの点滅色（白）

# ダメージ表現アニメーション：HP更新直前の表示HP（old）→更新後の実HP（new）への変化を、
# anim_frame（0=ダメージ発生直後）の経過に応じて表示に反映する（DAMAGE_FLASH_FRAMES, DAMAGE_TRANSITION_FRAMES参照）
# anim_frame >= DAMAGE_FLASH_FRAMES + DAMAGE_TRANSITION_FRAMES の間はアニメーションなし（表示HP=実HP）
DAMAGE_ANIM_DONE_FRAME = DAMAGE_FLASH_FRAMES + DAMAGE_TRANSITION_FRAMES
heroine_damage_anim_old_hp = HEROINE_MAX_HP
heroine_damage_anim_new_hp = HEROINE_MAX_HP
heroine_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
heroine_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
samurai_damage_anim_old_hp = SAMURAI_MAX_HP
samurai_damage_anim_new_hp = SAMURAI_MAX_HP
samurai_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
samurai_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
warrior_damage_anim_old_hp = WARRIOR_MAX_HP
warrior_damage_anim_new_hp = WARRIOR_MAX_HP
warrior_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
warrior_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
sister_damage_anim_old_hp   = SISTER_MAX_HP
sister_damage_anim_new_hp   = SISTER_MAX_HP
sister_damage_anim_frame    = DAMAGE_ANIM_DONE_FRAME
sister_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
kunoichi_damage_anim_old_hp = KUNOICHI_MAX_HP
kunoichi_damage_anim_new_hp = KUNOICHI_MAX_HP
kunoichi_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
kunoichi_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
wizard_damage_anim_old_hp   = WIZARD_MAX_HP
wizard_damage_anim_new_hp   = WIZARD_MAX_HP
wizard_damage_anim_frame    = DAMAGE_ANIM_DONE_FRAME
wizard_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
fighter_damage_anim_old_hp  = FIGHTER_MAX_HP
fighter_damage_anim_new_hp  = FIGHTER_MAX_HP
fighter_damage_anim_frame   = DAMAGE_ANIM_DONE_FRAME
fighter_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
enemy_damage_anim_old_hp = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)
enemy_damage_anim_new_hp = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)
enemy_damage_anim_frame  = [DAMAGE_ANIM_DONE_FRAME] * len(ENEMY_X_RATIOS)
enemy_damage_anim_flash_color = [DAMAGE_FLASH_COLOR_WHIP] * len(ENEMY_X_RATIOS)

# 敵の撃破状態：True の敵は殲滅済み（選択対象・通常表示の対象外となる）
enemy_defeated = [False] * len(ENEMY_X_RATIOS)
battle_annihilate_targets = []  # 殲滅演出（アルファ値を下げて消滅）中の敵のインデックスのリスト（[] = 演出なし。ムチは1体、炎は複数を同時に格納）
battle_annihilate_frame   = 0   # 殲滅演出の経過フレーム数（共通カウンタ）

# 戦闘内ステート：ヒロイン・サムライ・女戦士の行動選択（順序はbattle_command_phase_order参照） → 攻防演出
BATTLE_PHASE_COMMAND_HEROINE  = 0  # ヒロインの行動選択中（コマンドウィンドウ表示）
BATTLE_PHASE_COMMAND_SAMURAI  = 1  # サムライの行動選択中（コマンドウィンドウ表示。Spaceで1つ前の選択へ戻れる）
BATTLE_PHASE_COMMAND_WARRIOR  = 2  # 女戦士の行動選択中（コマンドウィンドウ表示。Spaceで1つ前の選択へ戻れる）
BATTLE_PHASE_COMMAND_SISTER   = 3  # シスターの行動選択中
BATTLE_PHASE_COMMAND_KUNOICHI = 4  # くノ一の行動選択中
BATTLE_PHASE_COMMAND_WIZARD   = 5  # 魔法使いの行動選択中
BATTLE_PHASE_COMMAND_FIGHTER  = 6  # 武道家の行動選択中
BATTLE_PHASE_EXCHANGE         = 7  # 攻防演出中（コマンドウィンドウ非表示）
battle_phase = BATTLE_PHASE_COMMAND_HEROINE
battle_exchange_frame = 0

# 行動選択順の基本サイクル：エンカウント時の注視キャラに応じて、この並びを回転させたものが
# battle_command_phase_order になる（例：女戦士注視→女戦士,ヒロイン,サムライ／ヒロイン注視→ヒロイン,サムライ,女戦士）
BATTLE_COMMAND_PHASE_CYCLE = [BATTLE_PHASE_COMMAND_HEROINE, BATTLE_PHASE_COMMAND_SAMURAI, BATTLE_PHASE_COMMAND_WARRIOR, BATTLE_PHASE_COMMAND_SISTER, BATTLE_PHASE_COMMAND_KUNOICHI, BATTLE_PHASE_COMMAND_WIZARD, BATTLE_PHASE_COMMAND_FIGHTER]
BATTLE_FOCUS_CHARACTER_TO_COMMAND_PHASE = {-1: BATTLE_PHASE_COMMAND_HEROINE, -2: BATTLE_PHASE_COMMAND_SAMURAI, -3: BATTLE_PHASE_COMMAND_WARRIOR, -4: BATTLE_PHASE_COMMAND_SISTER, -5: BATTLE_PHASE_COMMAND_KUNOICHI, -6: BATTLE_PHASE_COMMAND_WIZARD, -7: BATTLE_PHASE_COMMAND_FIGHTER}
BATTLE_COMMAND_PHASE_TO_CHARACTER = {BATTLE_PHASE_COMMAND_HEROINE: -1, BATTLE_PHASE_COMMAND_SAMURAI: -2, BATTLE_PHASE_COMMAND_WARRIOR: -3, BATTLE_PHASE_COMMAND_SISTER: -4, BATTLE_PHASE_COMMAND_KUNOICHI: -5, BATTLE_PHASE_COMMAND_WIZARD: -6, BATTLE_PHASE_COMMAND_FIGHTER: -7}
battle_command_phase_order = list(BATTLE_COMMAND_PHASE_CYCLE)  # start_battle()でbattle_focus_characterに応じて再計算する

# バトル参加キャラクターのワールド座標系での基準位置（メートル）。左から右へ
# 「注視キャラ（中央）, その後の順に右へ3人, 巡回して左へ3人」の並びとなるよう、
# start_battle()でbattle_command_phase_orderに応じて再計算する
# order_index 0=注視キャラ(0.0m), 1=次→右(+0.5m), 2=次々→右(+1.0m), 3=右端(+1.5m),
#              4=左端(-1.5m), 5=左から2番目(-1.0m), 6=中央左隣(-0.5m)
BATTLE_ORDER_POSITION_OFFSET_M = {0: 0.0, 1: 0.5, 2: 1.0, 3: 1.5, 4: -1.5, 5: -1.0, 6: -0.5}
battle_character_world_offset_m = {-1: 0.0, -2: 0.5, -3: 1.0, -4: 1.5, -5: -1.5, -6: -1.0, -7: -0.5}

# ムチ（近接攻撃）演出ステート：接近 → ダメージ待機 → 白色点滅 → 後退
BATTLE_WHIP_PHASE_APPROACH    = 0  # 敵に接近中
BATTLE_WHIP_PHASE_DAMAGE_WAIT = 1  # 最接近後、攻撃ボイス再生から白色点滅開始までの待機中
BATTLE_WHIP_PHASE_FLASH       = 2  # ダメージ演出（敵の白色点滅）中
BATTLE_WHIP_PHASE_RETURN      = 3  # 元の位置へ後退中
battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
battle_whip_frame = 0

# サムライの剣（近接攻撃）演出ステート：ムチと同じ4ステートをそのまま流用する
battle_samurai_whip_phase = BATTLE_WHIP_PHASE_APPROACH
battle_samurai_whip_frame = 0

# 女戦士の斧（近接攻撃）演出ステート：ムチと同じ4ステートをそのまま流用する
battle_warrior_whip_phase = BATTLE_WHIP_PHASE_APPROACH
battle_warrior_whip_frame = 0

# シスター・くノ一・魔法使い・武道家の攻撃演出ステート：いずれもムチと同じ4ステートを流用する
battle_sister_whip_phase   = BATTLE_WHIP_PHASE_APPROACH
battle_sister_whip_frame   = 0
battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_APPROACH
battle_kunoichi_whip_frame = 0
battle_wizard_whip_phase   = BATTLE_WHIP_PHASE_APPROACH
battle_wizard_whip_frame   = 0
battle_fighter_whip_phase  = BATTLE_WHIP_PHASE_APPROACH
battle_fighter_whip_frame  = 0

# 炎（全体攻撃）演出ステート：その場で詠唱（待機） → 敵全体に同時に赤色点滅
BATTLE_FLAME_PHASE_CAST  = 0  # 攻撃ボイス再生後、白色点滅開始までの待機中（その場にとどまる）
BATTLE_FLAME_PHASE_FLASH = 1  # ダメージ演出（敵全体の白色点滅）中
battle_flame_phase = BATTLE_FLAME_PHASE_CAST
battle_flame_frame = 0

# マカダンス（味方バフ）演出ステート：ヒロインが画面下に消える → バトルウィンドウがピンクに染まりダンスを再生
BATTLE_DANCE_PHASE_SINK  = 0  # ヒロインが画面下に消えるまで
BATTLE_DANCE_PHASE_DANCE = 1  # バトルウィンドウがピンクに染まり、ダンス画像を再生中
battle_dance_phase = BATTLE_DANCE_PHASE_SINK
battle_dance_frame = 0

# マカダンス（味方バフ）演出：ピンクの点滅演出が終わると、以後そのバトルが終了するまで
# （リザルト画面を含み、フィールドへ戻るまで）サムライは「心眼剣」のみ使用可能になる
samurai_powered_up = False

# 攻防ステート内の行動順：女戦士の行動決定後に、生存している敵全体・ヒロイン・サムライ・女戦士を含めてランダムに決定する
# （-1 = ヒロイン、-2 = サムライ、-3 = 女戦士、0以上 = 敵のインデックス。一巡したらコマンド選択ステートへ戻る）
battle_turn_order = []
battle_turn_index = 0

# 敵の攻撃演出ステート：接近 → ダメージ待機 → 白色点滅 → 後退（ムチ演出と同じ4ステートをそのまま流用する）
battle_enemy_attack_phase = BATTLE_WHIP_PHASE_APPROACH
battle_enemy_attack_frame = 0
battle_attacking_enemy_index = -1  # 現在攻撃中の敵のインデックス（-1 = 攻撃側はヒロイン／サムライ／女戦士）
battle_enemy_attack_target = -1    # 敵の攻撃対象（-1 = ヒロイン、-2 = サムライ、-3 = 女戦士。敵の番開始時にランダム決定）

# ムチ：接近・後退中の残像履歴（直近 BATTLE_WHIP_TRAIL_OFFSET_2 フレーム分の (x, 足元y, 画像高さ) を保持。古い順）
heroine_whip_trail = []
heroine_whip_trail_key = None  # 最後に記録したフレームの識別キー（(phase, frame)）。重複登録の防止用

# サムライの剣：接近・後退中の残像履歴（ヒロインのムチと同じ仕組み）
samurai_whip_trail = []
samurai_whip_trail_key = None

# 女戦士の斧：接近・後退中の残像履歴（ヒロインのムチと同じ仕組み）
warrior_whip_trail = []
warrior_whip_trail_key = None

# シスター・くノ一・魔法使い・武道家：接近・後退中の残像履歴
sister_whip_trail   = []
sister_whip_trail_key = None
kunoichi_whip_trail = []
kunoichi_whip_trail_key = None
wizard_whip_trail   = []
wizard_whip_trail_key = None
fighter_whip_trail  = []
fighter_whip_trail_key = None

# サムライの刀による斬撃エフェクト：敵への接近完了直後から開始し、ダメージ表現アニメーションとは独立して進行する
# （battle_slash_frame >= BATTLE_SLASH_TOTAL_FRAMES の間は非表示）
battle_slash_frame = BATTLE_SLASH_TOTAL_FRAMES
battle_slash_target_enemy_index = -1  # 軌跡を表示する敵のインデックス（ENEMY_X_RATIOSのインデックス）

# 心眼剣の斬撃エフェクト：7本それぞれ独立に進行する（刀の斬撃と同じ仕組みを7本分用意し、方向のみランダムにする）
# （battle_shingan_slash_frames[i] >= BATTLE_SLASH_TOTAL_FRAMES の間は該当の斬撃を非表示）
battle_shingan_frame = -1  # 心眼剣攻撃全体の経過フレーム数（-1=非アクティブ）
battle_shingan_slash_frames = [BATTLE_SLASH_TOTAL_FRAMES] * SHINGANKEN_SLASH_COUNT
battle_shingan_slash_angles = [0.0] * SHINGANKEN_SLASH_COUNT
battle_shingan_target_enemy_index = -1  # 軌跡を表示する敵のインデックス（ENEMY_X_RATIOSのインデックス）

# [開発用] システムポーズ：Pキーでフレーム処理を停止／再開（描画は継続）。
# ポーズ中は矢印右キーで1フレームだけ処理を進められる。
# また、矢印右キーを押し続けた場合はキーリピートで連続して1フレームずつ進める
# （最初は PAUSE_STEP_REPEAT_DELAY_SEC 秒後に1回、以後は PAUSE_STEP_REPEAT_INTERVAL_SEC 秒間隔で繰り返す）
PAUSE_STEP_REPEAT_DELAY_SEC    = 0.5  # 押し続けてから最初のリピートが発生するまでの秒数
PAUSE_STEP_REPEAT_INTERVAL_SEC = 0.05  # 2回目以降のリピート間隔（秒）
PAUSE_STEP_REPEAT_DELAY_FRAMES    = max(1, round(PAUSE_STEP_REPEAT_DELAY_SEC * FIXED_FPS))
PAUSE_STEP_REPEAT_INTERVAL_FRAMES = max(1, round(PAUSE_STEP_REPEAT_INTERVAL_SEC * FIXED_FPS))

# [開発用] デバッグ状態：Dキーで切り替え（モードに関係なくゲーム中ずっと保持される）。
# ONの間は、開発・バグ調査に有益な情報（足元コライダ表示、キャラ画像の枠など）を表示する。デフォルトON
is_debug = False

is_paused = False
pause_step_requested = False
pause_step_key_held       = False  # 矢印右キーが押され続けているか（リピート判定用）
pause_step_key_hold_frame = 0      # 矢印右キーを押し続けているフレーム数（リピート判定用カウンタ）
pause_step_key_repeated   = False  # 押し続けている間に既に1回以上リピートが発生したか（遅延／間隔の切り替え用）

# ----------------------------------------------------------
# フォント
# ----------------------------------------------------------
RESULT_TEXT_FONT_SIZE = 32  # リザルトセリフのフォントサイズ
DEBUG_FONT_SIZE       = 24  # FPS等のデバッグ表示・敵/ヒロイン/サムライのHPデバッグ表示のフォントサイズ

# 各フォントサイズはSCREEN_W_BASEを基準に設定されているため、SCREEN_Wに応じてFONT_SCALEで拡縮する
font           = pygame.font.SysFont(None, max(1, int(DEBUG_FONT_SIZE * FONT_SCALE)))
font_result    = pygame.font.Font('C:/Windows/Fonts/meiryo.ttc', max(1, int(RESULT_TEXT_FONT_SIZE * FONT_SCALE)))
font_battle_menu = pygame.font.Font('C:/Windows/Fonts/meiryo.ttc', max(1, int(BATTLE_MENU_FONT_SIZE * FONT_SCALE)))

# 左上のデバッグ表示（FPS・座標等）：開始位置・行間もFONT_SCALEで拡縮する
DEBUG_TEXT_MARGIN      = int(10 * FONT_SCALE)  # 画面左上からの余白（px）
DEBUG_TEXT_LINE_HEIGHT = int(20 * FONT_SCALE)  # 1行あたりの高さ（px）

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
HEROINE_HEIGHT_M = 1.8  # ヒロインの身長（メートル）
SAMURAI_HEIGHT_M = 1.4  # サムライの身長（メートル）
WARRIOR_HEIGHT_M = 2  # 女戦士の身長（メートル）
SISTER_HEIGHT_M   = 1.5  # シスターの身長（メートル）
KUNOICHI_HEIGHT_M = 1.65  # くノ一の身長（メートル）
WIZARD_HEIGHT_M   = 1.7   # 魔法使いの身長（メートル）
FIGHTER_HEIGHT_M  = 1.8   # 武道家の身長（メートル）
ENEMY_GOBLIN_HEIGHT_M = 1.2  # ゴブリンの身長（メートル）。立ち姿画像のデバッグ表示（実際の絵の上端の算出）に使用

HP_GRAYSCALE_DARKNESS = 0.5  # HP低下によるグレースケール表示の暗さ（1=通常のグレースケール、0=真っ黒）

TILE_SIZE_M = 2.0

def heroine_height_px():
    return int(HEROINE_HEIGHT_M * METER_TO_PIXEL * zoom)

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
HEROINE_FRONT_IMG_PATH = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "bunny", "bunny_front.png")
DANCE_DIR = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "bunny", "bunny_dance_0")
SAMURAI_FRONT_IMG_PATH = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "samurai", "samurai_front.png")
SAMURAI_BACK_IMG_PATH  = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "samurai", "samurai_back.png")
WARRIOR_FRONT_IMG_PATH = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "warrior", "warrior_front.png")
WARRIOR_BACK_IMG_PATH  = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "warrior", "warrior_back.png")
SISTER_FRONT_IMG_PATH    = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "sister", "sister_front.png")
SISTER_BACK_IMG_PATH     = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "sister", "sister_back.png")
KUNOICHI_FRONT_IMG_PATH  = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "kunoichi", "kunoichi_front.png")
KUNOICHI_BACK_IMG_PATH   = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "kunoichi", "kunoichi_back.png")
WIZARD_FRONT_IMG_PATH    = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "wizard", "wizard_front.png")
WIZARD_BACK_IMG_PATH     = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "wizard", "wizard_back.png")
FIGHTER_FRONT_IMG_PATH   = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "fighter", "fighter_front.png")
FIGHTER_BACK_IMG_PATH    = os.path.join(BASE_DIR, "..", "assets", "images", "characters", "fighter", "fighter_back.png")
ENEMY_GOBLIN_IMG_PATH = os.path.join(BASE_DIR, "..", "assets", "images", "enemies", "goblin", "goblin_idle.png")
VOICES_DIR = os.path.join(BASE_DIR, "..", "assets", "sound", "voices")
VOICE_GOBLIN_DAMAGED_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "goblin_damaged.mp3")
VOICE_HEROINE_DAMAGED_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "bunny_damaged_0.mp3")
VOICE_SAMURAI_DAMAGED_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "samurai_damaged_0.mp3")
VOICE_WARRIOR_DAMAGED_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "warrior_damaged_0.mp3")
VOICE_DANCE_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "voices", "bunny_dance_0.mp3")
BGM_BATTLE_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "bgms", "battle.mp3")
BGM_BATTLE2_PATH = os.path.join(BASE_DIR, "..", "assets", "sound", "bgms", "battle2.mp3")
SES_DIR = os.path.join(BASE_DIR, "..", "assets", "sound", "ses")
VOICE_KATANA_SLASH_PATH = os.path.join(SES_DIR, "katana_slash.mp3")
VOICE_SHINGANKEN_0_PATH = os.path.join(VOICES_DIR, "shinganken_0.mp3")  # 心眼剣開始時のかけ声
VOICE_SHINGANKEN_1_PATH = os.path.join(VOICES_DIR, "shinganken_1.mp3")  # 心眼剣・攻撃発生時のかけ声

def load_walk_images():
    files = [f for f in os.listdir(WALK_DIR)
             if f.lower().endswith(".png") and f.startswith("bunny_walk_")]

    def sort_key(fname):
        return int(os.path.splitext(fname)[0].split("_")[-1])

    files.sort(key=sort_key)

    images = []
    for fname in files:
        img = pygame.image.load(os.path.join(WALK_DIR, fname)).convert_alpha()
        # ★ [デバッグ] 各歩行画像で実際の絵が始まる高さをワールド座標系（メートル）で記録する
        character_art_top_height_m[fname] = scan_art_top_height_m(img, HEROINE_HEIGHT_M)
        w, h = img.get_size()
        scale = heroine_height_px() / h
        img = pygame.transform.smoothscale(img, (int(w * scale), heroine_height_px()))
        images.append(img)

    return images, files

# ---------------------------------------------------------
# load_dance_images()：bunny_dance_0_<番号>.png を全て検出して読み込む
#                      （マカダンス演出で番号順に再生する。スケールは描画時に行うためオリジナルのまま保持）
# ---------------------------------------------------------
def load_dance_images():
    files = [f for f in os.listdir(DANCE_DIR)
             if f.lower().endswith(".png") and f.startswith("bunny_dance_0_")]

    def sort_key(fname):
        return int(os.path.splitext(fname)[0].split("_")[-1])

    files.sort(key=sort_key)

    return [pygame.image.load(os.path.join(DANCE_DIR, fname)).convert_alpha() for fname in files]

# ---------------------------------------------------------
# scan_art_top_height_m()：
# 立ち姿画像を上端の行から走査し、アルファ値が0でないピクセルを最初に含む行を探す。
# その行から画像下端（足元）までのピクセル高さを、画像全体の高さが height_m に相当するものとして
# ワールド座標系の高さ（メートル）に変換して返す（is_debug時の緑線表示で、ズームや拡縮に関わらず
# 「実際のキャラ絵の上端」の位置を再算出できるようにするため）
# ---------------------------------------------------------
def scan_art_top_height_m(img_raw, height_m):
    orig_w, orig_h = img_raw.get_size()
    mask = pygame.mask.from_surface(img_raw, 0)
    rects = mask.get_bounding_rects()
    top_row = min((r.top for r in rects), default=0)
    return (orig_h - top_row) / orig_h * height_m

walk_images = []
walk_image_filenames = []  # walk_imagesと対応するファイル名のリスト（緑線デバッグ表示・HPグレースケールでcharacter_art_top_height_mを参照する際のkeyに使用）
frame_index = 0
frame_timer = 0
FRAME_INTERVAL = 1
last_image = None

battle_back_img     = None  # 後ろ姿画像（スケール後）
battle_back_img_raw = None  # 後ろ姿画像（オリジナル）
result_heroine_win_img  = None  # 勝利バストショット画像（bunny_front.pngをHEROINE_HEIGHT_M分の高さに一度だけスケール）
result_samurai_win_img  = None  # 勝利バストショット画像（サムライがトドメを刺した場合）
result_warrior_win_img  = None  # 勝利バストショット画像（女戦士がトドメを刺した場合）
result_sister_win_img   = None  # 勝利バストショット画像（シスターがトドメを刺した場合）
result_kunoichi_win_img = None  # 勝利バストショット画像（くノ一がトドメを刺した場合）
result_wizard_win_img   = None  # 勝利バストショット画像（魔法使いがトドメを刺した場合）
result_fighter_win_img  = None  # 勝利バストショット画像（武道家がトドメを刺した場合）
result_active_win_img   = None  # リザルト開始時に選ばれた、実際に表示する勝利バストショット画像
enemy_img_raw       = None  # 敵（goblin）画像（オリジナル）
heroine_front_img_raw = None  # ヒロイン前姿画像（オリジナル） — ステータスウィンドウ用
samurai_front_img_raw = None  # サムライ前姿画像（オリジナル） — ステータスウィンドウ用
samurai_back_img_raw  = None  # サムライ後ろ姿画像（オリジナル） — ステータスウィンドウ用
warrior_front_img_raw = None  # 女戦士前姿画像（オリジナル） — ステータスウィンドウ用
warrior_back_img_raw  = None  # 女戦士後ろ姿画像（オリジナル） — ステータスウィンドウ用
sister_front_img_raw    = None  # シスター前姿画像（オリジナル） — ステータスウィンドウ用
sister_back_img_raw     = None  # シスター後ろ姿画像（オリジナル） — ステータスウィンドウ用
kunoichi_front_img_raw  = None  # くノ一前姿画像（オリジナル） — ステータスウィンドウ用
kunoichi_back_img_raw   = None  # くノ一後ろ姿画像（オリジナル） — ステータスウィンドウ用
wizard_front_img_raw    = None  # 魔法使い前姿画像（オリジナル） — ステータスウィンドウ用
wizard_back_img_raw     = None  # 魔法使い後ろ姿画像（オリジナル） — ステータスウィンドウ用
fighter_front_img_raw   = None  # 武道家前姿画像（オリジナル） — ステータスウィンドウ用
fighter_back_img_raw    = None  # 武道家後ろ姿画像（オリジナル） — ステータスウィンドウ用
character_art_top_height_m = {}  # 各立ち姿画像で実際の絵が始まる高さ（{ファイル名: 画像下端からの高さ（メートル）}）。is_debug時の緑線表示・HPグレースケール表示に使用
hp_grayscale_cache = {}  # HPに応じたグレースケール合成画像のキャッシュ（{(ファイル名, 現在HP, 最大HP): Surface}）
hp_grayscale_full_cache = {}  # 画像全体をグレースケール化＋暗くした画像のキャッシュ（{ファイル名: Surface}）。HPに依存しない部分を一度だけ計算する
HP_GRAYSCALE_CACHE_MAX_ENTRIES = 64  # hp_grayscale_cacheの最大保持数。ダメージ表現アニメーションで遷移中の中間HP値が次々キャッシュされ肥大化するのを防ぐ
dance_images_raw    = []  # マカダンス演出用画像（bunny_dance_0_<番号>.png を番号順に並べたリスト。スケールは描画時に行う）
voice_win_by_number = {}  # 勝利ボイス（{番号: Sound}。bunny_win_<番号>.mp3 の番号をキーとし、リザルト開始時にランダム選択する）
voice_samurai_win_by_number  = {}  # 勝利ボイス（サムライがトドメを刺した場合）
voice_warrior_win_by_number  = {}  # 勝利ボイス（女戦士がトドメを刺した場合）
voice_sister_win_by_number   = {}  # 勝利ボイス（シスターがトドメを刺した場合・ファイルが存在しない場合は空dict）
voice_kunoichi_win_by_number = {}  # 勝利ボイス（くノ一がトドメを刺した場合）
voice_wizard_win_by_number   = {}  # 勝利ボイス（魔法使いがトドメを刺した場合）
voice_fighter_win_by_number  = {}  # 勝利ボイス（武道家がトドメを刺した場合）
result_win_voice         = None  # リザルト開始時に選ばれた勝利ボイス（再生・長さ判定用）
result_victory_message        = ''  # 選ばれた勝利ボイスに対応する勝利メッセージ本文
result_message_complete_frame = 0  # 勝利メッセージが全文表示し終わるフレーム（= 最後の文字が追加される瞬間）
result_win_bgm_start_frame    = 0  # 勝利BGMの再生を開始するフレーム（= メッセージ表示完了から指定フレーム経過した瞬間）
voice_battle_start_list = []  # エンカウント時かけ声候補（bunny_battle_start_<番号>.mp3 を全て読み込み、再生時にランダム選択する）
voice_samurai_battle_start_list = []  # エンカウント時（サムライ注視）かけ声候補（samurai_battle_start_<番号>.mp3 を全て読み込み、再生時にランダム選択する）
voice_warrior_battle_start_list  = []  # エンカウント時（女戦士注視）かけ声候補
voice_sister_battle_start_list   = []  # エンカウント時（シスター注視）かけ声候補（ファイルが存在しない場合は空list）
voice_kunoichi_battle_start_list = []  # エンカウント時（くノ一注視）かけ声候補
voice_wizard_battle_start_list   = []  # エンカウント時（魔法使い注視）かけ声候補
voice_fighter_battle_start_list  = []  # エンカウント時（武道家注視）かけ声候補
voice_samurai_attack_list = []  # サムライ攻撃時のかけ声候補（samurai_attack_start_<番号>.mp3 を全て読み込み、再生時にランダム選択する）
voice_warrior_attack_list = []  # 女戦士攻撃時のかけ声候補（warrior_attack_<番号>.mp3 を全て読み込み、再生時にランダム選択する）
voice_attack_by_number = {}  # 攻撃ボイス（{番号: Sound}。bunny_attack_<番号>.mp3 の番号をキーとし、攻撃手段ごとに候補番号を選んで再生する）
voice_goblin_damaged = None  # 敵（ゴブリン）被弾やられボイス
voice_heroine_damaged = None  # ヒロイン被弾やられボイス
voice_samurai_damaged = None  # サムライ被弾やられボイス
voice_warrior_damaged = None  # 女戦士被弾やられボイス
sound_battle2_bgm = None  # 戦闘曲（battle2.mp3）。エンカウント後ズームアウト開始時に再生し、決着時に即停止する
voice_dance = None  # マカダンス開始時のかけ声
voice_katana_slash = None  # サムライの刀の斬撃エフェクト開始時SE
voice_shinganken_0 = None  # 心眼剣開始時のかけ声
voice_shinganken_1 = None  # 心眼剣・攻撃発生時のかけ声

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
# load_samurai_win_voices()：samurai_win_<番号>.mp3 を全て検出して読み込み、
#                            再生速度変更後のSoundを {番号: Sound} の辞書として返す
#                            （サムライがトドメを刺した場合のリザルト開始時にランダム選択し、
#                              対応する勝利メッセージ RESULT_SAMURAI_VICTORY_MESSAGES と組み合わせて使う）
# ---------------------------------------------------------
def load_samurai_win_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("samurai_win_")]

    def voice_number(fname):
        return int(os.path.splitext(fname)[0].split("_")[-1])

    voices_by_number = {}
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_WIN_SPEED)
        voice.set_volume(VOICE_WIN_VOLUME)
        voices_by_number[voice_number(fname)] = voice

    return voices_by_number

# ---------------------------------------------------------
# load_warrior_win_voices()：warrior_win_<番号>.mp3 を全て検出して読み込み、
#                            再生速度変更後のSoundを {番号: Sound} の辞書として返す
#                            （女戦士がトドメを刺した場合のリザルト開始時にランダム選択し、
#                              対応する勝利メッセージ RESULT_WARRIOR_VICTORY_MESSAGES と組み合わせて使う）
# ---------------------------------------------------------
def load_warrior_win_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("warrior_win_")]

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
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_BATTLE_START_SPEED)
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
# load_samurai_battle_start_voices()：samurai_battle_start_<番号>.mp3 を全て検出して読み込み、
#                                     Soundのリストとして返す（エンカウントのたびランダムに選んで再生する）
# ---------------------------------------------------------
def load_samurai_battle_start_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("samurai_battle_start_")]

    voices = []
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_BATTLE_START_SPEED)
        voice.set_volume(VOICE_SAMURAI_BATTLE_START_VOLUME)
        voices.append(voice)

    return voices

# ---------------------------------------------------------
# play_samurai_battle_start_voice()：エンカウント時（サムライ注視）のかけ声候補の中からランダムに選んで再生する
# ---------------------------------------------------------
def play_samurai_battle_start_voice():
    if voice_samurai_battle_start_list:
        random.choice(voice_samurai_battle_start_list).play()

# ---------------------------------------------------------
# load_warrior_battle_start_voices()：warrior_battle_start.mp3（連番なし）を含め、
#                                     "warrior_battle_start"で始まる.mp3を全て検出して読み込み、
#                                     Soundのリストとして返す（エンカウントのたびランダムに選んで再生する）
# ---------------------------------------------------------
def load_warrior_battle_start_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("warrior_battle_start")]

    voices = []
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_BATTLE_START_SPEED)
        voice.set_volume(VOICE_WARRIOR_BATTLE_START_VOLUME)
        voices.append(voice)

    return voices

# ---------------------------------------------------------
# play_warrior_battle_start_voice()：エンカウント時（女戦士注視）のかけ声候補の中からランダムに選んで再生する
# ---------------------------------------------------------
def play_warrior_battle_start_voice():
    if voice_warrior_battle_start_list:
        random.choice(voice_warrior_battle_start_list).play()

# ---------------------------------------------------------
# load_samurai_attack_voices()：samurai_attack_start_<番号>.mp3 を全て検出して読み込み、
#                               Soundのリストとして返す（サムライの攻撃の番のたびランダムに選んで再生する）
# ---------------------------------------------------------
def load_samurai_attack_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("samurai_attack_start_")]

    voices = []
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_BATTLE_START_SPEED)
        voice.set_volume(VOICE_SAMURAI_ATTACK_VOLUME)
        voices.append(voice)

    return voices

# ---------------------------------------------------------
# play_samurai_attack_voice()：サムライの攻撃時のかけ声候補の中からランダムに選んで再生する
# ---------------------------------------------------------
def play_samurai_attack_voice():
    if voice_samurai_attack_list:
        random.choice(voice_samurai_attack_list).play()

# ---------------------------------------------------------
# load_warrior_attack_voices()：warrior_attack_<番号>.mp3 を全て検出して読み込み、
#                               Soundのリストとして返す（女戦士の攻撃の番のたびランダムに選んで再生する）
# ---------------------------------------------------------
def load_warrior_attack_voices():
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith("warrior_attack_")]

    voices = []
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_BATTLE_START_SPEED)
        voice.set_volume(VOICE_WARRIOR_ATTACK_VOLUME)
        voices.append(voice)

    return voices

# ---------------------------------------------------------
# play_warrior_attack_voice()：女戦士の攻撃時のかけ声候補の中からランダムに選んで再生する
# ---------------------------------------------------------
def play_warrior_attack_voice():
    if voice_warrior_attack_list:
        random.choice(voice_warrior_attack_list).play()


def _load_win_voices_for(char_prefix):
    """<char_prefix>_win_<番号>.mp3 を全て検出して {番号: Sound} 辞書で返す（ファイルなし→空dict）"""
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith(char_prefix + "_win_")]
    voices_by_number = {}
    for fname in files:
        num = int(os.path.splitext(fname)[0].split("_")[-1])
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_WIN_SPEED)
        voice.set_volume(VOICE_WIN_VOLUME)
        voices_by_number[num] = voice
    return voices_by_number


def _load_battle_start_voices_for(char_prefix, volume):
    """<char_prefix>_battle_start*.mp3 を全て検出してSoundリストで返す（ファイルなし→空list）"""
    files = [f for f in os.listdir(VOICES_DIR)
             if f.lower().endswith(".mp3") and f.startswith(char_prefix + "_battle_start")]
    voices = []
    for fname in files:
        voice = load_sound_at_speed(os.path.join(VOICES_DIR, fname), VOICE_BATTLE_START_SPEED)
        voice.set_volume(volume)
        voices.append(voice)
    return voices


def _play_battle_start_voice_from(lst):
    if lst:
        random.choice(lst).play()

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
    global battle_samurai_whip_phase, battle_samurai_whip_frame
    global battle_warrior_whip_phase, battle_warrior_whip_frame
    global battle_sister_whip_phase, battle_sister_whip_frame
    global battle_kunoichi_whip_phase, battle_kunoichi_whip_frame
    global battle_wizard_whip_phase, battle_wizard_whip_frame
    global battle_fighter_whip_phase, battle_fighter_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_dance_phase, battle_dance_frame
    global battle_enemy_attack_phase, battle_enemy_attack_frame, battle_attacking_enemy_index
    global battle_enemy_attack_target
    global battle_shingan_frame, battle_shingan_slash_frames, battle_shingan_target_enemy_index

    attacker = battle_turn_order[battle_turn_index]
    if attacker == -1:
        battle_attacking_enemy_index = -1
        if battle_menu_selected_index == BATTLE_MENU_INDEX_FLAME:
            battle_flame_phase = BATTLE_FLAME_PHASE_CAST
            battle_flame_frame = 0
            play_attack_voice()
        elif battle_menu_selected_index == BATTLE_MENU_INDEX_DANCE:
            battle_dance_phase = BATTLE_DANCE_PHASE_SINK
            battle_dance_frame = 0
            pygame.mixer.music.load(BGM_BATTLE_PATH)
            pygame.mixer.music.set_volume(BGM_BATTLE_VOLUME)
            pygame.mixer.music.play(start=BATTLE_DANCE_BGM_START_SEC)
            #if voice_dance:
                #voice_dance.play()
        else:
            battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
            battle_whip_frame = 0
            play_attack_voice()
    elif attacker == -2:
        # サムライの番：選択した行動（刀／心眼剣）で攻撃する
        # （SAMURAI_MENU_INDEX_SWORD/SHINGANKENはどちらも0のため、menu_selected_indexだけでは区別できない。
        #   マカダンスのバフ後（samurai_powered_up）かどうかで判定する）
        battle_attacking_enemy_index = -1
        if samurai_powered_up:
            battle_shingan_frame = 0
            battle_shingan_slash_frames = [BATTLE_SLASH_TOTAL_FRAMES] * SHINGANKEN_SLASH_COUNT
            battle_shingan_target_enemy_index = battle_samurai_target_enemy_index
            if voice_shinganken_0:
                voice_shinganken_0.play()
        else:
            battle_samurai_whip_phase = BATTLE_WHIP_PHASE_APPROACH
            battle_samurai_whip_frame = 0
            play_samurai_attack_voice()
    elif attacker == -3:
        # 女戦士の番：斧で攻撃する（流れ・ボイス再生のタイミングはヒロインのムチと同じ）
        battle_attacking_enemy_index = -1
        battle_warrior_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_warrior_whip_frame = 0
        play_warrior_attack_voice()
    elif attacker == -4:
        battle_attacking_enemy_index = -1
        battle_sister_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_sister_whip_frame = 0
    elif attacker == -5:
        battle_attacking_enemy_index = -1
        battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_kunoichi_whip_frame = 0
    elif attacker == -6:
        battle_attacking_enemy_index = -1
        battle_wizard_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_wizard_whip_frame = 0
    elif attacker == -7:
        battle_attacking_enemy_index = -1
        battle_fighter_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_fighter_whip_frame = 0
    else:
        battle_attacking_enemy_index = attacker
        battle_enemy_attack_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_enemy_attack_frame = 0
        # 敵の攻撃対象：全7仲間キャラからランダムに決定する
        battle_enemy_attack_target = random.choice([-1, -2, -3, -4, -5, -6, -7])

# ---------------------------------------------------------
# advance_battle_turn()：現在の番の演出が完了したあと、次の番へ進める
# （途中で撃破された敵の番はスキップする。全員の番が終わったらコマンド選択ステートへ戻る）
# ---------------------------------------------------------
def advance_battle_turn():
    global battle_turn_index, battle_phase
    global battle_whip_phase, battle_whip_frame
    global battle_samurai_whip_phase, battle_samurai_whip_frame
    global battle_warrior_whip_phase, battle_warrior_whip_frame
    global battle_sister_whip_phase, battle_sister_whip_frame
    global battle_kunoichi_whip_phase, battle_kunoichi_whip_frame
    global battle_wizard_whip_phase, battle_wizard_whip_frame
    global battle_fighter_whip_phase, battle_fighter_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_dance_phase, battle_dance_frame
    global battle_attacking_enemy_index
    global battle_target_enemy_index, battle_samurai_target_enemy_index, battle_warrior_target_enemy_index
    global battle_sister_target_enemy_index, battle_kunoichi_target_enemy_index
    global battle_wizard_target_enemy_index, battle_fighter_target_enemy_index

    battle_attacking_enemy_index = -1

    battle_turn_index += 1
    while battle_turn_index < len(battle_turn_order):
        attacker = battle_turn_order[battle_turn_index]
        if attacker >= 0 and enemy_defeated[attacker]:
            battle_turn_index += 1
            continue
        # 攻撃対象が既に倒されている場合：この番をスキップする
        if (attacker == -1 and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP
                and enemy_defeated[battle_target_enemy_index]):
            battle_turn_index += 1
            continue
        if attacker == -2 and enemy_defeated[battle_samurai_target_enemy_index]:
            battle_turn_index += 1
            continue
        if attacker == -3 and enemy_defeated[battle_warrior_target_enemy_index]:
            battle_turn_index += 1
            continue
        if attacker == -4 and enemy_defeated[battle_sister_target_enemy_index]:
            battle_turn_index += 1
            continue
        if attacker == -5 and enemy_defeated[battle_kunoichi_target_enemy_index]:
            battle_turn_index += 1
            continue
        if attacker == -6 and enemy_defeated[battle_wizard_target_enemy_index]:
            battle_turn_index += 1
            continue
        if attacker == -7 and enemy_defeated[battle_fighter_target_enemy_index]:
            battle_turn_index += 1
            continue
        break

    if battle_turn_index >= len(battle_turn_order):
        # 攻撃対象が撃破済みのまま残っている場合は、生存中の敵のいずれかへ向け直す
        if enemy_defeated[battle_target_enemy_index]:
            battle_target_enemy_index = find_alive_enemy_index(battle_target_enemy_index, 1)
        if enemy_defeated[battle_samurai_target_enemy_index]:
            battle_samurai_target_enemy_index = find_alive_enemy_index(battle_samurai_target_enemy_index, 1)
        if enemy_defeated[battle_warrior_target_enemy_index]:
            battle_warrior_target_enemy_index = find_alive_enemy_index(battle_warrior_target_enemy_index, 1)
        if enemy_defeated[battle_sister_target_enemy_index]:
            battle_sister_target_enemy_index = find_alive_enemy_index(battle_sister_target_enemy_index, 1)
        if enemy_defeated[battle_kunoichi_target_enemy_index]:
            battle_kunoichi_target_enemy_index = find_alive_enemy_index(battle_kunoichi_target_enemy_index, 1)
        if enemy_defeated[battle_wizard_target_enemy_index]:
            battle_wizard_target_enemy_index = find_alive_enemy_index(battle_wizard_target_enemy_index, 1)
        if enemy_defeated[battle_fighter_target_enemy_index]:
            battle_fighter_target_enemy_index = find_alive_enemy_index(battle_fighter_target_enemy_index, 1)

        battle_phase = battle_first_command_phase()
        battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_whip_frame = 0
        battle_samurai_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_samurai_whip_frame = 0
        battle_warrior_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_warrior_whip_frame = 0
        battle_sister_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_sister_whip_frame = 0
        battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_kunoichi_whip_frame = 0
        battle_wizard_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_wizard_whip_frame = 0
        battle_fighter_whip_phase = BATTLE_WHIP_PHASE_APPROACH
        battle_fighter_whip_frame = 0
        battle_flame_phase = BATTLE_FLAME_PHASE_CAST
        battle_flame_frame = 0
        battle_dance_phase = BATTLE_DANCE_PHASE_SINK
        battle_dance_frame = 0
    else:
        start_battle_turn()

# ---------------------------------------------------------
# initialize()
# ---------------------------------------------------------
def initialize():
    global tile_map, walk_images, walk_image_filenames, last_image, battle_back_img, battle_back_img_raw
    global result_heroine_win_img, result_samurai_win_img, result_warrior_win_img, enemy_img_raw, dance_images_raw, voice_win_by_number, voice_samurai_win_by_number, voice_warrior_win_by_number
    global result_sister_win_img, result_kunoichi_win_img, result_wizard_win_img, result_fighter_win_img
    global voice_sister_win_by_number, voice_kunoichi_win_by_number, voice_wizard_win_by_number, voice_fighter_win_by_number
    global heroine_front_img_raw, samurai_front_img_raw, samurai_back_img_raw, character_art_top_height_m
    global warrior_front_img_raw, warrior_back_img_raw
    global sister_front_img_raw, sister_back_img_raw
    global kunoichi_front_img_raw, kunoichi_back_img_raw
    global wizard_front_img_raw, wizard_back_img_raw
    global fighter_front_img_raw, fighter_back_img_raw
    global voice_battle_start_list, voice_samurai_battle_start_list, voice_warrior_battle_start_list, voice_samurai_attack_list, voice_warrior_attack_list, voice_attack_by_number, voice_goblin_damaged, voice_heroine_damaged, voice_samurai_damaged, voice_warrior_damaged, voice_dance, voice_katana_slash
    global voice_sister_battle_start_list, voice_kunoichi_battle_start_list, voice_wizard_battle_start_list, voice_fighter_battle_start_list
    global sound_battle2_bgm
    global voice_shinganken_0, voice_shinganken_1
    global player_world_x, player_world_y

    for my in range(TILE_MIN, TILE_MAX + 1):
        for mx in range(TILE_MIN, TILE_MAX + 1):
            tile_map[(mx, my)] = random.choice(TILE_LIST)

    # ★ フィールド表示・ステータス前姿・勝利バストショットを兼ねるヒロイン前姿画像（bunny_front.png）を読み込む
    # 歩行アニメーションは廃止し、フィールドでもこの画像を静止表示する
    heroine_front_img_raw = pygame.image.load(HEROINE_FRONT_IMG_PATH).convert_alpha()
    walk_images = [heroine_front_img_raw]
    walk_image_filenames = ["bunny_front.png"]
    last_image = heroine_front_img_raw

    # ★ 後ろ姿画像を読み込み → スケール
    raw_img = pygame.image.load(BACK_IMG_PATH).convert_alpha()
    orig_w, orig_h = raw_img.get_size()

    battle_back_img_raw = raw_img  # オリジナルを保持

    target_h = int(HEROINE_HEIGHT_M * BATTLE_HEROINE_FIRST_METER_TO_PIXEL)
    scale = target_h / orig_h

    battle_back_img = pygame.transform.smoothscale(
        raw_img,
        (int(orig_w * scale), target_h)
    )

    # ★ 敵（goblin）画像を読み込み（描画時にスケールするためオリジナルのみ保持）
    enemy_img_raw = pygame.image.load(ENEMY_GOBLIN_IMG_PATH).convert_alpha()

    # ★ ステータスウィンドウ用：サムライ・女戦士・シスターの前姿／後ろ姿画像を読み込み（描画時にスケールするためオリジナルのまま保持）
    # （ヒロインのheroine_front_img_rawは上で読み込み済み）
    samurai_front_img_raw = pygame.image.load(SAMURAI_FRONT_IMG_PATH).convert_alpha()
    samurai_back_img_raw  = pygame.image.load(SAMURAI_BACK_IMG_PATH).convert_alpha()
    warrior_front_img_raw = pygame.image.load(WARRIOR_FRONT_IMG_PATH).convert_alpha()
    warrior_back_img_raw  = pygame.image.load(WARRIOR_BACK_IMG_PATH).convert_alpha()
    sister_front_img_raw    = pygame.image.load(SISTER_FRONT_IMG_PATH).convert_alpha()
    sister_back_img_raw     = pygame.image.load(SISTER_BACK_IMG_PATH).convert_alpha()
    kunoichi_front_img_raw  = pygame.image.load(KUNOICHI_FRONT_IMG_PATH).convert_alpha()
    kunoichi_back_img_raw   = pygame.image.load(KUNOICHI_BACK_IMG_PATH).convert_alpha()
    wizard_front_img_raw    = pygame.image.load(WIZARD_FRONT_IMG_PATH).convert_alpha()
    wizard_back_img_raw     = pygame.image.load(WIZARD_BACK_IMG_PATH).convert_alpha()
    fighter_front_img_raw   = pygame.image.load(FIGHTER_FRONT_IMG_PATH).convert_alpha()
    fighter_back_img_raw    = pygame.image.load(FIGHTER_BACK_IMG_PATH).convert_alpha()

    # ★ [デバッグ] 立ち姿画像ごとに「実際のキャラ絵が始まる高さ」をワールド座標系（メートル）で算出して記録する
    character_art_top_height_m["goblin_idle.png"] = scan_art_top_height_m(enemy_img_raw, ENEMY_GOBLIN_HEIGHT_M)
    character_art_top_height_m["bunny_front.png"] = scan_art_top_height_m(heroine_front_img_raw, HEROINE_HEIGHT_M)
    character_art_top_height_m["bunny_back.png"]  = scan_art_top_height_m(battle_back_img_raw, HEROINE_HEIGHT_M)
    character_art_top_height_m["samurai_front.png"] = scan_art_top_height_m(samurai_front_img_raw, SAMURAI_HEIGHT_M)
    character_art_top_height_m["samurai_back.png"]  = scan_art_top_height_m(samurai_back_img_raw, SAMURAI_HEIGHT_M)
    character_art_top_height_m["warrior_front.png"] = scan_art_top_height_m(warrior_front_img_raw, WARRIOR_HEIGHT_M)
    character_art_top_height_m["warrior_back.png"]  = scan_art_top_height_m(warrior_back_img_raw, WARRIOR_HEIGHT_M)
    character_art_top_height_m["sister_front.png"]    = scan_art_top_height_m(sister_front_img_raw, SISTER_HEIGHT_M)
    character_art_top_height_m["sister_back.png"]     = scan_art_top_height_m(sister_back_img_raw, SISTER_HEIGHT_M)
    character_art_top_height_m["kunoichi_front.png"]  = scan_art_top_height_m(kunoichi_front_img_raw, KUNOICHI_HEIGHT_M)
    character_art_top_height_m["kunoichi_back.png"]   = scan_art_top_height_m(kunoichi_back_img_raw, KUNOICHI_HEIGHT_M)
    character_art_top_height_m["wizard_front.png"]    = scan_art_top_height_m(wizard_front_img_raw, WIZARD_HEIGHT_M)
    character_art_top_height_m["wizard_back.png"]     = scan_art_top_height_m(wizard_back_img_raw, WIZARD_HEIGHT_M)
    character_art_top_height_m["fighter_front.png"]   = scan_art_top_height_m(fighter_front_img_raw, FIGHTER_HEIGHT_M)
    character_art_top_height_m["fighter_back.png"]    = scan_art_top_height_m(fighter_back_img_raw, FIGHTER_HEIGHT_M)

    # ★ 勝利バストショット画像（ヒロイン）：bunny_front.pngを、
    # RESULT_HEROINE_WIN_WIDTH_M（ゲームウィンドウ幅が何mに相当するか）から算出した
    # HEROINE_HEIGHT_M分の高さに一度だけスケールする（以後リザルト中の追加の拡縮は行わない）
    result_heroine_win_meter_to_pixel = SCREEN_W / RESULT_HEROINE_WIN_WIDTH_M
    her_win_orig_w, her_win_orig_h = heroine_front_img_raw.get_size()
    her_win_img_h = max(1, int(HEROINE_HEIGHT_M * result_heroine_win_meter_to_pixel))
    her_win_img_w = max(1, int(her_win_orig_w * her_win_img_h / her_win_orig_h))
    result_heroine_win_img = pygame.transform.smoothscale(heroine_front_img_raw, (her_win_img_w, her_win_img_h))

    # ★ 勝利バストショット画像（サムライがトドメを刺した場合）：samurai_front.pngを、
    # RESULT_SAMURAI_WIN_WIDTH_M（ゲームウィンドウ幅が何mに相当するか）から算出した
    # SAMURAI_HEIGHT_M分の高さに一度だけスケールする（以後リザルト中の追加の拡縮は行わない）
    result_samurai_win_meter_to_pixel = SCREEN_W / RESULT_SAMURAI_WIN_WIDTH_M
    sam_win_orig_w, sam_win_orig_h = samurai_front_img_raw.get_size()
    sam_win_img_h = max(1, int(SAMURAI_HEIGHT_M * result_samurai_win_meter_to_pixel))
    sam_win_img_w = max(1, int(sam_win_orig_w * sam_win_img_h / sam_win_orig_h))
    result_samurai_win_img = pygame.transform.smoothscale(samurai_front_img_raw, (sam_win_img_w, sam_win_img_h))

    # ★ 勝利バストショット画像（女戦士がトドメを刺した場合）：warrior_front.pngを、
    # RESULT_WARRIOR_WIN_WIDTH_M（ゲームウィンドウ幅が何mに相当するか）から算出した
    # WARRIOR_HEIGHT_M分の高さに一度だけスケールする（以後リザルト中の追加の拡縮は行わない）
    result_warrior_win_meter_to_pixel = SCREEN_W / RESULT_WARRIOR_WIN_WIDTH_M
    war_win_orig_w, war_win_orig_h = warrior_front_img_raw.get_size()
    war_win_img_h = max(1, int(WARRIOR_HEIGHT_M * result_warrior_win_meter_to_pixel))
    war_win_img_w = max(1, int(war_win_orig_w * war_win_img_h / war_win_orig_h))
    result_warrior_win_img = pygame.transform.smoothscale(warrior_front_img_raw, (war_win_img_w, war_win_img_h))

    def _make_win_img(front_img_raw, height_m, win_width_m):
        m2p = SCREEN_W / win_width_m
        ow, oh = front_img_raw.get_size()
        ih = max(1, int(height_m * m2p))
        iw = max(1, int(ow * ih / oh))
        return pygame.transform.smoothscale(front_img_raw, (iw, ih))

    result_sister_win_img   = _make_win_img(sister_front_img_raw,   SISTER_HEIGHT_M,   RESULT_SISTER_WIN_WIDTH_M)
    result_kunoichi_win_img = _make_win_img(kunoichi_front_img_raw, KUNOICHI_HEIGHT_M, RESULT_KUNOICHI_WIN_WIDTH_M)
    result_wizard_win_img   = _make_win_img(wizard_front_img_raw,   WIZARD_HEIGHT_M,   RESULT_WIZARD_WIN_WIDTH_M)
    result_fighter_win_img  = _make_win_img(fighter_front_img_raw,  FIGHTER_HEIGHT_M,  RESULT_FIGHTER_WIN_WIDTH_M)

    # ★ マカダンス演出用画像を読み込み（描画時にスケールするためオリジナルのまま保持）
    dance_images_raw = load_dance_images()

    voice_win_by_number = load_win_voices()

    voice_samurai_win_by_number = load_samurai_win_voices()

    voice_warrior_win_by_number  = load_warrior_win_voices()
    voice_sister_win_by_number   = _load_win_voices_for("sister")
    voice_kunoichi_win_by_number = _load_win_voices_for("kunoichi")
    voice_wizard_win_by_number   = _load_win_voices_for("wizard")
    voice_fighter_win_by_number  = _load_win_voices_for("fighter")

    voice_battle_start_list = load_battle_start_voices()

    voice_samurai_battle_start_list  = load_samurai_battle_start_voices()
    voice_warrior_battle_start_list  = load_warrior_battle_start_voices()
    voice_sister_battle_start_list   = _load_battle_start_voices_for("sister",   VOICE_WARRIOR_BATTLE_START_VOLUME)
    voice_kunoichi_battle_start_list = _load_battle_start_voices_for("kunoichi", VOICE_WARRIOR_BATTLE_START_VOLUME)
    voice_wizard_battle_start_list   = _load_battle_start_voices_for("wizard",   VOICE_WARRIOR_BATTLE_START_VOLUME)
    voice_fighter_battle_start_list  = _load_battle_start_voices_for("fighter",  VOICE_WARRIOR_BATTLE_START_VOLUME)

    voice_samurai_attack_list = load_samurai_attack_voices()

    voice_warrior_attack_list = load_warrior_attack_voices()

    voice_attack_by_number = load_attack_voices()

    voice_goblin_damaged = pygame.mixer.Sound(VOICE_GOBLIN_DAMAGED_PATH)
    voice_goblin_damaged.set_volume(VOICE_GOBLIN_DAMAGED_VOLUME)

    voice_heroine_damaged = pygame.mixer.Sound(VOICE_HEROINE_DAMAGED_PATH)
    voice_heroine_damaged.set_volume(VOICE_HEROINE_DAMAGED_VOLUME)

    voice_samurai_damaged = pygame.mixer.Sound(VOICE_SAMURAI_DAMAGED_PATH)
    voice_samurai_damaged.set_volume(VOICE_SAMURAI_DAMAGED_VOLUME)

    voice_warrior_damaged = pygame.mixer.Sound(VOICE_WARRIOR_DAMAGED_PATH)
    voice_warrior_damaged.set_volume(VOICE_WARRIOR_DAMAGED_VOLUME)

    voice_dance = load_sound_at_speed(VOICE_DANCE_PATH, VOICE_DANCE_SPEED)
    voice_dance.set_volume(VOICE_DANCE_VOLUME)

    sound_battle2_bgm = pygame.mixer.Sound(BGM_BATTLE2_PATH)
    sound_battle2_bgm.set_volume(BGM_BATTLE2_VOLUME)

    voice_katana_slash = pygame.mixer.Sound(VOICE_KATANA_SLASH_PATH)
    voice_katana_slash.set_volume(VOICE_KATANA_SLASH_VOLUME)

    voice_shinganken_0 = pygame.mixer.Sound(VOICE_SHINGANKEN_0_PATH)
    voice_shinganken_0.set_volume(VOICE_SHINGANKEN_VOLUME)

    voice_shinganken_1 = pygame.mixer.Sound(VOICE_SHINGANKEN_1_PATH)
    voice_shinganken_1.set_volume(VOICE_SHINGANKEN_VOLUME)

    player_world_x, player_world_y = resolve_collision(player_world_x, player_world_y)

# ---------------------------------------------------------
# get_samurai_base_position()：攻防フェーズ（ズームアウト完了後）でのサムライの基準位置・サイズを返す
# 心眼剣のように移動せずその場でトドメを刺す攻撃で、enter_result_state() の samurai_override に渡すために使う
# （render_battle() 内の sam_base_x / sam_base_bottom_y / sam_base_img_h と同じ式だが、
#   攻防フェーズではズームアウトが完了している（focus_t_eased == 1.0）ため、LAST側の定数のみで算出できる）
# ---------------------------------------------------------
def get_samurai_base_position():
    band_bottom_full = SCREEN_H // 2 - BATTLE_MAIN_WINDOW_HEIGHT // 2 + BATTLE_MAIN_WINDOW_HEIGHT
    sam_base_bottom_y = band_bottom_full + int(BATTLE_HEROINE_LAST_FOCUS_M * BATTLE_HEROINE_LAST_METER_TO_PIXEL)
    sam_base_img_h = max(1, int(SAMURAI_HEIGHT_M * BATTLE_HEROINE_LAST_METER_TO_PIXEL))
    sam_base_x = SCREEN_W // 2 + int(battle_character_world_offset_m[-2] * BATTLE_HEROINE_LAST_METER_TO_PIXEL)
    return sam_base_x, sam_base_bottom_y, sam_base_img_h

# ---------------------------------------------------------
# enter_result_state()：バトルからリザルトへ遷移する
# ---------------------------------------------------------
def enter_result_state(heroine_override=None,
                       samurai_finish=False, samurai_override=None,
                       warrior_finish=False, warrior_override=None,
                       sister_finish=False, sister_override=None,
                       kunoichi_finish=False, kunoichi_override=None,
                       wizard_finish=False, wizard_override=None,
                       fighter_finish=False, fighter_override=None):
    global game_state
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame
    global result_flashout_heroine_override, result_flashout_samurai_override, result_flashout_is_samurai
    global result_flashout_warrior_override, result_flashout_is_warrior, result_flashout_active_char
    global result_win_voice, result_active_win_img
    global result_victory_message, result_message_complete_frame, result_win_bgm_start_frame
    global heroine_hp, samurai_hp, warrior_hp, sister_hp, kunoichi_hp, wizard_hp, fighter_hp
    global heroine_damage_anim_old_hp, heroine_damage_anim_new_hp, heroine_damage_anim_frame
    global samurai_damage_anim_old_hp, samurai_damage_anim_new_hp, samurai_damage_anim_frame
    global warrior_damage_anim_old_hp, warrior_damage_anim_new_hp, warrior_damage_anim_frame
    global sister_damage_anim_old_hp, sister_damage_anim_new_hp, sister_damage_anim_frame
    global kunoichi_damage_anim_old_hp, kunoichi_damage_anim_new_hp, kunoichi_damage_anim_frame
    global wizard_damage_anim_old_hp, wizard_damage_anim_new_hp, wizard_damage_anim_frame
    global fighter_damage_anim_old_hp, fighter_damage_anim_new_hp, fighter_damage_anim_frame

    game_state = STATE_RESULT

    # ★ 決着の瞬間：戦闘曲（battle2.mp3）を即停止する
    sound_battle2_bgm.stop()

    # ★ 戦闘終了時にHP全回復（ダメージアニメ状態もリセット）
    heroine_hp = HEROINE_MAX_HP
    heroine_damage_anim_old_hp = HEROINE_MAX_HP
    heroine_damage_anim_new_hp = HEROINE_MAX_HP
    heroine_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
    samurai_hp = SAMURAI_MAX_HP
    samurai_damage_anim_old_hp = SAMURAI_MAX_HP
    samurai_damage_anim_new_hp = SAMURAI_MAX_HP
    samurai_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
    warrior_hp = WARRIOR_MAX_HP
    warrior_damage_anim_old_hp = WARRIOR_MAX_HP
    warrior_damage_anim_new_hp = WARRIOR_MAX_HP
    warrior_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
    sister_hp = SISTER_MAX_HP
    sister_damage_anim_old_hp = SISTER_MAX_HP
    sister_damage_anim_new_hp = SISTER_MAX_HP
    sister_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
    kunoichi_hp = KUNOICHI_MAX_HP
    kunoichi_damage_anim_old_hp = KUNOICHI_MAX_HP
    kunoichi_damage_anim_new_hp = KUNOICHI_MAX_HP
    kunoichi_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
    wizard_hp = WIZARD_MAX_HP
    wizard_damage_anim_old_hp = WIZARD_MAX_HP
    wizard_damage_anim_new_hp = WIZARD_MAX_HP
    wizard_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME
    fighter_hp = FIGHTER_MAX_HP
    fighter_damage_anim_old_hp = FIGHTER_MAX_HP
    fighter_damage_anim_new_hp = FIGHTER_MAX_HP
    fighter_damage_anim_frame  = DAMAGE_ANIM_DONE_FRAME

    battle_flashout_frame    = 0
    result_white_delay_frame = 0
    result_slidein_frame     = 0
    result_text_delay_frame  = 0
    result_text_frame        = 0
    # フラッシュアウト中のヒロイン／サムライ／女戦士表示位置・スケールの上書き指定（(x, 足元y, 画像高さ) のタプル、または None＝通常位置）
    # ムチ・剣・斧で最後の敵を倒した直後にリザルトへ遷移した場合などに、表示位置が瞬間的にスナップして見えるのを防ぐために使う
    result_flashout_heroine_override = heroine_override
    result_flashout_samurai_override = samurai_override
    result_flashout_warrior_override = warrior_override
    # フラッシュアウトで表示するキャラ：サムライ／女戦士以外がトドメを刺した場合もヒロインの代わりに表示する
    result_flashout_is_samurai = samurai_finish
    result_flashout_is_warrior = (warrior_finish or sister_finish or kunoichi_finish or wizard_finish or fighter_finish)
    if samurai_finish:
        result_flashout_active_char = -2
    elif warrior_finish:
        result_flashout_active_char = -3
    elif sister_finish:
        result_flashout_active_char = -4
    elif kunoichi_finish:
        result_flashout_active_char = -5
    elif wizard_finish:
        result_flashout_active_char = -6
    elif fighter_finish:
        result_flashout_active_char = -7
    else:
        result_flashout_active_char = -1

    def _pick_voice_win(voice_dict, messages, img):
        """voice_dictが空でない場合はランダムにボイスを選び、メッセージ・画像を設定する"""
        if voice_dict:
            n = random.choice(list(voice_dict.keys()))
            return voice_dict[n], messages.get(n, ''), img
        return None, messages.get(0, ''), img

    if warrior_finish:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_warrior_win_by_number, RESULT_WARRIOR_VICTORY_MESSAGES, result_warrior_win_img)
    elif samurai_finish:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_samurai_win_by_number, RESULT_SAMURAI_VICTORY_MESSAGES, result_samurai_win_img)
    elif sister_finish:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_sister_win_by_number, RESULT_SISTER_VICTORY_MESSAGES, result_sister_win_img)
    elif kunoichi_finish:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_kunoichi_win_by_number, RESULT_KUNOICHI_VICTORY_MESSAGES, result_kunoichi_win_img)
    elif wizard_finish:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_wizard_win_by_number, RESULT_WIZARD_VICTORY_MESSAGES, result_wizard_win_img)
    elif fighter_finish:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_fighter_win_by_number, RESULT_FIGHTER_VICTORY_MESSAGES, result_fighter_win_img)
    else:
        result_win_voice, result_victory_message, result_active_win_img = \
            _pick_voice_win(voice_win_by_number, RESULT_VICTORY_MESSAGES, result_heroine_win_img)
    result_message_complete_frame = (len(result_victory_message) - 1) * RESULT_TEXT_FRAMES_PER_CHAR
    result_win_bgm_start_frame = result_message_complete_frame + RESULT_WIN_BGM_DELAY_FRAMES

    # 勝利BGM代用（battle.mp3の指定秒数からの再生）の「先読みシーク」は start_battle() で
    # 済ませてあるため、ここでは無音・一時停止の状態を維持するだけでよい
    # （ここで pygame.mixer.music.stop() すると、シーク済みの再生位置・一時停止状態が失われてしまうため呼ばない）

# ---------------------------------------------------------
# battle_first_command_phase() / battle_second_command_phase() / battle_third_command_phase()：
# コマンド選択の1番手・2番手・3番手のフェーズを返す（battle_command_phase_orderを参照。
# エンカウント時の注視キャラ（battle_focus_character）に応じてstart_battle()で決定される）
# ---------------------------------------------------------
def battle_first_command_phase():
    return battle_command_phase_order[0]


def battle_second_command_phase():
    return battle_command_phase_order[1]


def battle_third_command_phase():
    return battle_command_phase_order[2]


def battle_fourth_command_phase():
    return battle_command_phase_order[3]


def battle_fifth_command_phase():
    return battle_command_phase_order[4]


def battle_sixth_command_phase():
    return battle_command_phase_order[5]


def battle_seventh_command_phase():
    return battle_command_phase_order[6]


# ---------------------------------------------------------
# サムライの行動選択肢を返す（マカダンスでバフがかかる前は「刀」のみ、バフ後は「心眼剣」のみ）
# ---------------------------------------------------------
def get_samurai_menu_options():
    return SAMURAI_MENU_OPTIONS_POWERED_UP if samurai_powered_up else SAMURAI_MENU_OPTIONS_NORMAL

# ---------------------------------------------------------
# バトルのコマンド選択操作：人間のキー入力／AIユーザモードの双方から呼び出される共通処理
# （戦闘シーケンスのコア＝update()側は、これらがどちらから呼ばれたかを意識しない）
# ---------------------------------------------------------
def battle_menu_cursor_step(direction):
    # 行動メニューのカーソルを1段階動かす（direction: -1=上, +1=下）
    global battle_menu_selected_index, battle_samurai_menu_selected_index, battle_warrior_menu_selected_index
    global battle_sister_menu_selected_index, battle_kunoichi_menu_selected_index
    global battle_wizard_menu_selected_index, battle_fighter_menu_selected_index
    if battle_phase == BATTLE_PHASE_COMMAND_HEROINE:
        battle_menu_selected_index = (battle_menu_selected_index + direction) % len(BATTLE_MENU_OPTIONS)
    elif battle_phase == BATTLE_PHASE_COMMAND_SAMURAI:
        battle_samurai_menu_selected_index = (battle_samurai_menu_selected_index + direction) % len(get_samurai_menu_options())
    elif battle_phase == BATTLE_PHASE_COMMAND_WARRIOR:
        battle_warrior_menu_selected_index = (battle_warrior_menu_selected_index + direction) % len(WARRIOR_MENU_OPTIONS)
    elif battle_phase == BATTLE_PHASE_COMMAND_SISTER:
        battle_sister_menu_selected_index = (battle_sister_menu_selected_index + direction) % len(SISTER_MENU_OPTIONS)
    elif battle_phase == BATTLE_PHASE_COMMAND_KUNOICHI:
        battle_kunoichi_menu_selected_index = (battle_kunoichi_menu_selected_index + direction) % len(KUNOICHI_MENU_OPTIONS)
    elif battle_phase == BATTLE_PHASE_COMMAND_WIZARD:
        battle_wizard_menu_selected_index = (battle_wizard_menu_selected_index + direction) % len(WIZARD_MENU_OPTIONS)
    elif battle_phase == BATTLE_PHASE_COMMAND_FIGHTER:
        battle_fighter_menu_selected_index = (battle_fighter_menu_selected_index + direction) % len(FIGHTER_MENU_OPTIONS)


def battle_target_cursor_step(direction):
    # 攻撃対象（敵）のカーソルを1段階動かす（direction: -1=左, +1=右。撃破済みの敵は選択をスキップする）
    global battle_target_enemy_index, battle_samurai_target_enemy_index, battle_warrior_target_enemy_index
    global battle_sister_target_enemy_index, battle_kunoichi_target_enemy_index
    global battle_wizard_target_enemy_index, battle_fighter_target_enemy_index
    if battle_phase == BATTLE_PHASE_COMMAND_HEROINE and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP:
        battle_target_enemy_index = find_alive_enemy_index(battle_target_enemy_index, direction)
    elif battle_phase == BATTLE_PHASE_COMMAND_SAMURAI and battle_samurai_menu_selected_index in (SAMURAI_MENU_INDEX_SWORD, SAMURAI_MENU_INDEX_SHINGANKEN):
        battle_samurai_target_enemy_index = find_alive_enemy_index(battle_samurai_target_enemy_index, direction)
    elif battle_phase == BATTLE_PHASE_COMMAND_WARRIOR and battle_warrior_menu_selected_index == WARRIOR_MENU_INDEX_AXE:
        battle_warrior_target_enemy_index = find_alive_enemy_index(battle_warrior_target_enemy_index, direction)
    elif battle_phase == BATTLE_PHASE_COMMAND_SISTER:
        battle_sister_target_enemy_index = find_alive_enemy_index(battle_sister_target_enemy_index, direction)
    elif battle_phase == BATTLE_PHASE_COMMAND_KUNOICHI:
        battle_kunoichi_target_enemy_index = find_alive_enemy_index(battle_kunoichi_target_enemy_index, direction)
    elif battle_phase == BATTLE_PHASE_COMMAND_WIZARD:
        battle_wizard_target_enemy_index = find_alive_enemy_index(battle_wizard_target_enemy_index, direction)
    elif battle_phase == BATTLE_PHASE_COMMAND_FIGHTER:
        battle_fighter_target_enemy_index = find_alive_enemy_index(battle_fighter_target_enemy_index, direction)


def _init_command_phase(phase):
    """指定フェーズのメニュー選択・ターゲットを初期化する（battle_command_confirm から呼ぶ）"""
    global battle_menu_selected_index, battle_target_enemy_index
    global battle_samurai_menu_selected_index, battle_samurai_target_enemy_index
    global battle_warrior_menu_selected_index, battle_warrior_target_enemy_index
    global battle_sister_menu_selected_index, battle_sister_target_enemy_index
    global battle_kunoichi_menu_selected_index, battle_kunoichi_target_enemy_index
    global battle_wizard_menu_selected_index, battle_wizard_target_enemy_index
    global battle_fighter_menu_selected_index, battle_fighter_target_enemy_index
    first = find_alive_enemy_index(-1, 1)
    if phase == BATTLE_PHASE_COMMAND_HEROINE:
        battle_menu_selected_index = 0
        battle_target_enemy_index = first
    elif phase == BATTLE_PHASE_COMMAND_SAMURAI:
        battle_samurai_menu_selected_index = 0
        battle_samurai_target_enemy_index = first
    elif phase == BATTLE_PHASE_COMMAND_WARRIOR:
        battle_warrior_menu_selected_index = 0
        battle_warrior_target_enemy_index = first
    elif phase == BATTLE_PHASE_COMMAND_SISTER:
        battle_sister_menu_selected_index = 0
        battle_sister_target_enemy_index = first
    elif phase == BATTLE_PHASE_COMMAND_KUNOICHI:
        battle_kunoichi_menu_selected_index = 0
        battle_kunoichi_target_enemy_index = first
    elif phase == BATTLE_PHASE_COMMAND_WIZARD:
        battle_wizard_menu_selected_index = 0
        battle_wizard_target_enemy_index = first
    elif phase == BATTLE_PHASE_COMMAND_FIGHTER:
        battle_fighter_menu_selected_index = 0
        battle_fighter_target_enemy_index = first


def battle_command_confirm():
    # 行動決定（Enterキー相当）：1番手→2番手→…→7番手の選択完了後、攻防ステートへ遷移する
    global battle_phase, battle_exchange_frame
    global battle_turn_order, battle_turn_index
    phase_fns = [battle_first_command_phase, battle_second_command_phase, battle_third_command_phase,
                 battle_fourth_command_phase, battle_fifth_command_phase, battle_sixth_command_phase,
                 battle_seventh_command_phase]
    phases = [f() for f in phase_fns]
    if battle_phase in phases[:6]:
        idx = phases.index(battle_phase)
        battle_phase = phases[idx + 1]
        _init_command_phase(battle_phase)
    elif battle_phase == phases[6]:
        battle_phase = BATTLE_PHASE_EXCHANGE
        battle_exchange_frame = 0
        # 行動順を決定する：生存している敵全体・全7仲間キャラを含めてランダムにシャッフルする
        alive_indices = [i for i in range(len(enemy_defeated)) if not enemy_defeated[i]]
        battle_turn_order = [-1, -2, -3, -4, -5, -6, -7] + alive_indices
        random.shuffle(battle_turn_order)
        battle_turn_index = 0
        start_battle_turn()


def result_to_field():
    # リザルト画面を閉じてフィールドへ戻る（Enterキー相当）
    global game_state, samurai_powered_up
    game_state = STATE_FIELD
    samurai_powered_up = False  # ★ マカダンスによるサムライの見た目強化は、バトル終了（フィールドへ戻る）までで終了する
    pygame.mixer.music.fadeout(BGM_FIELD_RETURN_FADEOUT_MS)


def start_battle():
    # フィールドからバトルを開始する（Eキー相当）：各種バトル状態を初期化する
    global game_state, battle_anim_frame
    global heroine_focus_delay_frame, heroine_zoomout_frame, heroine_idle_frame, heroine_idle_phase_offset
    global battle_focus_character, battle_command_phase_order, battle_character_world_offset_m
    global enemy_silhouette_frame, enemy_idle_frame, enemy_idle_phase_offsets
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame
    global battle_menu_selected_index, battle_target_enemy_index, battle_target_cursor_frame
    global battle_samurai_menu_selected_index, battle_samurai_target_enemy_index
    global battle_warrior_menu_selected_index, battle_warrior_target_enemy_index
    global battle_sister_menu_selected_index, battle_sister_target_enemy_index
    global battle_kunoichi_menu_selected_index, battle_kunoichi_target_enemy_index
    global battle_wizard_menu_selected_index, battle_wizard_target_enemy_index
    global battle_fighter_menu_selected_index, battle_fighter_target_enemy_index
    global battle_phase, battle_exchange_frame
    global battle_whip_phase, battle_whip_frame
    global battle_samurai_whip_phase, battle_samurai_whip_frame
    global battle_warrior_whip_phase, battle_warrior_whip_frame
    global battle_sister_whip_phase, battle_sister_whip_frame
    global battle_kunoichi_whip_phase, battle_kunoichi_whip_frame
    global battle_wizard_whip_phase, battle_wizard_whip_frame
    global battle_fighter_whip_phase, battle_fighter_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_dance_phase, battle_dance_frame
    global battle_turn_order, battle_turn_index
    global battle_enemy_attack_phase, battle_enemy_attack_frame, battle_attacking_enemy_index, battle_enemy_attack_target
    global enemy_defeated, enemy_hp, battle_annihilate_targets, battle_annihilate_frame
    global heroine_whip_trail_key, samurai_whip_trail_key, warrior_whip_trail_key
    global sister_whip_trail_key, kunoichi_whip_trail_key, wizard_whip_trail_key, fighter_whip_trail_key
    global enemy_damage_anim_old_hp, enemy_damage_anim_new_hp, enemy_damage_anim_frame, enemy_damage_anim_flash_color
    global samurai_powered_up
    global heroine_macadance_used
    global battle_slash_frame, battle_slash_target_enemy_index
    global battle_shingan_frame, battle_shingan_slash_frames, battle_shingan_target_enemy_index

    game_state = STATE_BATTLE
    battle_anim_frame = 0
    heroine_focus_delay_frame = 0
    heroine_zoomout_frame = 0
    heroine_idle_frame = 0
    heroine_idle_phase_offset = random.randint(0, BATTLE_HEROINE_IDLE_PERIOD_FRAMES - 1)
    # ★ ズームアウトの注視先を全7仲間キャラからランダムに決定する
    battle_focus_character = random.choice([-1, -2, -3, -4, -5, -6, -7])
    # ★ 行動選択順は、注視キャラを先頭として7キャラのサイクルを巡回させたものになる
    focus_command_phase = BATTLE_FOCUS_CHARACTER_TO_COMMAND_PHASE[battle_focus_character]
    start_idx = BATTLE_COMMAND_PHASE_CYCLE.index(focus_command_phase)
    battle_command_phase_order = BATTLE_COMMAND_PHASE_CYCLE[start_idx:] + BATTLE_COMMAND_PHASE_CYCLE[:start_idx]
    battle_character_world_offset_m = {
        BATTLE_COMMAND_PHASE_TO_CHARACTER[phase]: BATTLE_ORDER_POSITION_OFFSET_M[order_index]
        for order_index, phase in enumerate(battle_command_phase_order)
    }
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
    battle_samurai_menu_selected_index  = 0
    battle_samurai_target_enemy_index   = 0
    battle_warrior_menu_selected_index  = 0
    battle_warrior_target_enemy_index   = 0
    battle_sister_menu_selected_index   = 0
    battle_sister_target_enemy_index    = 0
    battle_kunoichi_menu_selected_index = 0
    battle_kunoichi_target_enemy_index  = 0
    battle_wizard_menu_selected_index   = 0
    battle_wizard_target_enemy_index    = 0
    battle_fighter_menu_selected_index  = 0
    battle_fighter_target_enemy_index   = 0
    battle_phase = battle_command_phase_order[0]
    battle_exchange_frame = 0
    battle_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_whip_frame = 0
    battle_samurai_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_samurai_whip_frame = 0
    battle_warrior_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_warrior_whip_frame = 0
    battle_sister_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_sister_whip_frame = 0
    battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_kunoichi_whip_frame = 0
    battle_wizard_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_wizard_whip_frame = 0
    battle_fighter_whip_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_fighter_whip_frame = 0
    battle_flame_phase = BATTLE_FLAME_PHASE_CAST
    battle_flame_frame = 0
    battle_dance_phase = BATTLE_DANCE_PHASE_SINK
    battle_dance_frame = 0
    samurai_powered_up = False
    heroine_macadance_used = False
    battle_turn_order = []
    battle_turn_index = 0
    battle_enemy_attack_phase = BATTLE_WHIP_PHASE_APPROACH
    battle_enemy_attack_frame = 0
    battle_attacking_enemy_index = -1
    battle_enemy_attack_target = -1
    enemy_defeated = [False] * len(ENEMY_X_RATIOS)
    enemy_hp = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)
    # ★ ダメージ表現アニメーションも、敵HPのリセットに合わせて初期化する（前回バトルの状態を持ち越さない）
    enemy_damage_anim_old_hp = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)
    enemy_damage_anim_new_hp = [GOBLIN_MAX_HP] * len(ENEMY_X_RATIOS)
    enemy_damage_anim_frame  = [DAMAGE_ANIM_DONE_FRAME] * len(ENEMY_X_RATIOS)
    enemy_damage_anim_flash_color = [DAMAGE_FLASH_COLOR_WHIP] * len(ENEMY_X_RATIOS)
    battle_annihilate_targets = []
    battle_annihilate_frame   = 0
    heroine_whip_trail.clear()
    heroine_whip_trail_key = None
    samurai_whip_trail.clear()
    samurai_whip_trail_key = None
    warrior_whip_trail.clear()
    warrior_whip_trail_key = None
    sister_whip_trail.clear()
    sister_whip_trail_key = None
    kunoichi_whip_trail.clear()
    kunoichi_whip_trail_key = None
    wizard_whip_trail.clear()
    wizard_whip_trail_key = None
    fighter_whip_trail.clear()
    fighter_whip_trail_key = None
    battle_slash_frame = BATTLE_SLASH_TOTAL_FRAMES  # ★ 刀の斬撃エフェクトも、バトルごとに非表示状態へリセットする
    battle_slash_target_enemy_index = -1
    battle_shingan_frame = -1  # ★ 心眼剣の斬撃エフェクトも、バトルごとに非表示状態へリセットする
    battle_shingan_slash_frames = [BATTLE_SLASH_TOTAL_FRAMES] * SHINGANKEN_SLASH_COUNT
    battle_shingan_target_enemy_index = -1
    # ★ バトル中BGMは一旦オフ（マカダンス用BGMと干渉するため）。元に戻す場合は以下のコメントを解除
    # pygame.mixer.music.load(BGM_BATTLE_PATH)
    # pygame.mixer.music.set_volume(BGM_BATTLE_VOLUME)
    # pygame.mixer.music.play()
    pygame.mixer.music.stop()

    # 勝利BGM代用（battle.mp3の指定秒数からの再生）の「先読みシーク」をバトル開始時点で済ませておく。
    # MP3は途中の再生位置へシークする際に先頭からのデコードが必要で処理時間がかかり（実測で約100ms）、
    # enter_result_state()（攻防フェーズの決着直後）で行うと、その一瞬だけ処理落ちして「ひっかかる」ように
    # 感じられてしまう。そのため、まだ何も始まっていないバトル開始時点で無音・一時停止の状態でシークだけ
    # 先に終わらせ、リザルト中（result_win_bgm_start_frame）では unpause するだけにする
    pygame.mixer.music.load(BGM_BATTLE_PATH)
    pygame.mixer.music.set_volume(0.0)
    pygame.mixer.music.play(start=RESULT_WIN_BGM_START_SEC)
    pygame.mixer.music.pause()

# ---------------------------------------------------------
# AIユーザモード：実際のユーザ操作を模してコマンド選択・リザルト画面の進行を自動操作する
# ---------------------------------------------------------
def ai_cyclic_step_direction(current_index, target_index, length):
    # current_index から target_index へ周回的（% length）に近い方向（-1 or +1）を返す
    # （一致している場合は +1 を返すが、この場合カーソルは動かないため方向に意味はない）
    if length <= 1 or current_index == target_index:
        return 1
    forward_steps  = (target_index - current_index) % length
    backward_steps = (current_index - target_index) % length
    return 1 if forward_steps <= backward_steps else -1


def process_ai_battle_input():
    # game_state == STATE_BATTLE / STATE_RESULT かつポーズ中でない場合に毎フレーム呼ばれる
    global ai_command_step, ai_command_wait_frame
    global ai_menu_target_index, ai_menu_step_dir
    global ai_enemy_target_index, ai_enemy_step_dir
    global ai_result_wait_frame
    global ai_field_wait_frame
    global heroine_macadance_used

    if game_state == STATE_FIELD:
        # フィールドモード開始から指定フレーム経過した瞬間にEキー相当の入力を行いバトルを開始する
        ai_field_wait_frame += 1
        if ai_field_wait_frame >= AI_FIELD_BATTLE_START_FRAMES:
            start_battle()
            ai_field_wait_frame = 0
        return

    ai_field_wait_frame = 0

    if game_state == STATE_RESULT:
        # 勝利BGM再生開始（音量復帰）から指定フレーム経過した瞬間にEnterキー相当の入力を行う
        if result_text_frame >= result_win_bgm_start_frame:
            ai_result_wait_frame += 1
            if ai_result_wait_frame >= AI_RESULT_ENTER_FRAMES:
                result_to_field()
                ai_result_wait_frame = 0
        return

    if game_state != STATE_BATTLE or heroine_zoomout_frame < BATTLE_HEROINE_ZOOMOUT_FRAMES:
        return

    all_command_phases = (BATTLE_PHASE_COMMAND_HEROINE, BATTLE_PHASE_COMMAND_SAMURAI, BATTLE_PHASE_COMMAND_WARRIOR,
                          BATTLE_PHASE_COMMAND_SISTER, BATTLE_PHASE_COMMAND_KUNOICHI,
                          BATTLE_PHASE_COMMAND_WIZARD, BATTLE_PHASE_COMMAND_FIGHTER)
    if battle_phase not in all_command_phases:
        ai_command_step = AI_COMMAND_STEP_DECIDE
        ai_command_wait_frame = 0
        return

    if battle_phase == BATTLE_PHASE_COMMAND_HEROINE:
        menu_options = BATTLE_MENU_OPTIONS
        current_menu_index = battle_menu_selected_index
        target_selection_indices = (BATTLE_MENU_INDEX_WHIP,)
        current_target_index = battle_target_enemy_index
    elif battle_phase == BATTLE_PHASE_COMMAND_SAMURAI:
        menu_options = get_samurai_menu_options()
        current_menu_index = battle_samurai_menu_selected_index
        target_selection_indices = (SAMURAI_MENU_INDEX_SWORD, SAMURAI_MENU_INDEX_SHINGANKEN)
        current_target_index = battle_samurai_target_enemy_index
    elif battle_phase == BATTLE_PHASE_COMMAND_WARRIOR:
        menu_options = WARRIOR_MENU_OPTIONS
        current_menu_index = battle_warrior_menu_selected_index
        target_selection_indices = (WARRIOR_MENU_INDEX_AXE,)
        current_target_index = battle_warrior_target_enemy_index
    elif battle_phase == BATTLE_PHASE_COMMAND_SISTER:
        menu_options = SISTER_MENU_OPTIONS
        current_menu_index = battle_sister_menu_selected_index
        target_selection_indices = tuple(range(len(SISTER_MENU_OPTIONS)))
        current_target_index = battle_sister_target_enemy_index
    elif battle_phase == BATTLE_PHASE_COMMAND_KUNOICHI:
        menu_options = KUNOICHI_MENU_OPTIONS
        current_menu_index = battle_kunoichi_menu_selected_index
        target_selection_indices = tuple(range(len(KUNOICHI_MENU_OPTIONS)))
        current_target_index = battle_kunoichi_target_enemy_index
    elif battle_phase == BATTLE_PHASE_COMMAND_WIZARD:
        menu_options = WIZARD_MENU_OPTIONS
        current_menu_index = battle_wizard_menu_selected_index
        target_selection_indices = tuple(range(len(WIZARD_MENU_OPTIONS)))
        current_target_index = battle_wizard_target_enemy_index
    else:  # BATTLE_PHASE_COMMAND_FIGHTER
        menu_options = FIGHTER_MENU_OPTIONS
        current_menu_index = battle_fighter_menu_selected_index
        target_selection_indices = tuple(range(len(FIGHTER_MENU_OPTIONS)))
        current_target_index = battle_fighter_target_enemy_index

    if ai_command_step == AI_COMMAND_STEP_DECIDE:
        # 行動を完全ランダムに決定し、メニューカーソルを近い方向から目標位置へ合わせ始める
        # ★ マカダンスはバトル中1回のみ使用可能（既に使用済みの場合は選択肢から除外する）
        if battle_phase == BATTLE_PHASE_COMMAND_HEROINE and heroine_macadance_used:
            candidate_indices = [i for i in range(len(menu_options)) if i != BATTLE_MENU_INDEX_DANCE]
            ai_menu_target_index = random.choice(candidate_indices)
        else:
            ai_menu_target_index = random.randrange(len(menu_options))
            if battle_phase == BATTLE_PHASE_COMMAND_HEROINE and ai_menu_target_index == BATTLE_MENU_INDEX_DANCE:
                heroine_macadance_used = True
        ai_menu_step_dir = ai_cyclic_step_direction(current_menu_index, ai_menu_target_index, len(menu_options))
        ai_command_step = AI_COMMAND_STEP_MENU_CURSOR
        ai_command_wait_frame = 0
        return

    ai_command_wait_frame += 1
    if ai_command_wait_frame < AI_CURSOR_MOVE_FRAMES:
        return
    ai_command_wait_frame = 0

    if ai_command_step == AI_COMMAND_STEP_MENU_CURSOR:
        if current_menu_index != ai_menu_target_index:
            battle_menu_cursor_step(ai_menu_step_dir)
            return
        if ai_menu_target_index in target_selection_indices:
            # 複数の敵から攻撃対象を選ぶ必要がある場合：対象をランダムに決定し、カーソルを合わせ始める
            alive_indices = [i for i in range(len(enemy_defeated)) if not enemy_defeated[i]]
            ai_enemy_target_index = random.choice(alive_indices)
            ai_enemy_step_dir = random.choice([-1, 1])
            ai_command_step = AI_COMMAND_STEP_TARGET_CURSOR
        else:
            # 複数の敵から選ぶ必要がなければ決定したものとみなす
            battle_command_confirm()
            ai_command_step = AI_COMMAND_STEP_DECIDE
    elif ai_command_step == AI_COMMAND_STEP_TARGET_CURSOR:
        if current_target_index != ai_enemy_target_index:
            battle_target_cursor_step(ai_enemy_step_dir)
            return
        battle_command_confirm()
        ai_command_step = AI_COMMAND_STEP_DECIDE

# ---------------------------------------------------------
# process_input()
# ---------------------------------------------------------
def process_input():
    global zoom
    global move_x, move_y
    global moving
    global game_state
    global battle_phase
    global is_paused, pause_step_requested
    global pause_step_key_held, pause_step_key_hold_frame, pause_step_key_repeated
    global status_phase, status_anim_frame, status_view
    global is_debug
    global ai_mode_active, ai_command_step, ai_command_wait_frame, ai_result_wait_frame, ai_field_wait_frame

    moving = False
    move_x = 0.0
    move_y = 0.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEWHEEL and not is_paused:
            if event.y > 0:
                zoom -= ZOOM_STEP
            elif event.y < 0:
                zoom += ZOOM_STEP

            zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom))

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e and not is_paused:
            if game_state == STATE_FIELD:
                start_battle()

        # Sキー：フィールド上でステータスモードへ遷移し、ステータスウィンドウを開く
        if event.type == pygame.KEYDOWN and event.key == pygame.K_s and not is_paused:
            if game_state == STATE_FIELD:
                game_state = STATE_STATUS
                status_phase = STATUS_PHASE_OPENING
                status_anim_frame = 0
                status_view = STATUS_VIEW_BACK

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

        # [開発用] Dキー：デバッグ状態の切り替え（モードに関係なくゲーム中ずっと保持される）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_d:
            is_debug = not is_debug

        # Aキー：AIユーザモードの切り替え（ON時はコマンド選択・リザルト画面の進行を自動操作する）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
            ai_mode_active = not ai_mode_active
            ai_command_step = AI_COMMAND_STEP_DECIDE
            ai_command_wait_frame = 0
            ai_result_wait_frame = 0
            ai_field_wait_frame = 0

        # 攻撃選択サブウィンドウ：上下キーで選択位置を変更（ズームアウト完了後・コマンド選択中のみ。
        # システムポーズ中・AIユーザモード中は無効）
        _all_cmd = (BATTLE_PHASE_COMMAND_HEROINE, BATTLE_PHASE_COMMAND_SAMURAI, BATTLE_PHASE_COMMAND_WARRIOR,
                    BATTLE_PHASE_COMMAND_SISTER, BATTLE_PHASE_COMMAND_KUNOICHI,
                    BATTLE_PHASE_COMMAND_WIZARD, BATTLE_PHASE_COMMAND_FIGHTER)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_UP and not is_paused and not ai_mode_active:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase in _all_cmd):
                battle_menu_cursor_step(-1)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN and not is_paused and not ai_mode_active:
            if (game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase in _all_cmd):
                battle_menu_cursor_step(1)

        # ステータスモード：上下キーでキャラクターの前姿／後ろ姿を切り替え（システムポーズ中は無効）
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN) and not is_paused:
            if game_state == STATE_STATUS and status_phase == STATUS_PHASE_OPEN:
                status_view = STATUS_VIEW_FRONT if status_view == STATUS_VIEW_BACK else STATUS_VIEW_BACK

        # ムチ／剣選択中：左右キーで攻撃対象の敵を変更（ズームアウト完了後・コマンド選択中のみ。撃破済みの敵は選択をスキップする。
        # システムポーズ中・AIユーザモード中は無効）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT and not is_paused and not ai_mode_active:
            if game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
                battle_target_cursor_step(-1)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT and not is_paused and not ai_mode_active:
            if game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
                battle_target_cursor_step(1)

        # Enterキー：ヒロインの行動選択 → サムライの行動選択 → 攻防ステートへ遷移（コマンドウィンドウは非表示）／リザルト画面からフィールドへ
        # （システムポーズ中は意図しない進行を防ぐため無効。バトル・リザルトでのこの操作はAIユーザモード中も無効＝AI側が自動で行う）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and not is_paused:
            if (not ai_mode_active and game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase in _all_cmd):
                battle_command_confirm()
            elif not ai_mode_active and game_state == STATE_RESULT:
                result_to_field()
            elif game_state == STATE_STATUS and status_phase == STATUS_PHASE_OPEN:
                status_phase = STATUS_PHASE_CLOSING

        # Spaceキー：ステータスウィンドウを閉じてフィールドモードへ戻る／2番手の行動選択をキャンセルして1番手の選択へ戻る
        # （システムポーズ中は無効。バトルでのキャンセルはAIユーザモード中も無効）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and not is_paused:
            if game_state == STATE_STATUS and status_phase == STATUS_PHASE_OPEN:
                status_phase = STATUS_PHASE_CLOSING
            elif (not ai_mode_active and game_state == STATE_BATTLE and heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES
                    and battle_phase != battle_first_command_phase() and battle_phase in _all_cmd):
                phase_fns = [battle_first_command_phase, battle_second_command_phase, battle_third_command_phase,
                             battle_fourth_command_phase, battle_fifth_command_phase, battle_sixth_command_phase,
                             battle_seventh_command_phase]
                phases = [f() for f in phase_fns]
                if battle_phase in phases[1:]:
                    idx = phases.index(battle_phase)
                    battle_phase = phases[idx - 1]

        # 矢印右キー：ポーズ中は1フレームだけ処理を進める（押し続けるとキーリピートでも進む）
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            if is_paused:
                pause_step_requested = True
                pause_step_key_held       = True
                pause_step_key_hold_frame = 0
                pause_step_key_repeated   = False

        # 矢印右キーを離した瞬間：キーリピートの判定状態をリセットする
        if event.type == pygame.KEYUP and event.key == pygame.K_RIGHT:
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

    if ai_mode_active and not is_paused:
        process_ai_battle_input()

    if game_state in (STATE_BATTLE, STATE_RESULT) or is_paused:
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
    global player_world_x, player_world_y
    global game_state
    global battle_anim_frame, heroine_focus_delay_frame, heroine_zoomout_frame, heroine_idle_frame
    global enemy_silhouette_frame, enemy_idle_frame
    global battle_flashout_frame, result_white_delay_frame, result_slidein_frame
    global result_text_delay_frame, result_text_frame
    global battle_phase, battle_exchange_frame
    global battle_whip_phase, battle_whip_frame
    global battle_samurai_whip_phase, battle_samurai_whip_frame
    global battle_warrior_whip_phase, battle_warrior_whip_frame
    global battle_sister_whip_phase, battle_sister_whip_frame
    global battle_kunoichi_whip_phase, battle_kunoichi_whip_frame
    global battle_wizard_whip_phase, battle_wizard_whip_frame
    global battle_fighter_whip_phase, battle_fighter_whip_frame
    global battle_flame_phase, battle_flame_frame
    global battle_dance_phase, battle_dance_frame
    global samurai_powered_up
    global battle_enemy_attack_phase, battle_enemy_attack_frame, battle_enemy_attack_target
    global battle_target_cursor_frame
    global battle_target_enemy_index, battle_samurai_target_enemy_index, battle_warrior_target_enemy_index
    global battle_sister_target_enemy_index, battle_kunoichi_target_enemy_index
    global battle_wizard_target_enemy_index, battle_fighter_target_enemy_index
    global enemy_defeated, enemy_hp, battle_annihilate_targets, battle_annihilate_frame
    global heroine_hp, samurai_hp, warrior_hp, sister_hp, kunoichi_hp, wizard_hp, fighter_hp
    global status_phase, status_anim_frame
    global heroine_damage_anim_old_hp, heroine_damage_anim_new_hp, heroine_damage_anim_frame, heroine_damage_anim_flash_color
    global samurai_damage_anim_old_hp, samurai_damage_anim_new_hp, samurai_damage_anim_frame, samurai_damage_anim_flash_color
    global warrior_damage_anim_old_hp, warrior_damage_anim_new_hp, warrior_damage_anim_frame, warrior_damage_anim_flash_color
    global sister_damage_anim_old_hp, sister_damage_anim_new_hp, sister_damage_anim_frame, sister_damage_anim_flash_color
    global kunoichi_damage_anim_old_hp, kunoichi_damage_anim_new_hp, kunoichi_damage_anim_frame, kunoichi_damage_anim_flash_color
    global wizard_damage_anim_old_hp, wizard_damage_anim_new_hp, wizard_damage_anim_frame, wizard_damage_anim_flash_color
    global fighter_damage_anim_old_hp, fighter_damage_anim_new_hp, fighter_damage_anim_frame, fighter_damage_anim_flash_color
    global battle_slash_frame, battle_slash_target_enemy_index
    global battle_shingan_frame, battle_shingan_slash_frames, battle_shingan_slash_angles, battle_shingan_target_enemy_index

    if game_state == STATE_STATUS:
        # ステータスウィンドウの開閉アニメ（バトルメインウィンドウと同じフレーム数で開閉する）
        if status_phase == STATUS_PHASE_OPENING:
            if status_anim_frame < BATTLE_MAIN_WINDOW_ANIM_FRAMES:
                status_anim_frame += 1
            else:
                status_phase = STATUS_PHASE_OPEN
        elif status_phase == STATUS_PHASE_CLOSING:
            if status_anim_frame > 0:
                status_anim_frame -= 1
            else:
                game_state = STATE_FIELD
        return

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

        # ★ ダメージ表現アニメーション：毎フレーム経過カウンタを進める（DAMAGE_ANIM_DONE_FRAMEで止まる）
        # 攻防フェーズの進行とは独立しているため、攻撃側の演出タイミングには影響しない
        if heroine_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            heroine_damage_anim_frame += 1
        if samurai_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            samurai_damage_anim_frame += 1
        if warrior_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            warrior_damage_anim_frame += 1
        if sister_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            sister_damage_anim_frame += 1
        if kunoichi_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            kunoichi_damage_anim_frame += 1
        if wizard_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            wizard_damage_anim_frame += 1
        if fighter_damage_anim_frame < DAMAGE_ANIM_DONE_FRAME:
            fighter_damage_anim_frame += 1
        for i in range(len(enemy_damage_anim_frame)):
            if enemy_damage_anim_frame[i] < DAMAGE_ANIM_DONE_FRAME:
                enemy_damage_anim_frame[i] += 1

        # ★ サムライの刀の斬撃エフェクト：毎フレーム経過カウンタを進める（BATTLE_SLASH_TOTAL_FRAMESで止まる）
        # ダメージ表現アニメーションと同様、攻防フェーズの進行とは独立している
        if battle_slash_frame < BATTLE_SLASH_TOTAL_FRAMES:
            battle_slash_frame += 1

        # ★ 心眼剣の斬撃エフェクト（7本）：刀の斬撃と同様、それぞれ独立に毎フレーム経過カウンタを進める
        for i in range(SHINGANKEN_SLASH_COUNT):
            if battle_shingan_slash_frames[i] < BATTLE_SLASH_TOTAL_FRAMES:
                battle_shingan_slash_frames[i] += 1

        # ① バトルメインウィンドウ開くアニメ
        if battle_anim_frame < BATTLE_MAIN_WINDOW_ANIM_FRAMES:
            battle_anim_frame += 1
            return

        # ② 静止フレーム
        if heroine_focus_delay_frame < BATTLE_HEROINE_FOCUS_DELAY_FRAMES:
            heroine_focus_delay_frame += 1
            return

        # ③ ズームアウト：静止が完了した瞬間にかけ声をランダムに選んで再生（注視先に応じてヒロイン／サムライ／女戦士のかけ声を切り替える）
        # 　　また、この瞬間から戦闘曲（battle2.mp3）を再生する
        if heroine_zoomout_frame == 0:
            sound_battle2_bgm.play(loops=-1)
            if battle_focus_character == -3:
                play_warrior_battle_start_voice()
            elif battle_focus_character == -4:
                _play_battle_start_voice_from(voice_sister_battle_start_list)
            elif battle_focus_character == -5:
                _play_battle_start_voice_from(voice_kunoichi_battle_start_list)
            elif battle_focus_character == -6:
                _play_battle_start_voice_from(voice_wizard_battle_start_list)
            elif battle_focus_character == -7:
                _play_battle_start_voice_from(voice_fighter_battle_start_list)
            elif battle_focus_character == -2:
                play_samurai_battle_start_voice()
            else:
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
            if battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME, BATTLE_MENU_INDEX_DANCE):
                # 攻防ステート（ムチ・炎・マカダンス選択時）：ヒロインと生存中の敵全体が、ランダムに決定された行動順（battle_turn_order）に
                # 従って1体ずつ「接近 → 攻撃」（マカダンスの場合は専用演出）を行う。一巡したらコマンド選択ステートへ戻る
                if battle_attacking_enemy_index == -1:
                    attacker = battle_turn_order[battle_turn_index]
                    if attacker == -2:
                        # SAMURAI_MENU_INDEX_SWORD/SHINGANKENはどちらも0のため、menu_selected_indexだけでは区別できない。
                        # マカダンスのバフ後（samurai_powered_up）かどうかで刀／心眼剣を判定する
                        if samurai_powered_up:
                            # 心眼剣：接近せずその場にとどまり、SHINGANKEN_WAIT_FRAMES経過後から
                            # SHINGANKEN_SLASH_INTERVAL_FRAMESごとに次々と斬撃を発生させる（計SHINGANKEN_SLASH_COUNT回）。
                            # 各斬撃の軌跡は刀の斬撃と同じ長さ・中心で、方向のみ360度からランダムに選ぶ
                            # （ダメージ表現アニメーションとは独立して進行する）。
                            # 最後（7回目）の斬撃の軌跡先端が終点に到達した瞬間にまとめてダメージを適用し、
                            # その後SHINGANKEN_END_DELAY_FRAMES経過したら攻撃終了とする（後退はしない）
                            battle_shingan_frame += 1
                            for slash_i in range(SHINGANKEN_SLASH_COUNT):
                                slash_start_frame = SHINGANKEN_WAIT_FRAMES + slash_i * SHINGANKEN_SLASH_INTERVAL_FRAMES
                                if battle_shingan_frame == slash_start_frame:
                                    battle_shingan_slash_frames[slash_i] = 0
                                    battle_shingan_slash_angles[slash_i] = random.uniform(0.0, 2 * math.pi)
                                    if voice_katana_slash:
                                        voice_katana_slash.play()
                                    if slash_i == 0 and voice_shinganken_1:
                                        # 1回目の斬撃開始＝暗転完了後の攻撃発生タイミングで、専用のかけ声を再生する
                                        voice_shinganken_1.play()

                            last_slash_start_frame = SHINGANKEN_WAIT_FRAMES + (SHINGANKEN_SLASH_COUNT - 1) * SHINGANKEN_SLASH_INTERVAL_FRAMES
                            if battle_shingan_frame == last_slash_start_frame + (BATTLE_SLASH_DRAW_FRAMES - 1):
                                # 最後の斬撃の軌跡先端が終点に到達した瞬間：ダメージを適用し、点滅演出を開始する
                                target = battle_samurai_target_enemy_index
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - SHINGANKEN_DAMAGE)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_SWORD

                                if enemy_hp[target] <= 0:
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0

                                if all(enemy_defeated):
                                    # 最後の敵を撃破：後退はせず、ダメージ演出完了直後に戦闘終了演出（リザルトへの遷移）を行う
                                    # サムライがトドメを刺したため、リザルトはサムライのバストショット・ボイス・メッセージを表示する
                                    # （心眼剣は接近しないため、サムライは現在位置のままリザルトのフラッシュアウトに引き継ぐ）
                                    shingan_sam_x, shingan_sam_bottom_y, shingan_sam_img_h = get_samurai_base_position()
                                    enter_result_state(samurai_finish=True,
                                                        samurai_override=(shingan_sam_x, shingan_sam_bottom_y, shingan_sam_img_h))

                            if (not all(enemy_defeated)
                                    and battle_shingan_frame >= last_slash_start_frame + SHINGANKEN_END_DELAY_FRAMES):
                                battle_samurai_target_enemy_index = find_alive_enemy_index(battle_samurai_target_enemy_index, 1)
                                advance_battle_turn()
                        else:
                            # サムライの番：剣で攻撃対象（battle_samurai_target_enemy_index）を攻撃する
                            # （流れはムチと同じ4ステート。攻撃ボイスは再生しない）
                            if battle_samurai_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                                battle_samurai_whip_frame += 1
                                if battle_samurai_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                    battle_samurai_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                    battle_samurai_whip_frame = 0
                                    # ★ 刀の斬撃エフェクト：接近完了直後に開始する（ダメージ表現アニメーションとは独立して進行する）
                                    battle_slash_frame = 0
                                    battle_slash_target_enemy_index = battle_samurai_target_enemy_index
                                    if voice_katana_slash:
                                        voice_katana_slash.play()
                            elif battle_samurai_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                                battle_samurai_whip_frame += 1
                                if battle_samurai_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                    battle_samurai_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                    battle_samurai_whip_frame = 0
                                    if voice_goblin_damaged:
                                        voice_goblin_damaged.play()
                            elif battle_samurai_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                                battle_samurai_whip_frame += 1
                                if battle_samurai_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                    # ダメージ演出完了の瞬間にHPを更新する（0未満にはならない。0になっていたら撃破扱い）
                                    target = battle_samurai_target_enemy_index
                                    damage = random.randint(BATTLE_SWORD_DAMAGE_MIN, BATTLE_SWORD_DAMAGE_MAX)
                                    # ★ ダメージ表現アニメーション：更新前の見た目HPを起点に、更新後の実HPへ向けたアニメを開始する
                                    old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                    enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                    enemy_damage_anim_old_hp[target] = old_display_hp
                                    enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                    enemy_damage_anim_frame[target]  = 0
                                    enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_SWORD

                                    if enemy_hp[target] <= 0:
                                        enemy_defeated[target] = True
                                        battle_annihilate_targets = [target]
                                        battle_annihilate_frame   = 0

                                    if all(enemy_defeated):
                                        # 最後の敵を撃破：後退はせず、ダメージ演出完了直後に戦闘終了演出（リザルトへの遷移）を行う
                                        # （ヒロインのムチと同様、最接近位置をそのままリザルトのフラッシュアウトに引き継ぐ）
                                        # サムライがトドメを刺したため、リザルトはサムライのバストショット・ボイス・メッセージを表示する
                                        sword_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                        sword_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                        sword_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (SAMURAI_HEIGHT_M / HEROINE_HEIGHT_M))
                                        enter_result_state(samurai_finish=True,
                                                            samurai_override=(sword_target_x, sword_target_bottom_y, sword_target_img_h))
                                    else:
                                        battle_samurai_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                        battle_samurai_whip_frame = 0
                            elif battle_samurai_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                                battle_samurai_whip_frame += 1
                                if battle_samurai_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                    battle_samurai_target_enemy_index = find_alive_enemy_index(battle_samurai_target_enemy_index, 1)
                                    advance_battle_turn()
                    elif attacker == -3:
                        # 女戦士の番：斧で攻撃対象（battle_warrior_target_enemy_index）を攻撃する
                        # （流れはヒロインのムチと同じ4ステート）
                        if battle_warrior_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            battle_warrior_whip_frame += 1
                            if battle_warrior_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_warrior_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                battle_warrior_whip_frame = 0
                        elif battle_warrior_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                            battle_warrior_whip_frame += 1
                            if battle_warrior_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                battle_warrior_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                battle_warrior_whip_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_warrior_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                            battle_warrior_whip_frame += 1
                            if battle_warrior_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                # ダメージ演出完了の瞬間にHPを更新する（0未満にはならない。0になっていたら撃破扱い）
                                target = battle_warrior_target_enemy_index
                                damage = BATTLE_AXE_DAMAGE
                                # ★ ダメージ表現アニメーション：更新前の見た目HPを起点に、更新後の実HPへ向けたアニメを開始する
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_AXE

                                if enemy_hp[target] <= 0:
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0

                                if all(enemy_defeated):
                                    # 最後の敵を撃破：後退はせず、ダメージ演出完了直後に戦闘終了演出（リザルトへの遷移）を行う
                                    # 女戦士がトドメを刺したため、リザルトは女戦士のバストショット・ボイス・メッセージを表示する
                                    axe_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                    axe_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                    axe_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (WARRIOR_HEIGHT_M / HEROINE_HEIGHT_M))
                                    enter_result_state(warrior_finish=True,
                                                        warrior_override=(axe_target_x, axe_target_bottom_y, axe_target_img_h))
                                else:
                                    battle_warrior_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                    battle_warrior_whip_frame = 0
                        elif battle_warrior_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            battle_warrior_whip_frame += 1
                            if battle_warrior_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_warrior_target_enemy_index = find_alive_enemy_index(battle_warrior_target_enemy_index, 1)
                                advance_battle_turn()
                    elif attacker == -4:
                        if battle_sister_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            battle_sister_whip_frame += 1
                            if battle_sister_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_sister_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                battle_sister_whip_frame = 0
                        elif battle_sister_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                            battle_sister_whip_frame += 1
                            if battle_sister_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                battle_sister_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                battle_sister_whip_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_sister_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                            battle_sister_whip_frame += 1
                            if battle_sister_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                target = battle_sister_target_enemy_index
                                damage = random.randint(BATTLE_WHIP_DAMAGE_MIN, BATTLE_WHIP_DAMAGE_MAX)
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_WHIP
                                if enemy_hp[target] <= 0:
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0
                                if all(enemy_defeated):
                                    sis_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                    sis_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                    sis_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE)
                                    enter_result_state(sister_finish=True,
                                                        sister_override=(sis_target_x, sis_target_bottom_y, sis_target_img_h))
                                else:
                                    battle_sister_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                    battle_sister_whip_frame = 0
                        elif battle_sister_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            battle_sister_whip_frame += 1
                            if battle_sister_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_sister_target_enemy_index = find_alive_enemy_index(battle_sister_target_enemy_index, 1)
                                advance_battle_turn()
                    elif attacker == -5:
                        if battle_kunoichi_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            battle_kunoichi_whip_frame += 1
                            if battle_kunoichi_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                battle_kunoichi_whip_frame = 0
                        elif battle_kunoichi_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                            battle_kunoichi_whip_frame += 1
                            if battle_kunoichi_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                battle_kunoichi_whip_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_kunoichi_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                            battle_kunoichi_whip_frame += 1
                            if battle_kunoichi_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                target = battle_kunoichi_target_enemy_index
                                damage = random.randint(BATTLE_WHIP_DAMAGE_MIN, BATTLE_WHIP_DAMAGE_MAX)
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_WHIP
                                if enemy_hp[target] <= 0:
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0
                                if all(enemy_defeated):
                                    kun_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                    kun_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                    kun_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE)
                                    enter_result_state(kunoichi_finish=True,
                                                        kunoichi_override=(kun_target_x, kun_target_bottom_y, kun_target_img_h))
                                else:
                                    battle_kunoichi_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                    battle_kunoichi_whip_frame = 0
                        elif battle_kunoichi_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            battle_kunoichi_whip_frame += 1
                            if battle_kunoichi_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_kunoichi_target_enemy_index = find_alive_enemy_index(battle_kunoichi_target_enemy_index, 1)
                                advance_battle_turn()
                    elif attacker == -6:
                        if battle_wizard_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            battle_wizard_whip_frame += 1
                            if battle_wizard_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_wizard_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                battle_wizard_whip_frame = 0
                        elif battle_wizard_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                            battle_wizard_whip_frame += 1
                            if battle_wizard_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                battle_wizard_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                battle_wizard_whip_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_wizard_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                            battle_wizard_whip_frame += 1
                            if battle_wizard_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                target = battle_wizard_target_enemy_index
                                damage = random.randint(BATTLE_WHIP_DAMAGE_MIN, BATTLE_WHIP_DAMAGE_MAX)
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_WHIP
                                if enemy_hp[target] <= 0:
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0
                                if all(enemy_defeated):
                                    wiz_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                    wiz_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                    wiz_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE)
                                    enter_result_state(wizard_finish=True,
                                                        wizard_override=(wiz_target_x, wiz_target_bottom_y, wiz_target_img_h))
                                else:
                                    battle_wizard_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                    battle_wizard_whip_frame = 0
                        elif battle_wizard_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            battle_wizard_whip_frame += 1
                            if battle_wizard_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_wizard_target_enemy_index = find_alive_enemy_index(battle_wizard_target_enemy_index, 1)
                                advance_battle_turn()
                    elif attacker == -7:
                        if battle_fighter_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            battle_fighter_whip_frame += 1
                            if battle_fighter_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_fighter_whip_phase = BATTLE_WHIP_PHASE_DAMAGE_WAIT
                                battle_fighter_whip_frame = 0
                        elif battle_fighter_whip_phase == BATTLE_WHIP_PHASE_DAMAGE_WAIT:
                            battle_fighter_whip_frame += 1
                            if battle_fighter_whip_frame >= BATTLE_WHIP_DAMAGE_DELAY_FRAMES:
                                battle_fighter_whip_phase = BATTLE_WHIP_PHASE_FLASH
                                battle_fighter_whip_frame = 0
                                if voice_goblin_damaged:
                                    voice_goblin_damaged.play()
                        elif battle_fighter_whip_phase == BATTLE_WHIP_PHASE_FLASH:
                            battle_fighter_whip_frame += 1
                            if battle_fighter_whip_frame >= BATTLE_WHIP_FLASH_FRAMES:
                                target = battle_fighter_target_enemy_index
                                damage = random.randint(BATTLE_WHIP_DAMAGE_MIN, BATTLE_WHIP_DAMAGE_MAX)
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_WHIP
                                if enemy_hp[target] <= 0:
                                    enemy_defeated[target] = True
                                    battle_annihilate_targets = [target]
                                    battle_annihilate_frame   = 0
                                if all(enemy_defeated):
                                    fig_target_x = int(SCREEN_W * ENEMY_X_RATIOS[target])
                                    fig_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                                    fig_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE)
                                    enter_result_state(fighter_finish=True,
                                                        fighter_override=(fig_target_x, fig_target_bottom_y, fig_target_img_h))
                                else:
                                    battle_fighter_whip_phase = BATTLE_WHIP_PHASE_RETURN
                                    battle_fighter_whip_frame = 0
                        elif battle_fighter_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            battle_fighter_whip_frame += 1
                            if battle_fighter_whip_frame >= BATTLE_WHIP_APPROACH_FRAMES:
                                battle_fighter_target_enemy_index = find_alive_enemy_index(battle_fighter_target_enemy_index, 1)
                                advance_battle_turn()
                    elif battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP:
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
                                # ★ ダメージ表現アニメーション：更新前の見た目HPを起点に、更新後の実HPへ向けたアニメを開始する
                                old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[target], enemy_damage_anim_new_hp[target], enemy_damage_anim_frame[target])
                                enemy_hp[target] = max(0, enemy_hp[target] - damage)
                                enemy_damage_anim_old_hp[target] = old_display_hp
                                enemy_damage_anim_new_hp[target] = enemy_hp[target]
                                enemy_damage_anim_frame[target]  = 0
                                enemy_damage_anim_flash_color[target] = DAMAGE_FLASH_COLOR_WHIP

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
                    elif battle_menu_selected_index == BATTLE_MENU_INDEX_FLAME:
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
                                    # ★ ダメージ表現アニメーション：更新前の見た目HPを起点に、更新後の実HPへ向けたアニメを開始する
                                    old_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[i], enemy_damage_anim_new_hp[i], enemy_damage_anim_frame[i])
                                    enemy_hp[i] = max(0, enemy_hp[i] - damage)
                                    enemy_damage_anim_old_hp[i] = old_display_hp
                                    enemy_damage_anim_new_hp[i] = enemy_hp[i]
                                    enemy_damage_anim_frame[i]  = 0
                                    enemy_damage_anim_flash_color[i] = DAMAGE_FLASH_COLOR_FLAME
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
                        # マカダンス：待機モーションのヒロインが画面下に消える → バトルウィンドウがピンクに染まりダンスを再生
                        # （仲間がいないため、演出が終わったらそのまま次の番へ進む）
                        if battle_dance_phase == BATTLE_DANCE_PHASE_SINK:
                            battle_dance_frame += 1
                            if battle_dance_frame >= BATTLE_DANCE_SINK_FRAMES:
                                battle_dance_phase = BATTLE_DANCE_PHASE_DANCE
                                battle_dance_frame = 0
                        elif battle_dance_phase == BATTLE_DANCE_PHASE_DANCE:
                            battle_dance_frame += 1
                            if battle_dance_frame >= BATTLE_DANCE_SCROLL_FRAMES:
                                pygame.mixer.music.stop()
                                # ★ マカダンスBGM代用で上書きされたため、勝利BGM代用（battle.mp3の指定秒数）の
                                # 先読みシークをやり直し、無音・一時停止の状態に戻しておく
                                # （これをしないと、リザルトでのunpause()が「停止中」の音楽に対する操作になり鳴らない）
                                pygame.mixer.music.load(BGM_BATTLE_PATH)
                                pygame.mixer.music.set_volume(0.0)
                                pygame.mixer.music.play(start=RESULT_WIN_BGM_START_SEC)
                                pygame.mixer.music.pause()
                                # ★ サムライのピンク点滅演出が終わったので、以後バトル終了まで「心眼剣」を使用可能にする
                                samurai_powered_up = True
                                advance_battle_turn()
                else:
                    # 敵の番：battle_attacking_enemy_index の敵がヒロインに接近して攻撃する（流れはムチと同じ4ステート）
                    # 敵の攻撃ボイスは未実装のため再生しない
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
                            # ダメージ演出完了の瞬間に攻撃対象（ヒロインまたはサムライ）のHPを更新する（0未満にはならない。0になっても現状は何も起きない）
                            damage = random.randint(BATTLE_ENEMY_ATTACK_DAMAGE_MIN, BATTLE_ENEMY_ATTACK_DAMAGE_MAX)
                            # ★ ダメージ表現アニメーション：更新前の見た目HPを起点に、更新後の実HPへ向けたアニメを開始する
                            if battle_enemy_attack_target == -2:
                                old_display_hp = get_damage_display_hp(samurai_damage_anim_old_hp, samurai_damage_anim_new_hp, samurai_damage_anim_frame)
                                samurai_hp = max(0, samurai_hp - damage)
                                samurai_damage_anim_old_hp = old_display_hp
                                samurai_damage_anim_new_hp = samurai_hp
                                samurai_damage_anim_frame  = 0
                                samurai_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                                if voice_samurai_damaged:
                                    voice_samurai_damaged.play()
                            elif battle_enemy_attack_target == -3:
                                old_display_hp = get_damage_display_hp(warrior_damage_anim_old_hp, warrior_damage_anim_new_hp, warrior_damage_anim_frame)
                                warrior_hp = max(0, warrior_hp - damage)
                                warrior_damage_anim_old_hp = old_display_hp
                                warrior_damage_anim_new_hp = warrior_hp
                                warrior_damage_anim_frame  = 0
                                warrior_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                                if voice_warrior_damaged:
                                    voice_warrior_damaged.play()
                            elif battle_enemy_attack_target == -4:
                                old_display_hp = get_damage_display_hp(sister_damage_anim_old_hp, sister_damage_anim_new_hp, sister_damage_anim_frame)
                                sister_hp = max(0, sister_hp - damage)
                                sister_damage_anim_old_hp = old_display_hp
                                sister_damage_anim_new_hp = sister_hp
                                sister_damage_anim_frame  = 0
                                sister_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                            elif battle_enemy_attack_target == -5:
                                old_display_hp = get_damage_display_hp(kunoichi_damage_anim_old_hp, kunoichi_damage_anim_new_hp, kunoichi_damage_anim_frame)
                                kunoichi_hp = max(0, kunoichi_hp - damage)
                                kunoichi_damage_anim_old_hp = old_display_hp
                                kunoichi_damage_anim_new_hp = kunoichi_hp
                                kunoichi_damage_anim_frame  = 0
                                kunoichi_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                            elif battle_enemy_attack_target == -6:
                                old_display_hp = get_damage_display_hp(wizard_damage_anim_old_hp, wizard_damage_anim_new_hp, wizard_damage_anim_frame)
                                wizard_hp = max(0, wizard_hp - damage)
                                wizard_damage_anim_old_hp = old_display_hp
                                wizard_damage_anim_new_hp = wizard_hp
                                wizard_damage_anim_frame  = 0
                                wizard_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                            elif battle_enemy_attack_target == -7:
                                old_display_hp = get_damage_display_hp(fighter_damage_anim_old_hp, fighter_damage_anim_new_hp, fighter_damage_anim_frame)
                                fighter_hp = max(0, fighter_hp - damage)
                                fighter_damage_anim_old_hp = old_display_hp
                                fighter_damage_anim_new_hp = fighter_hp
                                fighter_damage_anim_frame  = 0
                                fighter_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                            else:
                                old_display_hp = get_damage_display_hp(heroine_damage_anim_old_hp, heroine_damage_anim_new_hp, heroine_damage_anim_frame)
                                heroine_hp = max(0, heroine_hp - damage)
                                heroine_damage_anim_old_hp = old_display_hp
                                heroine_damage_anim_new_hp = heroine_hp
                                heroine_damage_anim_frame  = 0
                                heroine_damage_anim_flash_color = DAMAGE_FLASH_COLOR_ENEMY_ATTACK
                                if voice_heroine_damaged:
                                    voice_heroine_damaged.play()
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
                    battle_phase = BATTLE_PHASE_COMMAND_HEROINE
                    battle_exchange_frame = 0

        return

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
    # ★ bunny_front.pngをズームに合わせてスケールし、現在HPに応じてグレースケール化して表示する
    target_h = heroine_height_px()
    orig_w, orig_h = heroine_front_img_raw.get_size()
    scaled_img = pygame.transform.smoothscale(heroine_front_img_raw, (max(1, int(orig_w * target_h / orig_h)), target_h))
    display_image = apply_hp_grayscale(scaled_img, "bunny_front.png", HEROINE_HEIGHT_M, heroine_hp, HEROINE_MAX_HP)
    rect = display_image.get_rect(midbottom=(sx, sy))
    screen.blit(display_image, rect)
    if is_debug:
        pygame.draw.rect(screen, (255, 255, 255), rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
        draw_art_top_debug_line("bunny_front.png", HEROINE_HEIGHT_M, sy, display_image.get_height(), rect.left, rect.right)  # ★ [デバッグ] 実際の絵の上端

    screen.blit(font.render(f"FPS: {clock.get_fps():.1f}", True, (255, 255, 255)), (DEBUG_TEXT_MARGIN, DEBUG_TEXT_MARGIN + 0 * DEBUG_TEXT_LINE_HEIGHT))
    screen.blit(font.render(f"Player: ({player_world_x:.2f}, {player_world_y:.2f})", True, (255, 255, 255)), (DEBUG_TEXT_MARGIN, DEBUG_TEXT_MARGIN + 1 * DEBUG_TEXT_LINE_HEIGHT))
    screen.blit(font.render(f"Camera: ({camera_world_x:.2f}, {camera_world_y:.2f})", True, (255, 255, 0)), (DEBUG_TEXT_MARGIN, DEBUG_TEXT_MARGIN + 2 * DEBUG_TEXT_LINE_HEIGHT))
    screen.blit(font.render(f"Zoom: {zoom:.2f}", True, (0, 200, 255)), (DEBUG_TEXT_MARGIN, DEBUG_TEXT_MARGIN + 3 * DEBUG_TEXT_LINE_HEIGHT))

    if is_debug:
        # ★ [デバッグ] 足元コライダ表示
        collider_px = int(PLAYER_COLLIDER_RADIUS * METER_TO_PIXEL * zoom)
        cx, cy = world_to_screen(player_world_x, player_world_y)

        if is_near_mountain(player_world_x, player_world_y):
            color = (255, 255, 0)
        else:
            color = (0, 128, 255)

        pygame.draw.circle(screen, color, (cx, cy), collider_px, 2)

# ---------------------------------------------------------
# smoothscale_visible(raw_img, target_w, target_h, anchor_pos, clip_rect)
# raw_imgをtarget_w×target_hに拡大した場合の画像をmidbottom=anchor_posに配置したと仮定し、
# その仮想的な配置矩形（dest_rect）のうち clip_rect と重なる範囲だけを元画像から切り出してスケーリングする。
# 戻り値: (切り出し後にスケーリング済みのSurface（重なりが無ければNone）, 描画位置（左上座標）, dest_rect（スケール後の仮想配置矩形））
# ★ target_w×target_h全体をスケーリングしてから画面外をクリップする方式だと、
#   出力サイズが大きいほどsmoothscaleのコストが増大し（SCREEN_Wの2乗に比例）処理落ちの原因となるため、
#   表示に必要な範囲だけを先に切り出してからスケーリングすることでコストを画面サイズ程度に抑える
# ---------------------------------------------------------
def smoothscale_visible(raw_img, target_w, target_h, anchor_pos, clip_rect):
    target_w = max(1, target_w)
    target_h = max(1, target_h)
    dest_rect = pygame.Rect(0, 0, target_w, target_h)
    dest_rect.midbottom = anchor_pos

    visible_rect = dest_rect.clip(clip_rect)
    if visible_rect.width <= 0 or visible_rect.height <= 0:
        return None, None, dest_rect

    orig_w, orig_h = raw_img.get_size()
    scale_x = target_w / orig_w
    scale_y = target_h / orig_h
    src_rect = pygame.Rect(
        int((visible_rect.x - dest_rect.x) / scale_x),
        int((visible_rect.y - dest_rect.y) / scale_y),
        max(1, math.ceil(visible_rect.width / scale_x)),
        max(1, math.ceil(visible_rect.height / scale_y)),
    )
    src_rect = src_rect.clip(pygame.Rect(0, 0, orig_w, orig_h))
    if src_rect.width <= 0 or src_rect.height <= 0:
        return None, None, dest_rect

    sub = raw_img.subsurface(src_rect)
    scaled = pygame.transform.smoothscale(sub, (visible_rect.width, visible_rect.height))
    return scaled, visible_rect.topleft, dest_rect

# ---------------------------------------------------------
# blit_heroine_trail_image(raw_img, pos, alpha, clip_rect)：残像（直近フレームの位置・スケールのヒロイン画像）を半透明で描画する
# pos は (x, 足元y, 画像高さ) のタプル。alpha は不透明度（0.0～1.0）
# ---------------------------------------------------------
def blit_heroine_trail_image(raw_img, pos, alpha, clip_rect):
    x, boty, h = pos
    orig_w, orig_h = raw_img.get_size()
    w = max(1, int(orig_w * h / orig_h))
    trail_img, trail_pos, trail_rect = smoothscale_visible(raw_img, w, h, (x, boty), clip_rect)
    if trail_img is not None:
        trail_img.set_alpha(int(255 * alpha))
        screen.blit(trail_img, trail_pos)
    if is_debug:
        pygame.draw.rect(screen, (255, 255, 255), trail_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線

# ---------------------------------------------------------
# get_art_top_y(filename, char_height_m, bottom_y, img_h)：
# character_art_top_height_m に記録された「実際のキャラ絵が始まる高さ」をもとに、
# 現在の表示足元位置(bottom_y)・表示高さ(img_h)から、実際の絵の上端のy座標（緑線の位置）を返す
# （art_height_mが未登録、またはchar_height_mが0以下の場合はbottom_yを返す）
# ---------------------------------------------------------
def get_art_top_y(filename, char_height_m, bottom_y, img_h):
    art_height_m = character_art_top_height_m.get(filename)
    if art_height_m is None or char_height_m <= 0:
        return bottom_y
    return bottom_y - int(img_h * art_height_m / char_height_m)

# ---------------------------------------------------------
# draw_art_top_debug_line(filename, char_height_m, bottom_y, img_h, x_left, x_right)：
# character_art_top_height_m に記録された「実際のキャラ絵が始まる高さ」をもとに、
# 現在の表示足元位置(bottom_y)・表示高さ(img_h)に合わせて緑色の横線を描画する（is_debug用）
# ---------------------------------------------------------
def draw_art_top_debug_line(filename, char_height_m, bottom_y, img_h, x_left, x_right):
    art_height_m = character_art_top_height_m.get(filename)
    if art_height_m is None or char_height_m <= 0:
        return
    line_y = get_art_top_y(filename, char_height_m, bottom_y, img_h)
    pygame.draw.line(screen, (0, 255, 0), (x_left, line_y), (x_right, line_y), 1)

# ---------------------------------------------------------
# lerp_point(p1, p2, t)：2点間を t（0.0～1.0）で線形補間した座標を返す
# ---------------------------------------------------------
def lerp_point(p1, p2, t):
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)

# ---------------------------------------------------------
# draw_slash_triangle(p1, p2, frame)：
# 点p1（軌跡の末尾）から点p2（軌跡の先端）へ向かう方向を対称軸とした、水色の細い二等辺三角形の軌跡を描画する。
# 軌跡の先端側（seg_end）を底辺、末尾側（seg_start）を頂点とする。
# frameに応じて「描画(0～DRAW_FRAMES-1)」→「維持」→「消去」の3段階で軌跡の範囲が変化する
# ---------------------------------------------------------
def draw_slash_triangle(p1, p2, frame):
    if frame < BATTLE_SLASH_DRAW_FRAMES:
        t = (frame + 1) / BATTLE_SLASH_DRAW_FRAMES if BATTLE_SLASH_DRAW_FRAMES > 0 else 1.0
        seg_start, seg_end = p1, lerp_point(p1, p2, t)
    elif frame < BATTLE_SLASH_DRAW_FRAMES + BATTLE_SLASH_HOLD_FRAMES:
        seg_start, seg_end = p1, p2
    else:
        erase_frame = frame - BATTLE_SLASH_DRAW_FRAMES - BATTLE_SLASH_HOLD_FRAMES
        t = (erase_frame + 1) / BATTLE_SLASH_ERASE_FRAMES if BATTLE_SLASH_ERASE_FRAMES > 0 else 1.0
        seg_start, seg_end = lerp_point(p1, p2, t), p2

    # 頂点(apex)＝seg_start、底辺の中心＝seg_end とし、底辺はseg_start→seg_end方向に対して
    # 垂直になるよう配置する（この方向が二等辺三角形の対称軸になる）
    dx = seg_end[0] - seg_start[0]
    dy = seg_end[1] - seg_start[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return

    # 軌跡の方向に対して垂直な単位ベクトル（底辺の方向）
    nx, ny = -dy / length, dx / length
    half_base = (BATTLE_SLASH_BASE_WIDTH_M * ENEMY_GOBLIN_LAST_METER_TO_PIXEL) / 2.0

    points = [
        seg_start,
        (seg_end[0] + nx * half_base, seg_end[1] + ny * half_base),
        (seg_end[0] - nx * half_base, seg_end[1] - ny * half_base),
    ]

    # 基本色と点滅色（白）をBATTLE_SLASH_BLINK_PERIOD_FRAMES周期で交互に表示する
    blink_half = max(1, BATTLE_SLASH_BLINK_PERIOD_FRAMES // 2)
    color = BATTLE_SLASH_FLASH_COLOR if (frame // blink_half) % 2 != 0 else BATTLE_SLASH_COLOR

    pygame.draw.polygon(screen, color, points)

# ---------------------------------------------------------
# draw_katana_slash(rect, top_y, frame)：
# サムライの刀の斬撃エフェクト：矩形(左端=rect.left, 右端=rect.right, 下端=rect.bottom, 上端=top_y)の
# 右上（軌跡の末尾）から左下（軌跡の先端）へ向かう軌跡を draw_slash_triangle() で描画する
# ---------------------------------------------------------
def draw_katana_slash(rect, top_y, frame):
    p1 = (rect.right, top_y)       # 右上（軌跡の末尾）
    p2 = (rect.left, rect.bottom)  # 左下（軌跡の先端）
    draw_slash_triangle(p1, p2, frame)

# ---------------------------------------------------------
# draw_shingan_slash(rect, top_y, frame, angle)：
# 心眼剣の斬撃エフェクト：刀の軌跡（矩形の右上から左下）と同じ中心・長さの線分を、
# angle（ラジアン）で指定する方向へ向けて配置し、draw_slash_triangle() で描画する
# ---------------------------------------------------------
def draw_shingan_slash(rect, top_y, frame, angle):
    p1 = (rect.right, top_y)
    p2 = (rect.left, rect.bottom)
    center = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
    half_length = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / 2.0
    dx, dy = math.cos(angle), math.sin(angle)
    slash_p1 = (center[0] - dx * half_length, center[1] - dy * half_length)  # 軌跡の末尾
    slash_p2 = (center[0] + dx * half_length, center[1] + dy * half_length)  # 軌跡の先端
    draw_slash_triangle(slash_p1, slash_p2, frame)

# ---------------------------------------------------------
# get_shingan_darken_alpha(frame)：
# 心眼剣のバトルウィンドウ暗転オーバーレイのアルファ値（0～SHINGANKEN_DARKEN_MAX_ALPHA）を、
# 攻撃開始からの経過フレーム数（battle_shingan_frame）から算出する。
# 0～SHINGANKEN_DARKEN_FRAMES: 0→MAXへ暗転
# SHINGANKEN_DARKEN_FRAMES～最後の斬撃開始: MAXを維持
# 最後の斬撃開始～+SHINGANKEN_DARKEN_FRAMES: MAX→0へ暗転解除
# ---------------------------------------------------------
def get_shingan_darken_alpha(frame):
    if frame < 0:
        return 0
    if frame < SHINGANKEN_DARKEN_FRAMES:
        return int(SHINGANKEN_DARKEN_MAX_ALPHA * (frame + 1) / SHINGANKEN_DARKEN_FRAMES)

    last_slash_start_frame = SHINGANKEN_WAIT_FRAMES + (SHINGANKEN_SLASH_COUNT - 1) * SHINGANKEN_SLASH_INTERVAL_FRAMES
    if frame < last_slash_start_frame:
        return SHINGANKEN_DARKEN_MAX_ALPHA

    erase_frame = frame - last_slash_start_frame
    if erase_frame < SHINGANKEN_DARKEN_FRAMES:
        return int(SHINGANKEN_DARKEN_MAX_ALPHA * (1.0 - (erase_frame + 1) / SHINGANKEN_DARKEN_FRAMES))
    return 0

# ---------------------------------------------------------
# draw_darken_overlay(alpha, clip_rect)：
# clip_rect全体を半透明の黒で覆う（暗転）
# ---------------------------------------------------------
def draw_darken_overlay(alpha, clip_rect):
    if alpha <= 0:
        return
    alpha = min(255, alpha)
    overlay = pygame.Surface((clip_rect.width, clip_rect.height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, clip_rect.topleft)

# ---------------------------------------------------------
# get_hp_grayscale_full(img_raw, filename)：
# 画像全体をグレースケール化＋HP_GRAYSCALE_DARKNESSで暗くした画像を返す（ファイル名ごとに一度だけ計算しキャッシュする）
# apply_hp_grayscaleはHP値ごとにこの画像の一部を切り出して合成するだけでよく、
# pygame.transform.grayscale()等の重い処理をHP変化のたびに繰り返さないようにするための事前計算
# ---------------------------------------------------------
def get_hp_grayscale_full(img_raw, filename):
    cached = hp_grayscale_full_cache.get(filename)
    if cached is not None:
        return cached

    gray = pygame.transform.grayscale(img_raw)
    # HP_GRAYSCALE_DARKNESSに応じてグレースケール画像のRGBを暗くする（1=そのまま、0=真っ黒。アルファは変えない）
    darkness = max(0.0, min(1.0, HP_GRAYSCALE_DARKNESS))
    darken_amount = int(round(255 * darkness))
    darken_overlay = pygame.Surface(gray.get_size(), pygame.SRCALPHA)
    darken_overlay.fill((darken_amount, darken_amount, darken_amount, 255))
    gray.blit(darken_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    hp_grayscale_full_cache[filename] = gray
    return gray

# ---------------------------------------------------------
# apply_hp_grayscale(img_raw, filename, char_height_m, current_hp, max_hp)：
# HPの残量に応じて、画像の「実際の絵が始まる行」(character_art_top_height_mで算出済み)から
# 画像下端までの範囲を、下から (1 - 現在HP/最大HP) の割合だけグレースケール化した画像を返す
# （HP満タンなら元画像のまま、HP0なら絵の範囲全体がグレースケールになる）
# グレースケール部分の明るさはHP_GRAYSCALE_DARKNESSで調整する（1=通常のグレースケール、0=真っ黒）
# ---------------------------------------------------------
def apply_hp_grayscale(img_raw, filename, char_height_m, current_hp, max_hp):
    hp_ratio = max(0.0, min(1.0, current_hp / max_hp)) if max_hp > 0 else 1.0
    if hp_ratio >= 1.0:
        return img_raw

    cache_key = (filename, current_hp, max_hp)
    cached = hp_grayscale_cache.get(cache_key)
    if cached is not None:
        return cached

    art_height_m = character_art_top_height_m.get(filename)
    if art_height_m is None or char_height_m <= 0:
        return img_raw

    orig_w, orig_h = img_raw.get_size()
    art_top_row = max(0, min(orig_h, int(orig_h * (1 - art_height_m / char_height_m))))
    gray_row_start = int(art_top_row + (orig_h - art_top_row) * hp_ratio)
    if gray_row_start >= orig_h:
        return img_raw

    result = img_raw.copy()
    gray_rect = pygame.Rect(0, gray_row_start, orig_w, orig_h - gray_row_start)
    gray_full = get_hp_grayscale_full(img_raw, filename)
    # 通常のblitはアルファ合成されてしまうため、対象範囲を一旦透明にしてからBLEND_RGBA_MAXで上書きし、
    # グレースケール画像のRGBA値をそのまま（合成せず）コピーする
    target = result.subsurface(gray_rect)
    target.fill((0, 0, 0, 0))
    target.blit(gray_full.subsurface(gray_rect), (0, 0), special_flags=pygame.BLEND_RGBA_MAX)

    # ダメージ表現アニメーション中は中間HP値が次々キャッシュされるため、上限を超えたら古いキャッシュを破棄する
    if len(hp_grayscale_cache) >= HP_GRAYSCALE_CACHE_MAX_ENTRIES:
        hp_grayscale_cache.clear()
    hp_grayscale_cache[cache_key] = result
    return result

# ---------------------------------------------------------
# get_damage_display_hp(old_hp, new_hp, anim_frame)：
# ダメージ表現アニメーションの経過フレーム(anim_frame)に応じて、見た目に反映するHP値を返す
# ・anim_frame < DAMAGE_FLASH_FRAMES：白色点滅フェーズ中は見た目HPは更新前のまま（old_hp）
# ・それ以降 DAMAGE_TRANSITION_FRAMES の間：old_hp→new_hpへ線形に変化させる
# ・DAMAGE_ANIM_DONE_FRAME以降：見た目HP＝実HP（new_hp）
# ---------------------------------------------------------
def get_damage_display_hp(old_hp, new_hp, anim_frame):
    if anim_frame < DAMAGE_FLASH_FRAMES:
        return old_hp
    if anim_frame >= DAMAGE_ANIM_DONE_FRAME:
        return new_hp
    t = (anim_frame - DAMAGE_FLASH_FRAMES) / DAMAGE_TRANSITION_FRAMES
    t = max(0.0, min(1.0, t))
    return old_hp + (new_hp - old_hp) * t

# ---------------------------------------------------------
# apply_damage_flash(img_raw, filename, char_height_m, old_hp, new_hp, max_hp, anim_frame, flash_color)：
# ダメージ表現アニメーションの①点滅フェーズ(anim_frame < DAMAGE_FLASH_FRAMES)の間、
# 「更新前HP（old_hp）と更新後HP（new_hp）の間に相当する範囲」（＝この時点ではまだ通常表示のままの範囲）を
# BLEND_RGB_ADDでflash_colorを加算して点滅させる（攻撃の種類ごとに色を変えられる。DAMAGE_FLASH_COLOR_*参照）
# ---------------------------------------------------------
def apply_damage_flash(img_raw, filename, char_height_m, old_hp, new_hp, max_hp, anim_frame, flash_color):
    if anim_frame >= DAMAGE_FLASH_FRAMES or max_hp <= 0 or old_hp == new_hp:
        return img_raw

    blink_half = max(1, DAMAGE_FLASH_BLINK_PERIOD_FRAMES // 2)
    if (anim_frame // blink_half) % 2 != 0:
        return img_raw

    art_height_m = character_art_top_height_m.get(filename)
    if art_height_m is None or char_height_m <= 0:
        return img_raw

    orig_w, orig_h = img_raw.get_size()
    art_top_row = max(0, min(orig_h, int(orig_h * (1 - art_height_m / char_height_m))))

    old_ratio = max(0.0, min(1.0, old_hp / max_hp))
    new_ratio = max(0.0, min(1.0, new_hp / max_hp))
    row_old = int(art_top_row + (orig_h - art_top_row) * old_ratio)
    row_new = int(art_top_row + (orig_h - art_top_row) * new_ratio)
    flash_top = min(row_old, row_new)
    flash_bottom = max(row_old, row_new)
    if flash_bottom <= flash_top:
        return img_raw

    result = img_raw.copy()
    flash_rect = pygame.Rect(0, flash_top, orig_w, flash_bottom - flash_top)
    result.subsurface(flash_rect).fill(flash_color, special_flags=pygame.BLEND_RGB_ADD)
    return result

# ---------------------------------------------------------
# render_battle()
# ---------------------------------------------------------
def render_battle():
    global heroine_whip_trail_key, samurai_whip_trail_key, warrior_whip_trail_key
    global sister_whip_trail_key, kunoichi_whip_trail_key, wizard_whip_trail_key, fighter_whip_trail_key

    render_field()

    # ★ バトルメインウィンドウ開くアニメ進行度（0.0～1.0）
    progress = min(1.0, battle_anim_frame / BATTLE_MAIN_WINDOW_ANIM_FRAMES)
    current_height = int(BATTLE_MAIN_WINDOW_HEIGHT * progress)

    band_y = SCREEN_H//2 - current_height//2
    band_bottom = band_y + current_height

    # ★ バトルウィンドウの表示範囲（このウィンドウ内に収まる部分だけを各画像から切り出してスケーリングする）
    clip_rect = pygame.Rect(0, band_y, SCREEN_W, current_height)

    # ★ バトルメインウィンドウが開ききった時点での下端（ヒロインの足元位置の基準として使う。開くアニメ中も移動させない）
    band_bottom_full = SCREEN_H // 2 - BATTLE_MAIN_WINDOW_HEIGHT // 2 + BATTLE_MAIN_WINDOW_HEIGHT

    # ★ ヒロイン・サムライ・女戦士の基準位置（攻撃演出等による移動を含まない通常時の位置）を先に計算する
    # （敵の攻撃接近先の算出に、各キャラの描画より先に必要となるため）
    # ズームアウトのカメラは、battle_focus_character に応じてヒロイン・サムライ・女戦士のいずれかの足元に注視する。
    # 他のキャラは、ワールド座標系での相対位置（ヒロインを基準に、サムライは1m右・女戦士は2m右）を保ったまま表示する
    focus_t_zoom = min(1.0, heroine_zoomout_frame / BATTLE_HEROINE_ZOOMOUT_FRAMES) \
                   if BATTLE_HEROINE_ZOOMOUT_FRAMES > 0 else 1.0
    focus_t_eased = 1.0 - (1.0 - focus_t_zoom) ** 2
    focus_meter_to_pixel_start = BATTLE_HEROINE_FIRST_METER_TO_PIXEL
    focus_meter_to_pixel_end   = BATTLE_HEROINE_LAST_METER_TO_PIXEL
    focus_meter_to_pixel = focus_meter_to_pixel_start + (focus_meter_to_pixel_end - focus_meter_to_pixel_start) * focus_t_eased
    focus_bottom_y_start = band_bottom_full + int(BATTLE_HEROINE_FIRST_FOCUS_M * BATTLE_HEROINE_FIRST_METER_TO_PIXEL)
    focus_bottom_y_end   = band_bottom_full + int(BATTLE_HEROINE_LAST_FOCUS_M * BATTLE_HEROINE_LAST_METER_TO_PIXEL)
    focus_bottom_y = int(focus_bottom_y_start + (focus_bottom_y_end - focus_bottom_y_start) * focus_t_eased)

    heroine_base_img_h = max(1, int(HEROINE_HEIGHT_M * focus_meter_to_pixel))
    heroine_base_bottom_y = focus_bottom_y

    sam_meter_to_pixel = focus_meter_to_pixel
    sam_base_bottom_y = focus_bottom_y
    sam_base_img_h = max(1, int(SAMURAI_HEIGHT_M * sam_meter_to_pixel))

    warrior_base_bottom_y = focus_bottom_y
    warrior_base_img_h = max(1, int(WARRIOR_HEIGHT_M * focus_meter_to_pixel))

    sister_base_bottom_y = focus_bottom_y
    sister_base_img_h = max(1, int(SISTER_HEIGHT_M * focus_meter_to_pixel))

    kunoichi_base_bottom_y = focus_bottom_y
    kunoichi_base_img_h = max(1, int(KUNOICHI_HEIGHT_M * focus_meter_to_pixel))

    wizard_base_bottom_y = focus_bottom_y
    wizard_base_img_h = max(1, int(WIZARD_HEIGHT_M * focus_meter_to_pixel))

    fighter_base_bottom_y = focus_bottom_y
    fighter_base_img_h = max(1, int(FIGHTER_HEIGHT_M * focus_meter_to_pixel))

    heroine_base_x  = SCREEN_W // 2 + int(battle_character_world_offset_m[-1] * focus_meter_to_pixel)
    sam_base_x      = SCREEN_W // 2 + int(battle_character_world_offset_m[-2] * focus_meter_to_pixel)
    warrior_base_x  = SCREEN_W // 2 + int(battle_character_world_offset_m[-3] * focus_meter_to_pixel)
    sister_base_x   = SCREEN_W // 2 + int(battle_character_world_offset_m[-4] * focus_meter_to_pixel)
    kunoichi_base_x = SCREEN_W // 2 + int(battle_character_world_offset_m[-5] * focus_meter_to_pixel)
    wizard_base_x   = SCREEN_W // 2 + int(battle_character_world_offset_m[-6] * focus_meter_to_pixel)
    fighter_base_x  = SCREEN_W // 2 + int(battle_character_world_offset_m[-7] * focus_meter_to_pixel)

    # ★ マカダンス：ヒロインが画面下に消えた後、バトルウィンドウがピンクに染まりダンス画像を再生する
    dance_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_menu_selected_index == BATTLE_MENU_INDEX_DANCE
                    and battle_attacking_enemy_index == -1 and battle_turn_order[battle_turn_index] == -1
                    and battle_dance_phase == BATTLE_DANCE_PHASE_DANCE)

    # バトルメインウィンドウ
    overlay = pygame.Surface((SCREEN_W, current_height))
    overlay.fill(BATTLE_DANCE_WINDOW_COLOR if dance_active else BATTLE_WINDOW_COLOR)
    screen.blit(overlay, (0, band_y))

    # ★ マカダンス：ピンクのウィンドウの上（敵より奥）にセクシーダンス画像を番号順・ループ再生する
    # 画像内の彼女の体の幅（画像幅 × BATTLE_DANCE_BODY_WIDTH_RATIO）がバトルウィンドウ幅に一致するよう等方スケーリングし、
    # 下端がウィンドウ下端に一致する位置から開始して、
    # BATTLE_DANCE_SCROLL_FRAMES かけて「下端から画像高さの BATTLE_DANCE_ANCHOR_RATIO 倍」の位置がウィンドウ上端に一致するまで移動する
    if dance_active and dance_images_raw:
        dance_img_index = int(battle_dance_frame // BATTLE_DANCE_IMAGE_INTERVAL_FRAMES) % len(dance_images_raw)
        dance_raw = dance_images_raw[dance_img_index]
        dance_orig_w, dance_orig_h = dance_raw.get_size()
        dance_img_w = max(1, int(SCREEN_W / BATTLE_DANCE_BODY_WIDTH_RATIO))
        dance_img_h = max(1, int(dance_orig_h * dance_img_w / dance_orig_w))

        scroll_t = (battle_dance_frame / BATTLE_DANCE_SCROLL_FRAMES) if BATTLE_DANCE_SCROLL_FRAMES > 0 else 1.0
        scroll_t = max(0.0, min(1.0, scroll_t))
        start_bottom_y = band_bottom + int(dance_img_h * BATTLE_DANCE_START_RATIO)
        end_bottom_y   = band_y + int(dance_img_h * BATTLE_DANCE_ANCHOR_RATIO)
        dance_bottom_y = int(start_bottom_y + (end_bottom_y - start_bottom_y) * scroll_t)

        dance_img_rect = pygame.Rect(0, 0, dance_img_w, dance_img_h)
        dance_img_rect.midbottom = (SCREEN_W // 2, dance_bottom_y)

        # ★ 巨大なdance_img_w×dance_img_hサイズへの全体スケーリングは行わず、
        #   実際にウィンドウ内に表示される範囲だけを元画像から切り出してスケーリングする
        #   （全体スケーリングだと出力ピクセル数がSCREEN_Wの2乗に比例して増加し、メモリ・速度の両面で問題になるため）
        visible_rect = dance_img_rect.clip(clip_rect)
        if visible_rect.width > 0 and visible_rect.height > 0:
            scale = dance_img_w / dance_orig_w
            src_rect = pygame.Rect(
                int((visible_rect.x - dance_img_rect.x) / scale),
                int((visible_rect.y - dance_img_rect.y) / scale),
                max(1, math.ceil(visible_rect.width / scale)),
                max(1, math.ceil(visible_rect.height / scale)),
            )
            src_rect = src_rect.clip(pygame.Rect(0, 0, dance_orig_w, dance_orig_h))
            if src_rect.width > 0 and src_rect.height > 0:
                dance_sub = dance_raw.subsurface(src_rect)
                dance_img = pygame.transform.smoothscale(dance_sub, (visible_rect.width, visible_rect.height))
                screen.blit(dance_img, visible_rect.topleft)
        if is_debug:
            screen.set_clip(clip_rect)
            pygame.draw.rect(screen, (255, 255, 255), dance_img_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
            screen.set_clip(None)

    # 心眼剣の暗転オーバーレイの上からサムライだけを常時再描画するための画像・位置（描画されていない場合はNone）
    shingan_samurai_img = None
    shingan_samurai_pos = None

    # ★ 敵（goblin）の描画：黒シルエット → 通常表示への解除（ヒロインの奥＝先に描画）
    if enemy_img_raw:
        enemy_orig_w, enemy_orig_h = enemy_img_raw.get_size()

        # ズームアウト進行度（0.0 → 1.0）：ヒロインと同じタイミングで指定スケールへ収束
        enemy_t_zoom = min(1.0, heroine_zoomout_frame / BATTLE_HEROINE_ZOOMOUT_FRAMES) \
                       if BATTLE_HEROINE_ZOOMOUT_FRAMES > 0 else 1.0
        enemy_t_eased = 1.0 - (1.0 - enemy_t_zoom) ** 2

        enemy_start_img_h = int(ENEMY_GOBLIN_HEIGHT_M * ENEMY_GOBLIN_FIRST_METER_TO_PIXEL)
        enemy_end_img_h   = int(ENEMY_GOBLIN_HEIGHT_M * ENEMY_GOBLIN_LAST_METER_TO_PIXEL)
        enemy_img_h = max(1, int(enemy_start_img_h + (enemy_end_img_h - enemy_start_img_h) * enemy_t_eased))

        enemy_img_w = max(1, int(enemy_orig_w * enemy_img_h / enemy_orig_h))

        # 黒シルエット → 通常表示：ズームアウト完了直後から数フレームかけて解除
        reveal_t = min(1.0, enemy_silhouette_frame / ENEMY_SILHOUETTE_RELEASE_FRAMES) \
                   if ENEMY_SILHOUETTE_RELEASE_FRAMES > 0 else 1.0

        # 足元位置は登場時から変えない（ENEMY_GROUND_Y_FROM_BOTTOM_RATIO基準で固定）
        enemy_bottom_y = SCREEN_H - int(SCREEN_H * ENEMY_GROUND_Y_FROM_BOTTOM_RATIO)

        # ★ 敵の攻撃演出（ヒロインに接近 → 最接近で停止 → 元の位置へ後退）の進行度
        enemy_attack_active = (battle_phase == BATTLE_PHASE_EXCHANGE
                               and battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME, BATTLE_MENU_INDEX_DANCE)
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
        # 心眼剣の暗転オーバーレイの上から対象敵だけを再描画するための画像・位置（対象がいない場合はNone）
        shingan_target_enemy_img = None
        shingan_target_enemy_pos = None
        # 心眼剣の斬撃エフェクトを暗転オーバーレイより手前（あと）で描画するための、対象敵の絵の上端Y座標
        shingan_target_top_y = None
        screen.set_clip(clip_rect)
        for i, x_ratio in enumerate(ENEMY_X_RATIOS):
            enemy_x = int(SCREEN_W * x_ratio)
            enemy_img_bottom_y = enemy_bottom_y
            is_attacking = enemy_attack_active and i == battle_attacking_enemy_index
            final_img_w, final_img_h = enemy_img_w, enemy_img_h

            if is_attacking:
                # ★ 敵の攻撃：攻撃対象（ヒロインまたはサムライ）に接近 → 指定スケール・位置で最接近 → 元の位置へ後退
                # 接近・後退とも、目的地に近づくほど減速する ease-out 補間（ムチ演出と同じ手法）を用いる
                # （攻撃中は待機モーションを適用しない＝スケール変化と競合させないため）
                if battle_enemy_attack_target == -2:
                    # サムライへの攻撃：サムライの基準位置に向けて接近する
                    attack_target_x = sam_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE * (SAMURAI_HEIGHT_M / HEROINE_HEIGHT_M))
                elif battle_enemy_attack_target == -3:
                    # 女戦士への攻撃：女戦士の基準位置に向けて接近する
                    attack_target_x = warrior_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE * (WARRIOR_HEIGHT_M / HEROINE_HEIGHT_M))
                elif battle_enemy_attack_target == -4:
                    attack_target_x = sister_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE * (SISTER_HEIGHT_M / HEROINE_HEIGHT_M))
                elif battle_enemy_attack_target == -5:
                    attack_target_x = kunoichi_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE * (KUNOICHI_HEIGHT_M / HEROINE_HEIGHT_M))
                elif battle_enemy_attack_target == -6:
                    attack_target_x = wizard_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE * (WIZARD_HEIGHT_M / HEROINE_HEIGHT_M))
                elif battle_enemy_attack_target == -7:
                    attack_target_x = fighter_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE * (FIGHTER_HEIGHT_M / HEROINE_HEIGHT_M))
                else:
                    # ヒロインへの攻撃：ヒロインの基準位置に向けて接近する
                    attack_target_x = heroine_base_x
                    attack_target_bottom_y = band_bottom - int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_GROUND_Y_OFFSET_RATIO)
                    attack_target_img_h = int(SCREEN_H * BATTLE_ENEMY_ATTACK_TARGET_SCALE)

                enemy_x = int(enemy_x + (attack_target_x - enemy_x) * enemy_attack_t)
                enemy_img_bottom_y = int(enemy_bottom_y + (attack_target_bottom_y - enemy_bottom_y) * enemy_attack_t)
                target_img_h = max(1, int(enemy_img_h + (attack_target_img_h - enemy_img_h) * enemy_attack_t))
                target_img_w = max(1, int(enemy_orig_w * target_img_h / enemy_orig_h))
                final_img_w, final_img_h = target_img_w, target_img_h
            elif heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
                # 待機モーション：縦横逆位相スクワッシュ（ズームアウト完了後・攻撃中以外のみ適用）
                # 個体ごとに位相をランダムにずらし、3体が同期して動かないようにする（周期はENEMY_IDLE_PERIOD_FRAMESで共通）
                phase = enemy_idle_phase_offsets[i] if i < len(enemy_idle_phase_offsets) else 0
                enemy_idle_t = math.sin((enemy_idle_frame + phase) / ENEMY_IDLE_PERIOD_FRAMES * 2 * math.pi)
                enemy_sx = 1.0 + ENEMY_IDLE_SCALE_DELTA * enemy_idle_t
                enemy_sy = 1.0 - ENEMY_IDLE_SCALE_DELTA * enemy_idle_t
                final_img_w = max(1, int(enemy_img_w * enemy_sx))
                final_img_h = max(1, int(enemy_img_h * enemy_sy))
                # スケーリング中心 = 敵の足元：enemy_bottom_y はそのまま維持

            # ★ 表示に必要な範囲だけを元画像から切り出してスケーリングする（マカダンスと同じ対策）
            # ★ 現在HPに応じて、画像下部（絵の範囲のうち減った体力分）をグレースケール化する
            # ★ ダメージ表現アニメーション：表示HPは実HPに即時追従せず、old_hp→new_hpへ数フレームかけて変化させる
            enemy_display_hp = get_damage_display_hp(enemy_damage_anim_old_hp[i], enemy_damage_anim_new_hp[i], enemy_damage_anim_frame[i])
            enemy_display_img_raw = apply_hp_grayscale(enemy_img_raw, "goblin_idle.png", ENEMY_GOBLIN_HEIGHT_M, int(round(enemy_display_hp)), GOBLIN_MAX_HP)
            enemy_display_img_raw = apply_damage_flash(enemy_display_img_raw, "goblin_idle.png", ENEMY_GOBLIN_HEIGHT_M, enemy_damage_anim_old_hp[i], enemy_damage_anim_new_hp[i], GOBLIN_MAX_HP, enemy_damage_anim_frame[i], enemy_damage_anim_flash_color[i])
            enemy_img, enemy_pos, enemy_rect = smoothscale_visible(enemy_display_img_raw, final_img_w, final_img_h, (enemy_x, enemy_img_bottom_y), clip_rect)

            if i == battle_shingan_target_enemy_index:
                shingan_target_enemy_img = enemy_img
                shingan_target_enemy_pos = enemy_pos

            if enemy_img is not None:
                # 黒シルエット → 通常表示：ズームアウト完了直後から数フレームかけて解除
                if reveal_t < 1.0:
                    gray = int(255 * reveal_t)
                    tint = pygame.Surface(enemy_img.get_size(), pygame.SRCALPHA)
                    tint.fill((gray, gray, gray, 255))
                    enemy_img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

                # ★ 撃破演出：殲滅対象の敵は数フレームかけてアルファ値を下げ、完全に消滅させる（消滅後は描画しない）
                if i in battle_annihilate_targets:
                    annihilate_t = min(1.0, battle_annihilate_frame / BATTLE_ANNIHILATE_FRAMES) \
                                   if BATTLE_ANNIHILATE_FRAMES > 0 else 1.0
                    alpha = int(255 * (1.0 - annihilate_t))
                    if alpha > 0:
                        enemy_img.set_alpha(alpha)
                        screen.blit(enemy_img, enemy_pos)
                        if is_debug:
                            pygame.draw.rect(screen, (255, 255, 255), enemy_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
                            draw_art_top_debug_line("goblin_idle.png", ENEMY_GOBLIN_HEIGHT_M, enemy_img_bottom_y, final_img_h, enemy_rect.left, enemy_rect.right)  # ★ [デバッグ] 実際の絵の上端
                elif not enemy_defeated[i]:
                    screen.blit(enemy_img, enemy_pos)
                    if is_debug:
                        pygame.draw.rect(screen, (255, 255, 255), enemy_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
                        draw_art_top_debug_line("goblin_idle.png", ENEMY_GOBLIN_HEIGHT_M, enemy_img_bottom_y, final_img_h, enemy_rect.left, enemy_rect.right)  # ★ [デバッグ] 実際の絵の上端

            # [デバッグ表示] 敵のHPを「現在HP/最大HP」の文字列で頭上に表示する（生存中のみ）
            if not enemy_defeated[i]:
                enemy_hp_text = font.render(f"{enemy_hp[i]}/{GOBLIN_MAX_HP}", True, (255, 255, 255))
                enemy_hp_rect = enemy_hp_text.get_rect(midbottom=(enemy_rect.centerx, enemy_rect.top - 4))
                screen.blit(enemy_hp_text, enemy_hp_rect)

            # ★ サムライの刀の斬撃エフェクト：接近完了直後から始まり、ダメージ表現アニメーションとは独立して進行する
            # （敵画像の下端・右端・左端と、緑線表示位置（実際の絵の上端）を結んだ矩形の右上から左下へ軌跡を描画する）
            if i == battle_slash_target_enemy_index and battle_slash_frame < BATTLE_SLASH_TOTAL_FRAMES:
                slash_top_y = get_art_top_y("goblin_idle.png", ENEMY_GOBLIN_HEIGHT_M, enemy_img_bottom_y, final_img_h)
                draw_katana_slash(enemy_rect, slash_top_y, battle_slash_frame)

            # ★ 心眼剣の斬撃エフェクト：暗転オーバーレイより手前に描画する必要があるため、ここでは
            # 対象敵の絵の上端Y座標だけを記憶しておき、実際の描画は暗転オーバーレイの描画後に行う
            if i == battle_shingan_target_enemy_index:
                for slash_i in range(SHINGANKEN_SLASH_COUNT):
                    if battle_shingan_slash_frames[slash_i] < BATTLE_SLASH_TOTAL_FRAMES:
                        shingan_target_top_y = get_art_top_y("goblin_idle.png", ENEMY_GOBLIN_HEIGHT_M, enemy_img_bottom_y, final_img_h)
                        break

            enemy_rects.append(enemy_rect)

        # ★ 攻撃対象選択カーソル（対象の敵の頭上に点滅表示する下向き三角カーソル）
        # ヒロインのムチ選択中：左右キーで選んだ対象1体のみ／炎選択中：全体攻撃のため生存中の敵全体に表示する
        # サムライの剣選択中：左右キーで選んだ対象1体のみ
        # HPデバッグ表示と被らないよう、頭上のクリアランスにテキスト分の高さも加味して上方へ表示する
        cursor_target_indices = []
        if heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
            if battle_phase == BATTLE_PHASE_COMMAND_HEROINE and battle_menu_selected_index in (BATTLE_MENU_INDEX_WHIP, BATTLE_MENU_INDEX_FLAME):
                if battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP:
                    cursor_target_indices = [battle_target_enemy_index] if 0 <= battle_target_enemy_index < len(enemy_rects) else []
                else:
                    cursor_target_indices = [i for i in range(len(enemy_rects)) if not enemy_defeated[i]]
            elif battle_phase == BATTLE_PHASE_COMMAND_SAMURAI and battle_samurai_menu_selected_index == SAMURAI_MENU_INDEX_SWORD:
                cursor_target_indices = [battle_samurai_target_enemy_index] if 0 <= battle_samurai_target_enemy_index < len(enemy_rects) else []

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

    # ★ ヒロイン後ろ姿の描画（マカダンスのダンス中は画面下に消えているため描画しないが、
    #    サムライはこのブロック内で描画されるため、ダンス中もブロック自体は実行する）
    if battle_back_img_raw:
        orig_w, orig_h = battle_back_img_raw.get_size()

        # 画像高さ・足元位置：上で計算済みのヒロインの基準位置をそのまま使う
        img_h = heroine_base_img_h
        bottom_y = heroine_base_bottom_y

        heroine_x = heroine_base_x

        # ★ マカダンス：待機モーションのヒロインがバトルウィンドウ下端の外側まで沈み、画面下に消える
        dance_sinking = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_menu_selected_index == BATTLE_MENU_INDEX_DANCE
                         and battle_attacking_enemy_index == -1 and battle_turn_order[battle_turn_index] == -1
                         and battle_dance_phase == BATTLE_DANCE_PHASE_SINK)
        if dance_sinking:
            sink_t = (battle_dance_frame / BATTLE_DANCE_SINK_FRAMES) if BATTLE_DANCE_SINK_FRAMES > 0 else 1.0
            sink_t = max(0.0, min(1.0, sink_t))
            sink_target_bottom_y = band_bottom + img_h
            bottom_y = int(bottom_y + (sink_target_bottom_y - bottom_y) * sink_t)

        # ★ ムチ（近接攻撃）：敵に接近 → 最接近で停止 → 元の位置へ後退
        # 接近・後退とも、進行方向の目的地に近づくほど減速する ease-out 補間（行きと帰りで共通の式 = ヒロインのズームアウト等と同じ手法）を用いる
        whip_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_menu_selected_index == BATTLE_MENU_INDEX_WHIP
                       and battle_attacking_enemy_index == -1 and battle_turn_order[battle_turn_index] == -1)
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

            heroine_x = int(heroine_x + (whip_target_x - heroine_x) * whip_t)
            bottom_y  = int(bottom_y + (whip_target_bottom_y - bottom_y) * whip_t)
            img_h     = max(1, int(img_h + (whip_target_img_h - img_h) * whip_t))

        img_w = max(1, int(orig_w * img_h / orig_h))

        # ④ 待機モーション：縦横逆位相スクワッシュ（ズームアウト完了後・ムチ演出中以外で適用、エンカウント毎に位相をランダムにずらす）
        # （サムライ等の仲間キャラにも同じスケールを適用するため、idle_sx/idle_syは関係なくここで算出する）
        idle_active = heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES and not whip_active
        idle_t  = math.sin((heroine_idle_frame + heroine_idle_phase_offset) / BATTLE_HEROINE_IDLE_PERIOD_FRAMES * 2 * math.pi)
        idle_sx = 1.0 + BATTLE_HEROINE_IDLE_SCALE_DELTA * idle_t   # 横：+側で膨らむ
        idle_sy = 1.0 - BATTLE_HEROINE_IDLE_SCALE_DELTA * idle_t   # 縦：横と逆位相
        final_img_w, final_img_h = img_w, img_h
        if idle_active:
            final_img_w = max(1, int(img_w * idle_sx))
            final_img_h = max(1, int(img_h * idle_sy))
            # スケーリング中心 = キャラ下端：bottom_y はそのまま維持

        # ★ 表示に必要な範囲だけを元画像から切り出してスケーリングする（マカダンスと同じ対策）
        # ★ 現在HPに応じて、画像下部（絵の範囲のうち減った体力分）をグレースケール化する
        # ★ ダメージ表現アニメーション：表示HPは実HPに即時追従せず、old_hp→new_hpへ数フレームかけて変化させる
        heroine_display_hp = get_damage_display_hp(heroine_damage_anim_old_hp, heroine_damage_anim_new_hp, heroine_damage_anim_frame)
        heroine_display_img_raw = apply_hp_grayscale(battle_back_img_raw, "bunny_back.png", HEROINE_HEIGHT_M, int(round(heroine_display_hp)), HEROINE_MAX_HP)
        heroine_display_img_raw = apply_damage_flash(heroine_display_img_raw, "bunny_back.png", HEROINE_HEIGHT_M, heroine_damage_anim_old_hp, heroine_damage_anim_new_hp, HEROINE_MAX_HP, heroine_damage_anim_frame, heroine_damage_anim_flash_color)
        img, img_pos, img_rect = smoothscale_visible(heroine_display_img_raw, final_img_w, final_img_h, (heroine_x, bottom_y), clip_rect)

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

        # ★ ヒロインの描画本体（サムライとの前後関係を切り替えられるよう、関数化して呼び出しタイミングを後で決める）
        def draw_heroine_sprite():
            screen.set_clip(clip_rect)
            if whip_active and battle_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                # 戻るとき：B → A → 現在画像 の順で重ねる
                if trail_b is not None:
                    blit_heroine_trail_image(battle_back_img_raw, trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                if trail_a is not None:
                    blit_heroine_trail_image(battle_back_img_raw, trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                if img is not None:
                    screen.blit(img, img_pos)
            else:
                # 近づくとき（および通常時）：現在画像 → A → B の順で重ねる
                if img is not None:
                    screen.blit(img, img_pos)
                if trail_a is not None:
                    blit_heroine_trail_image(battle_back_img_raw, trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                if trail_b is not None:
                    blit_heroine_trail_image(battle_back_img_raw, trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
            if is_debug:
                pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
                draw_art_top_debug_line("bunny_back.png", HEROINE_HEIGHT_M, bottom_y, final_img_h, img_rect.left, img_rect.right)  # ★ [デバッグ] 実際の絵の上端
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

        # ★ サムライ（仲間キャラ）の後ろ姿：ヒロインの1m右を基準位置とし、剣（近接攻撃）の番には敵に接近・後退する
        sam_back_img_raw = samurai_back_img_raw
        sam_back_art_key = "samurai_back.png"
        if sam_back_img_raw:
            sam_orig_w, sam_orig_h = sam_back_img_raw.get_size()

            # ★ 剣（近接攻撃）：敵に接近 → 最接近で停止 → 元の位置へ後退（流れはヒロインのムチと同じ）
            samurai_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_attacking_enemy_index == -1
                              and battle_turn_order[battle_turn_index] == -2)
            # 剣（近接攻撃）：心眼剣選択時は接近せず、その場にとどまる
            sword_active = samurai_active and battle_samurai_menu_selected_index == SAMURAI_MENU_INDEX_SWORD
            if sword_active:
                if battle_samurai_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                    raw_t = (battle_samurai_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                    sword_t = 1.0 - (1.0 - raw_t) ** 2          # 敵に近づくほど減速
                elif battle_samurai_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                    sword_t = 1.0
                else:  # BATTLE_WHIP_PHASE_RETURN
                    raw_t = (battle_samurai_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                    sword_t = (1.0 - raw_t) ** 2                # 元の位置に近づくほど減速
                sword_t = max(0.0, min(1.0, sword_t))

                sword_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_samurai_target_enemy_index])
                sword_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                sword_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (SAMURAI_HEIGHT_M / HEROINE_HEIGHT_M))

                sam_x = int(sam_base_x + (sword_target_x - sam_base_x) * sword_t)
                sam_bottom_y = int(sam_base_bottom_y + (sword_target_bottom_y - sam_base_bottom_y) * sword_t)
                sam_img_h = max(1, int(sam_base_img_h + (sword_target_img_h - sam_base_img_h) * sword_t))
            else:
                sam_x = sam_base_x
                sam_bottom_y = sam_base_bottom_y
                sam_img_h = sam_base_img_h

            sam_img_w = max(1, int(sam_orig_w * sam_img_h / sam_orig_h))

            # ④ 待機モーション：ヒロインと同じ縦横逆位相スクワッシュ（剣攻撃中は適用しない）
            sam_final_w, sam_final_h = sam_img_w, sam_img_h
            if idle_active and not sword_active:
                sam_final_w = max(1, int(sam_img_w * idle_sx))
                sam_final_h = max(1, int(sam_img_h * idle_sy))

            # ★ 表示に必要な範囲だけを元画像から切り出してスケーリングする（マカダンスと同じ対策）
            # ★ 現在HPに応じて、画像下部（絵の範囲のうち減った体力分）をグレースケール化する
            # ★ ダメージ表現アニメーション：表示HPは実HPに即時追従せず、old_hp→new_hpへ数フレームかけて変化させる
            samurai_display_hp = get_damage_display_hp(samurai_damage_anim_old_hp, samurai_damage_anim_new_hp, samurai_damage_anim_frame)
            samurai_display_img_raw = apply_hp_grayscale(sam_back_img_raw, sam_back_art_key, SAMURAI_HEIGHT_M, int(round(samurai_display_hp)), SAMURAI_MAX_HP)
            samurai_display_img_raw = apply_damage_flash(samurai_display_img_raw, sam_back_art_key, SAMURAI_HEIGHT_M, samurai_damage_anim_old_hp, samurai_damage_anim_new_hp, SAMURAI_MAX_HP, samurai_damage_anim_frame, samurai_damage_anim_flash_color)
            sam_img, sam_img_pos, sam_img_rect = smoothscale_visible(samurai_display_img_raw, sam_final_w, sam_final_h, (sam_x, sam_bottom_y), clip_rect)
            shingan_samurai_img = sam_img
            shingan_samurai_pos = sam_img_pos

            # ★ マカダンス中：男性の仲間（サムライ）全体へのバフ演出として、サムライはヒロインのように消さず、
            # ピンク色（ダンス中のウィンドウ色と同じ色）に点滅させる
            if dance_active and sam_img is not None:
                blink_half = max(1, BATTLE_WHIP_FLASH_BLINK_PERIOD_FRAMES // 2)
                if (battle_dance_frame // blink_half) % 2 == 0:
                    sam_img.fill(BATTLE_DANCE_SAMURAI_FLASH_COLOR, special_flags=pygame.BLEND_RGB_ADD)

            # ★ 残像（接近・後退中のみ）：ヒロインのムチと同じ仕組みを再利用する
            sword_moving = sword_active and battle_samurai_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
            sam_current_pos = (sam_x, sam_bottom_y, sam_img_h)
            sam_trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

            def find_sam_trail_pos(offset):
                if offset <= 0 or len(samurai_whip_trail) < offset:
                    return None
                px, py, _ = samurai_whip_trail[-offset]
                min_offset_sq = BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2
                if (px - sam_x) ** 2 + (py - sam_bottom_y) ** 2 < min_offset_sq:
                    return None
                return samurai_whip_trail[-offset]

            sam_trail_a = None
            sam_trail_b = None
            if sword_moving:
                sam_trail_a = find_sam_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1)
                sam_trail_b = find_sam_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2)

            # ★ サムライの描画本体（ヒロインとの前後関係を切り替えられるよう、関数化して呼び出しタイミングを後で決める）
            def draw_samurai_sprite():
                screen.set_clip(clip_rect)
                if sword_active and battle_samurai_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                    # 戻るとき：B → A → 現在画像 の順で重ねる
                    if sam_trail_b is not None:
                        blit_heroine_trail_image(sam_back_img_raw, sam_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                    if sam_trail_a is not None:
                        blit_heroine_trail_image(sam_back_img_raw, sam_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                    if sam_img is not None:
                        screen.blit(sam_img, sam_img_pos)
                else:
                    # 近づくとき（および通常時）：現在画像 → A → B の順で重ねる
                    if sam_img is not None:
                        screen.blit(sam_img, sam_img_pos)
                    if sam_trail_a is not None:
                        blit_heroine_trail_image(sam_back_img_raw, sam_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                    if sam_trail_b is not None:
                        blit_heroine_trail_image(sam_back_img_raw, sam_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                if is_debug:
                    pygame.draw.rect(screen, (255, 255, 255), sam_img_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
                    draw_art_top_debug_line(sam_back_art_key, SAMURAI_HEIGHT_M, sam_bottom_y, sam_final_h, sam_img_rect.left, sam_img_rect.right)  # ★ [デバッグ] 実際の絵の上端
                screen.set_clip(None)

                # [デバッグ表示] サムライのHPを「現在HP/最大HP」の文字列で頭上に表示する
                samurai_hp_text = font.render(f"{samurai_hp}/{SAMURAI_MAX_HP}", True, (255, 255, 255))
                samurai_hp_rect = samurai_hp_text.get_rect(midbottom=(sam_img_rect.centerx, sam_img_rect.top - 4))
                screen.blit(samurai_hp_text, samurai_hp_rect)

            # 残像履歴を更新する（実際にフレームが進んだときのみ記録し、ポーズ中の再描画で重複登録しないようにする）
            if sword_moving:
                sam_trail_key = (battle_samurai_whip_phase, battle_samurai_whip_frame)
                if samurai_whip_trail_key != sam_trail_key:
                    samurai_whip_trail_key = sam_trail_key
                    samurai_whip_trail.append(sam_current_pos)
                    if len(samurai_whip_trail) > sam_trail_history_size:
                        samurai_whip_trail.pop(0)
            else:
                samurai_whip_trail.clear()
                samurai_whip_trail_key = None

            # ★ 女戦士（仲間キャラ）の後ろ姿：ヒロインの2m右を基準位置とし、斧（近接攻撃）の番には敵に接近・後退する
            if warrior_back_img_raw:
                war_orig_w, war_orig_h = warrior_back_img_raw.get_size()

                # ★ 斧（近接攻撃）：敵に接近 → 最接近で停止 → 元の位置へ後退（流れはヒロインのムチと同じ）
                warrior_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_attacking_enemy_index == -1
                                  and battle_turn_order[battle_turn_index] == -3)
                # 女戦士の行動は斧のみのため、剣のsword_activeのような行動選択判定は不要：常に接近・後退する
                axe_active = warrior_active
                if axe_active:
                    if battle_warrior_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                        raw_t = (battle_warrior_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                        axe_t = 1.0 - (1.0 - raw_t) ** 2          # 敵に近づくほど減速
                    elif battle_warrior_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                        axe_t = 1.0
                    else:  # BATTLE_WHIP_PHASE_RETURN
                        raw_t = (battle_warrior_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                        axe_t = (1.0 - raw_t) ** 2                # 元の位置に近づくほど減速
                    axe_t = max(0.0, min(1.0, axe_t))

                    axe_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_warrior_target_enemy_index])
                    axe_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                    axe_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (WARRIOR_HEIGHT_M / HEROINE_HEIGHT_M))

                    warrior_x = int(warrior_base_x + (axe_target_x - warrior_base_x) * axe_t)
                    warrior_bottom_y = int(warrior_base_bottom_y + (axe_target_bottom_y - warrior_base_bottom_y) * axe_t)
                    warrior_img_h = max(1, int(warrior_base_img_h + (axe_target_img_h - warrior_base_img_h) * axe_t))
                else:
                    warrior_x = warrior_base_x
                    warrior_bottom_y = warrior_base_bottom_y
                    warrior_img_h = warrior_base_img_h

                warrior_img_w = max(1, int(war_orig_w * warrior_img_h / war_orig_h))

                # ④ 待機モーション：ヒロインと同じ縦横逆位相スクワッシュ（斧攻撃中は適用しない）
                warrior_final_w, warrior_final_h = warrior_img_w, warrior_img_h
                if idle_active and not axe_active:
                    warrior_final_w = max(1, int(warrior_img_w * idle_sx))
                    warrior_final_h = max(1, int(warrior_img_h * idle_sy))

                # ★ 表示に必要な範囲だけを元画像から切り出してスケーリングする（マカダンスと同じ対策）
                # ★ 現在HPに応じて、画像下部（絵の範囲のうち減った体力分）をグレースケール化する
                # ★ ダメージ表現アニメーション：表示HPは実HPに即時追従せず、old_hp→new_hpへ数フレームかけて変化させる
                warrior_display_hp = get_damage_display_hp(warrior_damage_anim_old_hp, warrior_damage_anim_new_hp, warrior_damage_anim_frame)
                warrior_display_img_raw = apply_hp_grayscale(warrior_back_img_raw, "warrior_back.png", WARRIOR_HEIGHT_M, int(round(warrior_display_hp)), WARRIOR_MAX_HP)
                warrior_display_img_raw = apply_damage_flash(warrior_display_img_raw, "warrior_back.png", WARRIOR_HEIGHT_M, warrior_damage_anim_old_hp, warrior_damage_anim_new_hp, WARRIOR_MAX_HP, warrior_damage_anim_frame, warrior_damage_anim_flash_color)
                warrior_img, warrior_img_pos, warrior_img_rect = smoothscale_visible(warrior_display_img_raw, warrior_final_w, warrior_final_h, (warrior_x, warrior_bottom_y), clip_rect)

                # ★ 残像（接近・後退中のみ）：ヒロインのムチと同じ仕組みを再利用する
                axe_moving = axe_active and battle_warrior_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
                warrior_current_pos = (warrior_x, warrior_bottom_y, warrior_img_h)
                warrior_trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

                def find_warrior_trail_pos(offset):
                    if offset <= 0 or len(warrior_whip_trail) < offset:
                        return None
                    px, py, _ = warrior_whip_trail[-offset]
                    min_offset_sq = BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2
                    if (px - warrior_x) ** 2 + (py - warrior_bottom_y) ** 2 < min_offset_sq:
                        return None
                    return warrior_whip_trail[-offset]

                warrior_trail_a = None
                warrior_trail_b = None
                if axe_moving:
                    warrior_trail_a = find_warrior_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1)
                    warrior_trail_b = find_warrior_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2)

                # ★ 女戦士の描画本体（他キャラとの前後関係を切り替えられるよう、関数化して呼び出しタイミングを後で決める）
                def draw_warrior_sprite():
                    screen.set_clip(clip_rect)
                    if axe_active and battle_warrior_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                        # 戻るとき：B → A → 現在画像 の順で重ねる
                        if warrior_trail_b is not None:
                            blit_heroine_trail_image(warrior_back_img_raw, warrior_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                        if warrior_trail_a is not None:
                            blit_heroine_trail_image(warrior_back_img_raw, warrior_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                        if warrior_img is not None:
                            screen.blit(warrior_img, warrior_img_pos)
                    else:
                        # 近づくとき（および通常時）：現在画像 → A → B の順で重ねる
                        if warrior_img is not None:
                            screen.blit(warrior_img, warrior_img_pos)
                        if warrior_trail_a is not None:
                            blit_heroine_trail_image(warrior_back_img_raw, warrior_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                        if warrior_trail_b is not None:
                            blit_heroine_trail_image(warrior_back_img_raw, warrior_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                    if is_debug:
                        pygame.draw.rect(screen, (255, 255, 255), warrior_img_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
                        draw_art_top_debug_line("warrior_back.png", WARRIOR_HEIGHT_M, warrior_bottom_y, warrior_final_h, warrior_img_rect.left, warrior_img_rect.right)  # ★ [デバッグ] 実際の絵の上端
                    screen.set_clip(None)

                    # [デバッグ表示] 女戦士のHPを「現在HP/最大HP」の文字列で頭上に表示する
                    warrior_hp_text = font.render(f"{warrior_hp}/{WARRIOR_MAX_HP}", True, (255, 255, 255))
                    warrior_hp_rect = warrior_hp_text.get_rect(midbottom=(warrior_img_rect.centerx, warrior_img_rect.top - 4))
                    screen.blit(warrior_hp_text, warrior_hp_rect)

                # 残像履歴を更新する（実際にフレームが進んだときのみ記録し、ポーズ中の再描画で重複登録しないようにする）
                if axe_moving:
                    warrior_trail_key = (battle_warrior_whip_phase, battle_warrior_whip_frame)
                    if warrior_whip_trail_key != warrior_trail_key:
                        warrior_whip_trail_key = warrior_trail_key
                        warrior_whip_trail.append(warrior_current_pos)
                        if len(warrior_whip_trail) > warrior_trail_history_size:
                            warrior_whip_trail.pop(0)
                else:
                    warrior_whip_trail.clear()
                    warrior_whip_trail_key = None

                # ★ シスター（仲間キャラ）の後ろ姿
                if sister_back_img_raw:
                    sis_orig_w, sis_orig_h = sister_back_img_raw.get_size()
                    sister_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_attacking_enemy_index == -1
                                     and battle_turn_order[battle_turn_index] == -4)
                    if sister_active:
                        if battle_sister_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            raw_t = (battle_sister_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            sis_t = 1.0 - (1.0 - raw_t) ** 2
                        elif battle_sister_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                            sis_t = 1.0
                        else:
                            raw_t = (battle_sister_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            sis_t = (1.0 - raw_t) ** 2
                        sis_t = max(0.0, min(1.0, sis_t))
                        sis_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_sister_target_enemy_index])
                        sis_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                        sis_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (SISTER_HEIGHT_M / HEROINE_HEIGHT_M))
                        sister_x = int(sister_base_x + (sis_target_x - sister_base_x) * sis_t)
                        sister_bottom_y = int(sister_base_bottom_y + (sis_target_bottom_y - sister_base_bottom_y) * sis_t)
                        sister_img_h = max(1, int(sister_base_img_h + (sis_target_img_h - sister_base_img_h) * sis_t))
                    else:
                        sister_x = sister_base_x
                        sister_bottom_y = sister_base_bottom_y
                        sister_img_h = sister_base_img_h
                    sister_img_w = max(1, int(sis_orig_w * sister_img_h / sis_orig_h))
                    sister_final_w, sister_final_h = sister_img_w, sister_img_h
                    if idle_active and not sister_active:
                        sister_final_w = max(1, int(sister_img_w * idle_sx))
                        sister_final_h = max(1, int(sister_img_h * idle_sy))
                    sister_display_hp = get_damage_display_hp(sister_damage_anim_old_hp, sister_damage_anim_new_hp, sister_damage_anim_frame)
                    sister_display_img_raw = apply_hp_grayscale(sister_back_img_raw, "sister_back.png", SISTER_HEIGHT_M, int(round(sister_display_hp)), SISTER_MAX_HP)
                    sister_display_img_raw = apply_damage_flash(sister_display_img_raw, "sister_back.png", SISTER_HEIGHT_M, sister_damage_anim_old_hp, sister_damage_anim_new_hp, SISTER_MAX_HP, sister_damage_anim_frame, sister_damage_anim_flash_color)
                    sister_img_surf, sister_img_pos, sister_img_rect = smoothscale_visible(sister_display_img_raw, sister_final_w, sister_final_h, (sister_x, sister_bottom_y), clip_rect)
                    sis_moving = sister_active and battle_sister_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
                    sister_current_pos = (sister_x, sister_bottom_y, sister_img_h)
                    sis_trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

                    def find_sister_trail_pos(offset):
                        if offset <= 0 or len(sister_whip_trail) < offset:
                            return None
                        px, py, _ = sister_whip_trail[-offset]
                        if (px - sister_x) ** 2 + (py - sister_bottom_y) ** 2 < BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2:
                            return None
                        return sister_whip_trail[-offset]

                    sis_trail_a = find_sister_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1) if sis_moving else None
                    sis_trail_b = find_sister_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2) if sis_moving else None

                    def draw_sister_sprite():
                        screen.set_clip(clip_rect)
                        if sister_active and battle_sister_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            if sis_trail_b is not None:
                                blit_heroine_trail_image(sister_back_img_raw, sis_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                            if sis_trail_a is not None:
                                blit_heroine_trail_image(sister_back_img_raw, sis_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if sister_img_surf is not None:
                                screen.blit(sister_img_surf, sister_img_pos)
                        else:
                            if sister_img_surf is not None:
                                screen.blit(sister_img_surf, sister_img_pos)
                            if sis_trail_a is not None:
                                blit_heroine_trail_image(sister_back_img_raw, sis_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if sis_trail_b is not None:
                                blit_heroine_trail_image(sister_back_img_raw, sis_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                        screen.set_clip(None)
                        sister_hp_text = font.render(f"{sister_hp}/{SISTER_MAX_HP}", True, (255, 255, 255))
                        sister_hp_rect = sister_hp_text.get_rect(midbottom=(sister_img_rect.centerx, sister_img_rect.top - 4))
                        screen.blit(sister_hp_text, sister_hp_rect)

                    if sis_moving:
                        sis_tkey = (battle_sister_whip_phase, battle_sister_whip_frame)
                        if sister_whip_trail_key != sis_tkey:
                            sister_whip_trail_key = sis_tkey
                            sister_whip_trail.append(sister_current_pos)
                            if len(sister_whip_trail) > sis_trail_history_size:
                                sister_whip_trail.pop(0)
                    else:
                        sister_whip_trail.clear()
                        sister_whip_trail_key = None
                else:
                    sister_active = False
                    def draw_sister_sprite(): pass

                # ★ くノ一（仲間キャラ）の後ろ姿
                if kunoichi_back_img_raw:
                    kun_orig_w, kun_orig_h = kunoichi_back_img_raw.get_size()
                    kunoichi_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_attacking_enemy_index == -1
                                      and battle_turn_order[battle_turn_index] == -5)
                    if kunoichi_active:
                        if battle_kunoichi_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            raw_t = (battle_kunoichi_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            kun_t = 1.0 - (1.0 - raw_t) ** 2
                        elif battle_kunoichi_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                            kun_t = 1.0
                        else:
                            raw_t = (battle_kunoichi_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            kun_t = (1.0 - raw_t) ** 2
                        kun_t = max(0.0, min(1.0, kun_t))
                        kun_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_kunoichi_target_enemy_index])
                        kun_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                        kun_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (KUNOICHI_HEIGHT_M / HEROINE_HEIGHT_M))
                        kunoichi_x = int(kunoichi_base_x + (kun_target_x - kunoichi_base_x) * kun_t)
                        kunoichi_bottom_y = int(kunoichi_base_bottom_y + (kun_target_bottom_y - kunoichi_base_bottom_y) * kun_t)
                        kunoichi_img_h = max(1, int(kunoichi_base_img_h + (kun_target_img_h - kunoichi_base_img_h) * kun_t))
                    else:
                        kunoichi_x = kunoichi_base_x
                        kunoichi_bottom_y = kunoichi_base_bottom_y
                        kunoichi_img_h = kunoichi_base_img_h
                    kunoichi_img_w = max(1, int(kun_orig_w * kunoichi_img_h / kun_orig_h))
                    kunoichi_final_w, kunoichi_final_h = kunoichi_img_w, kunoichi_img_h
                    if idle_active and not kunoichi_active:
                        kunoichi_final_w = max(1, int(kunoichi_img_w * idle_sx))
                        kunoichi_final_h = max(1, int(kunoichi_img_h * idle_sy))
                    kunoichi_display_hp = get_damage_display_hp(kunoichi_damage_anim_old_hp, kunoichi_damage_anim_new_hp, kunoichi_damage_anim_frame)
                    kunoichi_display_img_raw = apply_hp_grayscale(kunoichi_back_img_raw, "kunoichi_back.png", KUNOICHI_HEIGHT_M, int(round(kunoichi_display_hp)), KUNOICHI_MAX_HP)
                    kunoichi_display_img_raw = apply_damage_flash(kunoichi_display_img_raw, "kunoichi_back.png", KUNOICHI_HEIGHT_M, kunoichi_damage_anim_old_hp, kunoichi_damage_anim_new_hp, KUNOICHI_MAX_HP, kunoichi_damage_anim_frame, kunoichi_damage_anim_flash_color)
                    kunoichi_img_surf, kunoichi_img_pos, kunoichi_img_rect = smoothscale_visible(kunoichi_display_img_raw, kunoichi_final_w, kunoichi_final_h, (kunoichi_x, kunoichi_bottom_y), clip_rect)
                    kun_moving = kunoichi_active and battle_kunoichi_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
                    kunoichi_current_pos = (kunoichi_x, kunoichi_bottom_y, kunoichi_img_h)
                    kun_trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

                    def find_kunoichi_trail_pos(offset):
                        if offset <= 0 or len(kunoichi_whip_trail) < offset:
                            return None
                        px, py, _ = kunoichi_whip_trail[-offset]
                        if (px - kunoichi_x) ** 2 + (py - kunoichi_bottom_y) ** 2 < BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2:
                            return None
                        return kunoichi_whip_trail[-offset]

                    kun_trail_a = find_kunoichi_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1) if kun_moving else None
                    kun_trail_b = find_kunoichi_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2) if kun_moving else None

                    def draw_kunoichi_sprite():
                        screen.set_clip(clip_rect)
                        if kunoichi_active and battle_kunoichi_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            if kun_trail_b is not None:
                                blit_heroine_trail_image(kunoichi_back_img_raw, kun_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                            if kun_trail_a is not None:
                                blit_heroine_trail_image(kunoichi_back_img_raw, kun_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if kunoichi_img_surf is not None:
                                screen.blit(kunoichi_img_surf, kunoichi_img_pos)
                        else:
                            if kunoichi_img_surf is not None:
                                screen.blit(kunoichi_img_surf, kunoichi_img_pos)
                            if kun_trail_a is not None:
                                blit_heroine_trail_image(kunoichi_back_img_raw, kun_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if kun_trail_b is not None:
                                blit_heroine_trail_image(kunoichi_back_img_raw, kun_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                        screen.set_clip(None)
                        kunoichi_hp_text = font.render(f"{kunoichi_hp}/{KUNOICHI_MAX_HP}", True, (255, 255, 255))
                        kunoichi_hp_rect = kunoichi_hp_text.get_rect(midbottom=(kunoichi_img_rect.centerx, kunoichi_img_rect.top - 4))
                        screen.blit(kunoichi_hp_text, kunoichi_hp_rect)

                    if kun_moving:
                        kun_tkey = (battle_kunoichi_whip_phase, battle_kunoichi_whip_frame)
                        if kunoichi_whip_trail_key != kun_tkey:
                            kunoichi_whip_trail_key = kun_tkey
                            kunoichi_whip_trail.append(kunoichi_current_pos)
                            if len(kunoichi_whip_trail) > kun_trail_history_size:
                                kunoichi_whip_trail.pop(0)
                    else:
                        kunoichi_whip_trail.clear()
                        kunoichi_whip_trail_key = None
                else:
                    kunoichi_active = False
                    def draw_kunoichi_sprite(): pass

                # ★ 魔法使い（仲間キャラ）の後ろ姿
                if wizard_back_img_raw:
                    wiz_orig_w, wiz_orig_h = wizard_back_img_raw.get_size()
                    wizard_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_attacking_enemy_index == -1
                                     and battle_turn_order[battle_turn_index] == -6)
                    if wizard_active:
                        if battle_wizard_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            raw_t = (battle_wizard_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            wiz_t = 1.0 - (1.0 - raw_t) ** 2
                        elif battle_wizard_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                            wiz_t = 1.0
                        else:
                            raw_t = (battle_wizard_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            wiz_t = (1.0 - raw_t) ** 2
                        wiz_t = max(0.0, min(1.0, wiz_t))
                        wiz_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_wizard_target_enemy_index])
                        wiz_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                        wiz_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (WIZARD_HEIGHT_M / HEROINE_HEIGHT_M))
                        wizard_x = int(wizard_base_x + (wiz_target_x - wizard_base_x) * wiz_t)
                        wizard_bottom_y = int(wizard_base_bottom_y + (wiz_target_bottom_y - wizard_base_bottom_y) * wiz_t)
                        wizard_img_h = max(1, int(wizard_base_img_h + (wiz_target_img_h - wizard_base_img_h) * wiz_t))
                    else:
                        wizard_x = wizard_base_x
                        wizard_bottom_y = wizard_base_bottom_y
                        wizard_img_h = wizard_base_img_h
                    wizard_img_w = max(1, int(wiz_orig_w * wizard_img_h / wiz_orig_h))
                    wizard_final_w, wizard_final_h = wizard_img_w, wizard_img_h
                    if idle_active and not wizard_active:
                        wizard_final_w = max(1, int(wizard_img_w * idle_sx))
                        wizard_final_h = max(1, int(wizard_img_h * idle_sy))
                    wizard_display_hp = get_damage_display_hp(wizard_damage_anim_old_hp, wizard_damage_anim_new_hp, wizard_damage_anim_frame)
                    wizard_display_img_raw = apply_hp_grayscale(wizard_back_img_raw, "wizard_back.png", WIZARD_HEIGHT_M, int(round(wizard_display_hp)), WIZARD_MAX_HP)
                    wizard_display_img_raw = apply_damage_flash(wizard_display_img_raw, "wizard_back.png", WIZARD_HEIGHT_M, wizard_damage_anim_old_hp, wizard_damage_anim_new_hp, WIZARD_MAX_HP, wizard_damage_anim_frame, wizard_damage_anim_flash_color)
                    wizard_img_surf, wizard_img_pos, wizard_img_rect = smoothscale_visible(wizard_display_img_raw, wizard_final_w, wizard_final_h, (wizard_x, wizard_bottom_y), clip_rect)
                    wiz_moving = wizard_active and battle_wizard_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
                    wizard_current_pos = (wizard_x, wizard_bottom_y, wizard_img_h)
                    wiz_trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

                    def find_wizard_trail_pos(offset):
                        if offset <= 0 or len(wizard_whip_trail) < offset:
                            return None
                        px, py, _ = wizard_whip_trail[-offset]
                        if (px - wizard_x) ** 2 + (py - wizard_bottom_y) ** 2 < BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2:
                            return None
                        return wizard_whip_trail[-offset]

                    wiz_trail_a = find_wizard_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1) if wiz_moving else None
                    wiz_trail_b = find_wizard_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2) if wiz_moving else None

                    def draw_wizard_sprite():
                        screen.set_clip(clip_rect)
                        if wizard_active and battle_wizard_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            if wiz_trail_b is not None:
                                blit_heroine_trail_image(wizard_back_img_raw, wiz_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                            if wiz_trail_a is not None:
                                blit_heroine_trail_image(wizard_back_img_raw, wiz_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if wizard_img_surf is not None:
                                screen.blit(wizard_img_surf, wizard_img_pos)
                        else:
                            if wizard_img_surf is not None:
                                screen.blit(wizard_img_surf, wizard_img_pos)
                            if wiz_trail_a is not None:
                                blit_heroine_trail_image(wizard_back_img_raw, wiz_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if wiz_trail_b is not None:
                                blit_heroine_trail_image(wizard_back_img_raw, wiz_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                        screen.set_clip(None)
                        wizard_hp_text = font.render(f"{wizard_hp}/{WIZARD_MAX_HP}", True, (255, 255, 255))
                        wizard_hp_rect = wizard_hp_text.get_rect(midbottom=(wizard_img_rect.centerx, wizard_img_rect.top - 4))
                        screen.blit(wizard_hp_text, wizard_hp_rect)

                    if wiz_moving:
                        wiz_tkey = (battle_wizard_whip_phase, battle_wizard_whip_frame)
                        if wizard_whip_trail_key != wiz_tkey:
                            wizard_whip_trail_key = wiz_tkey
                            wizard_whip_trail.append(wizard_current_pos)
                            if len(wizard_whip_trail) > wiz_trail_history_size:
                                wizard_whip_trail.pop(0)
                    else:
                        wizard_whip_trail.clear()
                        wizard_whip_trail_key = None
                else:
                    wizard_active = False
                    def draw_wizard_sprite(): pass

                # ★ 武道家（仲間キャラ）の後ろ姿
                if fighter_back_img_raw:
                    fig_orig_w, fig_orig_h = fighter_back_img_raw.get_size()
                    fighter_active = (battle_phase == BATTLE_PHASE_EXCHANGE and battle_attacking_enemy_index == -1
                                      and battle_turn_order[battle_turn_index] == -7)
                    if fighter_active:
                        if battle_fighter_whip_phase == BATTLE_WHIP_PHASE_APPROACH:
                            raw_t = (battle_fighter_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            fig_t = 1.0 - (1.0 - raw_t) ** 2
                        elif battle_fighter_whip_phase in (BATTLE_WHIP_PHASE_DAMAGE_WAIT, BATTLE_WHIP_PHASE_FLASH):
                            fig_t = 1.0
                        else:
                            raw_t = (battle_fighter_whip_frame / BATTLE_WHIP_APPROACH_FRAMES) if BATTLE_WHIP_APPROACH_FRAMES > 0 else 1.0
                            fig_t = (1.0 - raw_t) ** 2
                        fig_t = max(0.0, min(1.0, fig_t))
                        fig_target_x = int(SCREEN_W * ENEMY_X_RATIOS[battle_fighter_target_enemy_index])
                        fig_target_bottom_y = SCREEN_H - int(SCREEN_H * BATTLE_WHIP_TARGET_GROUND_Y_FROM_BOTTOM_RATIO)
                        fig_target_img_h = int(SCREEN_H * BATTLE_WHIP_TARGET_SCALE * (FIGHTER_HEIGHT_M / HEROINE_HEIGHT_M))
                        fighter_x = int(fighter_base_x + (fig_target_x - fighter_base_x) * fig_t)
                        fighter_bottom_y = int(fighter_base_bottom_y + (fig_target_bottom_y - fighter_base_bottom_y) * fig_t)
                        fighter_img_h = max(1, int(fighter_base_img_h + (fig_target_img_h - fighter_base_img_h) * fig_t))
                    else:
                        fighter_x = fighter_base_x
                        fighter_bottom_y = fighter_base_bottom_y
                        fighter_img_h = fighter_base_img_h
                    fighter_img_w = max(1, int(fig_orig_w * fighter_img_h / fig_orig_h))
                    fighter_final_w, fighter_final_h = fighter_img_w, fighter_img_h
                    if idle_active and not fighter_active:
                        fighter_final_w = max(1, int(fighter_img_w * idle_sx))
                        fighter_final_h = max(1, int(fighter_img_h * idle_sy))
                    fighter_display_hp = get_damage_display_hp(fighter_damage_anim_old_hp, fighter_damage_anim_new_hp, fighter_damage_anim_frame)
                    fighter_display_img_raw = apply_hp_grayscale(fighter_back_img_raw, "fighter_back.png", FIGHTER_HEIGHT_M, int(round(fighter_display_hp)), FIGHTER_MAX_HP)
                    fighter_display_img_raw = apply_damage_flash(fighter_display_img_raw, "fighter_back.png", FIGHTER_HEIGHT_M, fighter_damage_anim_old_hp, fighter_damage_anim_new_hp, FIGHTER_MAX_HP, fighter_damage_anim_frame, fighter_damage_anim_flash_color)
                    fighter_img_surf, fighter_img_pos, fighter_img_rect = smoothscale_visible(fighter_display_img_raw, fighter_final_w, fighter_final_h, (fighter_x, fighter_bottom_y), clip_rect)
                    fig_moving = fighter_active and battle_fighter_whip_phase in (BATTLE_WHIP_PHASE_APPROACH, BATTLE_WHIP_PHASE_RETURN)
                    fighter_current_pos = (fighter_x, fighter_bottom_y, fighter_img_h)
                    fig_trail_history_size = max(BATTLE_WHIP_TRAIL_OFFSET_1, BATTLE_WHIP_TRAIL_OFFSET_2)

                    def find_fighter_trail_pos(offset):
                        if offset <= 0 or len(fighter_whip_trail) < offset:
                            return None
                        px, py, _ = fighter_whip_trail[-offset]
                        if (px - fighter_x) ** 2 + (py - fighter_bottom_y) ** 2 < BATTLE_WHIP_TRAIL_MIN_OFFSET_PX ** 2:
                            return None
                        return fighter_whip_trail[-offset]

                    fig_trail_a = find_fighter_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_1) if fig_moving else None
                    fig_trail_b = find_fighter_trail_pos(BATTLE_WHIP_TRAIL_OFFSET_2) if fig_moving else None

                    def draw_fighter_sprite():
                        screen.set_clip(clip_rect)
                        if fighter_active and battle_fighter_whip_phase == BATTLE_WHIP_PHASE_RETURN:
                            if fig_trail_b is not None:
                                blit_heroine_trail_image(fighter_back_img_raw, fig_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                            if fig_trail_a is not None:
                                blit_heroine_trail_image(fighter_back_img_raw, fig_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if fighter_img_surf is not None:
                                screen.blit(fighter_img_surf, fighter_img_pos)
                        else:
                            if fighter_img_surf is not None:
                                screen.blit(fighter_img_surf, fighter_img_pos)
                            if fig_trail_a is not None:
                                blit_heroine_trail_image(fighter_back_img_raw, fig_trail_a, BATTLE_WHIP_TRAIL_ALPHA_1, clip_rect)
                            if fig_trail_b is not None:
                                blit_heroine_trail_image(fighter_back_img_raw, fig_trail_b, BATTLE_WHIP_TRAIL_ALPHA_2, clip_rect)
                        screen.set_clip(None)
                        fighter_hp_text = font.render(f"{fighter_hp}/{FIGHTER_MAX_HP}", True, (255, 255, 255))
                        fighter_hp_rect = fighter_hp_text.get_rect(midbottom=(fighter_img_rect.centerx, fighter_img_rect.top - 4))
                        screen.blit(fighter_hp_text, fighter_hp_rect)

                    if fig_moving:
                        fig_tkey = (battle_fighter_whip_phase, battle_fighter_whip_frame)
                        if fighter_whip_trail_key != fig_tkey:
                            fighter_whip_trail_key = fig_tkey
                            fighter_whip_trail.append(fighter_current_pos)
                            if len(fighter_whip_trail) > fig_trail_history_size:
                                fighter_whip_trail.pop(0)
                    else:
                        fighter_whip_trail.clear()
                        fighter_whip_trail_key = None
                else:
                    fighter_active = False
                    def draw_fighter_sprite(): pass

                # ★ 攻撃中の味方キャラ（ヒロイン:whip_active／サムライ:samurai_active／女戦士:warrior_active等）を、
                # 他のキャラより奥（先）に描画することで、攻撃のための移動時に手前のキャラと重なって不自然にならないようにする
                # （マカダンス中はヒロインが画面下に消えているため、サムライ・その他のみ描画する）
                def _draw_non_attacker_sprites(skip_fn):
                    for fn in [draw_heroine_sprite, draw_samurai_sprite, draw_warrior_sprite,
                                draw_sister_sprite, draw_kunoichi_sprite, draw_wizard_sprite, draw_fighter_sprite]:
                        if fn is not skip_fn:
                            fn()

                if dance_active:
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
                elif whip_active:
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
                elif samurai_active:
                    draw_samurai_sprite()
                    draw_heroine_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
                elif warrior_active:
                    draw_warrior_sprite()
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
                elif sister_active:
                    draw_sister_sprite()
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
                elif kunoichi_active:
                    draw_kunoichi_sprite()
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
                elif wizard_active:
                    draw_wizard_sprite()
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_fighter_sprite()
                elif fighter_active:
                    draw_fighter_sprite()
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                else:
                    draw_heroine_sprite()
                    draw_samurai_sprite()
                    draw_warrior_sprite()
                    draw_sister_sprite()
                    draw_kunoichi_sprite()
                    draw_wizard_sprite()
                    draw_fighter_sprite()
            else:
                # ★ 攻撃中の味方キャラ（ヒロインの場合はwhip_active、サムライの場合はsamurai_active）を、
                # もう一方のキャラより奥（先）に描画することで、攻撃のための移動時に手前のキャラと重なって不自然にならないようにする
                # （マカダンス中はヒロインが画面下に消えているため、サムライのみ描画する）
                if dance_active:
                    draw_samurai_sprite()
                elif samurai_active:
                    draw_samurai_sprite()
                    draw_heroine_sprite()
                else:
                    draw_heroine_sprite()
                    draw_samurai_sprite()
        elif not dance_active:
            draw_heroine_sprite()

    # ★ 心眼剣：開始から指定フレームかけてバトルウィンドウ内の全て（キャラ・背景）を暗転させ、
    # 1回目の斬撃開始と同時に対象敵だけを通常表示に戻し、最後の斬撃開始から暗転を解除する
    # （オーバーレイは矩形に穴を開けず全面に描き、対象敵・サムライの絵だけを上から再描画することで、
    #   透明部分から背景の色が矩形に見えてしまうのを防ぐ）
    # ★ サムライは暗転中も常時通常表示にする（技を発動している本人なので暗転の影響を受けない）
    shingan_darken_alpha = get_shingan_darken_alpha(battle_shingan_frame)
    if shingan_darken_alpha > 0:
        draw_darken_overlay(shingan_darken_alpha, clip_rect)
        screen.set_clip(clip_rect)
        if shingan_samurai_img is not None:
            screen.blit(shingan_samurai_img, shingan_samurai_pos)
        if battle_shingan_frame >= SHINGANKEN_WAIT_FRAMES and shingan_target_enemy_img is not None:
            screen.blit(shingan_target_enemy_img, shingan_target_enemy_pos)
        screen.set_clip(None)

    # ★ 心眼剣の斬撃エフェクト：7本それぞれ独立に進行し、方向は360度からランダムに選ばれる
    # （暗転オーバーレイ・対象敵の再描画よりさらに手前に描画することで、暗転中も視認できるようにする）
    if 0 <= battle_shingan_target_enemy_index < len(enemy_rects) and shingan_target_top_y is not None:
        screen.set_clip(clip_rect)
        for slash_i in range(SHINGANKEN_SLASH_COUNT):
            if battle_shingan_slash_frames[slash_i] < BATTLE_SLASH_TOTAL_FRAMES:
                draw_shingan_slash(enemy_rects[battle_shingan_target_enemy_index], shingan_target_top_y, battle_shingan_slash_frames[slash_i], battle_shingan_slash_angles[slash_i])
        screen.set_clip(None)

    # ★ 攻撃選択サブウィンドウ（ズームアウト完了後・コマンド選択中のみ表示。攻防ステート中は非表示）
    if heroine_zoomout_frame >= BATTLE_HEROINE_ZOOMOUT_FRAMES:
        if battle_phase == BATTLE_PHASE_COMMAND_HEROINE:
            render_battle_menu(BATTLE_MENU_OPTIONS, battle_menu_selected_index)
        elif battle_phase == BATTLE_PHASE_COMMAND_SAMURAI:
            render_battle_menu(get_samurai_menu_options(), battle_samurai_menu_selected_index)
        elif battle_phase == BATTLE_PHASE_COMMAND_WARRIOR:
            render_battle_menu(WARRIOR_MENU_OPTIONS, battle_warrior_menu_selected_index)
        elif battle_phase == BATTLE_PHASE_COMMAND_SISTER:
            render_battle_menu(SISTER_MENU_OPTIONS, battle_sister_menu_selected_index)
        elif battle_phase == BATTLE_PHASE_COMMAND_KUNOICHI:
            render_battle_menu(KUNOICHI_MENU_OPTIONS, battle_kunoichi_menu_selected_index)
        elif battle_phase == BATTLE_PHASE_COMMAND_WIZARD:
            render_battle_menu(WIZARD_MENU_OPTIONS, battle_wizard_menu_selected_index)
        elif battle_phase == BATTLE_PHASE_COMMAND_FIGHTER:
            render_battle_menu(FIGHTER_MENU_OPTIONS, battle_fighter_menu_selected_index)

# ---------------------------------------------------------
# render_battle_menu()：攻撃選択サブウィンドウの描画
# ---------------------------------------------------------
def render_battle_menu(options, selected_index):
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
    for i, label in enumerate(options):
        color = BATTLE_MENU_SELECTED_COLOR if i == selected_index else BATTLE_MENU_UNSELECTED_COLOR
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
        # トドメを刺した味方（通常はヒロイン、サムライがトドメを刺した場合はサムライ）の後ろ姿をフェードアウト
        # （result_flashout_heroine_override / result_flashout_samurai_override が指定されている場合は、
        #   戦闘終了直前の表示位置・スケールをそのまま引き継ぐ。
        #   通常位置にスナップして見える違和感を防ぐため。例：ムチ・剣で最後の敵を倒した直後はリザルトの最接近位置を維持する）
        if result_flashout_is_warrior:
            _ch = result_flashout_active_char
            if _ch == -4:
                flashout_img_raw = sister_back_img_raw
                flashout_height_m = SISTER_HEIGHT_M
            elif _ch == -5:
                flashout_img_raw = kunoichi_back_img_raw
                flashout_height_m = KUNOICHI_HEIGHT_M
            elif _ch == -6:
                flashout_img_raw = wizard_back_img_raw
                flashout_height_m = WIZARD_HEIGHT_M
            elif _ch == -7:
                flashout_img_raw = fighter_back_img_raw
                flashout_height_m = FIGHTER_HEIGHT_M
            else:
                flashout_img_raw = warrior_back_img_raw
                flashout_height_m = WARRIOR_HEIGHT_M
            flashout_override = result_flashout_warrior_override
            flashout_world_offset_m = battle_character_world_offset_m[_ch]
        elif result_flashout_is_samurai:
            flashout_img_raw = samurai_back_img_raw
            flashout_override = result_flashout_samurai_override
            flashout_height_m = SAMURAI_HEIGHT_M
            flashout_world_offset_m = battle_character_world_offset_m[-2]
        else:
            flashout_img_raw = battle_back_img_raw
            flashout_override = result_flashout_heroine_override
            flashout_height_m = HEROINE_HEIGHT_M
            flashout_world_offset_m = battle_character_world_offset_m[-1]
        flashout_default_x = SCREEN_W // 2 + int(flashout_world_offset_m * BATTLE_HEROINE_LAST_METER_TO_PIXEL)

        if flashout_img_raw:
            orig_w, orig_h = flashout_img_raw.get_size()
            if flashout_override:
                x, boty, h = flashout_override
            else:
                h = int(flashout_height_m * BATTLE_HEROINE_LAST_METER_TO_PIXEL)
                x = flashout_default_x
                boty = band_bottom + int(BATTLE_HEROINE_LAST_FOCUS_M * BATTLE_HEROINE_LAST_METER_TO_PIXEL)
            w = max(1, int(orig_w * h / orig_h))
            img = pygame.transform.smoothscale(flashout_img_raw, (w, h))
            alpha_img = img.copy()
            alpha_img.set_alpha(int(255 * (1.0 - t)))
            alpha_img_rect = img.get_rect(midbottom=(x, boty))
            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(alpha_img, alpha_img_rect)
            if is_debug:
                pygame.draw.rect(screen, (255, 255, 255), alpha_img_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
            screen.set_clip(None)
        return

    # -------- フェーズ②：白ウィンドウ静止 --------
    overlay_white = pygame.Surface((SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
    overlay_white.fill((255, 255, 255))

    if result_white_delay_frame < RESULT_WHITE_DELAY_FRAMES:
        screen.blit(overlay_white, (0, band_y))
        return

    # -------- フェーズ③④：スライドイン（黒シルエット→通常） --------
    if result_active_win_img:
        win_w = result_active_win_img.get_width()

        # スライドイン進行度（0.0 → 1.0）
        t_slide = min(1.0, result_slidein_frame / RESULT_SLIDEIN_FRAMES) \
                  if RESULT_SLIDEIN_FRAMES > 0 else 1.0
        # ease-out
        t_eased = 1.0 - (1.0 - t_slide) ** 2

        # X 位置：画面外左端（-win_w/2）→ 画面中央
        start_cx = -win_w // 2
        end_cx   = SCREEN_W // 2
        cx = int(start_cx + (end_cx - start_cx) * t_eased)

        if result_flashout_is_warrior:
            win_h = result_active_win_img.get_height()
            _ch = result_flashout_active_char
            if _ch == -4:
                _margin_m, _height_m = RESULT_SISTER_WIN_TOP_MARGIN_M, SISTER_HEIGHT_M
            elif _ch == -5:
                _margin_m, _height_m = RESULT_KUNOICHI_WIN_TOP_MARGIN_M, KUNOICHI_HEIGHT_M
            elif _ch == -6:
                _margin_m, _height_m = RESULT_WIZARD_WIN_TOP_MARGIN_M, WIZARD_HEIGHT_M
            elif _ch == -7:
                _margin_m, _height_m = RESULT_FIGHTER_WIN_TOP_MARGIN_M, FIGHTER_HEIGHT_M
            else:
                _margin_m, _height_m = RESULT_WARRIOR_WIN_TOP_MARGIN_M, WARRIOR_HEIGHT_M
            top_margin_px = int(win_h * _margin_m / _height_m) if _height_m > 0 else 0
            img_rect = result_active_win_img.get_rect(midtop=(cx, band_y - top_margin_px))
        elif result_flashout_is_samurai:
            # サムライ（samurai_front.png）：画像上端からRESULT_SAMURAI_WIN_TOP_MARGIN_M分の位置が
            # ゲームウィンドウ上端(band_y)に一致するように配置する
            # （initialize()で一度だけ行ったスケールのまま、追加の拡縮は行わない）
            win_h = result_active_win_img.get_height()
            top_margin_px = int(win_h * RESULT_SAMURAI_WIN_TOP_MARGIN_M / SAMURAI_HEIGHT_M) if SAMURAI_HEIGHT_M > 0 else 0
            img_rect = result_active_win_img.get_rect(midtop=(cx, band_y - top_margin_px))
        else:
            # ヒロイン（bunny_front.png）：画像上端からRESULT_HEROINE_WIN_TOP_MARGIN_M分の位置が
            # ゲームウィンドウ上端(band_y)に一致するように配置する
            # （initialize()で一度だけ行ったスケールのまま、追加の拡縮は行わない）
            win_h = result_active_win_img.get_height()
            top_margin_px = int(win_h * RESULT_HEROINE_WIN_TOP_MARGIN_M / HEROINE_HEIGHT_M) if HEROINE_HEIGHT_M > 0 else 0
            img_rect = result_active_win_img.get_rect(midtop=(cx, band_y - top_margin_px))

        arrived = (result_slidein_frame >= RESULT_SLIDEIN_FRAMES)

        if arrived:
            # 到達後：RESULT_WINDOW_COLOR ウィンドウ + 通常表示
            overlay_result = pygame.Surface((SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            overlay_result.fill(RESULT_WINDOW_COLOR)
            screen.blit(overlay_result, (0, band_y))

            # 待機モーションの拡縮は行わず、initialize()で算出したサイズのまま静止表示する
            display_img = result_active_win_img
            display_rect = display_img.get_rect(midbottom=img_rect.midbottom)

            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(display_img, display_rect)
            if is_debug:
                pygame.draw.rect(screen, (255, 255, 255), display_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
            screen.set_clip(None)
        else:
            # スライドイン中：白ウィンドウ + 黒シルエット
            screen.blit(overlay_white, (0, band_y))
            # 黒シルエット：画像と同サイズの Surface に黒を乗算合成
            silhouette = result_active_win_img.copy()
            black_fill = pygame.Surface(silhouette.get_size(), pygame.SRCALPHA)
            black_fill.fill((0, 0, 0, 255))
            silhouette.blit(black_fill, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.set_clip(pygame.Rect(0, band_y, SCREEN_W, BATTLE_MAIN_WINDOW_HEIGHT))
            screen.blit(silhouette, img_rect)
            if is_debug:
                pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)  # ★ [デバッグ] 元画像サイズの枠線
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
    elif game_state == STATE_STATUS:
        render_status()
    else:  # STATE_RESULT
        render_result()

    pygame.display.flip()

# ---------------------------------------------------------
# render_status()：ステータスウィンドウ（バトルメインウィンドウと同じサイズ・開閉速度の黒背景ウィンドウ）
# ---------------------------------------------------------
def render_status():
    render_field()

    progress = min(1.0, status_anim_frame / BATTLE_MAIN_WINDOW_ANIM_FRAMES)
    current_height = int(BATTLE_MAIN_WINDOW_HEIGHT * progress)

    band_y = SCREEN_H // 2 - current_height // 2
    band_bottom = band_y + current_height

    overlay = pygame.Surface((SCREEN_W, current_height))
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, band_y))

    # ★ 全仲間キャラを身長に応じたサイズで、足元をウィンドウ下端に揃えて均等配置で表示する
    # 7人の配置（左から）：ヒロイン・サムライ・女戦士・シスター・くノ一・魔法使い・武道家
    # 位置式：cx + i * spacing_px  (i = -3, -2, -1, 0, +1, +2, +3)
    # spacing_px はワールド座標 STATUS_CHARACTER_SPACING_M から算出。値を調整すると全員の間隔が変わる
    cx = SCREEN_W // 2
    spacing_px = int(STATUS_CHARACTER_SPACING_M * STATUS_METER_TO_PIXEL)

    clip_rect = pygame.Rect(0, band_y, SCREEN_W, current_height)
    screen.set_clip(clip_rect)

    # ★ 上下キーで前姿／後ろ姿を切り替え（デフォルトは後ろ姿）
    heroine_img_raw = heroine_front_img_raw if status_view == STATUS_VIEW_FRONT else battle_back_img_raw
    if status_view == STATUS_VIEW_FRONT:
        samurai_img_raw  = samurai_front_img_raw
        warrior_img_raw  = warrior_front_img_raw
        sister_img_raw   = sister_front_img_raw
        kunoichi_img_raw = kunoichi_front_img_raw
        wizard_img_raw   = wizard_front_img_raw
        fighter_img_raw  = fighter_front_img_raw
    else:
        samurai_img_raw  = samurai_back_img_raw
        warrior_img_raw  = warrior_back_img_raw
        sister_img_raw   = sister_back_img_raw
        kunoichi_img_raw = kunoichi_back_img_raw
        wizard_img_raw   = wizard_back_img_raw
        fighter_img_raw  = fighter_back_img_raw

    if heroine_img_raw:
        img_h = int(HEROINE_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = heroine_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(heroine_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx - 3 * spacing_px, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            heroine_art_key = "bunny_front.png" if status_view == STATUS_VIEW_FRONT else "bunny_back.png"
            draw_art_top_debug_line(heroine_art_key, HEROINE_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    if samurai_img_raw:
        img_h = int(SAMURAI_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = samurai_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(samurai_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx - 2 * spacing_px, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            samurai_art_key = "samurai_front.png" if status_view == STATUS_VIEW_FRONT else "samurai_back.png"
            draw_art_top_debug_line(samurai_art_key, SAMURAI_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    if warrior_img_raw:
        img_h = int(WARRIOR_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = warrior_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(warrior_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx - spacing_px, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            warrior_art_key = "warrior_front.png" if status_view == STATUS_VIEW_FRONT else "warrior_back.png"
            draw_art_top_debug_line(warrior_art_key, WARRIOR_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    if sister_img_raw:
        img_h = int(SISTER_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = sister_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(sister_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            sister_art_key = "sister_front.png" if status_view == STATUS_VIEW_FRONT else "sister_back.png"
            draw_art_top_debug_line(sister_art_key, SISTER_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    if kunoichi_img_raw:
        img_h = int(KUNOICHI_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = kunoichi_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(kunoichi_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx + spacing_px, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            kunoichi_art_key = "kunoichi_front.png" if status_view == STATUS_VIEW_FRONT else "kunoichi_back.png"
            draw_art_top_debug_line(kunoichi_art_key, KUNOICHI_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    if wizard_img_raw:
        img_h = int(WIZARD_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = wizard_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(wizard_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx + 2 * spacing_px, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            wizard_art_key = "wizard_front.png" if status_view == STATUS_VIEW_FRONT else "wizard_back.png"
            draw_art_top_debug_line(wizard_art_key, WIZARD_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    if fighter_img_raw:
        img_h = int(FIGHTER_HEIGHT_M * STATUS_METER_TO_PIXEL)
        orig_w, orig_h = fighter_img_raw.get_size()
        img_w = max(1, int(orig_w * img_h / orig_h))
        img = pygame.transform.smoothscale(fighter_img_raw, (img_w, img_h))
        img_rect = img.get_rect(midbottom=(cx + 3 * spacing_px, band_bottom))
        screen.blit(img, img_rect)
        if is_debug:
            pygame.draw.rect(screen, (255, 255, 255), img_rect, 1)
            fighter_art_key = "fighter_front.png" if status_view == STATUS_VIEW_FRONT else "fighter_back.png"
            draw_art_top_debug_line(fighter_art_key, FIGHTER_HEIGHT_M, band_bottom, img_h, img_rect.left, img_rect.right)

    screen.set_clip(None)

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