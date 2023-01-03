import requests
from lxml import etree
import datetime
import re
from decimal import Decimal
import asyncio
import aiohttp
import aiofiles

url = "https://liansai.500.com/"
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
re_fid = re.compile(r"shuju-(?P<fid>.*?).shtml", re.S)



def remove_exponent(num):
    return num.to_integral() if num == num.to_integral() else num.normalize()


async def get_competition(ele):
    detail = url + ele.xpath("./@href")[0]
    title = ele.xpath("./text()")[0]
    conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
    async with aiohttp.ClientSession(connector=conn) as session1:
        async with session1.get(detail, headers=headers) as resp:
            txt = await resp.text()
            league_list = etree.HTML(txt)
            tr_list = league_list.xpath("//table[@class='lcur_race_list ltable jTrHover']//tr")
            for index in range(1, len(tr_list)):
                tr = tr_list[index]
                home_team = tr.xpath("./td[@class='td_lteam']/a/text()")[0]
                visiting_team = tr.xpath("./td[@class='td_rteam']/a/text()")[0]
                match_url = "https:" + tr.xpath("./td/a[text()='析']/@href")[0]
                fid = re_fid.search(match_url).group("fid")
                pan_url = match_url.replace("shuju-", "yazhi-")
                pan_resp = requests.get(pan_url, headers=headers)
                pan_detail = etree.HTML(pan_resp.content)
                game_time = pan_detail.xpath("//p[@class='game_time']/text()")[0]
                if game_time is not None:
                    game_time = game_time.replace("比赛时间", "")
                dt1 = datetime.datetime.strptime(game_time, '%Y-%m-%d %H:%M')
                trs = pan_detail.xpath("//table[@id='datatb']/tr")
                for i in range(0, min(3, len(trs))):
                    tr = trs[i]
                    tr_content = tr.xpath(".//table[@class='pl_table_data']")
                    tr_time = tr.xpath(".//time/text()")[0]
                    month = tr_time[0:tr_time.index("-")]
                    tr_time = str(dt1.year - 1 if dt1.month < int(month) else dt1.year) + "-" + tr_time
                    dt2 = datetime.datetime.strptime(tr_time, '%Y-%m-%d %H:%M')
                    if len(tr_content) == 2:
                        origin_pan = remove_exponent(Decimal(tr_content[1].xpath("./tbody/tr/td[2]/@ref")[0]))
                        instant_pan = remove_exponent(Decimal(tr_content[0].xpath("./tbody/tr/td[2]/@ref")[0]))
                        time_delta_days = (dt1-dt2).days
                        time_delta_seconds = round((dt1-dt2).seconds / 60 / 60, 2)
                        all_delta = time_delta_days * 24 + time_delta_seconds
                        if origin_pan != instant_pan and time_delta_days < 1:
                            async with aiofiles.open("500彩票.txt", "a+", encoding="utf-8") as f:
                                await f.write(f"赛事={title},主队={home_team},客队={visiting_team},初始盘口={origin_pan},即时盘口={instant_pan},变化时间=赛前{all_delta}小时,抓取网址={match_url}\n")
                                print(
                                    f"赛事={title},主队={home_team},客队={visiting_team},初始盘口={origin_pan},即时盘口={instant_pan},变化时间=赛前{all_delta}小时,抓取网址={match_url}")
                                break
                # await asyncio.sleep(1)


async def main():
    resp = requests.get(url, headers=headers)
    if len(resp.text) > 0:
        html = etree.HTML(resp.text)
        lst = html.xpath("//div[@class='lallrace_pop_in']/a")
        tasks = [asyncio.create_task(get_competition(ele)) for ele in lst]
        await asyncio.wait(tasks)


if __name__ == '__main__':
    asyncio.run(main())
