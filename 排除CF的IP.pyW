#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import bisect
import csv
import gzip
import ipaddress
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk
import urllib.request
from typing import Optional

# -----------------------------
# Common
# -----------------------------
SPLIT_RE = re.compile(r"[\s,;]+")

def iter_ip_tokens(text: str):
    """支持换行/空格/逗号/分号分隔；忽略空行与 # 注释行。"""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for tok in SPLIT_RE.split(line):
            tok = tok.strip()
            if tok:
                yield tok

def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def write_text_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def copy_to_clipboard(root: tk.Tk, s: str):
    root.clipboard_clear()
    root.clipboard_append(s)
    root.update()  # ensure clipboard updated


# ============================================================
# Country code -> Chinese name mapping
# ============================================================
CC_ZH = {
    "AF":"阿富汗","AL":"阿尔巴尼亚","DZ":"阿尔及利亚","AS":"美属萨摩亚","AD":"安道尔","AO":"安哥拉","AI":"安圭拉",
    "AQ":"南极洲","AG":"安提瓜和巴布达","AR":"阿根廷","AM":"亚美尼亚","AW":"阿鲁巴","AU":"澳大利亚","AT":"奥地利",
    "AZ":"阿塞拜疆","BS":"巴哈马","BH":"巴林","BD":"孟加拉国","BB":"巴巴多斯","BY":"白俄罗斯","BE":"比利时",
    "BZ":"伯利兹","BJ":"贝宁","BM":"百慕大","BT":"不丹","BO":"玻利维亚","BQ":"荷兰加勒比区","BA":"波斯尼亚和黑塞哥维那",
    "BW":"博茨瓦纳","BV":"布韦岛","BR":"巴西","IO":"英属印度洋领地","BN":"文莱","BG":"保加利亚","BF":"布基纳法索",
    "BI":"布隆迪","CV":"佛得角","KH":"柬埔寨","CM":"喀麦隆","CA":"加拿大","KY":"开曼群岛","CF":"中非共和国",
    "TD":"乍得","CL":"智利","CN":"中国","CX":"圣诞岛","CC":"科科斯（基林）群岛","CO":"哥伦比亚","KM":"科摩罗",
    "CG":"刚果（布）","CD":"刚果（金）","CK":"库克群岛","CR":"哥斯达黎加","CI":"科特迪瓦","HR":"克罗地亚","CU":"古巴",
    "CW":"库拉索","CY":"塞浦路斯","CZ":"捷克","DK":"丹麦","DJ":"吉布提","DM":"多米尼克","DO":"多米尼加共和国",
    "EC":"厄瓜多尔","EG":"埃及","SV":"萨尔瓦多","GQ":"赤道几内亚","ER":"厄立特里亚","EE":"爱沙尼亚","SZ":"斯威士兰",
    "ET":"埃塞俄比亚","FK":"福克兰群岛","FO":"法罗群岛","FJ":"斐济","FI":"芬兰","FR":"法国","GF":"法属圭亚那",
    "PF":"法属波利尼西亚","TF":"法属南部领地","GA":"加蓬","GM":"冈比亚","GE":"格鲁吉亚","DE":"德国","GH":"加纳",
    "GI":"直布罗陀","GR":"希腊","GL":"格陵兰","GD":"格林纳达","GP":"瓜德罗普","GU":"关岛","GT":"危地马拉",
    "GG":"根西","GN":"几内亚","GW":"几内亚比绍","GY":"圭亚那","HT":"海地","HM":"赫德岛和麦克唐纳群岛","VA":"梵蒂冈",
    "HN":"洪都拉斯","HK":"香港","HU":"匈牙利","IS":"冰岛","IN":"印度","ID":"印度尼西亚","IR":"伊朗","IQ":"伊拉克",
    "IE":"爱尔兰","IM":"马恩岛","IL":"以色列","IT":"意大利","JM":"牙买加","JP":"日本","JE":"泽西",
    "JO":"约旦","KZ":"哈萨克斯坦","KE":"肯尼亚","KI":"基里巴斯","KP":"朝鲜","KR":"韩国","KW":"科威特",
    "KG":"吉尔吉斯斯坦","LA":"老挝","LV":"拉脱维亚","LB":"黎巴嫩","LS":"莱索托","LR":"利比里亚","LY":"利比亚",
    "LI":"列支敦士登","LT":"立陶宛","LU":"卢森堡","MO":"澳门","MG":"马达加斯加","MW":"马拉维","MY":"马来西亚",
    "MV":"马尔代夫","ML":"马里","MT":"马耳他","MH":"马绍尔群岛","MQ":"马提尼克","MR":"毛里塔尼亚","MU":"毛里求斯",
    "YT":"马约特","MX":"墨西哥","FM":"密克罗尼西亚","MD":"摩尔多瓦","MC":"摩纳哥","MN":"蒙古","ME":"黑山",
    "MS":"蒙特塞拉特","MA":"摩洛哥","MZ":"莫桑比克","MM":"缅甸","NA":"纳米比亚","NR":"瑙鲁","NP":"尼泊尔",
    "NL":"荷兰","NC":"新喀里多尼亚","NZ":"新西兰","NI":"尼加拉瓜","NE":"尼日尔","NG":"尼日利亚","NU":"纽埃",
    "NF":"诺福克岛","MK":"北马其顿","MP":"北马里亚纳群岛","NO":"挪威","OM":"阿曼","PK":"巴基斯坦","PW":"帕劳",
    "PS":"巴勒斯坦","PA":"巴拿马","PG":"巴布亚新几内亚","PY":"巴拉圭","PE":"秘鲁","PH":"菲律宾","PN":"皮特凯恩群岛",
    "PL":"波兰","PT":"葡萄牙","PR":"波多黎各","QA":"卡塔尔","RE":"留尼汪","RO":"罗马尼亚","RU":"俄罗斯",
    "RW":"卢旺达","BL":"圣巴泰勒米","SH":"圣赫勒拿","KN":"圣基茨和尼维斯","LC":"圣卢西亚","MF":"法属圣马丁",
    "PM":"圣皮埃尔和密克隆","VC":"圣文森特和格林纳丁斯","WS":"萨摩亚","SM":"圣马力诺","ST":"圣多美和普林西比",
    "SA":"沙特阿拉伯","SN":"塞内加尔","RS":"塞尔维亚","SC":"塞舌尔","SL":"塞拉利昂","SG":"新加坡","SX":"荷属圣马丁",
    "SK":"斯洛伐克","SI":"斯洛文尼亚","SB":"所罗门群岛","SO":"索马里","ZA":"南非","GS":"南乔治亚和南桑威奇群岛",
    "SS":"南苏丹","ES":"西班牙","LK":"斯里兰卡","SD":"苏丹","SR":"苏里南","SE":"瑞典","CH":"瑞士",
    "SY":"叙利亚","TW":"台湾","TJ":"塔吉克斯坦","TZ":"坦桑尼亚","TH":"泰国","TL":"东帝汶","TG":"多哥",
    "TK":"托克劳","TO":"汤加","TT":"特立尼达和多巴哥","TN":"突尼斯","TR":"土耳其","TM":"土库曼斯坦","TC":"特克斯和凯科斯群岛",
    "TV":"图瓦卢","UG":"乌干达","UA":"乌克兰","AE":"阿联酋","GB":"英国","US":"美国","UM":"美属外岛","UY":"乌拉圭",
    "UZ":"乌兹别克斯坦","VU":"瓦努阿图","VE":"委内瑞拉","VN":"越南","VG":"英属维尔京群岛","VI":"美属维尔京群岛",
    "WF":"瓦利斯和富图纳","EH":"西撒哈拉","YE":"也门","ZM":"赞比亚","ZW":"津巴布韦",
}

def cc_to_zh(cc: Optional[str]) -> str:
    if not cc:
        return "未知"
    cc = cc.upper()
    return CC_ZH.get(cc, cc)


# ============================================================
# Tab 1: Cloudflare Filter
# ============================================================
CF_V4_URL = "https://www.cloudflare.com/ips-v4"
CF_V6_URL = "https://www.cloudflare.com/ips-v6"

def fetch_text(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ip-tool-gui/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")

def load_cf_networks_online(timeout: int = 10):
    v4_text = fetch_text(CF_V4_URL, timeout=timeout)
    v6_text = fetch_text(CF_V6_URL, timeout=timeout)
    v4_nets = [ipaddress.ip_network(l.strip(), strict=False) for l in v4_text.splitlines() if l.strip()]
    v6_nets = [ipaddress.ip_network(l.strip(), strict=False) for l in v6_text.splitlines() if l.strip()]
    return v4_nets, v6_nets

def load_cf_networks_from_file(path: str):
    v4_nets, v6_nets = [], []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            net = ipaddress.ip_network(line, strict=False)
            (v4_nets if net.version == 4 else v6_nets).append(net)
    return v4_nets, v6_nets

def export_cf_ranges_to_file(path: str, timeout: int = 10):
    v4_text = fetch_text(CF_V4_URL, timeout=timeout).strip()
    v6_text = fetch_text(CF_V6_URL, timeout=timeout).strip()
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Cloudflare IP ranges (auto-generated)\n")
        f.write("# Source: https://www.cloudflare.com/ips-v4 and https://www.cloudflare.com/ips-v6\n\n")
        if v4_text:
            f.write(v4_text + "\n")
        f.write("\n")
        if v6_text:
            f.write(v6_text + "\n")

def is_cloudflare_ip(ip_str: str, v4_nets, v6_nets) -> bool:
    ip_obj = ipaddress.ip_address(ip_str)
    nets = v4_nets if ip_obj.version == 4 else v6_nets
    return any(ip_obj in n for n in nets)

def cf_filter_text(text: str, v4_nets, v6_nets, dedupe=True):
    cf_list, non_cf_list, invalid = [], [], []
    seen = set()
    for tok in iter_ip_tokens(text):
        if dedupe and tok in seen:
            continue
        seen.add(tok)
        try:
            if is_cloudflare_ip(tok, v4_nets, v6_nets):
                cf_list.append(tok)
            else:
                non_cf_list.append(tok)
        except ValueError:
            invalid.append(tok)
    return cf_list, non_cf_list, invalid


class CloudflareFrame(ttk.Frame):
    def __init__(self, master, root: tk.Tk, set_status):
        super().__init__(master)
        self.root = root
        self.set_status = set_status

        self.v4_nets = None
        self.v6_nets = None
        self.ranges_path = None

        # Controls row
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        self.dedupe_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="去重", variable=self.dedupe_var).pack(side="left")

        self.mode_var = tk.StringVar(value="online")  # online/offline
        ttk.Radiobutton(top, text="在线(拉取官方网段)", variable=self.mode_var, value="online").pack(side="left", padx=12)
        ttk.Radiobutton(top, text="离线(本地网段文件)", variable=self.mode_var, value="offline").pack(side="left")

        ttk.Button(top, text="选择离线网段文件...", command=self.pick_ranges_file).pack(side="left", padx=8)
        ttk.Button(top, text="生成离线网段文件...", command=self.generate_ranges_file).pack(side="left")

        ttk.Button(top, text="打开IP文件...", command=self.open_ip_file).pack(side="right")
        ttk.Button(top, text="开始筛选", command=self.run_filter).pack(side="right", padx=8)

        # Main panes
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        ttk.Label(left, text="输入（粘贴IP 或 打开文件）").pack(anchor="w")
        self.input_box = ScrolledText(left, wrap="none", height=20)
        self.input_box.pack(fill="both", expand=True)

        right_paned = ttk.PanedWindow(right, orient="vertical")
        right_paned.pack(fill="both", expand=True)

        out_top = ttk.Frame(right_paned)
        out_bottom = ttk.Frame(right_paned)
        right_paned.add(out_top, weight=1)
        right_paned.add(out_bottom, weight=1)

        # Non-CF
        hdr1 = ttk.Frame(out_top)
        hdr1.pack(fill="x")
        ttk.Label(hdr1, text="✅ 非 Cloudflare IP（保留）").pack(side="left")
        ttk.Button(hdr1, text="复制", command=self.copy_non_cf).pack(side="right")
        ttk.Button(hdr1, text="保存...", command=self.save_non_cf).pack(side="right", padx=6)

        self.non_cf_box = ScrolledText(out_top, wrap="none", height=10)
        self.non_cf_box.pack(fill="both", expand=True)

        # CF
        hdr2 = ttk.Frame(out_bottom)
        hdr2.pack(fill="x")
        ttk.Label(hdr2, text="☁️ Cloudflare IP（剔除）").pack(side="left")
        ttk.Button(hdr2, text="复制", command=self.copy_cf).pack(side="right")
        ttk.Button(hdr2, text="保存...", command=self.save_cf).pack(side="right", padx=6)

        self.cf_box = ScrolledText(out_bottom, wrap="none", height=10)
        self.cf_box.pack(fill="both", expand=True)

        self.last_cf_list = []
        self.last_non_cf_list = []

    def pick_ranges_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.cidr *.list *.conf"), ("All", "*.*")])
        if not path:
            return
        self.ranges_path = path
        self.mode_var.set("offline")
        self.set_status(f"[CF] 离线网段文件：{path}")

    def generate_ranges_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        try:
            self.set_status("[CF] 正在拉取官方网段并生成离线文件...")
            self.root.update_idletasks()
            export_cf_ranges_to_file(path, timeout=10)
            self.ranges_path = path
            self.mode_var.set("offline")
            self.set_status(f"[CF] 已生成离线网段文件：{path}")
        except Exception as e:
            messagebox.showerror("错误", f"生成失败：{e}")
            self.set_status("[CF] 失败")

    def open_ip_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.log *.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            content = read_text_file(path)
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", content)
            self.set_status(f"[CF] 已载入IP文件：{path}")
        except Exception as e:
            messagebox.showerror("错误", f"打开失败：{e}")

    def _ensure_networks_loaded(self):
        mode = self.mode_var.get()
        if mode == "online":
            self.set_status("[CF] 在线拉取 Cloudflare 网段中...")
            self.root.update_idletasks()
            self.v4_nets, self.v6_nets = load_cf_networks_online(timeout=10)
            return True

        if not self.ranges_path:
            messagebox.showinfo("提示", "当前是离线模式，请先选择或生成离线网段文件。")
            return False
        try:
            self.set_status("[CF] 加载离线网段文件中...")
            self.root.update_idletasks()
            self.v4_nets, self.v6_nets = load_cf_networks_from_file(self.ranges_path)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"加载离线网段文件失败：{e}")
            return False

    def run_filter(self):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "请输入或打开包含 IP 的文本。")
            return
        if not self._ensure_networks_loaded():
            return

        self.set_status("[CF] 筛选中...")
        self.root.update_idletasks()

        cf_list, non_cf_list, invalid = cf_filter_text(
            text, self.v4_nets, self.v6_nets, dedupe=self.dedupe_var.get()
        )

        self.last_cf_list = cf_list
        self.last_non_cf_list = non_cf_list

        self.non_cf_box.delete("1.0", "end")
        self.non_cf_box.insert("1.0", "\n".join(non_cf_list))

        self.cf_box.delete("1.0", "end")
        self.cf_box.insert("1.0", "\n".join(cf_list))

        msg = f"[CF] 完成：非CF={len(non_cf_list)}，CF={len(cf_list)}"
        if invalid:
            msg += f"，无效IP={len(invalid)}（已忽略）"
        self.set_status(msg)

    def copy_non_cf(self):
        if not self.last_non_cf_list:
            messagebox.showinfo("提示", "没有非CF结果可复制，请先筛选。")
            return
        copy_to_clipboard(self.root, "\n".join(self.last_non_cf_list))
        self.set_status("[CF] 已复制：非CF结果")

    def copy_cf(self):
        if not self.last_cf_list:
            messagebox.showinfo("提示", "没有CF结果可复制，请先筛选。")
            return
        copy_to_clipboard(self.root, "\n".join(self.last_cf_list))
        self.set_status("[CF] 已复制：CF结果")

    def save_non_cf(self):
        if not self.last_non_cf_list:
            messagebox.showinfo("提示", "没有非CF结果可保存，请先筛选。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        write_text_file(path, "\n".join(self.last_non_cf_list) + "\n")
        self.set_status(f"[CF] 已保存非CF：{path}")

    def save_cf(self):
        if not self.last_cf_list:
            messagebox.showinfo("提示", "没有CF结果可保存，请先筛选。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        write_text_file(path, "\n".join(self.last_cf_list) + "\n")
        self.set_status(f"[CF] 已保存CF：{path}")


# ============================================================
# Tab 2: Country Grouping (DB-IP Country Lite)
# ============================================================
def open_maybe_gzip(path: str):
    if path.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")

class IPCountryDB:
    """
    读取 DB-IP country lite CSV/CSV.GZ: ip_start, ip_end, country
    用 starts 做 bisect 查询。
    """
    def __init__(self):
        self.v4_starts = []
        self.v4_ends = []
        self.v4_cc = []
        self.v6_starts = []
        self.v6_ends = []
        self.v6_cc = []
        self.loaded_path = None

    @staticmethod
    def _ip_to_int(ip_str: str):
        ip_obj = ipaddress.ip_address(ip_str)
        return ip_obj.version, int(ip_obj)

    def load_csv(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        v4_starts, v4_ends, v4_cc = [], [], []
        v6_starts, v6_ends, v6_cc = [], [], []

        with open_maybe_gzip(path) as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                # skip header if exists
                if row[0].strip().lower() == "ip_start":
                    continue
                if len(row) < 3:
                    continue

                ip_start, ip_end, cc = row[0].strip(), row[1].strip(), row[2].strip().upper()
                try:
                    v_s, s_int = self._ip_to_int(ip_start)
                    v_e, e_int = self._ip_to_int(ip_end)
                except ValueError:
                    continue
                if v_s != v_e:
                    continue

                if v_s == 4:
                    v4_starts.append(s_int)
                    v4_ends.append(e_int)
                    v4_cc.append(cc)
                else:
                    v6_starts.append(s_int)
                    v6_ends.append(e_int)
                    v6_cc.append(cc)

        def sort_pack(starts, ends, cc_list):
            idx = sorted(range(len(starts)), key=starts.__getitem__)
            starts[:] = [starts[i] for i in idx]
            ends[:] = [ends[i] for i in idx]
            cc_list[:] = [cc_list[i] for i in idx]

        sort_pack(v4_starts, v4_ends, v4_cc)
        sort_pack(v6_starts, v6_ends, v6_cc)

        self.v4_starts, self.v4_ends, self.v4_cc = v4_starts, v4_ends, v4_cc
        self.v6_starts, self.v6_ends, self.v6_cc = v6_starts, v6_ends, v6_cc
        self.loaded_path = path

    def lookup_country(self, ip_str: str):
        ip_obj = ipaddress.ip_address(ip_str)
        ip_int = int(ip_obj)

        if ip_obj.version == 4:
            starts, ends, ccs = self.v4_starts, self.v4_ends, self.v4_cc
        else:
            starts, ends, ccs = self.v6_starts, self.v6_ends, self.v6_cc

        if not starts:
            return None

        pos = bisect.bisect_right(starts, ip_int) - 1
        if pos < 0:
            return None
        if ip_int <= ends[pos]:
            return ccs[pos]
        return None


class CountryFrame(ttk.Frame):
    def __init__(self, master, root: tk.Tk, set_status):
        super().__init__(master)
        self.root = root
        self.set_status = set_status

        self.db = IPCountryDB()
        self.db_path = None

        self.focus = ["HK", "JP", "SG", "KR", "TW"]
        self.cc_name = {"HK": "香港", "JP": "日本", "SG": "新加坡", "KR": "韩国", "TW": "台湾"}

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="DB-IP 数据库文件（dbip-country-lite-YYYY-MM.csv 或 .csv.gz）：").pack(side="left")
        ttk.Button(top, text="选择...", command=self.pick_db_file).pack(side="left", padx=8)
        ttk.Button(top, text="加载数据库", command=self.load_db).pack(side="left")

        self.dedupe_var = tk.BooleanVar(value=True)
        self.show_others_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="去重", variable=self.dedupe_var).pack(side="left", padx=16)
        ttk.Checkbutton(top, text="输出其他国家(OTHER)", variable=self.show_others_var).pack(side="left")

        ttk.Button(top, text="打开IP文件...", command=self.open_ip_file).pack(side="right")
        ttk.Button(top, text="开始分组", command=self.run_group).pack(side="right", padx=8)

        # Main panes
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        ttk.Label(left, text="输入（粘贴IP 或 打开文件）").pack(anchor="w")
        self.input_box = ScrolledText(left, wrap="none", height=20)
        self.input_box.pack(fill="both", expand=True)

        # Right output
        hdr = ttk.Frame(right)
        hdr.pack(fill="x")
        ttk.Label(hdr, text="分组输出（格式：ip:443#国家/地区）").pack(side="left")
        ttk.Button(hdr, text="复制全部", command=self.copy_output).pack(side="right")
        ttk.Button(hdr, text="导出分组文件...", command=self.export_group_files).pack(side="right", padx=6)

        self.output_box = ScrolledText(right, wrap="none", height=20)
        self.output_box.pack(fill="both", expand=True)

        self.last_grouped = None  # dict cc -> list[str] (already formatted)
        self.last_invalid = []
        self.last_other_lines = []

    def pick_db_file(self):
        path = filedialog.askopenfilename(filetypes=[("DB-IP CSV", "*.csv *.csv.gz *.gz"), ("All", "*.*")])
        if not path:
            return
        self.db_path = path
        self.set_status(f"[GEO] 已选择数据库：{path}")

    def load_db(self):
        if not self.db_path:
            messagebox.showinfo("提示", "请先选择 DB-IP 数据库文件。")
            return
        try:
            self.set_status("[GEO] 正在加载数据库（可能需要几秒）...")
            self.root.update_idletasks()
            self.db.load_csv(self.db_path)
            self.set_status(f"[GEO] 数据库已加载：{self.db_path}")
        except Exception as e:
            messagebox.showerror("错误", f"加载数据库失败：{e}")
            self.set_status("[GEO] 失败")

    def open_ip_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.log *.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            content = read_text_file(path)
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", content)
            self.set_status(f"[GEO] 已载入IP文件：{path}")
        except Exception as e:
            messagebox.showerror("错误", f"打开失败：{e}")

    def _ensure_db_loaded(self):
        if self.db.loaded_path:
            return True
        # if chosen but not loaded, load now
        if self.db_path and not self.db.loaded_path:
            self.load_db()
            return bool(self.db.loaded_path)
        messagebox.showinfo("提示", "请先选择并加载 DB-IP 数据库文件。")
        return False

    def run_group(self):
        if not self._ensure_db_loaded():
            return

        text = self.input_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "请输入或打开包含 IP 的文本。")
            return

        self.set_status("[GEO] 分组中...")
        self.root.update_idletasks()

        grouped = {cc: [] for cc in self.focus}
        other_lines = []
        invalid = []
        seen = set()

        for ip in iter_ip_tokens(text):
            if self.dedupe_var.get() and ip in seen:
                continue
            seen.add(ip)

            try:
                cc = self.db.lookup_country(ip)
            except ValueError:
                invalid.append(ip)
                continue

            if cc in grouped:
                zh = self.cc_name.get(cc, cc_to_zh(cc))
                grouped[cc].append(f"{ip}:443#{zh}")
            else:
                if self.show_others_var.get():
                    zh = cc_to_zh(cc)
                    other_lines.append(f"{ip}:443#{zh}")

        # Render output
        parts = []
        for cc in self.focus:
            name = self.cc_name.get(cc, cc_to_zh(cc))
            lines = grouped[cc]
            parts.append(f"## {name} ({cc}) - {len(lines)}")
            if lines:
                parts.append("\n".join(lines))
            parts.append("")

        if self.show_others_var.get():
            parts.append(f"## 其他(OTHER) - {len(other_lines)}")
            if other_lines:
                parts.append("\n".join(other_lines))
            parts.append("")

        if invalid:
            parts.append(f"## 无效IP（已忽略） - {len(invalid)}")
            parts.append(", ".join(invalid))
            parts.append("")

        out_text = "\n".join(parts).rstrip() + "\n"
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", out_text)

        self.last_grouped = grouped
        self.last_invalid = invalid
        self.last_other_lines = other_lines

        msg = "[GEO] 完成：" + ", ".join([f"{cc}={len(grouped[cc])}" for cc in self.focus])
        if self.show_others_var.get():
            msg += f", OTHER={len(other_lines)}"
        if invalid:
            msg += f", 无效={len(invalid)}"
        self.set_status(msg)

    def copy_output(self):
        out = self.output_box.get("1.0", "end").strip()
        if not out:
            messagebox.showinfo("提示", "没有输出可复制，请先分组。")
            return
        copy_to_clipboard(self.root, out)
        self.set_status("[GEO] 已复制：全部输出")

    def export_group_files(self):
        if not self.last_grouped:
            messagebox.showinfo("提示", "没有分组结果可导出，请先分组。")
            return
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        try:
            for cc, lines in self.last_grouped.items():
                name = self.cc_name.get(cc, cc_to_zh(cc))
                filename = f"{cc}_{name}.txt"
                write_text_file(os.path.join(dir_path, filename), "\n".join(lines) + ("\n" if lines else ""))

            if self.last_other_lines:
                write_text_file(os.path.join(dir_path, "OTHER_其他.txt"), "\n".join(self.last_other_lines) + "\n")

            self.set_status(f"[GEO] 已导出到目录：{dir_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{e}")


# ============================================================
# App
# ============================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IP 工具箱（Cloudflare 过滤 + 国家归属分组）")
        self.geometry("1250x760")

        # Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        # Status bar
        self.status = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self, textvariable=self.status, anchor="w")
        status_bar.pack(fill="x", padx=10, pady=(0, 8))

        def set_status(s: str):
            self.status.set(s)

        self.cf_frame = CloudflareFrame(nb, self, set_status)
        self.geo_frame = CountryFrame(nb, self, set_status)

        nb.add(self.cf_frame, text="Cloudflare 过滤")
        nb.add(self.geo_frame, text="国家归属分组 (DB-IP)")


if __name__ == "__main__":
    # Windows 某些环境下提升 DPI 显示（可选）
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    App().mainloop()
