import os
import time
import string
import shutil
import shelve
import random
import sqlite3
import yagmail
import traceback
import winsound
import threading

import ChatRoom
from ChatRoom import Room
from ChatRoom.net import get_host_ip
from datetime import datetime, timedelta

import ttkbootstrap as ttk
from ttkbootstrap.style import Bootstyle
# from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText

DATA_PATH = ".Room"
LOG_FILE_PATH = os.path.join(DATA_PATH, "information_log.log")
IMAGE_PATH = os.path.join(DATA_PATH, "image")
# 主图标
MAIN_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-monitor-32.ico')
# 邮件图标
MAIL_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-mail-24.ico')
# 配置图标
CONFIG_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-mail-configuration-24.ico')
# 设置图标
SETTING_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8_settings_24px_2.ico')
# 警告图标
WARNING_ICO_PATH = os.path.join(IMAGE_PATH, 'icons8-warning-24.ico')

# 初始化文件
data_path = os.path.join(ChatRoom.__file__.replace("__init__.py", ""), ".Room")
if not os.path.exists(DATA_PATH):
    shutil.copytree(data_path, DATA_PATH)

def TK_CENTER(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int(screen_width / 2 - width / 2)
    y = int(screen_height / 2 - height / 2)
    size = '{}x{}+{}+{}'.format(width, height, x, y)

    return size

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
                    "tag" : "crimson",
                    # 超时(在这个时间前不发送邮件)
                    "deadline" : '1970-01-01 00:00:00',
                    # 备注
                    "note" : "ERR类型",
                },
                "INFO" : {
                    # 是否发送邮件
                    "mail" : False,
                    # 该类型邮件标签
                    "tag" : None,
                    # 超时(在这个时间前不发送邮件)
                    "deadline" : '1970-01-01 00:00:00',
                    # 备注
                    "note" : "INFO类型",
                },
                # 默认配置
                "DEFAULT" : {
                    # 是否发送邮件
                    "mail" : False,
                    # 该类型邮件标签
                    "tag" : None,
                    # 超时(在这个时间前不发送邮件)
                    "deadline" : '1971-01-01 00:00:00',
                    # 备注
                    "note" : "DEFAULT类型",
                }
            })

            self.set_config("system_setting", {
                "ip" : get_host_ip(),
                "port" : 2428,
                "password" : "Passable",
                "blacklist" : [],
                "user_napw_info" : {},

                "smtp_ip_1" : "",
                "smtp_port_1" : "",
                "smtp_account_1" : "",
                "smtp_password_1" : "",

                "smtp_ip_2" : "",
                "smtp_port_2" : "",
                "smtp_account_2" : "",
                "smtp_password_2" : "",

                "admin_mail" : "",
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

class MyMail():

    def __init__(self, gui):

        self.gui = gui

        self.mail_server_list = []

        # 检查参数
        err_flag = False
        if not self.gui.system_setting['admin_mail']:
            err_flag = True
            self.gui.func_insert_information("未设置管理员邮箱,邮件功能关闭!")

        if not self.gui.system_setting['smtp_ip_1'] or not self.gui.system_setting['smtp_ip_2']:
            err_flag = True
            self.gui.func_insert_information("未设置SMTP,邮件功能关闭!")

        if not err_flag:
            if self.gui.system_setting['smtp_ip_1']:
                yag = yagmail.SMTP(
                    user=self.gui.system_setting['smtp_account_1'],
                    password=self.gui.system_setting['smtp_password_1'],
                    host=self.gui.system_setting['smtp_ip_1'],
                    port=self.gui.system_setting['smtp_port_1'],
                )
                self.mail_server_list.append(yag)

            if self.gui.system_setting['smtp_ip_2']:
                yag = yagmail.SMTP(
                    user=self.gui.system_setting['smtp_account_2'],
                    password=self.gui.system_setting['smtp_password_2'],
                    host=self.gui.system_setting['smtp_ip_2'],
                    port=self.gui.system_setting['smtp_port_2'],
                )
                self.mail_server_list.append(yag)

            self.mail_server()

    def mail_server(self):
        """ 邮件通知服务 """
        def sub():
            self.gui.func_insert_information("邮件服务启动!")
            while True:
                try:
                    if self.gui.my_mail_mode:
                        time.sleep(30)
                        continue

                    if self.gui.my_mail_buffer_list:
                        yag = random.choice(self.mail_server_list)
                        self.gui.my_mail_buffer_list_lock.acquire()
                        try:
                            mail_info = ""
                            for log in self.gui.my_mail_buffer_list:
                                mail_info += "{0} {1} {2} {3} {4} \n{5}\n".format(
                                    *log
                                )

                            send_result = yag.send(
                                to=self.gui.system_setting['admin_mail'],
                                subject='Room Log',
                                contents=mail_info,
                            )

                            if send_result == {}:
                                self.gui.my_mail_buffer_list = []
                        finally:
                            self.gui.my_mail_buffer_list_lock.release()
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self.gui.func_insert_information("发送邮件通知失败!", "crimson")
                finally:
                    time.sleep(30)

        mail_server_th = threading.Thread(target=sub)
        mail_server_th.setDaemon(True)
        mail_server_th.start()

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
        # 系统设置
        self.system_setting = self.my_config.get_config("system_setting")
        # 信息栏插入锁
        self.my_information_lock = threading.Lock()

        # 初始化组件
        self.func_init_theme()
        self.func_init_pic()
        self.func_init_buttonbar()
        self.func_init_left_frame()
        self.func_init_right_frame()

        # 初始化自己节点

        default_room_user_info_dict = {
            'user_name' : "Room",
            'user_ip' : get_host_ip(),
            'user_sys_time': '1970-01-01 00:00:00',
            'user_net' : 'Net: ↓: 0 Kb/s ↑: 0 Kb/s',
            'cpu_percent' : 0,
            'mem_percent' : 0,
            'disk_percent' : 0,
            'python_num' : "python 5",
        }
        self.func_update_user(default_room_user_info_dict)

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
            config_app.attributes("-topmost", True)
            config_app.iconbitmap(CONFIG_ICO_PATH)
            config_app.geometry(TK_CENTER(config_app, 1000, 650))

            # 上方配置栏
            config_frame = ttk.Frame(config_app, bootstyle=SECONDARY)
            config_frame.pack(fill=BOTH, side=TOP)

            # 下方按钮
            button_frame = ttk.Frame(config_app, bootstyle=DARK)
            button_frame.pack(fill=BOTH, side=TOP)

            # 插入一行新配置
            def insert_a_line(all_config_controls_dict, name, mail, tag, deadline, note):
                # 一行配置
                config_line_frame = ttk.Frame(config_frame)
                config_line_frame.pack(fill=BOTH, side=TOP, ipadx=2, ipady=2)

                label1 = ttk.Label(config_line_frame, text="名称: ")
                label1.pack(fill=BOTH, side=LEFT)
                entry1 = ttk.Entry(config_line_frame, width=7, bootstyle=PRIMARY)
                entry1.insert(END, name)
                entry1.pack(fill=BOTH, side=LEFT)

                label5 = ttk.Label(config_line_frame, text=" 备注: ")
                label5.pack(fill=BOTH, side=LEFT)
                entry5 = ttk.Entry(config_line_frame, width=10, bootstyle=PRIMARY)
                entry5.insert(END, note)
                entry5.pack(fill=BOTH, side=LEFT)

                label2 = ttk.Label(config_line_frame, text=" 邮件通知: ")
                label2.pack(fill=BOTH, side=LEFT)
                entry2 = ttk.Combobox(config_line_frame, width=2, value=("是", "否"), bootstyle=PRIMARY)
                entry2.insert(END, mail)
                entry2.pack(fill=BOTH, side=LEFT)

                label3 = ttk.Label(config_line_frame, text=" 颜色标签: ")
                if tag != "None":
                    label3.config(background=tag)
                label3.pack(fill=BOTH, side=LEFT)
                entry3 = ttk.Combobox(config_line_frame, width=12, value=self.my_tag_list, bootstyle=PRIMARY)
                def choose(event):
                    # 选中事件
                    tag = entry3.get()
                    if tag == "None":
                        label3.config(background="")
                    else:
                        label3.config(background=tag)
                entry3.bind("<<ComboboxSelected>>", choose)
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
                        # Entry
                        "note"      : entry5,
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
                        config_value["note"],
                    )

            # 添加一行新的
            def add():
                insert_a_line(
                        all_config_controls_dict,
                        "New",
                        "否",
                        "None",
                        "1970-01-01 00:00:00",
                        "",
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
                    note = config_value_dict["note"].get()

                    mail = True if mail == "是" else False
                    tag = None if tag == "None" else tag

                    tmp_my_mail_type_config[name] = {
                        "mail" : mail,
                        "tag" : tag,
                        "deadline" : deadline,
                        "note" : note,
                    }

                # 保存内存
                self.my_mail_type_config = tmp_my_mail_type_config
                # 保存配置
                self.my_config.set_config("my_mail_type_config", self.my_mail_type_config)

                self.func_insert_information("日志配置保存成功!当前配置:", "yellowgreen")
                for name, config_dict in self.my_mail_type_config.items():
                    self.func_insert_information("{0:<12} 备注: {4:<12} 邮件: {1:<6} 标签: {2:<10} 超时: {3}".format(
                        name,
                        "开" if config_dict["mail"] else "关",
                        "None" if config_dict["tag"] == None else config_dict["tag"],
                        config_dict["deadline"],
                        config_dict["note"],
                    ))

            self.all_config_controls_dict = all_config_controls_dict

            save_button = ttk.Button(button_frame, width=52, bootstyle=DARK, text="保存", command=save)
            save_button.pack(fill=BOTH, side=RIGHT)

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
                self.func_insert_information("清空了 {0} 条邮件信息!".format(mail_len), "gold")
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
                    message += "{0} {1} {2} {3} {4} {5}\n".format(*log_list)
            else:
                message = "mail buffer is clean."

            show_mail_app = ttk.Toplevel(title="Mail Buffer")
            show_mail_app.attributes("-topmost", True)
            show_mail_app.iconbitmap(MAIL_ICO_PATH)
            show_mail_app.geometry(TK_CENTER(show_mail_app, 1000, 600))

            show_mail_label = ttk.Label(
                master=show_mail_app,
                text=message,
                font=ttk.font.Font(size=13),
            )
            show_mail_label.pack()

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
        btn = ttk.Button(
            master=buttonbar,
            # text='Settings',
            image='settings',
            compound=LEFT,
            command=self.func_setting,
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
            self.func_insert_information("清理日志!", "gold")

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
        color_dict = {
            'pink': '#FFC0CB 粉红',
            'crimson': '#DC143C 深红/猩红',
            'lavenderblush': '#FFF0F5 淡紫红',
            'palevioletred': '#DB7093 弱紫罗兰红',
            'hotpink': '#FF69B4 热情的粉红',
            'deeppink': '#FF1493 深粉红',
            'mediumvioletred': '#C71585 中紫罗兰红',
            'orchid': '#DA70D6 暗紫色/兰花紫',
            'thistle': '#D8BFD8 蓟色',
            'plum': '#DDA0DD 洋李色/李子紫',
            'violet': '#EE82EE 紫罗兰',
            'magenta': '#FF00FF 洋红/玫瑰红',
            'fuchsia': '#FF00FF 紫红/灯笼海棠',
            'darkmagenta': '#8B008B 深洋红',
            'purple': '#800080 紫色',
            'mediumorchid': '#BA55D3 中兰花紫',
            'darkviolet': '#9400D3 暗紫罗兰',
            'darkorchid': '#9932CC 暗兰花紫',
            'indigo': '#4B0082 靛青/紫兰色',
            'blueviolet': '#8A2BE2 蓝紫罗兰',
            'mediumpurple': '#9370DB 中紫色',
            'mediumslateblue': '#7B68EE 中暗蓝色/中板岩蓝',
            'slateblue': '#6A5ACD 石蓝色/板岩蓝',
            'darkslateblue': '#483D8B 暗灰蓝色/暗板岩蓝',
            'lavender': '#E6E6FA 淡紫色/熏衣草淡紫',
            'ghostwhite': '#F8F8FF 幽灵白',
            'blue': '#0000FF 纯蓝',
            'mediumblue': '#0000CD 中蓝色',
            'midnightblue': '#191970 午夜蓝',
            'darkblue': '#00008B 暗蓝色',
            'navy': '#000080 海军蓝',
            'royalblue': '#4169E1 皇家蓝/宝蓝',
            'cornflowerblue': '#6495ED 矢车菊蓝',
            'lightsteelblue': '#B0C4DE 亮钢蓝',
            'lightslategray': '#778899 亮蓝灰/亮石板灰',
            'slategray': '#708090 灰石色/石板灰',
            'dodgerblue': '#1E90FF 闪兰色/道奇蓝',
            'aliceblue': '#F0F8FF 爱丽丝蓝',
            'steelblue': '#4682B4 钢蓝/铁青',
            'lightskyblue': '#87CEFA 亮天蓝色',
            'skyblue': '#87CEEB 天蓝色',
            'deepskyblue': '#00BFFF 深天蓝',
            'lightblue': '#ADD8E6 亮蓝',
            'powderblue': '#B0E0E6 粉蓝色/火药青',
            'cadetblue': '#5F9EA0 军兰色/军服蓝',
            'azure': '#F0FFFF 蔚蓝色',
            'lightcyan': '#E0FFFF 淡青色',
            'paleturquoise': '#AFEEEE 弱绿宝石',
            'cyan': '#00FFFF 青色',
            'aqua': '#00FFFF 浅绿色/水色',
            'darkturquoise': '#00CED1 暗绿宝石',
            'darkslategray': '#2F4F4F 暗瓦灰色/暗石板灰',
            'darkcyan': '#008B8B 暗青色',
            'teal': '#008080 水鸭色',
            'mediumturquoise': '#48D1CC 中绿宝石',
            'lightseagreen': '#20B2AA 浅海洋绿',
            'turquoise': '#40E0D0 绿宝石',
            'aquamarine': '#7FFFD4 宝石碧绿',
            'mediumaquamarine': '#66CDAA 中宝石碧绿',
            'mediumspringgreen': '#00FA9A 中春绿色',
            'mintcream': '#F5FFFA 薄荷奶油',
            'springgreen': '#00FF7F 春绿色',
            'mediumseagreen': '#3CB371 中海洋绿',
            'seagreen': '#2E8B57 海洋绿',
            'honeydew': '#F0FFF0 蜜色/蜜瓜色',
            'lightgreen': '#90EE90 淡绿色',
            'palegreen': '#98FB98 弱绿色',
            'darkseagreen': '#8FBC8F 暗海洋绿',
            'limegreen': '#32CD32 闪光深绿',
            'lime': '#00FF00 闪光绿',
            'forestgreen': '#228B22 森林绿',
            'green': '#008000 纯绿',
            'darkgreen': '#006400 暗绿色',
            'chartreuse': '#7FFF00 黄绿色/查特酒绿',
            'lawngreen': '#7CFC00 草绿色/草坪绿',
            'greenyellow': '#ADFF2F 绿黄色',
            'darkolivegreen': '#556B2F 暗橄榄绿',
            'yellowgreen': '#9ACD32 黄绿色',
            'olivedrab': '#6B8E23 橄榄褐色',
            'beige': '#F5F5DC 米色/灰棕色',
            'lightgoldenrodyellow': '#FAFAD2 亮菊黄',
            'ivory': '#FFFFF0 象牙色',
            'lightyellow': '#FFFFE0 浅黄色',
            'yellow': '#FFFF00 纯黄',
            'olive': '#808000 橄榄',
            'darkkhaki': '#BDB76B 暗黄褐色/深卡叽布',
            'lemonchiffon': '#FFFACD 柠檬绸',
            'palegoldenrod': '#EEE8AA 灰菊黄/苍麒麟色',
            'khaki': '#F0E68C 黄褐色/卡叽布',
            'gold': '#FFD700 金色',
            'cornsilk': '#FFF8DC 玉米丝色',
            'goldenrod': '#DAA520 金菊黄',
            'darkgoldenrod': '#B8860B 暗金菊黄',
            'floralwhite': '#FFFAF0 花的白色',
            'oldlace': '#FDF5E6 老花色/旧蕾丝',
            'wheat': '#F5DEB3 浅黄色/小麦色',
            'moccasin': '#FFE4B5 鹿皮色/鹿皮靴',
            'orange': '#FFA500 橙色',
            'papayawhip': '#FFEFD5 番木色/番木瓜',
            'blanchedalmond': '#FFEBCD 白杏色',
            'navajowhite': '#FFDEAD 纳瓦白/土著白',
            'antiquewhite': '#FAEBD7 古董白',
            'tan': '#D2B48C 茶色',
            'burlywood': '#DEB887 硬木色',
            'bisque': '#FFE4C4 陶坯黄',
            'darkorange': '#FF8C00 深橙色',
            'linen': '#FAF0E6 亚麻布',
            'peru': '#CD853F 秘鲁色',
            'peachpuff': '#FFDAB9 桃肉色',
            'sandybrown': '#F4A460 沙棕色',
            'chocolate': '#D2691E 巧克力色',
            'saddlebrown': '#8B4513 重褐色/马鞍棕色',
            'seashell': '#FFF5EE 海贝壳',
            'sienna': '#A0522D 黄土赭色',
            'lightsalmon': '#FFA07A 浅鲑鱼肉色',
            'coral': '#FF7F50 珊瑚',
            'orangered': '#FF4500 橙红色',
            'darksalmon': '#E9967A 深鲜肉/鲑鱼色',
            'tomato': '#FF6347 番茄红',
            'mistyrose': '#FFE4E1 浅玫瑰色/薄雾玫瑰',
            'salmon': '#FA8072 鲜肉/鲑鱼色',
            'snow': '#FFFAFA 雪白色',
            'lightcoral': '#F08080 淡珊瑚色',
            'rosybrown': '#BC8F8F 玫瑰棕色',
            'indianred': '#CD5C5C 印度红',
            'red': '#FF0000 纯红',
            'brown': '#A52A2A 棕色',
            'firebrick': '#B22222 火砖色/耐火砖',
            'darkred': '#8B0000 深红色',
            'maroon': '#800000 栗色',
            'white': '#FFFFFF 纯白',
            'whitesmoke': '#F5F5F5 白烟',
            'gainsboro': '#DCDCDC 淡灰色',
            'lightgrey': '#D3D3D3 浅灰色',
            'silver': '#C0C0C0 银灰色',
            'darkgray': '#A9A9A9 深灰色',
            'gray': '#808080 灰色',
            'dimgray': '#696969 暗淡灰',
            'black': '#000000 纯黑',
        }

        for tag_name in color_dict:
            self.my_log_treeview.tag_configure(tag_name, background=tag_name)
            self.my_tag_list.append(tag_name)

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

        for tag_name in color_dict:
            self.my_info_text.tag_config(tag_name, foreground=tag_name)

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
            self.func_insert_information("邮件功能暂停结束, 邮件功能恢复正常!", "yellowgreen")

        if self.my_mail_mode == 0:
            # 切换到暂停 (最多暂停90s)
            self.my_mail_mode = 1
            self.mail_switch_btn.config(bootstyle=WARNING, image='mail-no')
            # 90s
            sleep_time = 90
            reset_date = datetime.now() + timedelta(seconds=sleep_time)
            self.func_insert_information("邮件功能暂停! {0} 恢复正常!".format(reset_date.strftime('%Y-%m-%d %H:%M:%S')), "gold")
            # 启动复原邮件的计时线程
            self.reset_switch_mail_timer = threading.Timer(sleep_time, reset_switch_mail)
            self.reset_switch_mail_timer.setDaemon(True)
            self.reset_switch_mail_timer.start()
        elif self.my_mail_mode == 1:
            # 切换到停止
            self.my_mail_mode = 2
            self.mail_switch_btn.config(bootstyle=DANGER, image='mail-no')
            self.func_insert_information("邮件功能停止!", "red")
            # 取消计时
            self.reset_switch_mail_timer.cancel()
        else:
            # 切换回正常
            self.my_mail_mode = 0
            self.mail_switch_btn.config(bootstyle=PRIMARY, image='mail-ok')
            self.func_insert_information("邮件功能正常!", "yellowgreen")
            # 取消计时
            self.reset_switch_mail_timer.cancel()

    def func_messagebox(self, Name, LogId, LogType, InsertTime, LogInfo):
        """ 显示一个警告窗口 """
        # def s_len(info):
        #     return len(info) + (len(info.encode('utf-8')) - len(info)) / 2

        # 根据长度自动分段加上换行
        LogInfoS = ""
        len_n = 0
        for s in LogInfo:
            if s in string.printable:
                len_n += 1
            else:
                len_n += 2

            LogInfoS += s
            if len_n % 34 == 0:
                LogInfoS += '\n'

        message_app = ttk.Toplevel(title="Warning")
        message_app.attributes("-topmost", True)
        message_app.iconbitmap(WARNING_ICO_PATH)
        message_app.geometry(TK_CENTER(message_app, 260, 170))

        up_frame = ttk.Frame(message_app, bootstyle=DANGER)
        up_frame.pack(fill=BOTH, side=TOP)

        down_frame = ttk.Frame(message_app, bootstyle=DARK)
        down_frame.pack(fill=BOTH, side=TOP)

        title = "{0} {1} {2} {3}".format(Name, LogId, LogType, InsertTime)
        label1 = ttk.Label(up_frame, text=title, bootstyle="inverse-danger")
        label1.pack()
        label2 = ttk.Label(down_frame, text=LogInfoS, bootstyle="inverse-dark")
        label2.pack()
        label3 = ttk.Label(down_frame, text="\n\n\n\n\n\n\n\n\n\n", bootstyle="inverse-dark")
        label3.pack()

    def func_setting(self):
        """ 系统设置界面 """
        def save_setting():
            try:
                self.system_setting["ip"] = ip_entry.get()
                port = port_entry.get()
                if port:
                    self.system_setting["port"] = int(port)
                self.system_setting["password"] = password_entry.get()
                self.system_setting["blacklist"] = eval(blacklist_entry.get())
                self.system_setting["user_napw_info"] = eval(user_napw_info_entry.get())

                self.system_setting["smtp_ip_1"] = smtp_ip_entry_1.get()
                smtp_port_1 = smtp_port_entry_1.get()
                if smtp_port_1:
                    self.system_setting["smtp_port_1"] = int(smtp_port_1)
                self.system_setting["smtp_account_1"] = smtp_account_entry_1.get()
                self.system_setting["smtp_password_1"] = smtp_password_entry_1.get()

                self.system_setting["smtp_ip_2"] = smtp_ip_entry_2.get()
                smtp_port_2 = smtp_port_entry_2.get()
                if smtp_port_2:
                    self.system_setting["smtp_port_2"] = int(smtp_port_2)
                self.system_setting["smtp_account_2"] = smtp_account_entry_2.get()
                self.system_setting["smtp_password_2"] = smtp_password_entry_2.get()

                self.system_setting["admin_mail"] = admin_mail_entry_1.get()

                self.my_config.set_config("system_setting", self.system_setting)

            except Exception:
                self.func_insert_information("设置保存失败! 请检查数据格式!", "red")
            else:
                self.func_insert_information("设置保存成功!重启后生效!", "yellowgreen")

        ip = self.system_setting["ip"]
        port = str(self.system_setting["port"])
        password = self.system_setting["password"]
        blacklist = str(self.system_setting["blacklist"])
        user_napw_info = str(self.system_setting["user_napw_info"])

        smtp_ip_1 = self.system_setting["smtp_ip_1"]
        smtp_port_1 = str(self.system_setting["smtp_port_1"])
        smtp_account_1 = self.system_setting["smtp_account_1"]
        smtp_password_1 = self.system_setting["smtp_password_1"]

        smtp_ip_2 = self.system_setting["smtp_ip_2"]
        smtp_port_2 = str(self.system_setting["smtp_port_2"])
        smtp_account_2 = self.system_setting["smtp_account_2"]
        smtp_password_2 = self.system_setting["smtp_password_2"]

        admin_mail = self.system_setting["admin_mail"]

        setting_app = ttk.Toplevel(title="Setting")
        setting_app.attributes("-topmost", True)
        setting_app.iconbitmap(SETTING_ICO_PATH)
        setting_app.geometry(TK_CENTER(setting_app, 700, 250))

        # ========= Room ============
        room_frame = ttk.Labelframe(setting_app, text='Room', padding=10)
        room_frame.grid(row=0, column=0, rowspan=1, columnspan=2)

        ip_label = ttk.Label(room_frame, text="ip: ")
        ip_label.grid(row=0, column=0, rowspan=1, columnspan=1, pady=1)
        ip_entry = ttk.Entry(room_frame, width=12)
        ip_entry.insert(END, ip)
        ip_entry.grid(row=0, column=1, rowspan=1, columnspan=1, pady=1)

        port_label = ttk.Label(room_frame, text=" port: ")
        port_label.grid(row=0, column=2, rowspan=1, columnspan=1, pady=1)
        port_entry = ttk.Entry(room_frame, width=5)
        port_entry.insert(END, port)
        port_entry.grid(row=0, column=3, rowspan=1, columnspan=1, pady=1)

        password_label = ttk.Label(room_frame, text=" password: ")
        password_label.grid(row=0, column=4, rowspan=1, columnspan=1, pady=1)
        password_entry = ttk.Entry(room_frame, width=12)
        password_entry.insert(END, password)
        password_entry.grid(row=0, column=5, rowspan=1, columnspan=1, pady=1)

        blacklist_label = ttk.Label(room_frame, text="blacklist: ")
        blacklist_label.grid(row=1, column=0, rowspan=1, columnspan=1, pady=1)
        blacklist_entry = ttk.Entry(room_frame, width=50)
        blacklist_entry.insert(END, blacklist)
        blacklist_entry.grid(row=1, column=1, rowspan=1, columnspan=5, pady=1)

        user_napw_info_label = ttk.Label(room_frame, text="UNI: ")
        user_napw_info_label.grid(row=2, column=0, rowspan=1, columnspan=1, pady=1)
        user_napw_info_entry = ttk.Entry(room_frame, width=50)
        user_napw_info_entry.insert(END, user_napw_info)
        user_napw_info_entry.grid(row=2, column=1, rowspan=1, columnspan=5, pady=1)

        # ============== Admin =============
        k_frame = ttk.Frame(setting_app, padding=10)
        k_frame.grid(row=0, column=2, rowspan=1, columnspan=1)

        admin_mail_label_1 = ttk.Label(k_frame, text="Admin Mail: ")
        admin_mail_label_1.grid(row=0, column=0, rowspan=1, columnspan=2, pady=1)
        admin_mail_entry_1 = ttk.Entry(k_frame, width=17)
        admin_mail_entry_1.insert(END, admin_mail)
        admin_mail_entry_1.grid(row=0, column=2, rowspan=1, columnspan=4, pady=1)

        save_button = ttk.Button(k_frame, text='Save', width=11, command=save_setting)
        save_button.grid(row=1, column=0, rowspan=1, columnspan=3, pady=1)
        save_button = ttk.Button(k_frame, text='Quit', width=11, command=lambda : setting_app.destroy())
        save_button.grid(row=1, column=3, rowspan=1, columnspan=3, pady=1)

        # ========= Mail ============
        mail_frame = ttk.Labelframe(setting_app, text='Smtp Mail', padding=10)
        mail_frame.grid(row=1, column=0, rowspan=1, columnspan=3)

        smtp_ip_label_1 = ttk.Label(mail_frame, text="ip: ")
        smtp_ip_label_1.grid(row=0, column=0, rowspan=1, columnspan=1, pady=1)
        smtp_ip_entry_1 = ttk.Entry(mail_frame, width=17)
        smtp_ip_entry_1.insert(END, smtp_ip_1)
        smtp_ip_entry_1.grid(row=0, column=1, rowspan=1, columnspan=1, pady=1)

        smtp_port_label_1 = ttk.Label(mail_frame, text=" port: ")
        smtp_port_label_1.grid(row=0, column=2, rowspan=1, columnspan=1, pady=1)
        smtp_port_entry_1 = ttk.Entry(mail_frame, width=4)
        smtp_port_entry_1.insert(END, smtp_port_1)
        smtp_port_entry_1.grid(row=0, column=3, rowspan=1, columnspan=1, pady=1)

        smtp_account_label_1 = ttk.Label(mail_frame, text=" account: ")
        smtp_account_label_1.grid(row=0, column=4, rowspan=1, columnspan=1, pady=1)
        smtp_account_entry_1 = ttk.Entry(mail_frame, width=22)
        smtp_account_entry_1.insert(END, smtp_account_1)
        smtp_account_entry_1.grid(row=0, column=5, rowspan=1, columnspan=1, pady=1)

        smtp_password_label_1 = ttk.Label(mail_frame, text=" password: ")
        smtp_password_label_1.grid(row=0, column=6, rowspan=1, columnspan=1, pady=1)
        smtp_password_entry_1 = ttk.Entry(mail_frame, width=17)
        smtp_password_entry_1.insert(END, smtp_password_1)
        smtp_password_entry_1.grid(row=0, column=7, rowspan=1, columnspan=1, pady=1)

        smtp_ip_label_2 = ttk.Label(mail_frame, text="ip: ")
        smtp_ip_label_2.grid(row=1, column=0, rowspan=1, columnspan=1, pady=1)
        smtp_ip_entry_2 = ttk.Entry(mail_frame, width=17)
        smtp_ip_entry_2.insert(END, smtp_ip_2)
        smtp_ip_entry_2.grid(row=1, column=1, rowspan=1, columnspan=1, pady=1)

        smtp_port_label_2 = ttk.Label(mail_frame, text=" port: ")
        smtp_port_label_2.grid(row=1, column=2, rowspan=1, columnspan=1, pady=1)
        smtp_port_entry_2 = ttk.Entry(mail_frame, width=4)
        smtp_port_entry_2.insert(END, smtp_port_2)
        smtp_port_entry_2.grid(row=1, column=3, rowspan=1, columnspan=1, pady=1)

        smtp_account_label_2 = ttk.Label(mail_frame, text=" account: ")
        smtp_account_label_2.grid(row=1, column=4, rowspan=1, columnspan=1, pady=1)
        smtp_account_entry_2 = ttk.Entry(mail_frame, width=22)
        smtp_account_entry_2.insert(END, smtp_account_2)
        smtp_account_entry_2.grid(row=1, column=5, rowspan=1, columnspan=1, pady=1)

        smtp_password_label_2 = ttk.Label(mail_frame, text=" password: ")
        smtp_password_label_2.grid(row=1, column=6, rowspan=1, columnspan=1, pady=1)
        smtp_password_entry_2 = ttk.Entry(mail_frame, width=17)
        smtp_password_entry_2.insert(END, smtp_password_2)
        smtp_password_entry_2.grid(row=1, column=7, rowspan=1, columnspan=1, pady=1)

    # =================== 系统服务 ===========================
    def auto_clena_log_server(self):
        """ 自动清理过旧的日志 """
        def sub():
            self.func_insert_information("自动清理过旧日志服务启动!")
            while True:
                # 每小时清理一次
                time.sleep(3600)
                self.func_insert_information("自动清理过旧日志!", "gold")
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
                self.func_insert_information("清除过旧日志 {0}!".format(delete_num), "gold")

        server_th = threading.Thread(target=sub)
        server_th.setDaemon(True)
        server_th.start()

    # =================== 用户函数 ===========================
    def func_update_user(self, user_info_dict):
        """ 初始化或更新用户信息 """
        user_name = user_info_dict["user_name"]
        user_ip = user_info_dict["user_ip"]
        user_sys_time = user_info_dict["user_sys_time"]
        user_net = user_info_dict["user_net"]
        cpu_percent = user_info_dict["cpu_percent"]
        mem_percent = user_info_dict["mem_percent"]
        disk_percent = user_info_dict["disk_percent"]
        python_num = user_info_dict["python_num"]

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
                my_textvariable='{0}-user-title'.format(user_name),
                set_textvariable='{0} {1}'.format(user_name, user_ip),
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
            # 更新标题
            self.setvar("{0}-user-title".format(user_name), '{0} {1}'.format(user_name, user_ip))
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

    def func_insert_information(self, info, tag=""):
        """ 向信息栏插入一行信息 """
        self.my_information_lock.acquire()
        try:
            if tag:
                self.my_info_text.insert(END, "{0}: ".format(time.strftime('%Y-%m-%d %H:%M:%S')))
                self.my_info_text.insert(END, "{0}\n".format(info), tag)
            else:
                self.my_info_text.insert(END, "{0}: {1}\n".format(time.strftime('%Y-%m-%d %H:%M:%S'), info))

            # 让滚动条始终滚动到最底部
            self.my_info_text.text.yview_moveto(1)
            with open(LOG_FILE_PATH, "a") as fa:
                fa.write(info + '\n')
        finally:
            self.my_information_lock.release()

    def func_room_log_information(self, title, info, log_tag=""):
        """ Room日志插入消息 """
        self.my_information_lock.acquire()
        try:
            self.my_info_text.insert(END, "{0} | ".format(time.strftime('%Y-%m-%d %H:%M:%S')))
            self.my_info_text.insert(END, "{0:^30}".format(title), log_tag)
            self.my_info_text.insert(END, " | {0}\n".format(info))
            self.my_info_text.text.yview_moveto(1)
        finally:
            self.my_information_lock.release()

    def func_clear_insert_information(self):
        """ 清空信息栏 """
        self.my_information_lock.acquire()
        try:
            self.my_info_text.delete(1.0, 'end')
        finally:
            self.my_information_lock.release()
        self.func_insert_information("clean all!", "yellowgreen")

    def func_insert_log(self, Name, LogId, LogType, LogInfo, InsertTime=None, tag=None, force_mail=False):
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

        if (mail_flag and InsertTime > deadline_flag) or (force_mail):
            # 允许发送邮件且日志时间在deadline_flag之后才进入邮件日志缓冲区
            self.my_mail_buffer_list_lock.acquire()
            try:
                self.my_mail_buffer_list.append((ID, Name, LogId, LogType, InsertTime, LogInfo))
            finally:
                self.my_mail_buffer_list_lock.release()

            if not self.my_mail_mode:
                self.func_messagebox(Name, LogId, LogType, InsertTime, LogInfo)
                winsound.PlaySound(self.my_err_audio_file, 1)

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

    def add(self, child, title="", bootstyle=PRIMARY, my_textvariable="", set_textvariable="",**kwargs):
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
        if my_textvariable:
            header = ttk.Label(
                master=frm,
                text=title,
                textvariable=my_textvariable,
                bootstyle=(style_color, INVERSE)
            )
            self.setvar(my_textvariable, set_textvariable)
        else:
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

class RoomApp():

    def __init__(self):
        """ 初始化 """
        self.user_old_sys_time_dict = {}

        self.user_offline_err_times_dict = {}

        self.user_mem_err_times_dict = {}

        self.user_disk_err_time_dict = {}

        # ========= Run =========
        self.run_gui()
        while True:
            time.sleep(1)
            try:
                self.gui
            except AttributeError:
                pass
            else:
                break
        self.run_room()

        self.update_user_info_server()

        self.my_mail = MyMail(self.gui)

    def gui_th(self):
        app = ttk.Window("ROOM LOG")
        app.attributes("-topmost", True)
        app.geometry(TK_CENTER(app, 1300, 800))
        app.iconbitmap(MAIN_ICO_PATH)
        self.gui = RoomLog(app)
        app.mainloop()

    def run_gui(self):
        """ 运行gui """
        th = threading.Thread(target=self.gui_th)
        th.setDaemon(True)
        th.start()

    def run_room(self):
        """ 运行room """
        # 获取配置
        ip = self.gui.system_setting['ip']
        port = self.gui.system_setting['port']
        password = self.gui.system_setting['password']
        user_napw_info = self.gui.system_setting['user_napw_info']
        blacklist = self.gui.system_setting['blacklist']

        self.gui.func_insert_information("Room Ip: {0} Room Port: {1}".format(ip, port), "slateblue")
        self.room = Room(
            ip=ip,
            port=port,
            password=password,
            user_napw_info=user_napw_info,
            blacklist=blacklist,
            gui=self.gui,
        )

    def update_user_info_server(self):
        """ 用户信息监控更新服务 """
        def sub():
            while True:
                try:
                    # 更新room
                    user_info_dict = {}
                    user_info_dict['user_name'] = "Room"
                    user_info_dict['user_ip'] = get_host_ip()
                    user = getattr(self.room.user, "myself")
                    try:
                        user.status.server_time
                    except AttributeError:
                        time.sleep(10)
                        continue
                    user_info_dict['user_sys_time'] = user.status.server_time[0]
                    self.user_old_sys_time_dict["Room"] = user_info_dict['user_sys_time']
                    user_info_dict['user_net'] = "Net: ↓: {0} ↑: {1}".format(user.status.network[0], user.status.network[1])
                    user_info_dict['cpu_percent'] = float(user.status.cpu_rate.replace("%",""))
                    user_info_dict['mem_percent'] = float(user.status.memory[0].replace("%",""))

                    try:
                        # windows
                        user_info_dict['disk_percent'] = user.status.disk["C:\\"]['percent']
                    except KeyError:
                        # lazy
                        user_info_dict['disk_percent'] = 0

                    user_info_dict['python_num'] = user.status.process_status[1]

                    self.gui.func_update_user(user_info_dict)

                    if user_info_dict['mem_percent'] >= 85:
                        try:
                            self.user_mem_err_times_dict["Room"]
                        except KeyError:
                            self.user_mem_err_times_dict["Room"] = 0
                        self.user_mem_err_times_dict["Room"] += 1
                        if self.user_mem_err_times_dict["Room"] <= 2:
                            self.gui.func_insert_log("Room", "00000", "ERR", "内存使用率过高!", tag="crimson", force_mail=True)
                    else:
                        self.user_mem_err_times_dict["Room"] = 0


                    if user_info_dict['disk_percent'] >= 85:
                        try:
                            self.user_disk_err_time_dict["Room"]
                        except KeyError:
                            self.user_disk_err_time_dict["Room"] = 0
                        self.user_disk_err_time_dict["Room"] += 1
                        if self.user_disk_err_time_dict["Room"] <= 2:
                            self.gui.func_insert_log("Room", "00000", "ERR", "硬盘使用率过高!", tag="crimson", force_mail=True)
                    else:
                        self.user_disk_err_time_dict["Room"] = 0

                    # 其他user
                    for user_name in self.room.server.get_user():
                        user_info_dict = {}
                        user_info_dict['user_name'] = user_name
                        user_info_dict['user_ip'] = self.room.server.user_addr_dict[user_name][0]
                        user = getattr(self.room.user, user_name)
                        try:
                            user.status.server_time
                        except AttributeError:
                            time.sleep(10)
                            continue
                        user_info_dict['user_sys_time'] = user.status.server_time[0]
                        self.user_old_sys_time_dict[user_name] = user_info_dict['user_sys_time']
                        user_info_dict['user_net'] = "Net: ↓: {0} ↑: {1}".format(user.status.network[0], user.status.network[1])
                        user_info_dict['cpu_percent'] = float(user.status.cpu_rate.replace("%",""))
                        user_info_dict['mem_percent'] = float(user.status.memory[0].replace("%",""))

                        try:
                            # windows
                            user_info_dict['disk_percent'] = user.status.disk["C:\\"]['percent']
                        except KeyError:
                            # lazy
                            user_info_dict['disk_percent'] = 0

                        user_info_dict['python_num'] = user.status.process_status[1]

                        self.gui.func_update_user(user_info_dict)

                        if user_info_dict['mem_percent'] >= 85:
                            try:
                                self.user_mem_err_times_dict[user_name]
                            except KeyError:
                                self.user_mem_err_times_dict[user_name] = 0
                            self.user_mem_err_times_dict[user_name] += 1
                            if self.user_mem_err_times_dict[user_name] <= 2:
                                self.gui.func_insert_log(user_name, "00000", "ERR", "内存使用率过高!", tag="crimson", force_mail=True)
                        else:
                            self.user_mem_err_times_dict[user_name] = 0

                        if user_info_dict['disk_percent'] >= 85:
                            try:
                                self.user_disk_err_time_dict[user_name]
                            except KeyError:
                                self.user_disk_err_time_dict[user_name] = 0
                            self.user_disk_err_time_dict[user_name] += 1
                            if self.user_disk_err_time_dict[user_name] <= 2:
                                self.gui.func_insert_log(user_name, "00000", "ERR", "硬盘使用率过高!", tag="crimson", force_mail=True)
                        else:
                            self.user_disk_err_time_dict[user_name] = 0

                    # 检查用户断线
                    now_date_str = (datetime.now() - timedelta(seconds=90)).strftime('%Y-%m-%d %H:%M:%S')
                    for user_name, user_date in self.user_old_sys_time_dict.items():
                        if now_date_str > user_date:
                            try:
                                self.user_offline_err_times_dict[user_name]
                            except KeyError:
                                self.user_offline_err_times_dict[user_name] = 0
                            self.user_offline_err_times_dict[user_name] += 1
                            if self.user_offline_err_times_dict[user_name] <= 2:
                                self.gui.func_insert_log(user_name, "00000", "ERR", "用户离线!", tag="crimson", force_mail=True)
                                self.gui.func_user_offline_bootstyle(user_name)
                        else:
                            self.user_offline_err_times_dict[user_name] = 0

                    time.sleep(10)
                except Exception as err:
                    self.gui.func_insert_information("更新用户信息失败!", "crimson")
                    traceback.print_exc(0)
                    print(err)
                    time.sleep(10)

        update_user_info_th = threading.Thread(target=sub)
        update_user_info_th.setDaemon(True)
        update_user_info_th.start()

if __name__ == '__main__':

    room_app = RoomApp()
    time.sleep(1)
    gui = room_app.gui
