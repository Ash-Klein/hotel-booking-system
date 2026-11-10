# -*- coding: utf-8 -*-
"""生成全部 UI 设计稿。"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "pylibs"))

OUT = os.path.join(ROOT, "UI界面")
os.makedirs(OUT, exist_ok=True)

from screens_mobile import screen01, screen02, screen03, screen04, screen05
from screens_desktop import screen06, screen07, screen08, screen09, screen10, screen11

MOBILE = [
    ("界面01-客人端-首页选店.png", screen01),
    ("界面02-客人端-房型报价.png", screen02),
    ("界面03-客人端-填单锁房.png", screen03),
    ("界面04-客人端-支付.png", screen04),
    ("界面05-客人端-订单改退.png", screen05),
]

DESKTOP = [
    ("界面06-门店端-今日工作台.png", screen06),
    ("界面07-门店端-库存房价.png", screen07),
    ("界面08-门店端-订单入住.png", screen08),
    ("界面09-集团端-门店房型.png", screen09),
    ("界面10-集团端-经营报表.png", screen10),
    ("界面11-集团端-权限审计.png", screen11),
]


def main():
    for name, fn in MOBILE + DESKTOP:
        path = os.path.join(OUT, name)
        fn(path)
        print("saved", name, os.path.getsize(path) // 1024, "KB", flush=True)


if __name__ == "__main__":
    main()
