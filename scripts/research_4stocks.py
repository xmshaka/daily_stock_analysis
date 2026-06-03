#!/usr/bin/env python3
"""4 只持仓股新标的调研 - 基于 a-stock-data SKILL"""
import urllib.request, requests, time
from datetime import datetime, timedelta

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

def eastmoney_datacenter(report_name, columns="ALL", filter_str="", page_size=50,
                         sort_columns="", sort_types="-1"):
    params = {"reportName": report_name, "columns": columns, "filter": filter_str,
              "pageNumber": "1", "pageSize": str(page_size),
              "sortColumns": sort_columns, "sortTypes": sort_types,
              "source": "WEB", "client": "WEB"}
    r = requests.get(DATACENTER_URL, params=params, headers={"User-Agent": UA}, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []

def tencent_quote(codes):
    prefixed = []
    for c in codes:
        if c.startswith(("6","9")): prefixed.append(f"sh{c}")
        elif c.startswith("8"): prefixed.append(f"bj{c}")
        else: prefixed.append(f"sz{c}")
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    result = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line: continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53: continue
        code = key[2:]
        def fv(i):
            try: return float(vals[i]) if vals[i] else 0
            except: return 0
        result[code] = {
            "name": vals[1], "price": fv(3), "last_close": fv(4),
            "change_pct": fv(32), "turnover_pct": fv(38),
            "pe_ttm": fv(39), "amplitude_pct": fv(43),
            "mcap_yi": fv(44), "float_mcap_yi": fv(45),
            "pb": fv(46), "limit_up": fv(47), "limit_down": fv(48),
            "vol_ratio": fv(49), "pe_static": fv(52),
        }
    return result

def em_f10_blocks(code):
    """东财 F10 板块归属（替代失效的百度 PAE）"""
    data = eastmoney_datacenter(
        "RPT_F10_CORETHEME_BOARDTYPE",
        columns="SECURITY_CODE,BOARD_NAME,NEW_BOARD_CODE,SELECTED_BOARD_REASON",
        filter_str=f'(SECURITY_CODE="{code}")', page_size=80)
    return [{"name": r.get("BOARD_NAME",""),
             "code": r.get("NEW_BOARD_CODE",""),
             "reason": (r.get("SELECTED_BOARD_REASON") or "").strip()}
            for r in data]

def stock_fund_flow_120d(code):
    """个股资金流（日级，新浪源，替代被 IP 封的东财 push2his）"""
    prefix = "sh" if code.startswith(("6","9")) else ("bj" if code.startswith("8") else "sz")
    url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           "MoneyFlow.ssl_qsfx_zjlrqs"
           f"?page=1&num=120&sort=opendate&asc=0&daima={prefix}{code}")
    headers = {"User-Agent":"Mozilla/5.0",
               "Referer":"https://finance.sina.com.cn/"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json() if r.text.strip().startswith("[") else []
    except Exception:
        return []
    rows = []
    for row in data:
        try:
            rows.append({
                "date":      row.get("opendate",""),
                "close":     float(row.get("trade",0) or 0),
                "main_net":  float(row.get("netamount",0) or 0),  # 主力净流入（元）
                "super_net": float(row.get("r0_net",0) or 0),     # 超大单净流入
                "main_ratio": float(row.get("ratioamount",0) or 0) * 100,  # 主力占成交额 %
            })
        except Exception:
            continue
    rows.reverse()  # 原为逆序，反转成正序便于后面 [-N:] 拿最近
    return rows

def dragon_tiger_board(code, trade_date, look_back=30):
    start = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)).strftime("%Y-%m-%d")
    data = eastmoney_datacenter(
        "RPT_DAILYBILLBOARD_DETAILSNEW",
        filter_str=f"(TRADE_DATE>='{start}')(TRADE_DATE<='{trade_date}')(SECURITY_CODE=\"{code}\")",
        page_size=50, sort_columns="TRADE_DATE", sort_types="-1")
    records = []
    for row in data:
        records.append({"date": str(row.get("TRADE_DATE",""))[:10],
                        "reason": row.get("EXPLANATION",""),
                        "net_buy_wan": round((row.get("BILLBOARD_NET_AMT") or 0)/10000, 1)})
    return records

def lockup_expiry(code, trade_date, forward_days=90):
    end = (datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=forward_days)).strftime("%Y-%m-%d")
    upcoming_data = eastmoney_datacenter(
        "RPT_LIFT_STAGE",
        filter_str=f"(SECURITY_CODE=\"{code}\")(FREE_DATE>='{trade_date}')(FREE_DATE<='{end}')",
        page_size=20, sort_columns="FREE_DATE", sort_types="1")
    upcoming = [{"date": str(r.get("FREE_DATE",""))[:10],
                 "type": r.get("LIMITED_STOCK_TYPE",""),
                 "shares": r.get("FREE_SHARES_NUM", 0),
                 "ratio": r.get("FREE_RATIO", 0)} for r in upcoming_data]
    return upcoming

def margin_trading(code, page_size=10):
    data = eastmoney_datacenter("RPTA_WEB_RZRQ_GGMX",
        filter_str=f'(SCODE="{code}")', page_size=page_size,
        sort_columns="DATE", sort_types="-1")
    return [{"date": str(r.get("DATE",""))[:10],
             "rzye": r.get("RZYE",0), "rqye": r.get("RQYE",0),
             "rzrqye": r.get("RZRQYE",0)} for r in data]

def holder_num_change(code, page_size=8):
    data = eastmoney_datacenter("RPT_HOLDERNUM_DET",
        filter_str=f'(SECURITY_CODE="{code}")', page_size=page_size,
        sort_columns="END_DATE", sort_types="-1")
    return [{"date": str(r.get("END_DATE",""))[:10],
             "holder_num": r.get("HOLDER_NUM", 0) or 0,
             "change_ratio": r.get("HOLDER_NUM_RATIO", 0) or 0,
             "avg_shares": r.get("AVG_HOLD_NUM", 0) or 0} for r in data]

def fmt_yi(x):
    return f"{x/1e8:.2f}亿"

def research_one(code, today):
    print(f"\n{'='*68}\n📊 {code} 调研报告\n{'='*68}")

    # 1. 实时行情 + 估值
    try:
        q = tencent_quote([code]).get(code)
    except Exception as e:
        print(f"❌ 腾讯行情失败: {e}"); return
    if not q:
        print(f"❌ 腾讯未返回 {code}"); return
    print(f"\n【1. 估值快照】 {q['name']}")
    print(f"  现价 {q['price']:.2f}  涨跌 {q['change_pct']:+.2f}%  换手 {q['turnover_pct']:.2f}%  量比 {q['vol_ratio']:.2f}")
    print(f"  PE(TTM) {q['pe_ttm']:.2f}  PB {q['pb']:.2f}  总市值 {q['mcap_yi']:.0f}亿  流通 {q['float_mcap_yi']:.0f}亿")

    # 2. 东财 F10 板块归属
    try:
        blocks = em_f10_blocks(code)
        if blocks:
            print(f"\n【2. 板块归属】 共 {len(blocks)} 个归属板块")
            shown = blocks[:10]
            for b in shown:
                reason = f"  // {b['reason'][:60]}" if b['reason'] else ""
                print(f"  · {b['name']:<14}{reason}")
            if len(blocks) > 10:
                print(f"  …还有 {len(blocks)-10} 个")
        else:
            print(f"\n【2. 板块归属】 ⚠️ 无数据")
    except Exception as e:
        print(f"\n【2. 板块归属】❌ {e}")

    # 3. 资金流向 120 日
    try:
        flow = stock_fund_flow_120d(code)
        if flow:
            recent20 = flow[-20:]
            total_main = sum(d["main_net"] for d in recent20)
            total_super = sum(d["super_net"] for d in recent20)
            recent5 = flow[-5:]
            print(f"\n【3. 资金流向(新浪)】 共{len(flow)}天数据")
            print(f"  近20日主力累计净流入: {fmt_yi(total_main)} (超大单 {fmt_yi(total_super)})")
            print(f"  近5日主力(万):")
            for d in recent5:
                tag = "🟢" if d["main_net"]>0 else "🔴"
                print(f"    {d['date']} {tag} 主力 {d['main_net']/1e4:>+8.0f}  超大单 {d['super_net']/1e4:>+8.0f}")
        else:
            print(f"\n【3. 资金流向】 ⚠️ 无数据")
    except Exception as e:
        print(f"\n【3. 资金流向】❌ {e}")

    # 4. 龙虎榜
    try:
        dt = dragon_tiger_board(code, today)
        if dt:
            print(f"\n【4. 龙虎榜】 近30日上榜 {len(dt)} 次")
            for r in dt[:5]:
                print(f"  {r['date']} 净买 {r['net_buy_wan']:+.0f}万 | {r['reason'][:40]}")
        else:
            print(f"\n【4. 龙虎榜】 近30日未上榜")
    except Exception as e:
        print(f"\n【4. 龙虎榜】❌ {e}")

    # 5. 解禁
    try:
        lk = lockup_expiry(code, today)
        if lk:
            print(f"\n【5. 解禁预警】 未来90天 {len(lk)} 批")
            for r in lk:
                print(f"  {r['date']} 类型={r['type']} 股数={r['shares']:.0f} 占流通{r['ratio']:.2f}%")
        else:
            print(f"\n【5. 解禁预警】 未来90天无待解禁 ✅")
    except Exception as e:
        print(f"\n【5. 解禁预警】❌ {e}")

    # 6. 融资融券
    try:
        mg = margin_trading(code, page_size=5)
        if mg:
            print(f"\n【6. 融资融券】 最近5日")
            latest, oldest = mg[0], mg[-1]
            chg = (latest["rzye"]-oldest["rzye"])/oldest["rzye"]*100 if oldest["rzye"] else 0
            print(f"  最新 {latest['date']}: 融资 {fmt_yi(latest['rzye'])} 融券 {fmt_yi(latest['rqye'])} 合计 {fmt_yi(latest['rzrqye'])}")
            print(f"  5日融资余额变化: {chg:+.2f}%")
        else:
            print(f"\n【6. 融资融券】 无数据（非两融标的？）")
    except Exception as e:
        print(f"\n【6. 融资融券】❌ {e}")

    # 7. 股东户数
    try:
        hd = holder_num_change(code, page_size=4)
        if hd:
            print(f"\n【7. 股东户数】 近4个报告期")
            for d in hd:
                arrow = "↓" if d["change_ratio"]<0 else "↑"
                print(f"  {d['date']} {d['holder_num']:>8.0f}户 {arrow}{d['change_ratio']:+.2f}% 户均{d['avg_shares']:.0f}股")
            if hd[0]["change_ratio"] < 0:
                print(f"  💡 最新一期股东数减少 → 筹码趋集中信号")
        else:
            print(f"\n【7. 股东户数】 无数据")
    except Exception as e:
        print(f"\n【7. 股东户数】❌ {e}")

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    codes = ["600143","601808","603619","600547"]
    print(f"\n🔍 4 只股票新标的调研 | 调研日 {today}")
    for c in codes:
        research_one(c, today)
        time.sleep(1)
    print(f"\n{'='*68}\n✅ 调研完成\n")
