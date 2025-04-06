import json
import logging
import time
from pywikibot import pagegenerators, Site, Page
from filelock import FileLock
from opencc import OpenCC
from pywikibot.exceptions import CircularRedirectError, InterwikiRedirectPageError, IsNotRedirectPageError, SectionError

logging.basicConfig(
    filename='meow.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
site = Site('zh', 'wikipedia')

# OpenCC
s2tc = OpenCC('s2t.json')
s2twc = OpenCC('s2tw.json')
s2hkc = OpenCC('s2hk.json')
t2sc = OpenCC('t2s.json')
tw2sc = OpenCC('tw2t.json')
hk2sc = OpenCC('hkt2s.json')


def is_exist(title: str) -> bool:
    page = Page(site, title)
    if page.exists():
        return True
    else:
        return False

def change_target(page: Page, target: Page) -> None:
    page.set_redirect_target(target_page=target, create=False, force=False)
    page.save()
    logger.info("机器人已修改页面{target_page}的重定向目标为{target}".format(target_page=page.title(), target=target.title()))

def get_recentchanges() -> any:
    lock = FileLock("record.json.lock", timeout=5)
    target_list = []
    try:
        with lock:
            with open('record.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            recentchanges = pagegenerators.RecentChangesPageGenerator(
                site=site,
                namespaces=[0],
                tag="mw-changed-redirect-target" # 仅侦测修改重定向目标的编辑
            )
            for page in recentchanges:
                if page.latest_revision_id not in data["done"]:
                    target = page.getRedirectTarget()
                    page_tuple = (page.title(), target)
                    target_list.append(page_tuple)
                    data["done"].append(page.latest_revision_id)
                    with open('record.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                else:
                    continue
    except CircularRedirectError:
        logger.error("A CircularRedirectError was raised while the bot was checking {page}".format(page=page.title()))
    except InterwikiRedirectPageError:
        logger.error("A InterwikiRedirectPageError was raised while the bot was checking {page}".format(page=page.title()))
    except IsNotRedirectPageError:
        logger.error("A IsNotRedirectPageError was raised while the bot was checking {page}".format(page=page.title()))
    except RuntimeError:
        logger.error("A RuntimeError was raised while checking {page}".format(page=page.title()))
    except SectionError:
        logger.error("A SectionError was raised while checking {page}".format(page=page.title()))
    except:
        logger.error("An unknown error was raised while checking {page}".format(page=page.title()))
    finally:
        return target_list

def main() -> None:
    while True:
        rc = get_recentchanges()
        if rc:
            for title, target in rc:
                if is_exist(title):
                    reserve_title_list = []
                    if title == s2tc.convert(title):
                        reserve_title_list.append(s2tc.convert(title))
                        reserve_title_list.append(s2hkc.convert(title))
                        reserve_title_list.append(s2twc.convert(title))
                    else:
                        reserve_title_list.append(t2sc.convert(title))
                        reserve_title_list.append(hk2sc.convert(title))
                        reserve_title_list.append(tw2sc.convert(title))
                    for reserve_title in reserve_title_list:
                        page = Page(site, reserve_title)
                        if page.isRedirectPage():
                            change_target(page, target)
                        else:
                            logger.warning("机器人计划修改{pagename}，但该页面不是重定向或不存在。".format(pagename=page.title()))
        else:
            time.sleep(30)