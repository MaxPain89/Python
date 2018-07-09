import argparse
import logging
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By


import yaml
import os
import requests

from selenium import webdriver

MAIN_PAGE_URL = "https://www.noip.com/"

XPATH_CAPCHA_FRAME_SELECTOR = '//*[@id="recaptcha_block"]/div/div/div/iframe'

XPATH_CONFIRM_BUTTON = '//*[@id="host-panel"]/table/tbody/tr/td[5]/button'

XPATH_ACTIVE_HOSTNAMES_BTN_SELECTOR = '//*[@id="content-wrapper"]' \
                                      '/div/div[2]/div[1]/div[1]' \
                                      '/div[1]/div/div/div/div/div/span[2]'

XPATH_WINDOW_LOGIN_BTN_SELECTOR = '//*[@id="signin"]/form/button'

XPATH_PASSWORD_FIELD_SELECTOR = '//*[@id="signin"]/form/input[2]'

XPATH_USERNAME_FIELD_SELECTOR = '//*[@id="signin"]/form/input[1]'

XPATH_LOGIN_BTN_SELECTOR = '//*[@id="topnav"]/li[1]/a'

XPATH_CAPCHA_CHECK_SELECTOR = '//*[@id="recaptcha-anchor"]/div[5]'

XPATH_FINAL_ACCEPT_BTN_SELECTOR = '//*[@id="content"]/section[3]' \
                                  '/div/div/div[1]/p[2]/a[2]'

XPATH_EXPIRES_LABEL = '//*[@id="host-panel"]/table/tbody/tr/td[1]' \
                      '/div/span/span/div'

EXPIRES_LABEL_PREFIX = 'Expires in '
EXPIRED_LABEL_PREFIX = 'Expired'
# sms.ru constants
SMS_TEMPLATE = "Your no-ip hostname expires in %d days"
SMS_API_URL = "https://sms.ru/sms/send"

log = logging.getLogger(__name__)


class Config:
    def __init__(self, config_dict):
        self.threshold = config_dict["threshold"]
        self.username = config_dict["no_ip"]["username"]
        self.password = config_dict["no_ip"]["password"]
        self.path_to_driver = config_dict["driver"]["path"]
        self.api_id = config_dict["sms.ru"]["api_id"]
        self.phone_number = config_dict["sms.ru"]["phone_number"]


class Checker:
    def __init__(self):
        self.driver = None
        self.waiter = None
        self.username = None
        self.password = None
        self.display = None

    def configure(self, conf):
        self.driver = self._get_driver(conf.path_to_driver)
        self.driver.set_window_size(1600, 1200)
        self.username = conf.username
        self.password = conf.password
        self.waiter = self._get_waiter(self.driver)

    @staticmethod
    def _get_driver(driver_path):
        log.info("Initializing selenium PhantomJS web driver...")
        return webdriver.PhantomJS(executable_path=driver_path)

    @staticmethod
    def _get_waiter(driver, timeout=30):
        return WebDriverWait(driver, timeout=timeout)

    def _click_and_expect_element(self, clickable_elem_selector,
                                  expected_elem_selector=None):
        element = self.driver.find_element_by_xpath(clickable_elem_selector)
        element.click()
        if expected_elem_selector:
            self.waiter.until(ec.visibility_of_element_located(
                (By.XPATH, expected_elem_selector)))

    def _fill_filed(self, field_selector, value):
        field = self.driver.find_element_by_xpath(
            field_selector)
        field.send_keys(value)

    def _get_main_page(self):
        log.info("Getting main page %s", MAIN_PAGE_URL)
        self.driver.get(MAIN_PAGE_URL)

        self.waiter.until(ec.visibility_of_element_located(
            (By.XPATH, XPATH_LOGIN_BTN_SELECTOR)))
        log.info("Done.")

    def _login(self):
        log.info("click to login login button...")
        self._click_and_expect_element(XPATH_LOGIN_BTN_SELECTOR,
                                       XPATH_USERNAME_FIELD_SELECTOR)
        log.info("Enter credentials...")
        self._fill_filed(XPATH_USERNAME_FIELD_SELECTOR, self.username)
        self._fill_filed(XPATH_PASSWORD_FIELD_SELECTOR, self.password)
        self._click_and_expect_element(XPATH_WINDOW_LOGIN_BTN_SELECTOR,
                                       XPATH_ACTIVE_HOSTNAMES_BTN_SELECTOR)

    def _open_hostname_section(self):
        log.info("Check hostnames...")
        self._click_and_expect_element(XPATH_ACTIVE_HOSTNAMES_BTN_SELECTOR,
                                       XPATH_EXPIRES_LABEL)

    def _get_expiration(self):
        log.info("Getting expiration...")
        expiration_label = self.driver.find_element_by_xpath(
            XPATH_EXPIRES_LABEL)
        # check text
        text = expiration_label.text
        if text.startswith(EXPIRES_LABEL_PREFIX):
            log.info("Found: %s", text)
            return int(text.split(" ")[2])
        elif text.startswith(EXPIRED_LABEL_PREFIX):
            log.info("Found: %s", text)
            return 0
        else:
            return -1

    def _close_browser(self):
        self.driver.quit()

    def check_expiration(self):
        try:
            self._get_main_page()
            self._login()
            self._open_hostname_section()
            return self._get_expiration()
        except Exception as e:
            log.error("Something went wrong. Err: %s", str(e))
            return -1
        finally:
            self._close_browser()


def get_path(path):
    if path == "":
        final_path = os.path.join(os.path.curdir, "drivers", "phantomjs")
    elif os.path.isabs(path):
        final_path = path
    else:
        final_path = os.path.join(os.path.curdir, path)
    if os.path.isfile(final_path):
        return final_path
    else:
        raise Exception("Couldn't find web driver")


def send_notification(api_id, phone_number, message):
    log.info("Send sms notification")
    payload = (('api_id', api_id), ('to', phone_number), ('msg', message))
    response = requests.get(SMS_API_URL, params=payload)
    response.raise_for_status()
    log.info("The notification was sent")


def parse_config(path_to_config):
    with open(path_to_config, 'r') as stream:
        return yaml.load(stream)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        description='Confirm expired no-ip address')
    parser.add_argument('-u', '--username', type=str,
                        help='username/email of no-ip account')
    parser.add_argument('-p', '--password', type=str,
                        help='password of no-ip account')
    parser.add_argument('--webdriver', type=str, default="",
                        help='path to web driver')
    parser.add_argument('--api_id', type=str, default="",
                        help='api_id for notifications')
    parser.add_argument('--phone_number', type=str, default="",
                        help='phone number for notifications')
    parser.add_argument('-c', '--config', type=str, required=True,
                        help='path to config')
    args = parser.parse_args()
    # configure web driver logger
    LOGGER.setLevel(logging.WARNING)
    config = Config(parse_config(args.config))
    checker = Checker()
    checker.configure(config)
    expiration = checker.check_expiration()
    log.info("Expiration : %s days", expiration)
    if config.threshold > expiration >= 0:
        log.info("Expiration less then threshold. Send sms notification.")
        send_notification(api_id=config.api_id,
                          phone_number=config.phone_number,
                          message=SMS_TEMPLATE % expiration)
