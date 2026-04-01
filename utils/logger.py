import datetime
import threading


class Logger:
    LEVELS = {
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40
    }

    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',  # Bright green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',  # Red
    }

    PREFIX_COLOR = '\033[96m'
    RESET_COLOR = '\033[0m'

    def __init__(self, level='DEBUG'):
        self.level = self.LEVELS.get(level.upper(), 10)
        self._lock = threading.Lock()  # Lock for thread-safety

    def _log(self, level, message, prefix=''):
        if self.LEVELS[level] >= self.level:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            color = self.COLORS.get(level, '')
            p = f'{self.PREFIX_COLOR}{prefix}:{self.RESET_COLOR} ' if prefix else ''
            with self._lock:
                print(f'{timestamp} {color}[{level}] {p}{self.RESET_COLOR}{message}', flush=True)

    def debug(self, message, prefix=''):
        self._log('DEBUG', message, prefix)

    def info(self, message, prefix=''):
        self._log('INFO', message, prefix)

    def warning(self, message, prefix=''):
        self._log('WARNING', message, prefix)

    def error(self, message, prefix=''):
        self._log('ERROR', message, prefix)


# Global instance named `logger`
logger = Logger('DEBUG')
