# scrapy-taobaomm

###How to get started?

Start redis server on main server and crawling machines.

use python or ipython on the command line at a gui machine.

initial Monitor, example:

```
>> from taobao.utils import Monitor
>> m = Monitor()
```

Each crawler needs to fetch an account from the account pool to start. To add accounts to account pool, use:

```
>> m.add_account('username','password')
```

then, at the crawling machine, Use `scrapy crawl taobao` to start a crawler.

waiting the crawler login taobao, when you look at a hint: "wait for captcha input..." ,try to solve captchas

###How to solve captchas?

We provide the Monitor class to monitor crawlers, including solving captchas for them.
To solve captchas for all crawlers that need captcha, use:

```
>> m.solve_captchas()
```