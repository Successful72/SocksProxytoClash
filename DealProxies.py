#!/usr/bin/env python3
"""
generate_clash.py
从 txt 直链拉取 socks5 代理列表，查询 IP 地理位置（中文），生成 Clash Meta 可识别的 proxies YAML 配置文件。

"""
import re
import time
import requests
import yaml
from datetime import datetime, timezone
import pytz

# ────────────────────────────────────────────
# Socks5代理文件直链
PROXY_LIST_URL = "https://raw.githubusercontent.com/watchttvv/free-proxy-list/refs/heads/main/proxy.txt"
# 输出文件路径（相对于仓库根目录）
OUTPUT_FILE    = "Proxies.yaml"
# ────────────────────────────────────────────

# IP归属地
GEO_API   = "http://ip-api.com/json/{ip}?fields=country,city,status&lang=zh-CN"
GEO_CACHE: dict[str, str] = {}   # IP归属地缓存


def fetch_proxy_list(url: str) -> str:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_proxies(text: str) -> list[dict]:
    """
    解析形如 socks5://IP:PORT [YYYY-MM-DD HH:MM] 的行，
    返回包含 server / port / timestamp 的字典列表。
    """
    pattern = re.compile(
        r"socks5://([^:]+):(\d+)\s*\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\]"
    )
    proxies = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = pattern.match(line)
        if m:
            proxies.append({
                "server":    m.group(1),
                "port":      int(m.group(2)),
                "timestamp": m.group(3),   # e.g. "2026-02-24 14:10"
            })
    return proxies


def get_geo(ip: str) -> str:
    """
    查询 IP 归属地，返回如 "美国纽约" 的字符串。
    ip-api.com 免费限额 45 req/min，每次查询后等待 1.4 秒。
    """
    if ip in GEO_CACHE:
        return GEO_CACHE[ip]
    try:
        resp = requests.get(GEO_API.format(ip=ip), timeout=5)
        data = resp.json()
        if data.get("status") == "success":
            country = data.get("country", "")
            city    = data.get("city", "")
            result  = f"{country}{city}" if (country or city) else "未知地区"
        else:
            result = "未知地区"
    except Exception:
        result = "未知地区"
    GEO_CACHE[ip] = result
    time.sleep(1.4)
    return result


def fmt_timestamp(ts: str) -> str:
    """
    将 "YYYY-MM-DD HH:MM" 转换为 "YYYYMMDDHHmm"。
    """
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
    return dt.strftime("%Y%m%d%H%M")


def generate_yaml(proxies_raw: list[dict]) -> str:
    name_counter: dict[str, int] = {}
    clash_proxies = []

    for p in proxies_raw:
        geo       = get_geo(p["server"])
        ts        = fmt_timestamp(p["timestamp"])
        base_name = f"免费-{geo}-{ts}"

        # 同名时追加序号保证唯一性
        count = name_counter.get(base_name, 0)
        name_counter[base_name] = count + 1
        name = base_name if count == 0 else f"{base_name}-{count:02d}"

        clash_proxies.append({
            "name":   name,
            "type":   "socks5",
            "server": p["server"],
            "port":   p["port"],
            "udp":    True,
        })

    cst_time = pytz.timezone('Asia/Shanghai')
    now_cst = datetime.now(cst_time).strftime("%Y-%m-%d %H:%M CST")
    header  = (
        f"# Clash Meta Free Socks5 Proxies\n"
        f"# Auto-generated at {now_cst}\n"
        f"# Total: {len(clash_proxies)} proxies\n\n"
    )
    body = yaml.dump(
        {"proxies": clash_proxies},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return header + body


def main():
    print(f"[*] Fetching proxy list from: {PROXY_LIST_URL}")
    raw_text    = fetch_proxy_list(PROXY_LIST_URL)
    proxies_raw = parse_proxies(raw_text)
    print(f"[*] Parsed {len(proxies_raw)} proxies. Querying geo info...")

    yaml_content = generate_yaml(proxies_raw)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"[✓] Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
