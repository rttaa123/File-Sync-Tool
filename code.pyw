# 导入所需的库
import tkinter as tk  # GUI界面库
from tkinter import ttk, filedialog, messagebox  # tkinter的附加组件
import os  # 操作系统接口
import sys  # 系统相关功能
import shutil  # 文件操作工具
import json  # JSON数据处理
from datetime import datetime  # 日期时间处理
import threading  # 多线程支持
import logging  # 日志记录
import time  # 用于自动同步的时间间隔
import base64

class FileSyncTool:
    """
    文件同步工具的主类，用于创建和管理文件同步任务
    """
    def __init__(self, root):
        self.root = root
        self.root.title("文件同步工具")
        self.root.geometry("620x400")
        
        # 设置任务文件和日志文件路径
        self.app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.tasks_file = os.path.join(self.app_path, "sync_tasks.json")
        self.error_log_file = os.path.join(self.app_path, "sync_error.log")
        self.operation_log_file = os.path.join(self.app_path, "sync_operation.log")
        
        self.auto_sync_thread = None
        self.auto_sync_running = False
        
        # 设置两个日志处理器
        # 错误日志配置
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        error_handler.setFormatter(error_formatter)
        
        # 操作日志配置
        operation_handler = logging.FileHandler(self.operation_log_file)
        operation_handler.setLevel(logging.INFO)
        operation_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        operation_handler.setFormatter(operation_formatter)
        
        # 配置根日志记录器
        self.logger = logging.getLogger('FileSyncTool')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(operation_handler)
        
        # 确保配置文件存在并初始化
        try:
            if not os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                self.logger.info("创建新的任务配置文件")
        except Exception as e:
            error_msg = f"初始化配置文件失败: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("错误", error_msg)
        
        self.tasks = self.load_tasks()
        self.create_gui()
        self.logger.info("文件同步工具启动成功")

    def create_gui(self):
        """
        创建图形用户界面的各个组件
        """
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # 添加工具栏按钮
        ttk.Button(toolbar, text="新建任务", command=self.new_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除任务", command=self.delete_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="执行同步", command=self.execute_sync).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="自动同步设置", command=self.show_auto_sync_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="加密设置", command=self.show_encrypt_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="解密设置", command=self.show_decrypt_settings).pack(side=tk.LEFT, padx=2)

        # 创建任务列表框架
        list_frame = ttk.LabelFrame(main_frame, text="同步任务列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 定义表格列
        columns = ('任务名称', '源路径', '目标路径', '上次同步时间', '自动同步')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        
        # 设置表格列头和列宽
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.column('任务名称', width=100)
        self.tree.column('源路径', width=150)
        self.tree.column('目标路径', width=150)
        self.tree.column('上次同步时间', width=120)
        self.tree.column('自动同步', width=60)
        
        # 添加垂直滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置表格和滚动条
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, pady=(5, 0))
        
        self.update_task_list()  # 更新任务列表显示

        # 启动自动同步检查
        self.start_auto_sync_checker()

    def encrypt_file(self, file_path):
        with open(file_path, 'rb') as file:
            file_data = file.read()
        encoded_data = base64.b64encode(file_data)
        with open(file_path, 'wb') as file:
            file.write(encoded_data)

    def encrypt_directory(self, dir_path):
        for root, dirs, files in os.walk(dir_path):
            for name in files:
                file_path = os.path.join(root, name)
                if os.path.isfile(file_path):
                    self.encrypt_file(file_path)

    def decrypt_file(self, file_path):
        with open(file_path, 'rb') as file:
            file_data = file.read()
        decoded_data = base64.b64decode(file_data)
        with open(file_path, 'wb') as file:
            file.write(decoded_data)

    def decrypt_directory(self, dir_path):
        for root, dirs, files in os.walk(dir_path):
            for name in files:
                file_path = os.path.join(root, name)
                if os.path.isfile(file_path):
                    self.decrypt_file(file_path)

    def show_encrypt_settings(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要设置的任务！")
            return

        task_values = self.tree.item(selected[0])['values']
        task_name = str(task_values[0])
        task = next((t for t in self.tasks if t['name'] == task_name), None)

        if not task:
            return

        # 创建加密设置对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("加密设置")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # 创建设置框架
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # 选择加密路径
        tk.Label(frame, text="选择加密路径:").pack(pady=5)
        encrypt_path_var = tk.StringVar(value="源路径")
        ttk.Radiobutton(frame, text="源路径", variable=encrypt_path_var, value=task['source']).pack(pady=5)
        ttk.Radiobutton(frame, text="目标路径", variable=encrypt_path_var, value=task['target']).pack(pady=5)

        # 加密开关
        encrypt_var = tk.BooleanVar(value=task.get('encrypt', False))
        ttk.Checkbutton(frame, text="启用加密", variable=encrypt_var).pack(pady=5)

        def save_settings():
            task['encrypt'] = encrypt_var.get()
            task['encrypt_path'] = encrypt_path_var.get()
            self.save_tasks()
            dialog.destroy()

            def submit_password():
                password1 = entry_password1.get()
                password2 = entry_password2.get()
    
                if password1 == password2:
                    task['password'] = password1
                    self.encrypt_directory(task['encrypt_path'])
                    messagebox.showwarning("提示", "设置成功，已加密")
                    self.logger.info(f"加密成功：{task['encrypt_path']}")
                    root.destroy()
                else:
                    messagebox.showwarning("错误提示", "两次输入密码不一致！")

            # 创建主窗口
            root = tk.Tk()
            root.title("设置密码")

            # 创建标签和输入框
            label_password1 = ttk.Label(root, text="请输入密码:")
            label_password1.grid(row=0, column=0, padx=10, pady=10)
            entry_password1 = ttk.Entry(root, show='*')
            entry_password1.grid(row=0, column=1, padx=10, pady=10)

            label_password2 = ttk.Label(root, text="请再次确认密码:")
            label_password2.grid(row=1, column=0, padx=10, pady=10)
            entry_password2 = ttk.Entry(root, show='*')
            entry_password2.grid(row=1, column=1, padx=10, pady=10)

            # 创建提交按钮
            submit_button = ttk.Button(root, text="提交", command=submit_password)
            submit_button.grid(row=2, columnspan=2, pady=10)

        # 添加保存和取消按钮
        ttk.Button(frame, text="保存", command=save_settings).pack(pady=10)
        ttk.Button(frame, text="取消", command=dialog.destroy).pack(pady=5)

    def show_decrypt_settings(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要设置的任务！")
            return

        task_values = self.tree.item(selected[0])['values']
        task_name = str(task_values[0])
        task = next((t for t in self.tasks if t['name'] == task_name), None)

        if not task:
            return

        # 创建解密设置对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("解密设置")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # 创建设置框架
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # 选择解密路径
        tk.Label(frame, text="选择解密路径:").pack(pady=5)
        decrypt_path_var = tk.StringVar(value="源路径")
        ttk.Radiobutton(frame, text="源路径", variable=decrypt_path_var, value=task['source']).pack(pady=5)
        ttk.Radiobutton(frame, text="目标路径", variable=decrypt_path_var, value=['target']).pack(pady=5)

        # 解密开关
        decrypt_var = tk.BooleanVar(value=task.get('decrypt', False))
        ttk.Checkbutton(frame, text="启用解密", variable=decrypt_var).pack(pady=5)

        def save_settings():
            task['decrypt'] = decrypt_var.get()
            task['decrypt_path'] = decrypt_path_var.get()
            self.save_tasks()
            dialog.destroy()

            def submit_password():
                password = entry_password.get()
                # 记录密码（这里只是打印出来，实际应用中可以保存到文件或数据库）
                if password == task['password']:
                    self.decrypt_directory(task['decrypt_path'])
                    messagebox.showwarning("提示", "解密成功")
                    self.logger.info(f"解密成功：{task['decrypt_path']}")
                    root.destroy()
                else:
                    messagebox.showwarning("错误", "输入密码不正确！")

            # 创建主窗口
            root = tk.Tk()
            root.title("输入密码")

            # 创建标签和输入框
            label_password = ttk.Label(root, text="请输入密码:")
            label_password.grid(row=0, column=0, padx=10, pady=10)
            entry_password = ttk.Entry(root, show='*')
            entry_password.grid(row=0, column=1, padx=10, pady=10)

            # 创建提交按钮
            submit_button = ttk.Button(root, text="提交", command=submit_password)
            submit_button.grid(row=1, columnspan=2, pady=10)

        # 添加保存和取消按钮
        ttk.Button(frame, text="保存", command=save_settings).pack(pady=10)
        ttk.Button(frame, text="取消", command=dialog.destroy).pack(pady=5)

    def show_auto_sync_settings(self):
        """
        显示自动同步设置对话框
        """
        selected = self.tree.selection()
        if not selected:
            self.logger.warning("自动同步设置失败：未选择任务")
            messagebox.showwarning("警告", "请选择要设置的任务！")
            return

        task_values = self.tree.item(selected[0])['values']
        task_name =str(task_values[0])
        task = next((t for t in self.tasks if t['name'] == task_name), None)

        if not task:
            return

        # 创建设置对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("自动同步设置")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # 创建设置框架
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # 自动同步开关
        auto_sync_var = tk.BooleanVar(value=task.get('auto_sync', False))
        ttk.Checkbutton(frame, text="启用自动同步", variable=auto_sync_var).pack(pady=5)

        # 同步间隔设置
        ttk.Label(frame, text="同步间隔(分钟):").pack(pady=5)
        interval_var = tk.StringVar(value=str(task.get('sync_interval', 30)))
        interval_entry = ttk.Entry(frame, textvariable=interval_var)
        interval_entry.pack(pady=5)

        def save_settings():
            try:
                interval = int(interval_var.get())
                if interval < 1:
                    self.logger.warning(f"自动同步设置失败：无效的同步间隔 - {interval}")
                    messagebox.showerror("错误", "同步间隔必须大于0分钟！", parent=dialog)
                    return
                
                task['auto_sync'] = auto_sync_var.get()
                task['sync_interval'] = interval
                self.save_tasks()
                self.update_task_list()
                self.logger.info(f"更新自动同步设置：{task_name}，间隔：{interval}分钟")
                dialog.destroy()
            except ValueError:
                self.logger.warning("自动同步设置失败：同步间隔不是有效数字")
                messagebox.showerror("错误", "请输入有效的数字！", parent=dialog)
                
        # 添加保存和取消按钮
        ttk.Button(frame, text="保存", command=save_settings).pack(pady=10)
        ttk.Button(frame, text="取消", command=dialog.destroy).pack(pady=5)

    def start_auto_sync_checker(self):
        """
        启动自动同步检查器
        """
        def auto_sync_checker():
            while True:
                try:
                    current_time = time.time()
                    for task in self.tasks:
                        if task.get('auto_sync', False):
                            last_sync_time = 0
                            if 'last_sync' in task:
                                try:
                                    last_sync_time = datetime.strptime(
                                        task['last_sync'], 
                                        "%Y-%m-%d %H:%M:%S"
                                    ).timestamp()
                                except ValueError:
                                    last_sync_time = 0
                            
                            interval_minutes = task.get('sync_interval', 30)
                            if current_time - last_sync_time >= interval_minutes * 60:
                                self.sync_single_task(task)
                                
                except Exception as e:
                    logging.error(f"自动同步检查错误: {str(e)}")
                
                time.sleep(60)  # 每分钟检查一次

        # 启动自动同步检查线程
        if not self.auto_sync_thread or not self.auto_sync_thread.is_alive():
            self.auto_sync_thread = threading.Thread(
                target=auto_sync_checker, 
                daemon=True
            )
            self.auto_sync_thread.start()

    def sync_single_task(self, task):
        """
        同步单个任务
        Args:
            task: 要同步的任务字典
        """
        if self.sync_files(task['source'], task['target']):
            task['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_tasks()
            self.update_task_list()

    def update_task_list(self):
        """
        更新任务列表显示
        """
        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加所有任务到列表
        for task in self.tasks:
            # 获取自动同步显示文本
            if task.get('auto_sync', False):
                auto_sync_text = f"{task.get('sync_interval', 30)}分钟"
            else:
                auto_sync_text = "否"
                
            self.tree.insert('', tk.END, values=(
                task['name'],
                task['source'],
                task['target'],
                task.get('last_sync', '从未同步'),
                auto_sync_text
            ))
    
    # def load_tasks(self):
    #     """
    #     从配置文件加载同步任务
    #     Returns:
    #         list: 任务列表，如果加载失败则返回空列表
    #     """
    #     try:
    #         if os.path.exists(self.tasks_file):
    #             with open(self.tasks_file, 'r', encoding='utf-8') as f:
    #                 return json.load(f)
    #         else:
    #             # 如果文件不存在，创建一个空文件
    #             with open(self.tasks_file, 'w', encoding='utf-8') as f:
    #                 json.dump([], f, ensure_ascii=False, indent=2)
    #             return []
    #     except Exception as e:
    #         error_msg = f"加载任务失败: {str(e)}"
    #         logging.error(error_msg)
    #         return []
    def load_tasks(self):
        """
        从配置文件加载同步任务
        Returns:
            list: 任务列表，如果加载失败则返回空列表
        """
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                    self.logger.info(f"成功加载 {len(tasks)} 个同步任务")
                    return tasks
            else:
                with open(self.tasks_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                self.logger.info("创建新的任务配置文件")
                return []
        except Exception as e:
            error_msg = f"加载任务失败: {str(e)}"
            self.logger.error(error_msg)
            return []
        
    def save_tasks(self):
        """
        保存同步任务到配置文件
        """
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error_msg = f"保存任务失败: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("错误", error_msg)

    
    
    def new_task(self):
        """
        创建新的同步任务的对话框
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("新建同步任务")
        dialog.geometry("500x200")
        dialog.transient(self.root)  # 设置为主窗口的子窗口
        dialog.grab_set()  # 模态窗口设置
        
        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 任务名称输入框
        ttk.Label(main_frame, text="任务名称:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.grid(row=0, column=1, columnspan=2, sticky='we', padx=5, pady=5)
        
        # 源路径选择
        ttk.Label(main_frame, text="源路径:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        source_entry = ttk.Entry(main_frame, width=40)
        source_entry.grid(row=1, column=1, sticky='we', padx=5, pady=5)
        ttk.Button(main_frame, text="浏览", command=lambda: source_entry.delete(0, tk.END) or source_entry.insert(0, filedialog.askdirectory())).grid(row=1, column=2, padx=5)
        
        # 目标路径选择
        ttk.Label(main_frame, text="目标路径:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        target_entry = ttk.Entry(main_frame, width=40)
        target_entry.grid(row=2, column=1, sticky='we', padx=5, pady=5)
        ttk.Button(main_frame, text="浏览", command=lambda: target_entry.delete(0, tk.END) or target_entry.insert(0, filedialog.askdirectory())).grid(row=2, column=2, padx=5)
        
        def save():
            name = name_entry.get().strip()
            source = source_entry.get().strip()
            target = target_entry.get().strip()
            
            if not all([name, source, target]):
                self.logger.warning("新建任务失败：存在空字段")
                messagebox.showerror("错误", "请填写所有字段！", parent=dialog)
                return
                
            if not os.path.exists(source):
                self.logger.warning(f"新建任务失败：源路径不存在 - {source}")
                messagebox.showerror("错误", "源路径不存在！", parent=dialog)
                return
                
            if any(task['name'] == name for task in self.tasks):
                self.logger.warning(f"新建任务失败：任务名称已存在 - {name}")
                messagebox.showerror("错误", "任务名称已存在！", parent=dialog)
                return
            
            self.tasks.append({
                'name': name,
                'source': source,
                'target': target,
                'password': ""
            })
            self.save_tasks()
            self.update_task_list()
            self.logger.info(f"成功创建新任务：{name}")
            dialog.destroy()

        
        # 添加保存和取消按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="保存", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def sync_files(self, source_dir, target_dir):
        """
        执行文件同步操作
        Args:
            source_dir: 源目录路径
            target_dir: 目标目录路径
        Returns:
            bool: 同步是否成功
        """
        try:
            self.logger.info(f"开始同步：{source_dir} -> {target_dir}")
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                self.logger.info(f"创建目标目录：{target_dir}")
            
            file_count = 0
            for root, dirs, files in os.walk(source_dir):
                rel_path = os.path.relpath(root, source_dir)
                target_root = os.path.join(target_dir, rel_path)
                
                for dir_name in dirs:
                    target_dir_path = os.path.join(target_root, dir_name)
                    if not os.path.exists(target_dir_path):
                        os.makedirs(target_dir_path)
                        self.logger.info(f"创建目录：{target_dir_path}")
                
                for filename in files:
                    file_extension = filename.split(".")[-1]
                    if file_extension in ['~', 'temp', 'bak', 'json', 'lock', 'log', 'tmp']:
                        continue
                    
                    source_file = os.path.join(root, filename)
                    target_file = os.path.join(target_root, filename)
                    
                    self.status_var.set(f"正在同步: {filename}")
                    self.root.update_idletasks()
                    
                    if not os.path.exists(target_file) or \
                        os.path.getmtime(source_file) > os.path.getmtime(target_file):
                        threading.Thread(target=shutil.copy2(source_file, target_file), daemon=True).start()
                        #self.logger.info(f"复制文件：{filename}")
                        file_count += 1
            
            self.delete_deleted_files(source_dir, target_dir)
            self.logger.info(f"同步完成，共同步 {file_count} 个文件")
            return True
            
        except Exception as e:
            error_msg = f"同步失败: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("错误", error_msg)
            return False

    def execute_sync(self):
        """
        执行选中的同步任务
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要执行的任务！")
            return
        
        # 获取选中的任务
        task_values = self.tree.item(selected[0])['values']
        task_name = str(task_values[0])
        task = next((t for t in self.tasks if t['name'] == task_name), None)
        
        if task:
            def sync_thread():
                """
                在新线程中执行同步操作
                """
                if self.sync_files(task['source'], task['target']):
                    task['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.save_tasks()
                    self.status_var.set("同步完成")
                else:
                    self.status_var.set("同步失败")
                self.update_task_list()
            
            # 启动同步线程
            threading.Thread(target=sync_thread, daemon=True).start()

    def delete_task(self):
        selected = self.tree.selection()
        if not selected:
            self.logger.warning("删除任务失败：未选择任务")
            messagebox.showwarning("警告", "请选择要删除的任务！")
            return
        
        if messagebox.askyesno("确认", "确定要删除选中的任务吗？"):
            task_values = self.tree.item(selected[0])['values']
            task_name = str(task_values[0])
            self.tasks = [t for t in self.tasks if t['name'] != task_name]
            self.save_tasks()
            self.update_task_list()
            self.logger.info(f"成功删除任务：{task_name}")

    def delete_deleted_files(self,source_dir, target_dir):
        for root, dirs, files in os.walk(target_dir):
            rel_path = os.path.relpath(root, target_dir)
            source_root = os.path.join(source_dir, rel_path)
            for dir_name in dirs:
                sourse_dir_path = os.path.join(source_root, dir_name)
                if not os.path.exists(sourse_dir_path):
                    shutil.rmtree(os.path.join(root, dir_name))
            for filename in files:
                target_file = os.path.join(root, filename)
                sourse_file = os.path.join(source_root, filename)
                if not os.path.exists(sourse_file):
                    os.remove(os.path.join(root, filename))

def main():
    root = tk.Tk()
    app = FileSyncTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()