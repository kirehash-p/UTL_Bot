import inspect
import logging
from functools import wraps
import traceback
import asyncio
import json
from typing import TypedDict

from module.log.log_handler import (
    ConsoleHandler,
    FileHandler,
    RotatingFileHandler,
    TimeRotatingFileHandler,
    SQLiteHandler,
    MariaDBHandler,
    DiscordHandler,
    SlackHandler,
)
from module.log.log_filter import DefaultFilter

log_level = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

class ConsoleConfig(TypedDict):
    alert_level: int

class FileConfig(TypedDict):
    alert_level: int
    file_path: str

class RotatingConfig(TypedDict):
    alert_level: int
    file_path: str
    max_bytes: int
    backup_count: int
    encoding: str
    delay: bool

class TimeRotatingConfig(TypedDict):
    alert_level: int
    file_path: str
    when: str
    interval: int
    backup_count: int
    encoding: str
    delay: bool
    utc: bool

class SQLiteDBConfig(TypedDict):
    db_path: str
    table: str

class SQLiteConfig(TypedDict):
    alert_level: int
    db_config: SQLiteDBConfig

class MariaDBDBConfig(TypedDict):
    host: str
    user: str
    password: str
    db: str
    port: int
    table: str

class MariaDBConfig(TypedDict):
    alert_level: int
    db_config: MariaDBDBConfig

class DiscordConfig(TypedDict):
    alert_level: int
    webhook_url: str
    username: str
    avatar_url: str

class SlackConfig(TypedDict):
    alert_level: int
    webhook_url: str
    service_name: str

class LogConfig(TypedDict):
    console: ConsoleConfig
    file: FileConfig
    rotating: RotatingConfig
    timed_rotating: TimeRotatingConfig
    sqlite: SQLiteConfig
    mariadb: MariaDBConfig
    discord: DiscordConfig
    slack: SlackConfig

template_config : LogConfig = {
    'console': { # コンソール画面に表示
        'alert_level': log_level['DEBUG'],
    },
    'file': { # ファイルに保存。consoleを有効化して標準出力をファイルにリダイレクトすることを推奨。
        'alert_level': log_level['INFO'],
        'file_path': 'log/log.log',
    },
    'rotating': { # ローテーションを設定してファイルに保存。
        'alert_level': log_level['DEBUG'],
        'file_path': 'log/log.log',
        'max_bytes': 1024 * 1024,
        'backup_count': 5,
        'encoding': None,
        'delay': False,
    },
    'timed_rotating': { # タイムドロテーションを設定してファイルに保存。
        'alert_level': log_level['DEBUG'],
        'file_path': 'log/log.log',
        'when': 'D',
        'interval': 1,
        'backup_count': 5,
        'encoding': None,
        'delay': False,
        'utc': False,
    },
    'sqlite': { # SQLiteに保存。非推奨。
        'alert_level': log_level['INFO'],
        'db_config': {
            'db_path': 'db/log.db',
            'table': 'logs',
        }
    },
    'mariadb': { # MariaDBに保存
        'alert_level': log_level['INFO'],
        'db_config': {
            'host': 'localhost',
            'user': 'user',
            'password': 'password',
            'db': 'db',
            'port': 3306,
            'table': 'logs',
        }
    },
    'discord': { # DiscordにWebhookを通して通知
        'alert_level': log_level['WARNING'],
        'webhook_url': '',
        'username': '',
        'avatar_url': '',
    },
    'slack': { # SlackにWebhookを通して通知
        'alert_level': log_level['WARNING'],
        'webhook_url': '',
        'service_name': '',
    }
}

def set_log_config(config):
    """ログの設定を作成。configがlistの場合はtemplate_configとkeyが一致した要素のみを返し、dictの場合は再帰的にマージしたものを返す

    Args:
        config (list or dict): ログの設定

    Returns:
        config (dict): ログの設定
    """

    def merge_dict(d1, d2):
        def recursive_update(d1, d2):
            for k, v in d1.items():
                if k in d2:
                    if isinstance(v, dict):
                        recursive_update(v, d2[k])
                    else:
                        d2[k] = v
            return d2

        def prune_dict(d1, d2):
            return {k: d2[k] for k in d1 if k in d2}
        
        return recursive_update(d1, prune_dict(d1, d2))
    
    default_config = template_config.copy()
    if isinstance(config, list):
        return {key: default_config[key] for key in config}
    elif isinstance(config, dict):
        return merge_dict(config, default_config)
    else:
        raise ValueError('config must be list or dict')


def get_logger(config: dict=template_config) -> logging.Logger:
    """Loggerの作成

    Returns:
        logger (logging.Logger): logging.Loggerのインスタンス
    """

    config = set_log_config(config)
    log_format = '[%(asctime)s] %(levelname)s\t%(real_filename)s - %(real_funcName)s:%(real_lineno)s -> %(message)s'
    logger = logging.getLogger(__name__)
    logger.addFilter(DefaultFilter())
    logger.setLevel(logging.DEBUG)

    if 'console' in config:
        console_handler = ConsoleHandler()
        console_handler.setLevel(config['console']['alert_level'])
        console_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console_handler)

    if 'file' in config:
        if not config['file']['file_path']:
            raise ValueError('file_path is required in config')
        file_handler = FileHandler(config['file']['file_path'])
        file_handler.setLevel(config['file']['alert_level'])
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)

    if 'rotating' in config:
        if not config['rotating']['file_path']:
            raise ValueError('file_path is required in config')
        rotating_handler = RotatingFileHandler(config['rotating']['file_path'], maxBytes=config['rotating']['max_bytes'], backupCount=config['rotating']['backup_count'],
                                                encoding=config['rotating']['encoding'], delay=config['rotating']['delay'])
        rotating_handler.setLevel(config['rotating']['alert_level'])
        rotating_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(rotating_handler)

    if 'timed_rotating' in config:
        if not config['timed_rotating']['file_path']:
            raise ValueError('file_path is required in config')
        timed_rotating_handler = TimeRotatingFileHandler(config['timed_rotating']['file_path'], when=config['timed_rotating']['when'],
                                interval=config['timed_rotating']['interval'], backupCount=config['timed_rotating']['backup_count'], 
                                encoding=config['timed_rotating']['encoding'], delay=config['timed_rotating']['delay'], utc=config['timed_rotating']['utc'])
        timed_rotating_handler.setLevel(config['timed_rotating']['alert_level'])
        timed_rotating_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(timed_rotating_handler)

    if 'sqlite' in config:
        sqlite_handler = SQLiteHandler(config['sqlite']['db_config'])
        sqlite_handler.setLevel(config['sqlite']['alert_level'])
        logger.addHandler(sqlite_handler)

    if 'mariadb' in config:
        mariadb_handler = MariaDBHandler(config['mariadb']['db_config'])
        mariadb_handler.setLevel(config['mariadb']['alert_level'])
        logger.addHandler(mariadb_handler)

    if 'discord' in config:
        discord_handler = DiscordHandler(config['discord'])
        discord_handler.setLevel(config['discord']['alert_level'])
        logger.addHandler(discord_handler)

    if 'slack' in config:
        slack_handler = SlackHandler(config['slack'])
        slack_handler.setLevel(config['slack']['alert_level'])
        logger.addHandler(slack_handler)

    return logger

def get_logger_from_json(json_path: str) -> logging.Logger:
    """jsonファイルから設定を読み込んでLoggerを作成

    Args:
        json_path (str): jsonファイルのパス

    Returns:
        logger (logging.Logger): logging.Loggerのインスタンス
    """

    with open(json_path, 'r') as f:
        config = json.load(f)
    return get_logger(config)

def log(logger: logging.Logger):
    """デコレーターでloggerを引数にとるためのラッパー関数

    Args:
        logger (logging.Logger)

    Returns:
        _decoratorの返り値
    """

    def _decorator(func):
        """デコレーターを使用する関数を引数とする

        Args:
            func (function)

        Returns:
            wrapperの返り値
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                """実際の処理を書くための関数

                Args:
                    *args, **kwargs: funcの引数

                Returns:
                    funcの返り値
                """

                func_name = func.__name__
                extra = {
                    'real_filename': inspect.getfile(func),
                    'real_funcName': func_name,
                    'real_lineno': inspect.currentframe().f_back.f_lineno
                }

                logger.info(f'[START] {func_name}', extra=extra)

                try:
                    res = await func(*args, **kwargs)
                except Exception as e:
                    exc_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    logger.error(exc_text, exc_info=False, extra=extra)
                    logger.info(f'[KILLED] {func_name}', extra=extra)
                else:
                    logger.info(f'[END] {func_name}', extra=extra)
                    return res
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                """実際の処理を書くための関数

                Args:
                    *args, **kwargs: funcの引数

                Returns:
                    funcの返り値
                """

                func_name = func.__name__
                extra = {
                    'real_filename': inspect.getfile(func),
                    'real_funcName': func_name,
                    'real_lineno': inspect.currentframe().f_back.f_lineno
                }

                logger.info(f'[START] {func_name}', extra=extra)

                try:
                    res = func(*args, **kwargs)
                except Exception as e:
                    exc_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    logger.error(exc_text, exc_info=False, extra=extra)
                    logger.info(f'[KILLED] {func_name}', extra=extra)
                else:
                    logger.info(f'[END] {func_name}', extra=extra)
                    return res

        return wrapper
    return _decorator

def log_exception(logger: logging.Logger):
    """例外をキャッチしてログに出力するデコレーター

    Args:
        logger (logging.Logger): ロガー

    Returns:
        _decoratorの返り値
    """

    def _decorator(func):
        """デコレーターを使用する関数を引数とする

        Args:
            func (function)

        Returns:
            wrapperの返り値
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                """実際の処理を書くための関数

                Args:
                    *args, **kwargs: funcの引数

                Returns:
                    funcの返り値
                """

                func_name = func.__name__
                extra = {
                    'real_filename': inspect.getfile(func),
                    'real_funcName': func_name,
                    'real_lineno': inspect.currentframe().f_back.f_lineno
                }

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    exc_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    logger.error(exc_text, exc_info=False, extra=extra)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                """実際の処理を書くための関数

                Args:
                    *args, **kwargs: funcの引数

                Returns:
                    funcの返り値
                """

                func_name = func.__name__
                extra = {
                    'real_filename': inspect.getfile(func),
                    'real_funcName': func_name,
                    'real_lineno': inspect.currentframe().f_back.f_lineno
                }

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    exc_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    logger.error(exc_text, exc_info=False, extra=extra)
        return wrapper
    return _decorator