import argparse
from pathlib import Path
import time
import logging

import cv2
import pygame.mixer

from secret import settings
from app_exception import OheyaObeyaError
from color import Color
from notifier import notify_slack, upload_to_slack
from predict import classify

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


def main(sound: bool) -> None:

    if sound:
        if not Path(SOUND_ROOT_PATH).exists():
            raise OheyaObeyaError('音源フォルダが見つかりません。(再配布不可の音源を使用しているため、GitHub上に音源ファイルは置いていません。使用する場合は、自身で用意してください)')
        pygame.mixer.init()

        # 実際には以下のサイトから素材を借りた
        # 効果音ラボ: https://soundeffect-lab.info/sound/button/
        # ※ 再配布不可なのでGitHub上には音源ファイルはuploadしていない
        #   使用する際は指定のパスに適当な音源を配置すること
        pygame.mixer.music.load(str(Path(SOUND_ROOT_PATH) / 'start.mp3'))
        pygame.mixer.music.play(1)

    camera_id = check_expected_camera_id()

    messy_flag = False
    messy_count = 0
    not_messy_count = 0
    cap = cv2.VideoCapture(camera_id)

    while True:
        # Capture
        image = cap.read()[1]
        path = Path('now.jpg')  # TODO: 保存モード/保存しないモードを用意する
        cv2.imwrite(str(path), image)

        # Predict
        result_dict = classify(path)
        display_prediction_result(result_dict)
        result = result_dict['prediction']

        # 汚部屋状態に切り替わったかどうかを判定
        # TODO: 連続した回数ではなく、過去n回分のm%分で判断させる
        if result == 'messy':
            messy_count += 1
            not_messy_count = 0
            logger.debug('messy_count = {}'.format(messy_count))
        else:
            not_messy_count += 1
            messy_count = 0
            logger.debug('not_messy_count = {}'.format(not_messy_count))

        if messy_count > 10 and not messy_flag:
            messy_flag = True
            alert_obeya(on=True, sound=sound)
        elif not_messy_count > 10 and messy_flag:
            messy_flag = False
            alert_obeya(on=False, sound=sound)

    cap.release()


def display_prediction_result(result_dict: dict) -> None:
    logger.debug(result_dict)
    result = result_dict['prediction']
    result_emoji = {'messy': '😱',
                    'so-so': '🤔',
                    'clean': '✨'}
    result_color = {'messy':
                    Color.PURPLE,
                    'so-so': Color.YELLOW,
                    'clean': Color.GREEN}
    logger.info('{} {} {} {}'.format(result_color[result],
                                     result_emoji[result],
                                     result,
                                     Color.END))


def alert_obeya(on: bool, sound: bool) -> None:
    if on:
        if sound:
            se_path = str(Path(SOUND_ROOT_PATH) / "obeya_se.wav")
            hayaku_sound = pygame.mixer.Sound(se_path)
            hayaku_sound.play()
            bgm_path = str(Path(SOUND_ROOT_PATH) / "obeya_bgm.wav")
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.play(-1)

        notify_slack('汚部屋警報が発生しました')
        display_alert(on=True)
        upload_to_slack(str(Path(IMAGE_ROOT_PATH) / 'obeya_keihou.png'))
    else:
        notify_slack('汚部屋警報は解除されました')
        display_alert(on=False)

        if sound:
            # 警告BGMを止める
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(Path(SOUND_ROOT_PATH) / "clear.mp3"))
            pygame.mixer.music.play(-1)
            time.sleep(2)
            pygame.mixer.music.stop()


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
    parser.add_argument('-s', '--sound',
                        help='指定した場合、音を鳴らします',
                        action='store_true')
    args = parser.parse_args()

    logger.info('Start.')

    try:
        main(args.sound)
    except OheyaObeyaError as e:
        import traceback
        traceback.print_exc()
        logger.error(e)

    logger.info('Completed.')
