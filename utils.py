from datetime import datetime

import pytz


def agora_sp():
    tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(tz)