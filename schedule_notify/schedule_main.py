import sys
import os
import time
import json
import requests

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from module.scraper.google import spreadsheet
from module.bot.bot_line import Bot_Line
from module.mytime import mytime

import data_operation

# schedule_commmand = '/schedule'

def get_schedule(data, day) -> data_operation.ScheduleData:
    day = mytime.interpret_day(day)
    if day == '':
        day = mytime.now_day_str()
    return data_operation.search(data, day), day

class SNLineBot(Bot_Line):
    def __init__(self, jsonfile=None, ss=None):
        super().__init__(jsonfile)
        self.ss = ss

    def create_schedule_message(self, schedule_data: data_operation.ScheduleData, searched_date: str) -> str:
        """予定情報をメッセージに整形する"""
        if not schedule_data:
            return f"{searched_date}の予定はありません"
        else:
            message = f"{searched_date}のスケジュール"
            if schedule_data['schedule_names'] != ['']:
                for i in range(len(schedule_data['schedule_names'])):
                    message += f"\n\n・{schedule_data['schedule_names'][i]}"
                    if schedule_data['schedule_places']:
                        message += f"\n 場所：{schedule_data['schedule_places'][i]}" if schedule_data['schedule_places'][i] else ""
                    if schedule_data['schedule_dates']:
                        message += f" \n 時間：{schedule_data['schedule_dates'][i]}" if schedule_data['schedule_dates'][i] else ""
                    if schedule_data['schedule_remarks']:
                        message += f"\n 備考：{schedule_data['schedule_remarks'][i]}" if schedule_data['schedule_remarks'][i] else ""
            if schedule_data['messages']:
                message += f"\n\n{schedule_data['messages']}"
            return message

    def send_schedule_message(self, search_date):
        data = data_operation.get_data(self.ss)
        schedule_data, searched_date = get_schedule(data, search_date)
        if not schedule_data or (schedule_data['schedule_names'] == [''] and schedule_data['messages'] == ''):
            return False # 予定がない場合は何もしない
        message = self.create_schedule_message(schedule_data, searched_date)
        if self.variable['line_notify_token']:
            ln_url = 'https://notify-api.line.me/api/notify'
            headers = {'Authorization': f'Bearer {self.variable["line_notify_token"]}'}
            payload = {'message': message}
            requests.post(ln_url, headers=headers, data=payload, timeout=60)
        else:
            for group_id in self.variable['notify_groups']:
                self.send_message_by_id(group_id, message)
        return True

def try_several_times(func: callable, n: int=3, logger=None, *args, **kwargs):
    """関数実行をn回を上限に試行する"""
    for i in range(n):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i < n-1:
                logger and logger.warning(f"f{func.__name__} failed for {i+1} times: {e}")
                time.sleep(5)
            else:
                logger and logger.error(f"f{func.__name__} failed for {n} times: {e}")
    return None

def main(logger=None):
    """スケジュール情報を取得し、LINEに通知するメイン関数"""

    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, '../conf/conf_etc.json')) as f:
        conf = json.load(f)

    notify_time = conf['schedule_notify_time']
    logger and logger.info(f"schedule_notify_time: {notify_time}")

    ss = spreadsheet.get_spread_sheet(os.path.join(base_path, '../conf/google_api_credential.json'), conf['schedule_sheet_key'])
    linebot = SNLineBot(jsonfile=os.path.join(base_path, '../conf/line_bot_config.json'), ss=ss)

    while True:
        # スプレッドシートの整理
        logger and logger.debug('arranging schedule data')
        try_several_times(data_operation.auto_arrange, 3, logger, ss, conf['schedule_margin'])

        # 次のスケジュール通知時間まで待機
        wait_time = mytime.get_diff_minute(notify_time)
        time.sleep(wait_time)

        # 予定を取得して通知
        logger and logger.debug('executing schedule notify')
        search_date = mytime.now_day_str()
        try_several_times(linebot.send_schedule_message, 3, logger, search_date)

        # 1分待機
        time.sleep(60)

if __name__ == '__main__':
    main()
