# -*- coding: utf-8 -*-
import scrapy
from taobao.items import TaobaoItem
import logging
from scrapy.utils.log import configure_logging
import redis
import time
import datetime
import os
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from taobao import utils
import ast
from taobao import settings
from xvfbwrapper import Xvfb
import platform
import base64
import threading
# import sys

# reload(sys)
# sys.setdefaultencoding('utf8')
configure_logging(install_root_handler=False)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=time.strftime("log/%Y%m%d%H%M%S")+".log",
                    filemode='w')


class TaobaommSpider(scrapy.Spider):
    name = "taobao"
    #allowed_domains = ["mm.taobao.com"]
    start_urls = (
        "https://mm.taobao.com/json/request_top_list.htm?page=",
    )
    pageindex = 1
    r = redis.StrictRedis(host=settings.REDIS_HOST, port=6379, db=0)
    r_local = redis.StrictRedis(
        host=utils.get_external_ip(), port=settings.REDIS_LOCAL_PORT, db=0)
    driver = None

    def __init__(self):
        logging.info("initiating crawler...")
        self.crawler_id = self.get_crawler_id()
        logging.info("crawler id is %s" % self.crawler_id)
        self.r.set('crawler:ip:%s' % self.crawler_id, utils.get_external_ip())
        self.r.set('crawler:port:%s' %
                   self.crawler_id, settings.REDIS_LOCAL_PORT)
        logging.info("crawler ip is %s" % utils.get_external_ip())
        account = self.get_account()
        self.username = account[0]
        self.password = account[1]
        logging.info("crawler account got")
        self.r_local.set('crawler:status:%s' % self.crawler_id, 'good')
        self.r_local.set('crawler:update_time:%s' %
                         self.crawler_id, datetime.datetime.utcnow().strftime("%s"))
        logging.info("local crawler status set")
        heartbeat_thread = threading.Thread(
            target=self.maintain_local_heartbeat)
        heartbeat_thread.start()
        logging.info("local crawler heartbeat started")
        # 使用xvfb + webdriver.Chrome作为headless browser
        # 解析的时候比较耗cpu，但是稳定
        # if platform.system() == "Linux":
        #     vdisplay = Xvfb()
        #     vdisplay.start()
        # co = ChromeOptions()
        # co.add_experimental_option(
        #     "prefs", {"profile.default_content_settings": {"popups": 1}})
        # self.driver = webdriver.Chrome(chrome_options=co)

        # 或者使用webdriver.PhantomJS作为headless browser，一定要加下面的参数，否则PhantomJS very slowly
        # 解析的时候耗cpu较低，但是有时候会没响应
        service_args = ['--load-images=false', '--disk-cache=true']
        self.driver = webdriver.PhantomJS(
            executable_path='/usr/bin/phantomjs',
            service_args=service_args)
        self.driver.set_window_size(640, 960)

    def get_crawler_id(self):
        while True:
            crawler_id = base64.standard_b64encode(
                datetime.datetime.utcnow().strftime("%s"))
            if self.r.sadd('crawler_id_set', crawler_id):
                return crawler_id

    def get_account(self):
        while True:
            account = self.r.spop('account_set')
            if account:
                self.r.set('crawler_account:%s' % self.crawler_id, account)
                return ast.literal_eval(account)
            time.sleep(settings.QUERY_INTERVAL)

    def maintain_local_heartbeat(self):
        while True:
            try:
                self.r_local.set('crawler:heartbeat:%s' %
                                 self.crawler_id, time.time())
                time.sleep(settings.CRAWLER_HEARTBEAT_INTERVAL)
            except:
                logging.error("heartbeat failed")
                break

    def start_requests(self):
        self.driver.get(settings.LOGIN_PAGE)
        time.sleep(5)
        u = self.driver.find_element_by_id("TPL_username_1")
        time.sleep(1)
        u.clear()
        u.send_keys(self.username)
        p = self.driver.find_element_by_id("TPL_password_1")
        time.sleep(1)
        p.clear()
        p.send_keys(self.password)
        self.driver.find_element_by_id("J_SubmitStatic").click()
        time.sleep(2)
        # print self.driver.current_url
        time.sleep(settings.UNTRACABLE_REQUEST_WAIT)

        if self.driver.current_url == settings.LOGIN_PAGE:
            # try to input captcha
            logging.error("login failed, investigating...")
            login_attempt = 0
            while login_attempt < settings.LOGIN_RETRY + 1:
                # wait for captcha input
                self.r_local.delete('captcha:%s' % self.crawler_id)
                self.r_local.delete('captcha_input:%s' % self.crawler_id)
                self.r_local.set('crawler:status:%s' %
                                 self.crawler_id, 'captcha_input')
                if settings.DEBUG_INFO:
                    logging.info(
                        "wait for captcha input...")
                while True:
                    captcha = self.driver.find_element_by_id('J_CodeInput_i')
                    if self.r_local.get('crawler:status:%s' % self.crawler_id) == 'captcha_snapshot':
                        self.r_local.set(
                            'captcha:%s' % self.crawler_id, self.driver.get_screenshot_as_png())
                        if settings.DEBUG_INFO:
                            logging.info(
                                "captcha for %s taken" % self.crawler_id)
                        while True:
                            # check input
                            captcha_input = self.r_local.get(
                                'captcha_input:%s' % self.crawler_id)
                            if captcha_input:
                                captcha.clear()
                                captcha.send_keys(captcha_input)
                                captcha.submit()
                                if settings.DEBUG_INFO:
                                    logging.info(
                                        "captcha input for %s submitted" % self.crawler_id)
                                time.sleep(
                                    settings.UNTRACABLE_REQUEST_WAIT)
                                break
                            time.sleep(settings.CAPTCHA_CHECK_INTERVAL)
                        break
                    time.sleep(settings.CAPTCHA_CHECK_INTERVAL)
                # 验证码输入错误
                if self.driver.current_url == settings.LOGIN_PAGE:
                    logging.error("login failed, retry...")
                    self.r_local.set('crawler:status:%s' %
                                     self.crawler_id, 'captcha_input')
                    self.r_local.set(
                        'crawler:update_time:%s' % self.crawler_id, datetime.datetime.utcnow().strftime("%s"))
                    # 如果验证码输入失败，密码也需要重新输入
                    p = self.driver.find_element_by_id("TPL_password_1")
                    p.clear()
                    p.send_keys(self.password)
                else:
                    self.r_local.set('crawler:status:%s' %
                                     self.crawler_id, 'good')
                    self.r_local.set(
                        'crawler:update_time:%s' % self.crawler_id, datetime.datetime.utcnow().strftime("%s"))
                    break
                login_attempt += 1
            if login_attempt >= settings.LOGIN_RETRY + 1:
                logging.error("login failed, exit...")
                return

        if settings.DEBUG_INFO:
            logging.info("logged in")
        logging.info("start crawling...")
        return [scrapy.Request(self.start_urls[0] + str(self.pageindex), meta={'driver': self.driver, 'PhantomJS': True})]

    def parse(self, response):
        for sel in response.xpath('//div[@class="list-item"]'):
            try:
                # 有些页面不标准，没有mm姓名
                name = sel.xpath(
                    './/a[@class="lady-name"]/text()').extract()[0]
                print u'美眉姓名：', name
                self.mkdir('images/full/%s' % (name))
                item = TaobaoItem()
                item['mm_name'] = name
                href = sel.xpath('.//a[@class="lady-avatar"]/@href').extract()
                url = response.urljoin(href[0])
                yield scrapy.Request(url,
                                     meta={
                                         'driver': response.meta['driver'],
                                         'PhantomJS': response.meta['PhantomJS'],
                                         #'cookiejar': response.meta['cookiejar'],
                                         'item': item},
                                     callback=self.parse_mm_page)
                print u'去美眉图片页抓图：scheduling', url
            except:
                # 跳过这个mm，继续下一个
                continue
        # request next page
        self.pageindex += 1
        next_page = self.start_urls[0] + str(self.pageindex)
        yield scrapy.Request(next_page,
                             meta={
                                 'driver': response.meta['driver'],
                                 'PhantomJS': response.meta['PhantomJS'],
                                 #'cookiejar': response.meta['cookiejar']
                             },
                             callback=self.parse)

    def parse_mm_page(self, response):

        item = response.meta['item']
        sel = response.xpath('//div[@class="mm-aixiu-content"]')
        items = []
        for href in sel.xpath('.//img/@src').extract():
            items.append('http:' + href)
        item['image_urls'] = items
        return item

    # 创建新目录
    def mkdir(self, path):
        path = path.strip()
        # 判断路径是否存在
        # 存在     True
        # 不存在   False
        isExists = os.path.exists(path)
        # 判断结果
        if not isExists:
            # 如果不存在则创建目录
            print u"偷偷新建了名字叫做", path, u'的文件夹'
            # 创建目录操作函数
            os.makedirs(path)
            return True
        else:
            # 如果目录存在则不创建，并提示目录已存在
            print u"名为", path, '的文件夹已经创建成功'
            return False
