import argparse
from datetime import datetime
import logging
from pathlib import Path

import numpy as np
import cv2
import pygame.mixer

from app_exception import OheyaObeyaError
from color import Color
from notifier import notify_slack, upload_to_slack
from predict import classify
from secret import settings

# log settings
logger = logging.getLogger('OheyaObeya')
logger.setLevel(logging.DEBUG)
s_handler = logging.StreamHandler()
log_format = '[%(levelname)s][%(asctime)s] %(message)s'
formatter = logging.Formatter(log_format)
s_handler.setFormatter(formatter)
logger.addHandler(s_handler)

SOUND_ROOT_PATH = 'material/sound'
IMAGE_ROOT_PATH = 'material/images'
CAMERA_RAW_SIZE = settings.CAMERA_RAW_SIZE

dir_name = datetime.now().strftime("%Y%m%d_%H%M%S")
DST_IMAGE_PATH = Path('captured') / dir_name


# TODO: モードが増えてきたのでちゃんと設計する
def main(alert_mode: bool, sound: bool, save_image: bool) -> None:

    if sound:
        if not Path(SOUND_ROOT_PATH).exists():
            raise OheyaObeyaError('音源フォルダが見つかりません。(再配布不可の音源を使用しているため、GitHub上に音源ファイルは置いていません。使用する場合は、自身で用意してください)')
        pygame.mixer.init()

        # 実際には以下のサイトから素材を借りた
        # 効果音ラボ: https://soundeffect-lab.info/sound/button/
        # PANICPUMPKIN: http://pansound.com/panicpumpkin/index.html
        # ※ 再配布不可なのでGitHub上には音源ファイルはuploadしていない
        #   使用する際は指定のパスに適当な音源を配置すること
        pygame.mixer.music.load(str(Path(SOUND_ROOT_PATH) / 'start.mp3'))
        pygame.mixer.music.play(1)

    camera_id = check_expected_camera_id()

    messy_flag = False
    messy_count = 0
    not_messy_count = 0
    cap = cv2.VideoCapture(camera_id)
    pygame.init()
    pygame.display.set_caption("OheyaObeya Classification Demo")
    screen = pygame.display.set_mode()
    status_font = pygame.font.Font(None, 100)
    status_color = {'messy': (255, 0, 0),
                    'so-so': (255, 165, 0),
                    'clean': (181, 255, 20)}
    sub_font = pygame.font.Font(None, 60)

    if save_image:
        for label_name in ['messy', 'so-so', 'clean']:
            dir_path = Path(DST_IMAGE_PATH) / label_name
            dir_path.mkdir(parents=True, exist_ok=True)

    while True:
        # Capture
        ret, image = cap.read()
        path = Path('now.jpg')
        cv2.imwrite(str(path), image)

        # Predict
        result_dict = classify(path)
        display_prediction_result(result_dict)
        result = result_dict['prediction']

        # 保存モードがONの場合は、日時_推測結果.jpgで画像を保存する
        if save_image:
            file_name = datetime.now().strftime("%Y%m%d_%H%M%S_{}.jpg".format(result))
            path = Path(DST_IMAGE_PATH) / result / file_name
            cv2.imwrite(str(path), image)

        # TODO: 連続した回数ではなく、過去n回分のm%分で判断させる
        if result == 'messy':
            messy_count += 1
            not_messy_count = 0
            logger.debug('messy_count = {}'.format(messy_count))
        else:
            not_messy_count += 1
            messy_count = 0
            logger.debug('not_messy_count = {}'.format(not_messy_count))

        # スクリーンを初期化
        screen.fill([0, 0, 0])

        # スクリーンにカメラの映像を表示する
        frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        frame = frame[:, ::-1]
        frame = np.rot90(frame)
        # frame = frame[:, ::-1]  # 上下を逆にする
        frame = pygame.surfarray.make_surface(frame)
        screen.blit(frame, (0, 0))

        # スクリーンに判定結果を表示する
        status_text = status_font.render(result, True, status_color[result])
        screen.blit(status_text, [20, 20])

        # スクリーンにmessyの確率を表示する
        messy_prob = [x['probability'] for x in result_dict['predictions'] if x['label'] == 'messy'][0]
        messy_prob_text = sub_font.render('{:.2f}'.format(messy_prob), True, (255, 0, 0))
        screen.blit(messy_prob_text, [20, 100])

        if messy_flag and alert_mode:
            # スクリーンに警報の文字を表示する
            messy_alarm = '!!! Obeya Alarm!!!'
            messy_alarm_text = sub_font.render(messy_alarm, True, (255, 0, 0))
            screen.blit(messy_alarm_text, [20, 150])

            # 警報中は、messyじゃない状態が続いたら緑のバーが伸びていく
            not_messy_bar = '{}: {}'.format(not_messy_count, '*' * not_messy_count)
            not_messy_bar_text = sub_font.render(not_messy_bar, True, (181, 255, 20))
            screen.blit(not_messy_bar_text, [150, 100])
        else:
            # messyの状態が続いたら赤いバーが伸びていく
            messy_bar = '{}: {}'.format(messy_count, '*' * messy_count)
            messy_bar_text = sub_font.render(messy_bar, True, (255, 0, 0))
            screen.blit(messy_bar_text, [150, 100])

        pygame.display.update()

        # 汚部屋警報のON/OFFが切り替わったか判定
        if messy_count > 10 and not messy_flag and alert_mode:
            messy_flag = True
            alert_obeya(on=True, sound=sound)
        elif not_messy_count > 10 and messy_flag:
            messy_flag = False
            alert_obeya(on=False, sound=sound)

        for event in pygame.event.get():
            pass

    cap.release()


def display_prediction_result(result_dict: dict) -> None:
    logger.debug(result_dict)
    result = result_dict['prediction']
    result_emoji = {'messy': '😱',
                    'so-so': '🤔',
                    'clean': '✨'}
    result_color = {'messy': Color.PURPLE,
                    'so-so': Color.YELLOW,
                    'clean': Color.GREEN}
    logger.info('{} {} {} {}'.format(result_color[result],
                                     result_emoji[result],
                                     result,
                                     Color.END))


def alert_obeya(on: bool, sound: bool) -> None:
    if on:
        notify_slack('汚部屋警報が発生しました')
        display_alert(on=True)

        if sound:
            # 警告BGMを流す
            se_path = str(Path(SOUND_ROOT_PATH) / "obeya_se.wav")
            hayaku_sound = pygame.mixer.Sound(se_path)
            hayaku_sound.play()
            bgm_path = str(Path(SOUND_ROOT_PATH) / "obeya_bgm.wav")
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.play(-1)

        upload_to_slack(str(Path(IMAGE_ROOT_PATH) / 'obeya_keihou.png'))
    else:
        notify_slack('汚部屋警報は解除されました')
        display_alert(on=False)

        if sound:
            # 警告BGMを止める
            pygame.mixer.music.stop()
            se_path = str(Path(SOUND_ROOT_PATH) / "clear.wav")
            clear_sound = pygame.mixer.Sound(se_path)
            clear_sound.play()


def display_alert(on: bool) -> None:
    if on:
        emoji, delimiter, n = '😱', '   ', 15
        message = '汚部屋警報発生'
        color = Color.PURPLE
    else:
        emoji, delimiter, n = '😄', '   ', 15
        message = '汚部屋警報は解除されました'
        color = Color.GREEN

    print(delimiter.join([emoji] * n))
    print(delimiter.join([emoji] * n))
    print('{}{}{}'.format(color, message, Color.END))
    print(delimiter.join([emoji] * n))
    print(delimiter.join([emoji] * n))


def check_expected_camera_id() -> int:
    n_camera = 2  # カメラの台数。環境によってここは変更すること

    for i in range(0, n_camera):
        cap = cv2.VideoCapture(i)
        image = cap.read()[1]

        logger.debug('camera {}: {}'.format(i, image.shape))

        # 想定しているUSBカメラで撮影しているかのチェック
        # 多分もっとよい方法はあると思うが、ここではカメラのサイズを見ている
        if image.shape == CAMERA_RAW_SIZE:
            cap.release()
            return i

        cap.release()
    else:
        message = 'Failed to capture. Not found an expected camera.'
        raise OheyaObeyaError(message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='capture.py',
                                     add_help=True)
    parser.add_argument('-a', '--alert',
                        help='指定した場合、アラート機能をONにします',
                        action='store_true')
    parser.add_argument('-s', '--sound',
                        help='指定した場合、音を鳴らします',
                        action='store_true')
    parser.add_argument('-i', '--save_image',
                        help='指定した場合、デモ中の連続画像を保存します',
                        action='store_true')
    args = parser.parse_args()

    logger.info('Start.')

    try:
        main(args.alert, args.sound, args.save_image)
    except OheyaObeyaError as e:
        import traceback
        traceback.print_exc()
        logger.error(e)

    logger.info('Completed.')
