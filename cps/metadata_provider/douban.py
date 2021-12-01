# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2021 OzzieIsaacs
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

# Douban Books api document: https://ihtmlcss.com
# Code by tabzhang
# Email tabzhang@foxmail.com


import re
import requests
from cps.services.Metadata import Metadata


class Douban(Metadata):
    __name__ = "Douban"
    __id__ = "douban"
    __timeout__ = 10
    __maxResult__ = 5
    __headers__ = {
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cookie': 'bid=OLQAA_wwA8k; douban-fav-remind=1; viewed="34769292"; gr_user_id=4cea3a35-e9db-4e25-bf51-b8348048509d; __utma=30149280.1048994135.1620725249.1620725249.1628041438.2; __utmz=30149280.1628041438.2.2.utmcsr=baidu|utmccn=(organic)|utmcmd=organic'
    }

    def getDetail(self, id):
        v = {
            'authors': [],
            'translator': [],
            'publisher': '',
            'binding': '',
            'pages': '',
            'price': '',
            'isbn': '',
            'publishedDate': '',
            'origin_title': '',
            'tags': [],
        }

        try:
            url = "https://book.douban.com/subject/" + id
            result = requests.get(
                url, headers=self.__headers__, timeout=self.__timeout__)
            status_code = result.status_code
            print('(' + str(status_code) + ')' + url)
            if status_code == 200:
                publisher = re.findall(r'出版社:<\/span>(.*?)<br\/>', result.text)
                binding = re.findall(r'装帧:<\/span>(.*?)<br\/>', result.text)
                pages = re.findall(r'页数:<\/span>(.*?)<br\/>', result.text)
                price = re.findall(r'定价:<\/span>(.*?)<br\/>', result.text)
                isbn = re.findall(r'ISBN:<\/span>(.*?)<br\/>', result.text)
                publishedDate = re.findall(
                    r'出版年:<\/span>(.*?)<br\/>', result.text)
                origin_title = re.findall(
                    r'原作名:<\/span>(.*?)<br\/>', result.text)

                # translator
                translatorGroup = re.findall(
                    r'<span class="pl"> 译者<\/span>:\s*[.|\s|\S]*</span><br/>', result.text)

                if len(translatorGroup) > 0:
                    translator = re.findall(r'>(.*?)</a>', translatorGroup[0])
                    v['translator'] = translator
                else:
                    v['translator'] = []

                # authors
                authorsGroup = re.findall(
                    r'<span class="pl"> 作者<\/span>:\s*[.|\s|\S]*</span><br/>', result.text)

                if len(authorsGroup) > 0:
                    authors = re.findall(r'>(.*?)</a>', authorsGroup[0])
                    v['authors'] = authors
                else:
                    v['authors'] = []

                # tags
                tagsGroup = re.findall(
                    r'<div class="indent">    <span class="">\s*[.|\s|\S]*?</div>', result.text)
                if len(tagsGroup) > 0:
                    tags = re.findall(r'>(.*?)</a>', tagsGroup[0])
                    v['tags'] = tags
                else:
                    v['tags'] = []

                v['publisher'] = '' if len(publisher) == 0 else publisher[0]
                v['binding'] = '' if len(binding) == 0 else binding[0]
                v['pages'] = '' if len(pages) == 0 else pages[0]
                v['price'] = '' if len(price) == 0 else price[0]
                v['isbn'] = '' if len(isbn) == 0 else isbn[0]
                v['publishedDate'] = '' if len(
                    publishedDate) == 0 else publishedDate[0]
                v['origin_title'] = '' if len(
                    origin_title) == 0 else origin_title[0]

            return v
        except requests.exceptions.RequestException as e:
            print(e)
            return v

    def search(self, query, __):

        if self.active:

            try:
                val = []
                result = requests.get(
                    "https://www.douban.com/j/search?start=0&cat=1001&q="+query.replace(" ", "+"), headers=self.__headers__, timeout=self.__timeout__)
                status_code = result.status_code

                if status_code == 200:
                    list = result.json()['items']

                    def loop(i):
                        item = list[i]
                        id = re.findall(r'(?<=sid: ).*(?=, qcat:)', item)
                        subjectId = '' if len(id) == 0 else id[0]

                        rating = re.findall(
                            '(?<=<span class="rating_nums">).*(?=<\/span>)', item)
                        description = re.findall(
                            r'(?<=<p>)(.*?)(?=<\/p>)', item)
                        cover = re.findall(r'<img src="(.*?)"', item)
                        title = re.findall(r'title="(.*?)"', item)
                        query = re.findall(
                            r'(?<= onclick="moreurl\(this,).*(?=\)" title=)', item)

                        v = {}
                        v['id'] = subjectId
                        v['rating'] = 0 if len(
                            rating) == 0 else float(rating[0]) / 2
                        v['description'] = '' if len(
                            description) == 0 else description[0]
                        v['cover'] = '/../../../static/generic_cover.jpg' if len(
                            cover) == 0 else cover[0].replace("https://", "https://images.weserv.nl/?url=http://")
                        v['title'] = '' if len(title) == 0 else title[0]
                        v['query'] = query

                        v['source'] = {
                            'id': self.__id__,
                            'description': 'Douban Book',
                            'link': 'https://book.douban.com/subject/' + subjectId
                        }
                        v['url'] = 'https://book.douban.com/subject/' + subjectId
                        v['tags'] = []

                        v['subjectId'] = subjectId

                        detail = self.getDetail(subjectId)
                        v['authors'] = detail['authors']
                        v['translator'] = detail['translator']
                        v['publisher'] = detail['publisher']
                        v['binding'] = detail['binding']
                        v['pages'] = detail['pages']
                        v['price'] = detail['price']
                        v['isbn'] = detail['isbn']
                        v['publishedDate'] = detail['publishedDate']
                        v['origin_title'] = detail['origin_title']
                        v['tags'] = detail['tags']

                        val.append(v)
                        if i < len(list) - 1 and i < self.__maxResult__ - 1:
                            i = i + 1
                            loop(i)
                        else:
                            return val

                    loop(0)
                else:
                    print(status_code)

                return val
            except requests.exceptions.RequestException as e:
                print(e)
                return val
