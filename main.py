import threading

from module.scraper.google import spreadsheet
from module.log.log import log, log_exception

from logger_config import logger
from info_notify.info_main import main as info_main
from schedule_notify.schedule_main import main as schedule_main

@log(logger)
def main():
    # ./info_notify/main.py:main()と./schedule_notify/main.py:main()をそれぞれ実行する
    threads = []
    threads.append(threading.Thread(target=start_info_main))
    threads.append(threading.Thread(target=start_schedule_main))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

@log_exception(logger)
def start_info_main():
    info_main(logger)

@log_exception(logger)
def start_schedule_main():
    schedule_main(logger)

if __name__ == '__main__':
    main()