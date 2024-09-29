from typing import TypedDict

from module.mytime import mytime

class ScheduleData(TypedDict):
    schedule_names: list[str]
    schedule_places: list[str]
    schedule_dates: list[str]
    schedule_remarks: list[str]
    messages: str

# 多次元リストを一次元化する再帰処理。
flatten = lambda x: [z for y in x for z in (flatten(y) if hasattr(y, '__iter__') and not isinstance(y, str) else (y,))]

# Googleスプレッドシートに接続し、予定表のデータ(1枚目)とbotのセリフのフォーマット(2枚目)のシートを読み込む。
def get_data(ss) -> list[list[str]]:
    data = ss.get_worksheet(0).get_all_values()
    return data

# Googleスプレッドシートに接続して指定日時分先までの日付をシートに自動で記入し、不要になったリマインドの履歴を別シートにアーカイブする。
def auto_arrange(ss, margin: int):
    data_sheet, archive_sheet = ss.get_worksheet(0), ss.get_worksheet(1)
    data = data_sheet.get_all_values()[3:] # 3行目以降に日付と予定が記入されている。
    del_idx_list = []
    insert_list = []
    for i in range(len(data)):
        if mytime.if_date_before_today(data[i][0]):
            del_idx_list.append(i)
            insert_list.append(list(map(lambda x: str(x), flatten(data[i]))))
    insert_list = insert_list[::-1]
    for i in reversed(del_idx_list):
        del data[i]
    for i in range(len(data)):
        data[i] = list(map(lambda x: str(x), flatten(data[i])))
    
    # 指定日時分先までの日付がなかった場合付け足す。高速化の余地あり。めんどいのでやらん。
    for i in range(margin):
        found = False
        for j in range(len(data)):
            if data[j][0] == mytime.future_date(i):
                found = True
                break
        if not found:
            data.append([mytime.future_date(i)]+[""]*(len(data[0])-1))
    data = sorted(data, key=lambda x: x[0]) # 日付順にソート
    data_sheet.update("A4", data)
    archive_sheet.insert_rows(insert_list, row=1)
    return

# データの中から引数で指定された日時の活動場所やイベントなどをリスト形式で返す。
def search(data, day) -> ScheduleData:
    for i in range(3, len(data)):
        if data[i][0] == day:
            Y = i
            break
    else:
        return None # 指定された日付が見つからなかった場合
    X = 1
    schedule_names = data[Y][X].replace('、',',').split(',')
    schedule_places = data[Y][X+1].replace('、',',').split(',') if data[Y][X+1] else []
    schedule_places.extend(['']*(len(schedule_names)-len(schedule_places)))
    schedule_dates = data[Y][X+2].replace('、',',').split(',') if data[Y][X+2] else []
    schedule_dates.extend(['']*(len(schedule_names)-len(schedule_dates)))
    schedule_remarks = data[Y][X+3].split(',') if data[Y][X+2] else []
    schedule_remarks.extend(['']*(len(schedule_names)-len(schedule_remarks)))
    messages = data[Y][X+4] if data[Y][X+4] else ""
    res = {
        "schedule_names": schedule_names,
        "schedule_places": schedule_places,
        "schedule_dates": schedule_dates,
        "schedule_remarks": schedule_remarks,
        "messages": messages
    }
    return res

