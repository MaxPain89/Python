import argparse
import logging
from selenium.webdriver.remote.remote_connection import LOGGER
from time import sleep
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

XPATH_ACTIVE_HOSTNAMES_BTN_SELECTOR = '//*[@id="content-wrapper"]' \
                                      '/div/div[2]/div[1]/div[1]/' \
                                      'div[1]/div/div/div/div/div/span[2]'

XPATH_WINDOW_LOGIN_BTN_SELECTOR = '//*[@id="signin"]/form/button'

XPATH_PASSWORD_FIELD_SELECTOR = '//*[@id="signin"]/form/input[2]'

XPATH_USERNAME_FIELD_SELECTOR = '//*[@id="signin"]/form/input[1]'

XPATH_LOGIN_BTN_SELECTOR = '//*[@id="topnav"]/li[1]/a'

log = logging.getLogger(__name__)


def get_path(path):
    if path == "":
        final_path = os.path.join(os.path.curdir, "drivers", "chromedriver")
    elif os.path.isabs(path):
        final_path = path
    else:
        final_path = os.path.join(os.path.curdir, path)
    if os.path.isfile(final_path):
        return final_path
    else:
        raise Exception("Couldn't find webdriver")


def update(username, password, chromedriver):
    # configure logger
    LOGGER.setLevel(logging.WARNING)
    try:
        chrome_driver_path = get_path(chromedriver)
        log.info("Find driver %s", chrome_driver_path)
        log.info("Initializing selenium chrome webdriver...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(executable_path=chrome_driver_path,
                                  options=chrome_options)
        log.info("Done.")

        main_page_url = "https://www.noip.com/"
        log.info("Getting main page %s", main_page_url)
        driver.get(main_page_url)

        log.info("Done.")

        log.info("Getting login button...")
        login_btn = driver.find_element_by_xpath(XPATH_LOGIN_BTN_SELECTOR)
        log.info("Done")

        log.info("Click to login button...")
        login_btn.click()
        log.info("Done")

        sleep(2)
        log.info("Enter login...")
        username_field = driver.find_element_by_xpath(
            XPATH_USERNAME_FIELD_SELECTOR)
        username_field.send_keys(username)
        log.info("Done")
        sleep(2)

        log.info("Enter password...")
        password_field = driver.find_element_by_xpath(
            XPATH_PASSWORD_FIELD_SELECTOR)
        password_field.send_keys(password)
        log.info("Done")
        sleep(2)

        log.info("Click to login button...")
        login_btn_in_window = driver.find_element_by_xpath(
            XPATH_WINDOW_LOGIN_BTN_SELECTOR)
        login_btn_in_window.click()
        log.info("Done")
        sleep(2)

        log.info("Click to active button...")
        active_btn = driver.find_element_by_xpath(
            XPATH_ACTIVE_HOSTNAMES_BTN_SELECTOR)
        active_btn.click()
        log.info("Done")
        sleep(2)

        log.info("Click to active button...")
        confirm_btn = driver.find_element_by_xpath(
            '//*[@id="host-panel"]/table/tbody/tr/td[5]/button')
        log.info("Done")
        # check text
        text = confirm_btn.text
        if text == "Confirm":
            log.info("Found")
            return True
    except Exception as e:
        log.error("Something went wrong. Err: %s", str(e))

    return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        description='Confirm expired no-ip address')
    parser.add_argument('-u', '--username', type=str,
                        help='username/email of no-ip account')
    parser.add_argument('-p', '--password', type=str,
                        help='password of no-ip account')
    parser.add_argument('--chromedriver', type=str, default="",
                        help='path to chrome driver')
    args = parser.parse_args()
    update(args.username, args.password, args.chromedriver)
