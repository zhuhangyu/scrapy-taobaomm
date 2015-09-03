# -*- coding: utf-8 -*-

import os
import random
from scrapy.conf import settings
import logging
from scrapy.http import HtmlResponse
from selenium import webdriver


class RandomUserAgentMiddleware(object):

    def process_request(self, request, spider):
        ua = random.choice(settings.get('USER_AGENT_LIST'))
        if ua:
            request.headers.setdefault('User-Agent', ua)
            #logging.info('User-Agent: ' + ua)


class ProxyMiddleware(object):

    def process_request(self, request, spider):
        addproxy = random.randrange(0, 1000)
        if addproxy > 500:
            request.meta['proxy'] = settings.get('HTTP_PROXY')


class PhantomJSMiddleware(object):
    # overwrite process request

    def process_request(self, request, spider):

        if request.meta.has_key('PhantomJS'):  # 如果设置了PhantomJS参数，才执行下面的代码
            logging.info('PhantomJS Requesting: '+request.url)
            try:
                driver = request.meta['driver']
                driver.get(request.url)
                content = driver.page_source.encode('utf8')
                url = driver.current_url.encode('utf8')
                return HtmlResponse(url, encoding='utf8',
                                    status=200, body=content)

            except Exception, e:  # 请求异常，当成500错误。交给重试中间件处理
                logging.error('PhantomJS Exception!')
                return HtmlResponse(request.url, encoding='utf8',
                                    status=503, body='')
        # 如果没设置PhantomJS参数，这个中间件其实没起作用，直接请求mm的图片地址
        # else:
        #     logging.info('Common Requesting: '+request.url)
