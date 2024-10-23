import sys
import os
from urllib.parse import urljoin
from typing import List, TypedDict
import json
import time
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from module.sql import sqlite
from module.scraper.google import spreadsheet
from module.bot.bot_line import Bot_Line
from module.mytime import mytime

class InfoDict(TypedDict):
    date: str
    info: str
    url: str

sqlite_db_path = os.path.join(os.path.dirname(__file__), 'info_notify.db')
sqlite_table_name = 'literature_info'
sqlite_columns = [
    ('date', 'TEXT'),
    ('info', 'TEXT'),
    ('url', 'TEXT'),
    ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
]

class INLineBot(Bot_Line):
    """お知らせ情報をLINEに通知するクラス"""

    def __init__(self, jsonfile=None):
        super().__init__(jsonfile)

    def create_info_message(self, info_list: InfoDict) -> str:
        """お知らせ情報をメッセージに整形する"""
        if not info_list:
            return "新しいお知らせはありません"
        else:
            message = "新しいお知らせがあります\n"
            message += "\n".join([f"\n・{info['info']} ({info['date']})\n{info['url']}" for info in info_list])
            return message

    def send_info_message(self, info_list: InfoDict):
        """お知らせ情報をLINEに送信する"""
        message = self.create_info_message(info_list)
        if self.variable['line_notify_token']:
            ln_url = 'https://notify-api.line.me/api/notify'
            headers = {'Authorization': f'Bearer {self.variable["line_notify_token"]}'}
            payload = {'message': message}
            requests.post(ln_url, headers=headers, data=payload, timeout=60)
        else:
            for group_id in self.variable['notify_groups']:
                self.send_message_by_id(group_id, message)
        return True

def get_info_list(url: str) -> List[InfoDict]:
    """URLからお知らせ情報のリストを取得する"""
    # ページを取得し、BeautifulSoupでパース
    response = requests.get(url, timeout=60)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')

    info_list = []

    # div class="textLinkList"内の<dt>と<dd>を取得
    for item in soup.select('div.textLinkList'):
        dts = item.find_all('dt')
        dds = item.find_all('dd')

        for dt, dd in zip(dts, dds):
            date_text = dt.get_text(strip=True)
            info_text = dd.find('a').get_text(strip=True)
            info_url = dd.find('a').get('href')
            info_url = urljoin(url, info_url) # サイト内リンクを絶対URLに変換
            info_list.append({
                'date': date_text,
                'info': info_text,
                'url': info_url
            })

    return info_list

def compare_diff(old_info_list: List[InfoDict], new_info_list: List[InfoDict]) -> List[InfoDict]:
    """古いお知らせ情報と新しいお知らせ情報を比較し、新しいお知らせ情報のみを取得する"""
    diff_info_list = []
    for new in new_info_list:
        if new not in old_info_list:
            diff_info_list.append(new)
    return diff_info_list

def main(logger=None):
    """お知らせ情報を取得し、LINEに通知するメイン関数"""

    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, '../conf/conf_etc.json'), 'r') as f:
        conf = json.load(f)
    notify_time = conf['info_notify_time']
    if logger:
        logger.info(f'info_notify_time: {notify_time}')
    linebot = INLineBot(jsonfile=os.path.join(base_path, '../conf/line_bot_config.json'))

    # SQLiteに接続し、テーブルがない場合は作成
    db = sqlite.Sqlite({'db_path': sqlite_db_path})
    db.create_table(sqlite_table_name, sqlite_columns)

    url = conf['info_notify_url']

    # データベースを最新の状態に更新
    new_info_list = get_info_list(url)
    current_info_list = [{'date': info[0], 'info': info[1], 'url': info[2]} for info in db.execute(f'SELECT * FROM {sqlite_table_name}')]
    diff_info_list = compare_diff(current_info_list, new_info_list)
    for info in diff_info_list:
        db.insert(sqlite_table_name, ['date', 'info', 'url'], [info['date'], info['info'], info['url']])

    while True:
        # 次のお知らせ通知時刻まで待機
        wait_time = mytime.get_diff_minute(notify_time)
        time.sleep(wait_time)

        # お知らせ情報を取得
        logger and logger.debug('Getting new information..')
        new_info_list = get_info_list(url)

        # 既存のお知らせ情報を取得
        old_info_list = db.execute(f'SELECT * FROM {sqlite_table_name}')
        old_info_list = [{'date': info[0], 'info': info[1], 'url': info[2]} for info in old_info_list]

        # お知らせ情報の差分を取得
        diff_info_list = compare_diff(old_info_list, new_info_list)

        # 差分がある場合
        if diff_info_list:
            # LINEに通知
            logger and logger.info('Send new information to LINE..')
            linebot.send_info_message(diff_info_list)

            # 差分をDBに挿入
            logger and logger.debug('Insert new information to DB..')
            for info in diff_info_list:
                db.insert(sqlite_table_name, ['date', 'info', 'url'], [info['date'], info['info'], info['url']])

        # 1分待機
        time.sleep(60)


if __name__ == '__main__':
    main()
