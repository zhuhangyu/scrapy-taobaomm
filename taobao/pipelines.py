# -*- coding: utf-8 -*-
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
import hashlib
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class TaobaoPipeline(object):

    def process_item(self, item, spider):
        return item


class getmmimgPipeline(ImagesPipeline):

    def get_media_requests(self, item, info):
        print u'开始下载图片：'+ item['mm_name'] + '*'*50
        # 因为在下面的file_path方法中获得不到mm的姓名，所以在这里把mm的姓名作为meta传过去
        return [Request(image_url, meta={'mm_name': item['mm_name']}) for image_url in item['image_urls']]

    def file_path(self, request, response=None, info=None):
        image_guid = hashlib.sha1(request.url).hexdigest()
        path = 'full/%s/%s.jpg' % (request.meta['mm_name'], image_guid)
        return path
