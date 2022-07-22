import os
import time
import shutil
import shelve
import sqlite3
import winsound

import ChatRoom
import threading
from datetime import datetime, timedelta

import ttkbootstrap as ttk
from ttkbootstrap.style import Bootstyle
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText

DATA_PATH = ".Room"
IMAGE_PATH = os.path.join(DATA_PATH, "image")
# 主图标
MAIN_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-monitor-32.ico')
# 邮件图标
MAIL_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-mail-24.ico')
# 配置图标
CONFIG_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-mail-configuration-24.ico')
# 设置图标
SETTING_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8_settings_24px_2.ico')

# 初始化文件
data_path = os.path.join(ChatRoom.__file__.replace("__init__.py", ""), ".Room")
if not os.path.exists(DATA_PATH):
    shutil.copytree(data_path, DATA_PATH)

class LogDB():
    def __init__(self):
        # 初始化数据库
        self.sql_file_path = os.path.join(DATA_PATH, "log.db")
        if not os.path.isfile(self.sql_file_path):
            conn = sqlite3.connect(self.sql_file_path)
            cursor = conn.cursor()
            cursor.execute('create table log (Name varchar(20) , LogID varchar(20), LogType varchar(10), InsertTime varchar(20), LogInfo varchar(100))')
            conn.commit()
            conn.close()

    def insert_log(self, Name, LogID, LogType, InsertTime, LogInfo):

        conn = sqlite3.connect(self.sql_file_path)
        cursor = conn.cursor()
        try:
            cursor.execute('insert into log (Name, LogID, LogType, InsertTime, LogInfo) values ("{0}", "{1}", "{2}", "{3}", "{4}")'.format(
                Name.replace('"','""'), LogID.replace('"','""'), LogType.replace('"','""'), InsertTime.replace('"','""'), LogInfo.replace('"','""'),
            ))
            conn.commit()
        finally:
            conn.close()

class MyConfig():
    def __init__(self):
        # 配置文件
        self.my_config_file_path = os.path.join(DATA_PATH, "config.sh")

        if not os.path.isfile(os.path.join(DATA_PATH, "config.sh.dat")):
            self.set_config("my_mail_type_config", {
                # 默认错误配置
                "ERR" : {
                    # 是否发送邮件
                    "mail" : True,
                    # 该类型邮件标签
                    "tag" : "Crimson",
                    # 超时(在这个时间前不发送邮件)
                    "deadline" : '1970-01-01 00:00:00',
                },
                "INFO" : {
                    # 是否发送邮件
                    "mail" : False,
                    # 该类型邮件标签
                    "tag" : None,
                    # 超时(在这个时间前不发送邮件)
                    "deadline" : '1970-01-01 00:00:00',
                },
                # 默认配置
                "DEFAULT" : {
                    # 是否发送邮件
                    "mail" : False,
                    # 该类型邮件标签
                    "tag" : None,
                    # 超时(在这个时间前不发送邮件)
                    "deadline" : '1971-01-01 00:00:00',
                }
            })

    def get_config(self, name, default=None):
        with shelve.open(self.my_config_file_path) as sh:
            try:
                return sh[name]
            except KeyError:
                return default

    def set_config(self, name, value):
        with shelve.open(self.my_config_file_path) as sh:
            sh[name] = value

class RoomLog(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack(fill=BOTH, expand=YES)

        # 系统变量
        # 数据库对象
        self.my_db_object = LogDB()
        # 配置文件
        self.my_config = MyConfig()
        # 警告音文件路径
        self.my_err_audio_file = os.path.join(DATA_PATH, "audio", "err.wav")
        self.my_log_id = 1
        self.my_user_frame_dict = {}
        self.my_user_child_frame_dict = {}
        # 标签列表
        self.my_tag_list = ["None"]
        # 日志所有item集合
        self.my_log_all_item_set = set()
        # 0: 正常模式 1:暂停 2:停止
        self.my_mail_mode = 0
        # 邮件缓存信息列表
        self.my_mail_buffer_list = []
        self.my_mail_buffer_list_lock = threading.Lock()
        # 邮件类型配置字典
        self.my_mail_type_config = self.my_config.get_config("my_mail_type_config")

        # 初始化组件
        self.func_init_theme()
        self.func_init_pic()
        self.func_init_buttonbar()
        self.func_init_left_frame()
        self.func_init_right_frame()

        # 初始化自己节点
        self.func_update_user("Room")

        # TEST 测试用户
        self.func_update_user("Andy")
        self.func_update_user("Andy2")
        self.func_update_user("Andy3")
        self.func_update_user("Andy4")
        self.func_update_user("Andy5")
        self.func_update_user("Andy6")
        self.func_update_user("Andy7")
        self.func_update_user("Andy8")

        # 启动服务
        self.auto_clena_log_server()

    # =================== 初始化函数 ===========================
    def func_init_theme(self):
        """ 设置默认主题 """
        style = ttk.Style()
        # print(style.theme_names())
        # ['cosmo', 'flatly', 'litera', 'minty', 'lumen', 'sandstone', 'yeti', 'pulse', 'united', 'morph', 'journal', 'darkly', 'superhero', 'solar', 'cyborg', 'vapor', 'simplex', 'cerculean']
        user_theme = self.my_config.get_config('theme', "darkly")
        style.theme_use(user_theme)

    def func_init_pic(self):
        """ 初始化组件图片 """
        image_files = {
            'settings': 'icons8_settings_24px_2.png',
            'theme': 'icons8-theme-24.png',
            'search': 'icons8_search_24px.png',
            'remove': 'icons8-remove-16.png',
            'mail-config': 'icons8-mail-configuration-24.png',
            'mail-ok': 'icons8-mail-24.png',
            'mail-no': 'icons8-mail-error-24.png',
            'mail-clean': 'icons8-broom-24.png',
            'log-clean': 'icons8-broom2-24.png',
            'plus6': 'icons8-plus6-24.png',
            'plus12': 'icons8-plus12-24.png',
            'delete': 'icons8-delete-24.png',
            'restore': 'icons8-restore-page-24.png',
        }

        self.photoimages = []
        for key, values in image_files.items():
            _path = os.path.join(IMAGE_PATH, values)
            self.photoimages.append(ttk.PhotoImage(name=key, file=_path))

    def func_init_buttonbar(self):
        """ 初始化顶部按钮栏 """
        # buttonbar
        buttonbar = ttk.Frame(self, style='primary.TFrame')
        buttonbar.pack(fill=X, pady=1, side=TOP)

        ## 邮件和错误配置
        def config_err():
            config_app = ttk.Toplevel(title="Config")
            config_app.iconbitmap(CONFIG_ICO_PATH)
            config_app.geometry('900x500')

            # 上方配置栏
            config_frame = ttk.Frame(config_app, bootstyle=SECONDARY)
            config_frame.pack(fill=BOTH, side=TOP)

            # 下方按钮
            button_frame = ttk.Frame(config_app, bootstyle=DARK)
            button_frame.pack(fill=BOTH, side=TOP)

            # 插入一行新配置
            def insert_a_line(all_config_controls_dict, name, mail, tag, deadline):
                # 一行配置
                config_line_frame = ttk.Frame(config_frame)
                config_line_frame.pack(fill=BOTH, side=TOP, ipadx=2, ipady=2)

                label1 = ttk.Label(config_line_frame, text="名称: ")
                label1.pack(fill=BOTH, side=LEFT)
                entry1 = ttk.Entry(config_line_frame, width=7, bootstyle=PRIMARY)
                entry1.insert(END, name)
                entry1.pack(fill=BOTH, side=LEFT)
                label2 = ttk.Label(config_line_frame, text=" 邮件通知: ")
                label2.pack(fill=BOTH, side=LEFT)
                entry2 = ttk.Combobox(config_line_frame, width=2, value=("是", "否"), bootstyle=PRIMARY)
                entry2.insert(END, mail)
                entry2.pack(fill=BOTH, side=LEFT)
                label3 = ttk.Label(config_line_frame, text=" 颜色标签: ")
                label3.pack(fill=BOTH, side=LEFT)
                entry3 = ttk.Combobox(config_line_frame, width=12, value=self.my_tag_list, bootstyle=PRIMARY)
                entry3.insert(END, tag)
                entry3.pack(fill=BOTH, side=LEFT)
                label4 = ttk.Label(config_line_frame, text=" 邮件禁用超时时间: ")
                label4.pack(fill=BOTH, side=LEFT)
                entry4 = ttk.Entry(config_line_frame, width=17, bootstyle=PRIMARY)
                entry4.insert(END, deadline)
                entry4.pack(fill=BOTH, side=LEFT)

                def func_restore():
                    entry4.delete(0, END)
                    entry4.insert(END, '1970-01-01 00:00:00')
                button_restore = ttk.Button(config_line_frame, text="restore", image='restore', command=func_restore)
                button_restore.pack(fill=BOTH, side=LEFT)

                def func_plus6():
                    get_date = datetime.strptime(entry4.get(), '%Y-%m-%d %H:%M:%S')
                    if get_date.year == 1970:
                        # 取当前时间
                        get_date = datetime.now()

                    date = get_date + timedelta(hours=6)
                    entry4.delete(0, END)
                    entry4.insert(END, date.strftime('%Y-%m-%d %H:%M:%S'))
                button_plus6 = ttk.Button(config_line_frame, text="plus6", image='plus6', command=func_plus6)
                button_plus6.pack(fill=BOTH, side=LEFT)

                def func_plus12():
                    get_date = datetime.strptime(entry4.get(), '%Y-%m-%d %H:%M:%S')
                    if get_date.year == 1970:
                        # 取当前时间
                        get_date = datetime.now()

                    date = get_date + timedelta(hours=12)
                    entry4.delete(0, END)
                    entry4.insert(END, date.strftime('%Y-%m-%d %H:%M:%S'))
                button_plus12 = ttk.Button(config_line_frame, text="plus12", image='plus12', command=func_plus12)
                button_plus12.pack(fill=BOTH, side=LEFT)

                def func_del():
                    del all_config_controls_dict[config_line_frame]
                    config_line_frame.destroy()
                del_button = ttk.Button(config_line_frame, text="del", image='delete', command=func_del, bootstyle=LIGHT)
                del_button.pack(fill=BOTH, side=RIGHT)

                all_config_controls_dict[config_line_frame] = {
                        # Entry
                        "name"      : entry1,
                        # Combobox
                        "mail"      : entry2,
                        # Combobox
                        "tag"       : entry3,
                        # Entry
                        "deadline"  : entry4,
                    }

            all_config_controls_dict = {}

            # 插入已经有的配置
            for name, config_value in self.my_mail_type_config.items():
                if name != "DEFAULT":
                    insert_a_line(
                        all_config_controls_dict,
                        name,
                        "是" if config_value["mail"] else "否",
                        config_value["tag"] if config_value["tag"] else "None",
                        config_value["deadline"],
                    )

            # 添加一行新的
            def add():
                insert_a_line(
                        all_config_controls_dict,
                        "New",
                        "否",
                        "None",
                        "1970-01-01 00:00:00",
                    )
            add_button = ttk.Button(button_frame, width=52, bootstyle=DARK, text="添加", command=add)
            add_button.pack(fill=BOTH, side=LEFT)

            # 保存全部
            def save():
                tmp_my_mail_type_config = {}
                tmp_my_mail_type_config["DEFAULT"] = self.my_mail_type_config["DEFAULT"]
                for _, config_value_dict in all_config_controls_dict.items():
                    name = config_value_dict["name"].get()
                    mail = config_value_dict["mail"].get()
                    tag = config_value_dict["tag"].get()
                    deadline = config_value_dict["deadline"].get()

                    mail = True if mail == "是" else False
                    tag = None if tag == "None" else tag

                    tmp_my_mail_type_config[name] = {
                        "mail" : mail,
                        "tag" : tag,
                        "deadline" : deadline,
                    }

                # 保存内存
                self.my_mail_type_config = tmp_my_mail_type_config
                # 保存配置
                self.my_config.set_config("my_mail_type_config", self.my_mail_type_config)

                self.func_insert_information("日志配置保存成功!当前配置:")
                for name, config_dict in self.my_mail_type_config.items():
                    self.func_insert_information("{0:<12} 邮件: {1:<6} 标签: {2:<10} 超时: {3}".format(
                        name,
                        "开" if config_dict["mail"] else "关",
                        "None" if config_dict["tag"] == None else config_dict["tag"],
                        config_dict["deadline"],
                    ))

            self.all_config_controls_dict = all_config_controls_dict

            save_button = ttk.Button(button_frame, width=52, bootstyle=DARK, text="保存", command=save)
            save_button.pack(fill=BOTH, side=RIGHT)

            config_app.mainloop()

        btn = ttk.Button(
            master=buttonbar,
            text='Config',
            image='mail-config',
            compound=LEFT,
            command=config_err,
        )
        btn.pack(side=LEFT, ipadx=5, ipady=5, padx=0, pady=1)

        ## 清空邮件
        def clen_mail_buffer():
            self.my_mail_buffer_list_lock.acquire()
            try:
                mail_len = len(self.my_mail_buffer_list)
                self.my_mail_buffer_list = []
                self.func_insert_information("清空了 {0} 条邮件信息!".format(mail_len))
            finally:
                self.my_mail_buffer_list_lock.release()

        btn = ttk.Button(
            master=buttonbar,
            text='Clean',
            image='mail-clean',
            compound=LEFT,
            command=clen_mail_buffer,
        )
        btn.pack(side=LEFT, ipadx=5, ipady=5, padx=0, pady=1)

        ## 显示邮件
        def show_mail():
            if self.my_mail_buffer_list:
                message = ""
                for log_list in self.my_mail_buffer_list:
                    message += "{0}\n".format(log_list)
            else:
                message = "mail buffer is clean."

            show_mail_app = ttk.Toplevel(title="Mail Buffer")
            show_mail_app.iconbitmap(MAIL_ICO_PATH)
            show_mail_app.geometry('1000x600')

            show_mail_label = ttk.Label(
                master=show_mail_app,
                text=message,
                font=ttk.font.Font(size=13),
            )
            show_mail_label.pack()

            show_mail_app.mainloop()

        btn = ttk.Button(
            master=buttonbar,
            text='Show',
            image='mail-ok',
            compound=LEFT,
            command=show_mail,
        )
        btn.pack(side=LEFT, ipadx=5, ipady=5, padx=0, pady=1)

        ## 邮件开关
        btn = ttk.Button(
            master=buttonbar,
            text='Switch',
            image='mail-ok',
            compound=LEFT,
            command=self.func_switch_mail,
        )
        btn.pack(side=LEFT, ipadx=5, ipady=5, padx=0, pady=1)
        self.mail_switch_btn = btn

        ## settings
        _func = lambda: Messagebox.ok(message='Changing settings')
        btn = ttk.Button(
            master=buttonbar,
            # text='Settings',
            image='settings',
            compound=LEFT,
            command=_func,
        )
        btn.pack(side=RIGHT, ipadx=5, ipady=5, padx=0, pady=1)

        ## theme
        def get_theme():
            while True:
                style = ttk.Style()
                # #以列表的形式返回多个主题名
                for theme in style.theme_names():
                    yield theme

        theme_get = get_theme()
        def change_theme():
            style = ttk.Style()
            used_theme = next(theme_get)
            style.theme_use(used_theme)
            self.my_config.set_config('theme', used_theme)

        btn = ttk.Button(
            master=buttonbar,
            # text='Theme',
            image='theme',
            compound=LEFT,
            command=change_theme,
        )
        btn.pack(side=RIGHT, ipadx=5, ipady=5, padx=0, pady=1)

    def func_init_left_frame(self):
        """ 初始化左边状态烂 """
        self.left_panel = ttk.Frame(self, style='bg.TFrame')
        self.left_panel.pack(side=LEFT, fill=Y)

    def func_init_right_frame(self):
        """ 初始化右边日志栏 """
        # right panel
        right_panel = ttk.Frame(self, padding=(2, 1))
        right_panel.pack(side=RIGHT, fill=BOTH, expand=YES)

        search_frm = ttk.Frame(right_panel)
        search_frm.pack(side=TOP, fill=X, padx=2, pady=1)

        search_entry = ttk.Entry(search_frm, textvariable='folder-path')
        search_entry.pack(side=LEFT, fill=X, expand=YES)
        search_entry.insert(END, 'Search')

        # 搜索过滤函数
        def func_search(any=None):
            search_text = search_entry.get()
            # print(search_text)

            # 把新收到的日志item添加到集合中
            for item in self.my_log_treeview.get_children():
                self.my_log_all_item_set.add(item)

            for item in sorted(self.my_log_all_item_set):
                # ID    user_name log_id  log_type insert_date          log_info
                # ('1', 'Andy', '00001', 'ERR', '2022-07-20 14:26:23', 'TEST INFO')
                log_tuple = self.my_log_treeview.item(item, 'values')
                if search_text.lower() in str(log_tuple).lower():
                    self.my_log_treeview.move((item, ), '', 0)
                else:
                    self.my_log_treeview.detach((item,))
        # 绑定回车键
        search_entry.bind('<Return>', func_search)

        # 清理日志按钮
        def func_clean_log():
            for item in self.my_log_treeview.get_children():
                self.my_log_treeview.delete(item)
            self.my_log_all_item_set = set()
            self.my_log_id = 1

        btn = ttk.Button(
            master=search_frm,
            image='log-clean',
            bootstyle=(LINK, SECONDARY),
            command=func_clean_log
        )
        btn.pack(side=RIGHT)

        log_frmae = ttk.Frame(right_panel)
        log_frmae.pack(side=TOP, fill=BOTH)

        ## Treeview
        self.my_log_treeview = ttk.Treeview(log_frmae, show='headings', height=26,
            columns=('ID', 'Name', 'LogId', 'LogType', 'InsertTime', 'LogInfo'),
        )
        # 创建滚动条
        scroll = ttk.Scrollbar(log_frmae)
        # side是滚动条放置的位置，上下左右。fill是将滚动条沿着y轴填充
        scroll.pack(side=RIGHT, fill=Y)
        # 配置几个颜色标签
        # Crimson 深红/猩红
        self.my_log_treeview.tag_configure('Crimson', background='Crimson')
        self.my_tag_list.append('Crimson')
        # Fuchsia 紫红/灯笼海棠
        self.my_log_treeview.tag_configure('Fuchsia', background='Fuchsia')
        self.my_tag_list.append('Fuchsia')
        # DarkOrchid 暗兰花紫
        self.my_log_treeview.tag_configure('DarkOrchid', background='DarkOrchid')
        self.my_tag_list.append('DarkOrchid')
        # LightSkyBlue 亮天蓝色
        self.my_log_treeview.tag_configure('LightSkyBlue', background='LightSkyBlue')
        self.my_tag_list.append('LightSkyBlue')
        # MediumPurple 中紫色
        self.my_log_treeview.tag_configure('MediumPurple', background='MediumPurple')
        self.my_tag_list.append('MediumPurple')
        # MediumPurple 中紫色
        self.my_log_treeview.tag_configure('OrangeRed', background='OrangeRed')
        self.my_tag_list.append('OrangeRed')

        # 将文本框关联到滚动条上，滚动条滑动，文本框跟随滑动
        scroll.config(command=self.my_log_treeview.yview)
        # 将滚动条关联到文本框
        self.my_log_treeview.config(yscrollcommand=scroll.set)

        # 表示列,不显示
        self.my_log_treeview.column("ID", width=45, anchor='center')
        self.my_log_treeview.column("Name", width=100, anchor='center')
        self.my_log_treeview.column("LogId", width=50, anchor='center')
        self.my_log_treeview.column("LogType", width=50, anchor='center')
        self.my_log_treeview.column("InsertTime", width=135, anchor='center')
        self.my_log_treeview.column("LogInfo", width=630, anchor='w')

        # 显示表头
        self.my_log_treeview.heading("ID", text="ID")
        self.my_log_treeview.heading("Name", text="Name")
        self.my_log_treeview.heading("LogId", text="LogId")
        self.my_log_treeview.heading("LogType", text="LogType")
        self.my_log_treeview.heading("InsertTime", text="InsertTime")
        self.my_log_treeview.heading("LogInfo", text="LogInfo")

        self.my_log_treeview.pack(fill=X, pady=1)

        ## scrolling text output
        scroll_cf = CollapsingFrame(right_panel, self)
        scroll_cf.pack(fill=BOTH, expand=YES)

        output_container = ttk.Frame(scroll_cf, padding=1)
        _value = 'Information'
        self.setvar('scroll-message', _value)
        self.my_info_text = ScrolledText(output_container, height=10)
        self.my_info_text.pack(fill=BOTH, expand=YES)
        scroll_cf.scrolledtext_add(
            output_container,
            textvariable='scroll-message',
            bootstyle=INFO,
        )

    # =================== 系统函数 ===========================
    def func_switch_mail(self):
        """ 切换邮件模式 """
        def reset_switch_mail():
            # 切换回正常
            self.my_mail_mode = 0
            self.mail_switch_btn.config(bootstyle=PRIMARY, image='mail-ok')
            self.func_insert_information("邮件功能暂停结束, 邮件功能恢复正常!")

        if self.my_mail_mode == 0:
            # 切换到暂停 (最多暂停12小时)
            self.my_mail_mode = 1
            self.mail_switch_btn.config(bootstyle=WARNING, image='mail-no')
            # 12小时
            sleep_time = 43200
            reset_date = datetime.now() + timedelta(seconds=sleep_time)
            self.func_insert_information("邮件功能暂停! {0} 恢复正常!".format(reset_date.strftime('%Y-%m-%d %H:%M:%S')))
            # 启动复原邮件的计时线程
            self.reset_switch_mail_timer = threading.Timer(sleep_time, reset_switch_mail)
            self.reset_switch_mail_timer.setDaemon(True)
            self.reset_switch_mail_timer.start()
        elif self.my_mail_mode == 1:
            # 切换到停止
            self.my_mail_mode = 2
            self.mail_switch_btn.config(bootstyle=DANGER, image='mail-no')
            self.func_insert_information("邮件功能停止!")
            # 取消计时
            self.reset_switch_mail_timer.cancel()
        else:
            # 切换回正常
            self.my_mail_mode = 0
            self.mail_switch_btn.config(bootstyle=PRIMARY, image='mail-ok')
            self.func_insert_information("邮件功能正常!")
            # 取消计时
            self.reset_switch_mail_timer.cancel()

    # =================== 系统服务 ===========================
    def auto_clena_log_server(self):
        """ 自动清理过旧的日志 """
        def sub():
            self.func_insert_information("自动清理过旧日志服务启动!")
            while True:
                # 每小时清理一次
                time.sleep(3600)
                self.func_insert_information("自动清理过旧日志!")
                delete_date = datetime.now() - timedelta(days=3)
                delete_num = 0
                for item in self.my_log_treeview.get_children():
                    # ('1', 'Andy', '00001', 'ERR', '2022-07-20 14:26:23', 'TEST INFO')
                    log_tuple = self.my_log_treeview.item(item, 'values')
                    InsertTime = log_tuple[4]
                    InsertTime = datetime.strptime(InsertTime, '%Y-%m-%d %H:%M:%S')
                    # print(InsertTime)

                    if InsertTime < delete_date:
                        # 三天前的日志清除
                        self.my_log_treeview.delete(item)
                        try:
                            self.my_log_all_item_set.remove(item)
                        except KeyError:
                            pass
                        delete_num += 1
                self.func_insert_information("清除过旧日志 {0}!".format(delete_num))

        server_th = threading.Thread(target=sub)
        server_th.setDaemon(True)
        server_th.start()

    # =================== 用户函数 ===========================
    def func_update_user(self, user_name):
        """ 初始化用户信息 """
        user_name = user_name
        user_ip = "10.88.3.152"
        user_sys_time = 'Time: {0}'.format(time.strftime('%Y-%m-%d %H:%M:%S'))
        user_net = 'Net: ↓: 5.48 Kb/s ↑: 0.90 Kb/s'
        cpu_percent = 17
        mem_percent = 41
        disk_percent = 59
        python_num = "python 5"

        try:
            self.my_user_frame_dict[user_name]
        except KeyError:
            # 第一次新建
            ## 用户抽屉
            bus_cf = CollapsingFrame(self.left_panel, self)
            self.my_user_frame_dict[user_name] = bus_cf
            bus_cf.pack(fill=X, pady=1)

            ## 用户框架
            bus_frm = ttk.Frame(bus_cf, padding=5)
            bus_frm.columnconfigure(1, weight=1)
            child_list = bus_cf.add(
                child=bus_frm,
                title='{0} {1}'.format(user_name, user_ip),
                # User控件样式
                bootstyle=SUCCESS)
            # 保存子控件
            self.my_user_child_frame_dict[user_name] = child_list

            ## 用户服务器时间
            textvariable = "{0}-time".format(user_name)
            lbl = ttk.Label(bus_frm, textvariable=textvariable)
            lbl.grid(row=0, column=0, columnspan=4, sticky=EW, padx=5, pady=2)
            self.setvar(textvariable, user_sys_time)

            ## 用户网络
            textvariable = "{0}-net".format(user_name)
            lbl = ttk.Label(bus_frm, textvariable=textvariable)
            lbl.grid(row=1, column=0, columnspan=4, sticky=EW, padx=5, pady=2)
            self.setvar(textvariable, user_net)

            ## cpu 占用率
            textvariable = "{0}-cpu-percent".format(user_name)
            pb = ttk.Progressbar(
                master=bus_frm,
                variable=textvariable,
                bootstyle=INFO,
            )
            pb.grid(row=2, column=0, columnspan=2, sticky=EW, padx=5, pady=2)
            self.setvar(textvariable, cpu_percent)

            ## 内存 占用率
            textvariable = "{0}-mem-percent".format(user_name)
            pb = ttk.Progressbar(
                master=bus_frm,
                variable=textvariable,
                bootstyle=INFO,
            )
            pb.grid(row=2, column=2, columnspan=2, sticky=EW, padx=5, pady=2)
            self.setvar(textvariable, mem_percent)

            ## 硬盘 占用率
            textvariable = "{0}-disk-percent".format(user_name)
            pb = ttk.Progressbar(
                master=bus_frm,
                variable=textvariable,
                bootstyle=INFO,
            )
            pb.grid(row=3, column=0, columnspan=2, sticky=EW, padx=5, pady=2)
            self.setvar(textvariable, disk_percent)

            ## Python 进程数
            textvariable = "{0}-python-num".format(user_name)
            lbl = ttk.Label(bus_frm, textvariable=textvariable)
            lbl.grid(row=3, column=2, columnspan=1, sticky=EW, padx=5, pady=2)
            self.setvar(textvariable, python_num)

            ## 删除本控件
            def del_self():
                bus_cf.destroy()
                del self.my_user_frame_dict[user_name]
            btn = ttk.Button(
                master=bus_frm,
                image='remove',
                bootstyle=(LINK, SECONDARY),
                command=del_self
            )
            btn.grid(row=3, column=3, columnspan=1, sticky=EW, padx=5, pady=2)
        else:
            # 刷新样式
            self.func_user_online_bootstyle(user_name)
            # 更新时间
            self.setvar("{0}-time".format(user_name), user_sys_time)
            # 更新网络
            self.setvar("{0}-net".format(user_name), user_net)
            # 更新CPU
            self.setvar("{0}-cpu-percent".format(user_name), cpu_percent)
            # 更新MEM
            self.setvar("{0}-mem-percent".format(user_name), mem_percent)
            # 更新DISK
            self.setvar("{0}-disk-percent".format(user_name), disk_percent)
            # 更新Python进程数量
            self.setvar("{0}-python-num".format(user_name), python_num)

    def func_user_offline_bootstyle(self, user_name):
        """ 用户离线切换样式 """
        frm, header, btn = self.my_user_child_frame_dict[user_name]

        frm.configure(bootstyle=DANGER)
        header.configure(bootstyle=(DANGER, INVERSE))
        btn.configure(bootstyle=DANGER)

    def func_user_online_bootstyle(self, user_name):
        """ 用户在线切换样式 """
        frm, header, btn = self.my_user_child_frame_dict[user_name]

        frm.configure(bootstyle=SUCCESS)
        header.configure(bootstyle=(SUCCESS, INVERSE))
        btn.configure(bootstyle=SUCCESS)

    def func_insert_information(self, info):
        """ 向信息栏插入一行信息 """
        self.my_info_text.insert(END, "{0}: {1}\n".format(time.strftime('%Y-%m-%d %H:%M:%S'), info))
        # 让滚动条始终滚动到最底部
        self.my_info_text.text.yview_moveto(1)

    def func_clear_insert_information(self):
        """ 清空信息栏 """
        self.my_info_text.delete(1.0, 'end')
        self.func_insert_information("clean all!")

    def func_insert_log(self, Name, LogId, LogType, LogInfo, InsertTime=None, tag=None):
        """ 插入一条日志信息 """
        if not InsertTime:
            InsertTime = time.strftime('%Y-%m-%d %H:%M:%S')

        # 获取日志配置
        try:
            # 日志ID配置优先
            log_config = self.my_mail_type_config[LogId]
        except KeyError:
            try:
                log_config = self.my_mail_type_config[LogType]
            except KeyError:
                log_config = self.my_mail_type_config["DEFAULT"]

        mail_flag = log_config["mail"]
        if tag:
            tag_flag = tag
        else:
            tag_flag = log_config["tag"]
        deadline_flag = log_config["deadline"]

        ID = self.my_log_id
        if tag_flag:
            self.my_log_treeview.insert("", 0, text="line1", values=(ID, Name, LogId, LogType, InsertTime, LogInfo), tags=(tag_flag,))
        else:
            self.my_log_treeview.insert("", 0, text="line1", values=(ID, Name, LogId, LogType, InsertTime, LogInfo))
        self.my_log_id += 1

        if mail_flag and InsertTime > deadline_flag:
            # 允许发送邮件且日志时间在deadline_flag之后才进入邮件日志缓冲区
            winsound.PlaySound(self.my_err_audio_file, 1)
            self.my_mail_buffer_list_lock.acquire()
            try:
                self.my_mail_buffer_list.append((ID, Name, LogId, LogType, InsertTime, LogInfo))
            finally:
                self.my_mail_buffer_list_lock.release()

        # 数据库保存
        self.my_db_object.insert_log(Name, LogId, LogType, InsertTime, LogInfo)

class CollapsingFrame(ttk.Frame):
    """ 抽屉部件 """
    def __init__(self, master, main_self, **kwargs):
        super().__init__(master, **kwargs)
        self.main_self = main_self
        self.columnconfigure(0, weight=1)
        self.cumulative_rows = 0

        # widget images
        self.images = [
            ttk.PhotoImage(file=os.path.join(IMAGE_PATH, 'icons8_double_up_24px.png')),
            ttk.PhotoImage(file=os.path.join(IMAGE_PATH, 'icons8_double_right_24px.png')),
            ttk.PhotoImage(file=os.path.join(IMAGE_PATH, 'icons8-clean-24px.png')),
        ]

    def add(self, child, title="", bootstyle=PRIMARY, **kwargs):
        """Add a child to the collapsible frame

        Parameters:

            child (Frame):
                The child frame to add to the widget.

            title (str):
                The title appearing on the collapsible section header.

            bootstyle (str):
                The style to apply to the collapsible section header.

            **kwargs (Dict):
                Other optional keyword arguments.
        """
        if child.winfo_class() != 'TFrame':
            return

        style_color = Bootstyle.ttkstyle_widget_color(bootstyle)
        frm = ttk.Frame(self, bootstyle=style_color)
        frm.grid(row=self.cumulative_rows, column=0, sticky=EW)

        # header title
        header = ttk.Label(
            master=frm,
            text=title,
            bootstyle=(style_color, INVERSE)
        )
        if kwargs.get('textvariable'):
            header.configure(textvariable=kwargs.get('textvariable'))
        header.pack(side=LEFT, fill=BOTH, padx=10)

        # header toggle button
        def _func(c=child): return self._toggle_open_close(c)
        btn = ttk.Button(
            master=frm,
            image=self.images[0],
            bootstyle=style_color,
            command=_func
        )
        btn.pack(side=RIGHT)

        # assign toggle button to child so that it can be toggled
        child.btn = btn
        child.grid(row=self.cumulative_rows + 1, column=0, sticky=NSEW)

        # increment the row assignment
        self.cumulative_rows += 2

        return frm, header, btn

    def scrolledtext_add(self, child, title="", bootstyle=PRIMARY, **kwargs):
        """Add a child to the collapsible frame

        Parameters:

            child (Frame):
                The child frame to add to the widget.

            title (str):
                The title appearing on the collapsible section header.

            bootstyle (str):
                The style to apply to the collapsible section header.

            **kwargs (Dict):
                Other optional keyword arguments.
        """
        if child.winfo_class() != 'TFrame':
            return

        style_color = Bootstyle.ttkstyle_widget_color(bootstyle)
        frm = ttk.Frame(self, bootstyle=style_color)
        frm.grid(row=self.cumulative_rows, column=0, sticky=EW)

        # header title
        header = ttk.Label(
            master=frm,
            text=title,
            bootstyle=(style_color, INVERSE)
        )
        if kwargs.get('textvariable'):
            header.configure(textvariable=kwargs.get('textvariable'))
        header.pack(side=LEFT, fill=BOTH, padx=10)

        # header toggle button
        def _func(c=child): return self._toggle_open_close(c)
        btn = ttk.Button(
            master=frm,
            image=self.images[0],
            bootstyle=style_color,
            command=_func
        )
        btn.pack(side=RIGHT)

        ## Clear information
        clear_btn = ttk.Button(
            master=frm,
            image=self.images[2],
            bootstyle=style_color,
            command=self.main_self.func_clear_insert_information
        )
        clear_btn.pack(side=RIGHT)

        # assign toggle button to child so that it can be toggled
        child.btn = btn
        child.grid(row=self.cumulative_rows + 1, column=0, sticky=NSEW)

        # increment the row assignment
        self.cumulative_rows += 2

    def _toggle_open_close(self, child):
        """Open or close the section and change the toggle button
        image accordingly.

        Parameters:

            child (Frame):
                The child element to add or remove from grid manager.
        """
        if child.winfo_viewable():
            child.grid_remove()
            child.btn.configure(image=self.images[1])
        else:
            child.grid()
            child.btn.configure(image=self.images[0])

if __name__ == '__main__':

    """ TEST """
    # app = ttk.Window("ROOM LOG")
    # app.geometry('1300x705')
    # RoomLog(app)
    # app.mainloop()

    """ Thread TEST """
    import threading
    L = []
    def sub(L):
        app = ttk.Window("ROOM LOG")
        app.geometry('1300x800')
        app.iconbitmap(MAIN_ICO_PATH)
        room_log = RoomLog(app)
        L.append(room_log)
        app.mainloop()

    th = threading.Thread(target=sub, args=(L, ))
    th.setDaemon(True)
    th.start()

    time.sleep(1)
    gui = L[0]
