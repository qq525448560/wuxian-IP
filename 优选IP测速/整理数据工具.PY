import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import datetime
import sys
import csv
import io
import re
import ipaddress


class IPDataFormatterGUI:
    def __init__(self, root):
        # 主窗口配置
        self.root = root
        self.root.title("IP数据批量整理工具")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)

        # 标记是否正在处理（防止重复点击）
        self.is_processing = False

        # 扩充版地区码映射表（IATA/常见地区码 -> 国家/地区）
        self.region_mapping = {
            # 亚洲
            "SIN": "新加坡", "ICN": "韩国", "NRT": "日本", "HND": "日本",
            "HKG": "中国香港", "TPE": "中国台湾", "BOM": "印度", "DEL": "印度",
            "KUL": "马来西亚", "BKK": "泰国", "SGN": "越南", "MNL": "菲律宾",
            "JKT": "印度尼西亚", "KHH": "中国台湾", "TKO": "日本", "SEL": "韩国",
            "KIX": "日本",  # 大阪（关西）

            # 欧洲
            "FRA": "德国", "LHR": "英国", "LCG": "英国", "AMS": "荷兰",
            "PAR": "法国", "MAD": "西班牙", "MIL": "意大利", "ROM": "意大利",
            "ZRH": "瑞士", "VIE": "奥地利", "PRG": "捷克", "STO": "瑞典",
            "CPH": "丹麦", "OSL": "挪威", "HEL": "芬兰", "WAW": "波兰",
            "BUD": "匈牙利", "ATH": "希腊",
            "TXL": "德国",  # 柏林（泰格尔，老码仍有人用）

            # 美洲
            "SJC": "美国", "LAX": "美国", "SFO": "美国", "SEA": "美国",
            "PHX": "美国", "DEN": "美国", "DFW": "美国", "HOU": "美国",
            "MIA": "美国", "ATL": "美国", "CHI": "美国", "NYC": "美国",
            "EWR": "美国", "IAD": "美国", "BOS": "美国",

            "TOR": "加拿大", "YTO": "加拿大", "MON": "加拿大",
            "YYZ": "加拿大",  # 多伦多皮尔逊
            "ORD": "美国",   # 芝加哥奥黑尔
            "BUF": "美国",   # 布法罗

            "SAO": "巴西", "RIO": "巴西", "MEX": "墨西哥",

            # 大洋洲
            "SYD": "澳大利亚", "MEL": "澳大利亚", "AKL": "新西兰",

            # 中东/非洲
            "DXB": "阿联酋", "JED": "沙特阿拉伯", "CAI": "埃及",
            "JNB": "南非", "CPT": "南非",

            # 兜底（重复键无影响，保留原逻辑）
            "HKG": "中国香港", "TPE": "中国台湾",
            "FRA": "德国", "LHR": "英国", "AMS": "荷兰", "PAR": "法国",
            "NYC": "美国", "CHI": "美国", "YTO": "加拿大",
            "YYZ": "加拿大", "ORD": "美国", "BUF": "美国", "TXL": "德国",
        }

        # ========== 界面布局 ==========
        # 1. 输入区域
        input_frame = tk.Frame(root, bd=2, relief=tk.GROOVE, padx=5, pady=5)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(input_frame, text="原始数据输入区（直接粘贴CSV数据）：", font=("微软雅黑", 10)).pack(anchor=tk.W)
        self.input_text = scrolledtext.ScrolledText(input_frame, font=("Consolas", 9), wrap=tk.NONE)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 2. 按钮区域
        btn_frame = tk.Frame(root, padx=10, pady=5)
        btn_frame.pack(fill=tk.X)

        self.process_btn = tk.Button(
            btn_frame, text="开始处理数据", font=("微软雅黑", 10),
            bg="#4CAF50", fg="white", command=self.start_process_thread
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)

        self.extract_btn = tk.Button(
            btn_frame, text="提取IP", font=("微软雅黑", 10),
            bg="#9C27B0", fg="white", command=self.start_extract_thread
        )
        self.extract_btn.pack(side=tk.LEFT, padx=5)

        # ✅ 新增：删除低速按钮（<10MB/s）
        self.filter_btn = tk.Button(
            btn_frame, text="删除低速(<10MB/s)", font=("微软雅黑", 10),
            bg="#607D8B", fg="white", command=self.start_filter_thread, state=tk.DISABLED
        )
        self.filter_btn.pack(side=tk.LEFT, padx=5)

        # ✅ 复制按钮（复制输出区所有内容）
        self.copy_btn = tk.Button(
            btn_frame, text="复制结果", font=("微软雅黑", 10),
            bg="#FF9800", fg="white", command=self.copy_result, state=tk.DISABLED
        )
        self.copy_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(
            btn_frame, text="清空数据", font=("微软雅黑", 10),
            bg="#f44336", fg="white", command=self.clear_all
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(
            btn_frame, text="保存结果", font=("微软雅黑", 10),
            bg="#2196F3", fg="white", command=self.save_result, state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(btn_frame, text="状态：就绪", font=("微软雅黑", 9), fg="#666")
        self.status_label.pack(side=tk.RIGHT)

        # 3. 输出区域
        output_frame = tk.Frame(root, bd=2, relief=tk.GROOVE, padx=5, pady=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(output_frame, text="结果输出区：", font=("微软雅黑", 10)).pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(output_frame, font=("Consolas", 9), wrap=tk.NONE, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)

    # ========== 核心功能 ==========
    def start_process_thread(self):
        """启动多线程处理数据（避免GUI卡顿）"""
        if self.is_processing:
            messagebox.showwarning("提示", "正在处理数据，请稍候！")
            return

        input_data = self.input_text.get("1.0", tk.END).strip()
        if not input_data:
            messagebox.showerror("错误", "请先粘贴原始数据！")
            return

        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.DISABLED)
        self.filter_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态：正在处理...")
        self.root.update_idletasks()

        t = threading.Thread(target=self.process_data, args=(input_data,))
        t.daemon = True
        t.start()

    def process_data(self, input_data: str):
        """处理数据的核心函数（子线程运行）"""
        try:
            reader = csv.reader(io.StringIO(input_data))
            rows = [row for row in reader if any(cell.strip() for cell in row)]
            if len(rows) < 2:
                self.update_gui("error", "未检测到有效数据（至少需要表头+1行数据）！")
                return

            formatted_results = []
            error_lines = []

            for row_num, fields in enumerate(rows[1:], start=2):
                try:
                    if len(fields) < 8:
                        error_lines.append(f"第{row_num}行：字段数量不足（需至少8个）→ {','.join(fields)}")
                        continue

                    ip = fields[0].strip()
                    port = fields[7].strip()
                    region_code = (fields[6].strip() or "").upper()
                    download_speed = fields[5].strip()

                    try:
                        ipaddress.ip_address(ip)
                    except Exception:
                        error_lines.append(f"第{row_num}行：IP不合法 → {ip}")
                        continue

                    if not port.isdigit() or not (1 <= int(port) <= 65535):
                        error_lines.append(f"第{row_num}行：端口不合法 → {port}")
                        continue

                    ds = download_speed.replace("MB/s", "").replace("mb/s", "").strip()
                    if ds == "":
                        ds = download_speed.strip()

                    country = self.region_mapping.get(region_code, f"未知地区({region_code})")
                    formatted_line = f"{ip}:{port}#{country} {ds}MB/s"
                    formatted_results.append(formatted_line)

                except Exception as e:
                    error_lines.append(f"第{row_num}行：处理失败 → {str(e)} | 内容：{','.join(fields)}")

            result_text = "\n".join(formatted_results)
            if error_lines:
                result_text += "\n\n【错误提示】以下行数据异常已跳过：\n" + "\n".join(error_lines)

            self.update_gui("success", result_text, valid_count=len(formatted_results))

        except Exception as e:
            self.update_gui("error", f"处理失败：{str(e)}")

    # ========== 提取IP（永远只提取IP，不要端口） ==========
    def start_extract_thread(self):
        if self.is_processing:
            messagebox.showwarning("提示", "正在处理/提取中，请稍候！")
            return

        out_text = self.output_text.get("1.0", tk.END).strip()
        in_text = self.input_text.get("1.0", tk.END).strip()
        source_text = out_text if out_text else in_text

        if not source_text:
            messagebox.showerror("错误", "输入区和输出区都没有内容，无法提取！")
            return

        keep_port = False  # ✅ 永远不保留端口

        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.DISABLED)
        self.filter_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态：正在提取IP...")
        self.root.update_idletasks()

        t = threading.Thread(target=self.extract_ips_worker, args=(source_text, keep_port))
        t.daemon = True
        t.start()

    def extract_ips_worker(self, text: str, keep_port: bool):
        try:
            results = self.extract_ips(text, keep_port=keep_port)
            if not results:
                self.update_gui("error", "未提取到任何有效IP！")
                return
            content = "\n".join(results)
            self.update_gui("success", content, valid_count=len(results))
        except Exception as e:
            self.update_gui("error", f"提取失败：{str(e)}")

    @staticmethod
    def extract_ips(text: str, keep_port: bool) -> list[str]:
        pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b"
        candidates = re.findall(pattern, text)

        seen = set()
        out = []

        for item in candidates:
            ip_part = item
            port_part = None

            if ":" in item:
                ip_part, port_str = item.split(":", 1)
                port_part = port_str

            try:
                ipaddress.ip_address(ip_part)
            except Exception:
                continue

            if keep_port:
                if port_part is None:
                    continue
                if not port_part.isdigit():
                    continue
                p = int(port_part)
                if not (1 <= p <= 65535):
                    continue
                normalized = f"{ip_part}:{p}"
            else:
                normalized = ip_part

            if normalized not in seen:
                seen.add(normalized)
                out.append(normalized)

        return out

    # ========== ✅ 新增：删除低速（<10MB/s） ==========
    def start_filter_thread(self):
        if self.is_processing:
            messagebox.showwarning("提示", "正在处理/提取/过滤中，请稍候！")
            return

        result_text = self.output_text.get("1.0", tk.END).strip()
        if not result_text:
            messagebox.showwarning("提示", "输出区没有内容，请先处理数据后再过滤！")
            return

        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.DISABLED)
        self.filter_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态：正在删除低速数据...")
        self.root.update_idletasks()

        t = threading.Thread(target=self.filter_low_speed_worker, args=(result_text, 10.0))
        t.daemon = True
        t.start()

    def filter_low_speed_worker(self, text: str, threshold: float):
        try:
            new_text, kept_count, removed_count = self.filter_low_speed(text, threshold)
            note = f"（已删除{removed_count}条< {threshold:g}MB/s）"
            self.update_gui("success", new_text, valid_count=kept_count, status_note=note)
        except Exception as e:
            self.update_gui("error", f"过滤失败：{str(e)}")

    @staticmethod
    def filter_low_speed(text: str, threshold: float) -> tuple[str, int, int]:
        """
        从“输出区结果格式”中过滤掉下载速度 < threshold 的行。
        兼容保留【错误提示】段落。
        返回：(新文本, 保留条数, 删除条数)
        """
        marker = "\n\n【错误提示】"
        if marker in text:
            main_part, err_part = text.split(marker, 1)
            err_block = marker + err_part
        else:
            main_part, err_block = text, ""

        lines = [ln for ln in main_part.splitlines() if ln.strip()]
        kept = []
        removed = 0

        for ln in lines:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*MB/s\b", ln, flags=re.I)
            if m:
                try:
                    speed = float(m.group(1))
                    if speed < threshold:
                        removed += 1
                        continue
                except Exception:
                    # 速度解析失败：保留该行
                    pass
            kept.append(ln)

        new_main = "\n".join(kept)
        if new_main and err_block:
            new_text = new_main + err_block
        elif err_block:
            # 主结果为空但有错误段：仍保留错误段
            new_text = err_block.lstrip("\n")
        else:
            new_text = new_main

        return new_text, len(kept), removed

    # ========== ✅ 复制按钮功能 ==========
    def copy_result(self):
        result_data = self.output_text.get("1.0", tk.END).strip()
        if not result_data:
            messagebox.showwarning("提示", "输出区无内容可复制！")
            self.copy_btn.config(state=tk.DISABLED)
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(result_data)
            self.root.update()
            messagebox.showinfo("复制成功", "已复制输出区全部内容到剪贴板！")
        except Exception as e:
            messagebox.showerror("复制失败", f"复制出错：{str(e)}")

    # ========== GUI更新 ==========
    def update_gui(self, status, content, valid_count: int | None = None, status_note: str = ""):
        def _update():
            if status == "success":
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", content)
                self.output_text.config(state=tk.DISABLED)

                if valid_count is None:
                    main_part = content.split("\n\n【错误提示】", 1)[0]
                    valid_count_local = len([ln for ln in main_part.splitlines() if ln.strip()])
                else:
                    valid_count_local = valid_count

                self.status_label.config(text=f"状态：完成（共{valid_count_local}条）{status_note}")

                # 有内容才允许保存/复制
                if content.strip():
                    self.save_btn.config(state=tk.NORMAL)
                    self.copy_btn.config(state=tk.NORMAL)
                else:
                    self.save_btn.config(state=tk.DISABLED)
                    self.copy_btn.config(state=tk.DISABLED)

                # 只有“主结果有至少1条”才允许继续过滤
                self.filter_btn.config(state=tk.NORMAL if valid_count_local > 0 else tk.DISABLED)

            elif status == "error":
                messagebox.showerror("错误", content)
                self.status_label.config(text=f"状态：失败 - {content[:20]}...")
                self.save_btn.config(state=tk.DISABLED)
                self.copy_btn.config(state=tk.DISABLED)
                self.filter_btn.config(state=tk.DISABLED)

            self.is_processing = False
            self.process_btn.config(state=tk.NORMAL)
            self.extract_btn.config(state=tk.NORMAL)

        self.root.after(0, _update)

    def clear_all(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.status_label.config(text="状态：就绪")
        self.save_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.filter_btn.config(state=tk.DISABLED)

    def save_result(self):
        result_data = self.output_text.get("1.0", tk.END).strip()
        if not result_data:
            messagebox.showwarning("提示", "无结果可保存！")
            return

        filename = f"IP数据整理结果_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=filename,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(result_data)
                messagebox.showinfo("保存成功", f"结果已保存到：\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"保存出错：{str(e)}")


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    app = IPDataFormatterGUI(root)
    root.mainloop()
