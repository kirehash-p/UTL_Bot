import json

# conf/log_var_config.jsonから設定を読み込む
with open('conf/log_var_config.json', 'r') as f:
    log_var = json.load(f)

from module.log.log import get_logger, log_level, LogConfig

log_config : LogConfig = {
    'console': {
        'alert_level': log_level['DEBUG'],
    },
    'timed_rotating': {
        'file_path': 'log/utl_bot.txt',
        'when': 'D',
        'interval': 1,
        'backup_count': 7,
        'alert_level': log_level['DEBUG'],
    },
    "discord": {
        "alert_level": log_var["discord"].get("alert_level", "WARNING"),
        "webhook_url": log_var["discord"].get("webhook"),
        "username": log_var["discord"].get("username", "UTL_Bot"),
    },
    "slack": {
        "alert_level": log_var["slack"].get("alert_level", "INFO"),
        "webhook_url": log_var["slack"].get("webhook"),
        "service_name": "UTL_Bot",
    },
}

logger = get_logger(log_config)
