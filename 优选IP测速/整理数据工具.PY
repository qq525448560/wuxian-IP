import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import datetime
import sys

class IPDataFormatterGUI:
    def __init__(self, root):
        # 主窗口配置
        self.root = root
        self.root.title("IP数据批量整理工具 v1.1（无序号版）")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 标记是否正在处理（防止重复点击）
        self.is_processing = False
        
        # 扩充版地区码映射表
        self.region_mapping = {
            # 亚洲
            "SIN": "新加坡", "ICN": "韩国", "NRT": "日本", "HND": "日本",
            "HKG": "中国香港", "TPE": "中国台湾", "BOM": "印度", "DEL": "印度",
            "KUL": "马来西亚", "BKK": "泰国", "SGN": "越南", "MNL": "菲律宾",
            "JKT": "印度尼西亚", "KHH": "中国台湾", "TKO": "日本", "SEL": "韩国",
            # 欧洲
            "FRA": "德国", "LHR": "英国", "LCG": "英国", "AMS": "荷兰",
            "PAR": "法国", "MAD": "西班牙", "MIL": "意大利", "ROM": "意大利",
            "ZRH": "瑞士", "VIE": "奥地利", "PRG": "捷克", "STO": "瑞典",
            "CPH": "丹麦", "OSL": "挪威", "HEL": "芬兰", "WAW": "波兰",
            "BUD": "匈牙利", "ATH": "希腊",
            # 美洲
            "SJC": "美国", "LAX": "美国", "SFO": "美国", "SEA": "美国",
            "PHX": "美国", "DEN": "美国", "DFW": "美国", "HOU": "美国",
            "MIA": "美国", "ATL": "美国", "CHI": "美国", "NYC": "美国",
            "EWR": "美国", "IAD": "美国", "BOS": "美国", "TOR": "加拿大",
            "YTO": "加拿大", "MON": "加拿大", "SAO": "巴西", "RIO": "巴西",
            "MEX": "墨西哥",
            # 大洋洲
            "SYD": "澳大利亚", "MEL": "澳大利亚", "AKL": "新西兰",
            # 中东/非洲
            "DXB": "阿联酋", "JED": "沙特阿拉伯", "CAI": "埃及",
            "JNB": "南非", "CPT": "南非"
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
        
        self.process_btn = tk.Button(btn_frame, text="开始处理数据", font=("微软雅黑", 10), 
                                     bg="#4CAF50", fg="white", command=self.start_process_thread)
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = tk.Button(btn_frame, text="清空所有内容", font=("微软雅黑", 10), 
                                   bg="#f44336", fg="white", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = tk.Button(btn_frame, text="保存处理结果", font=("微软雅黑", 10), 
                                  bg="#2196F3", fg="white", command=self.save_result, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(btn_frame, text="状态：就绪", font=("微软雅黑", 9), fg="#666")
        self.status_label.pack(side=tk.RIGHT)

        # 3. 输出区域
        output_frame = tk.Frame(root, bd=2, relief=tk.GROOVE, padx=5, pady=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(output_frame, text="处理结果输出区（可直接复制）：", font=("微软雅黑", 10)).pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(output_frame, font=("Consolas", 9), wrap=tk.NONE, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)

    # ========== 核心功能 ==========
    def start_process_thread(self):
        """启动多线程处理数据（避免GUI卡顿）"""
        if self.is_processing:
            messagebox.showwarning("提示", "正在处理数据，请稍候！")
            return
        
        # 获取输入数据
        input_data = self.input_text.get("1.0", tk.END).strip()
        if not input_data:
            messagebox.showerror("错误", "请先粘贴原始数据！")
            return
        
        # 启动子线程
        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态：正在处理...")
        self.root.update_idletasks()
        
        process_thread = threading.Thread(target=self.process_data, args=(input_data,))
        process_thread.daemon = True  # 守护线程，关闭窗口时自动退出
        process_thread.start()

    def process_data(self, input_data):
        """处理数据的核心函数（子线程运行）"""
        try:
            # 分割行并过滤空行
            lines = [line.strip() for line in input_data.split("\n") if line.strip()]
            if not lines:
                self.update_gui("error", "未检测到有效数据！")
                return
            
            # 解析数据
            formatted_results = []
            error_lines = []
            
            # 跳过表头，处理数据行
            for idx, line in enumerate(lines[1:], 1):
                try:
                    fields = [field.strip() for field in line.split(",")]
                    # 校验字段数量（至少8个字段：IP,已发送,已接收,丢包率,平均延迟,下载速度,地区码,端口）
                    if len(fields) < 8:
                        error_lines.append(f"第{idx+1}行：字段数量不足（需至少8个）→ {line}")
                        continue
                    
                    # 提取核心字段
                    ip = fields[0]
                    port = fields[7]
                    region_code = fields[6]
                    download_speed = fields[5]
                    
                    # 映射地区码
                    country = self.region_mapping.get(region_code, f"未知地区({region_code})")
                    
                    # 【关键修改】去掉序号，只保留核心内容
                    formatted_line = f"{ip}:{port}#{country} {download_speed}MB/s"
                    formatted_results.append(formatted_line)
                    
                except Exception as e:
                    error_lines.append(f"第{idx+1}行：处理失败 → {str(e)} | 内容：{line}")
            
            # 整理最终结果
            result_text = "\n".join(formatted_results)
            if error_lines:
                result_text += "\n\n【错误提示】以下行数据异常已跳过：\n" + "\n".join(error_lines)
            
            # 更新GUI（通过主线程）
            self.update_gui("success", result_text)
            
        except Exception as e:
            self.update_gui("error", f"处理失败：{str(e)}")

    def update_gui(self, status, content):
        """更新GUI内容（必须在主线程运行）"""
        def _update():
            if status == "success":
                # 启用输出框并填充结果
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", content)
                self.output_text.config(state=tk.DISABLED)
                
                # 计算有效数据条数（排除错误提示行）
                valid_count = len([line for line in content.split("\n") if not line.startswith("【错误提示】") and line.strip()])
                self.status_label.config(text=f"状态：处理完成（共{valid_count}条有效数据）")
                self.save_btn.config(state=tk.NORMAL)
            elif status == "error":
                messagebox.showerror("处理错误", content)
                self.status_label.config(text=f"状态：处理失败 - {content[:20]}...")
            
            # 恢复按钮状态
            self.is_processing = False
            self.process_btn.config(state=tk.NORMAL)
        
        # 确保在主线程更新GUI
        self.root.after(0, _update)

    def clear_all(self):
        """清空输入和输出"""
        self.input_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.status_label.config(text="状态：就绪")
        self.save_btn.config(state=tk.DISABLED)

    def save_result(self):
        """保存处理结果到文件"""
        result_data = self.output_text.get("1.0", tk.END).strip()
        if not result_data:
            messagebox.showwarning("提示", "无结果可保存！")
            return
        
        # 选择保存路径
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
    # 适配高DPI屏幕（Windows）
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
    
    # 启动GUI
    root = tk.Tk()
    app = IPDataFormatterGUI(root)
    root.mainloop()
