import sys
import threading
import logging
import traceback

from apscheduler.schedulers.background import BackgroundScheduler

from huaweisms.api.common import get_from_url_raw, check_error
from huaweisms.api.user import quick_login


# All of these endpoints return content type application/xml
from huaweisms.proxy import settings
from huaweisms.xml.util import parse_xml_string


logger = logging.getLogger("proxy_server")


END_POINTS = [
    "/api/device/signal",
    "/api/net/net-mode",
    "/api/net/current-plmn",
    "/api/device/information",
    "/api/monitoring/traffic-statistics",
]


class ModemData(object):
    """
    Very simple synchronised object
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}

    def set_data(self, key, value):
        with self._lock:
            self._data[key] = value

    def get_data(self, key):
        with self._lock:
            return self._data.get(key, None)

    def log_contents(self):
        with self._lock:
            for key, value in self._data.items():
                logger.debug("{key}={value}".format(key=key, value=value))


class ModemScraper(object):
    def __init__(self, modem_data):
        self._modem_data = modem_data
        self._ctx = None
        self._error_countdown = 0

    def run(self):

        try:

            # If we have detected an error, wait a bit before running again
            if self._error_countdown > 0:
                self._error_countdown -= 1
                return

            if self._ctx is None:
                # Log in required - This is all hard-coded
                self._ctx = quick_login(
                    settings.USERNAME, settings.PASSWORD, settings.MODEM_HOST
                )

            # Begin the scrape...
            for url in END_POINTS:
                result = get_from_url_raw(url=url, ctx=self._ctx)
                if result.status_code == 200:
                    text = result.text
                    xmldoc = parse_xml_string(text)
                    err = check_error(xmldoc.documentElement)

                    if err:
                        self._ctx = None
                        self._error_countdown = settings.ERROR_COUNTDOWN
                        logger.error("request error: {}".format(err))
                        break

                    # Everything is OK - store the result
                    self._modem_data.set_data(key=url, value=text)

        except Exception:
            # Don't blow up or it will break APScheduler
            logger.error("Error in scraper:\n{}".format(traceback.format_exc()))
        finally:
            self._modem_data.log_contents()


def setup_stdout_root_logger(level=logging.DEBUG):
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s t:%(threadName)s line:%(lineno)-4d %(levelname)-8s %(message)s"
    )
    ch.setFormatter(formatter)
    logging.root.addHandler(ch)
    logging.root.setLevel(level)


def main():
    setup_stdout_root_logger()

    modem_data = ModemData()
    scraper = ModemScraper(modem_data=modem_data)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scraper.run, "interval", seconds=2, coalesce=True, max_instances=1
    )

    try:
        scheduler.start()
    finally:
        scheduler.shutdown()


if __name__ == "__main__":

    main()
