# -*- coding: utf-8 -*-
import time
import copy
import queue
import random
import string
import threading
import itertools
from datetime import datetime
import traceback
from ChatRoom.log import Log
from ChatRoom.net import get_host_ip
from ChatRoom.net import Server, Client

class Room():

    def __init__(self, ip="", port=2428, password="Passable", log="INFO", user_napw_info=None, blacklist=None, encryption=True):
        """
        文档:
            创建一个聊天室

        参数:
            ip : str
                聊天室建立服务的IP地址
            port : int (Default: 2428)
                端口
            password : str (Default: "Passable")
                密码
            log : None or str (Default: "INFO")
                日志等级
                    None: 除了错误什么都不显示
                    "INFO": 显示基本连接信息
                    "DEBUG": 显示所有信息
            user_napw_info : dict (Default: {})
                用户加密密码信息字典, 设定后只有使用正确的用户名和密码才能登录服务端
                不指定跳过用户真实性检测
                使用 hash_encryption 函数生成需要的 user_napw_info
            blacklist : list (Default: [])
                ip黑名单, 在这个列表中的ip会被聊天室集群拉黑
            encryption : bool(default True)
                是否加密传输, 不加密效率较高

        例子:
            # 启动一个聊天室
            import ChatRoom
            room = ChatRoom.Room()

            # 其他功能请参考user_napw_info和blacklist的作用
        """

        if not ip:
            ip = get_host_ip()

        self.ip = ip
        self.port = port
        self.password = password
        self.user_napw_info = user_napw_info
        self.blacklist = blacklist
        self.encryption = encryption

        self._log = Log(log)

        self.server = Server(self.ip, self.port, self.password, log=log, user_napw_info=user_napw_info, blacklist=blacklist, encryption=encryption)

        self.server.register_disconnect_user_fun(self._disconnect_callback)

        self.user = self.server.user

        self._user_info_dict = {}

        self._callback_pretreatment(self.server.recv_info_queue)

        self._user_information_processing()

    def _disconnect_callback(self, client_name):
        # 删除节点信息
        del self._user_info_dict[client_name]

    def _callback_pretreatment(self, recv_info_queue):

        def sub():
            while True:
                try:
                    recv_data = recv_info_queue.get()
                    # [from_user, [cmd, xxx, xxx]]
                    from_user = recv_data[0]

                    try:
                        cmd = recv_data[1][0]
                    except Exception:
                        # 接收到来自User的消息格式不标准,可能是手动发送的
                        print("{0}: reve not format data: {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))
                        continue

                    # DEBUG
                    # print("{0} recv: {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))

                    if cmd == "CMD_UserInfo":
                        # 接收from_user信息
                        #  ['from_user', ['CMD_UserInfo', {'local_ip': '10.88.3.152', 'public_ip': '', 'port': 13004, 'password': 'Z(qC\x0b1=\nkc\ry|L\t+', 'is_public_network': False, 'lan_id': 'D'}]]
                        user_info = recv_data[1][1]
                        self._user_info_dict[from_user] = user_info
                    elif cmd == "CMD_GetUserNapwInfo":
                        # 向from_user发送其他user密码配置信息
                        # ['from_user', 'CMD_GetUserNapwInfo']
                        exec("self.user.{0}.send(['CMD_UserNapwInfo', self.user_napw_info])".format(from_user))
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info_format_err("Runtime Err 1", recv_data)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _user_information_processing(self):

        def sub():
            old_user_info_dict = {}
            while True:
                time.sleep(10)
                if old_user_info_dict == self._user_info_dict:
                    continue
                try:
                    for user_a, user_b in itertools.combinations(self._user_info_dict, 2):
                        # print(user_a, user_b)
                        user_info_a = self._user_info_dict[user_a]
                        user_info_b = self._user_info_dict[user_b]

                        if user_b in self._user_info_dict[user_a]['black_list']:
                            continue
                        if user_a in self._user_info_dict[user_b]['black_list']:
                            continue

                        if self._user_info_dict[user_a]['white_list']:
                            if user_b not in self._user_info_dict[user_a]['white_list']:
                                continue
                        if self._user_info_dict[user_b]['white_list']:
                            if user_a not in self._user_info_dict[user_b]['white_list']:
                                continue

                        if user_info_a['lan_id'] == user_info_b['lan_id']:
                            # 同一局域网, 局域网互联, a连接b
                            #                                   cmd               name,                      ip,                port,                    password
                            exec("self.user.{0}.send(['CMD_Connect', user_info_b['name'], user_info_b['local_ip'], user_info_b['port'], user_info_b['password']])".format(user_a))
                        else:
                            # 不同局域网
                            if user_info_a['is_public_network']:
                                # 公网a b去连接公网a
                                exec("self.user.{0}.send(['CMD_Connect', user_info_a['name'], user_info_a['public_ip'], user_info_a['port'], user_info_a['password']])".format(user_b))
                            elif user_info_b['is_public_network']:
                                # 公网b a去连接公网b
                                exec("self.user.{0}.send(['CMD_Connect', user_info_b['name'], user_info_b['public_ip'], user_info_b['port'], user_info_b['password']])".format(user_a))
                            else:
                                # 不同局域网下的a,b, 使用Room代理
                                # TODO
                                pass
                    old_user_info_dict = copy.deepcopy(self._user_info_dict)
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info_format_err("Runtime Err 2", "user_information_processing")

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

class User():

    def __init__(self, user_name, room_ip="", room_port=2428, room_password="Passable", public_ip="", server_port=0, user_password="", lan_id="Default", log="INFO", password_digits=16, encryption=True, white_list=[], black_list=[]):
        """
        文档:
            创建一个聊天室用户

        参数:
            user_name : str
                用户名
            user_password : str (Default: "")
                用户密码
            room_ip : str (Default: "127.0.0.1")
                需要连接的聊天室ip, 默认为本机ip
            room_port : int  (Default: 2428)
                需要连接的聊天室端口
            room_password : str (Default: "Passable")
                需要连接的聊天室密码
            public_ip : str (Default: "")
                如果本机拥有公网ip填写public_ip后本机被标记为公网ip用户
                其他用户连接本用户都将通过此公网ip进行连接
            server_port : int (Default: ramdom)
                本机消息服务对外端口, 默认为 0 系统自动分配
                请注意需要在各种安全组或防火墙开启此端口
            lan_id : str (Default: "Default")
                默认为"Default", 局域网id, 由用户手动设置
                同一局域网的用户请使用相同的局域网id, 这样同一内网下的用户将直接局域网互相连接而不会通过速度慢的中继连接等方式
            log : None or str (Default: "INFO")
                日志等级
                    None: 除了错误什么都不显示
                    "INFO": 显示基本连接信息
                    "DEBUG": 显示所有信息
            password_digits : int (Default: 16)
                密码位数, 默认16位
            encryption : bool(default True)
                是否加密传输, 不加密效率较高
            white_list : str (Default: [])
                白名单 : 如果设置白名单,只有白名单内的用户可以连接
            black_list : str (Default: [])
                黑名单 : 如果设置黑名单,黑名单内的用户不可连接
        例子:
            import ChatRoom

            # 创建一个聊天室用户
            user = ChatRoom.User(
                    user_name="Foo",
                )

            # 运行默认的回调函数(所有接受到的信息都在self.recv_info_queue队列里,需要用户手动实现回调函数并使用)
            # 默认的回调函数只打印信息
            user.default_callback()
        """

        self.user_name = user_name
        if self.user_name == "Room":
            raise ValueError('The user_name not be "Room"!')

        if not room_ip:
            room_ip = get_host_ip()

        self.room_ip = room_ip
        self.room_port = room_port
        self.room_password = room_password
        self.encryption = encryption
        self.white_list = white_list
        self.black_list = black_list

        self._log = Log(log)

        self.recv_info_queue = queue.Queue()

        self.user_password = user_password

        # 分组
        self.lan_id = lan_id

        self.local_ip = get_host_ip()
        self.public_ip = public_ip

        # 是否公网ip
        if self.public_ip:
            self.is_public_network = True
        else:
            self.is_public_network = False

        self.server_port = server_port

        self.server_password = self._random_password(password_digits)

        self.server = Server(self.local_ip, self.server_port,  self.server_password, log=log, encryption=encryption)

        time.sleep(.01)
        while True:
            if self.server.port:
                break
            else:
                time.sleep(.1)
        self.port = self.server.port

        self.client = Client(self.user_name, self.user_password, log="INFO", auto_reconnect=True, reconnect_name_whitelist=["Room"], encryption=encryption)

        # Redirect
        self.client.recv_info_queue = self.server.recv_info_queue
        self.user = self.client.user = self.server.user
        self.client.register_disconnect_user_fun(self._disconnect_callback)
        self.client.register_connect_user_fun(self._connect_callback)

        self._callback_pretreatment(self.client.recv_info_queue)

        # 进入聊天室
        self.client.conncet("Room", self.room_ip, self.room_port, self.room_password)
        self.user.Room.send(["CMD_GetUserNapwInfo"])

    def _disconnect_callback(self):
        pass

    def _connect_callback(self):

        # 发送用户信息
        self.client.user.Room.send(
            [   "CMD_UserInfo",
                {
                    "name" : self.user_name,
                    "local_ip" : self.local_ip,
                    "public_ip" : self.public_ip,
                    "port" : self.port,
                    "password" :  self.server_password,
                    "is_public_network" : self.is_public_network,
                    "lan_id" : self.lan_id,
                    "white_list" : self.white_list,
                    "black_list" : self.black_list,
                },
            ]
        )

    def _connect(self, server_name, ip, port, password):

        self._log.log_info_format("Connecty", server_name)
        self.client.conncet(server_name , ip, port, password)

    def _random_password(self, password_digits):

        key=random.sample(string.printable, password_digits)
        keys="".join(key)

        return keys

    def _callback_pretreatment(self, recv_info_queue):

        def sub():
            while True:
                try:
                    recv_data = recv_info_queue.get()
                    # [from_user, data]
                    from_user = recv_data[0]

                    # DEBUG
                    # print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.user_name, "pr recv:", recv_data)

                    if from_user == "Room":
                        # 过滤出Room消息
                        # ["Room", [cmd, xxx, xxx]]
                        try:
                            cmd = recv_data[1][0]
                        except Exception:
                            # 接收到来自Room的消息格式不标准,可能是手动发送的
                            print("{0}: reve not format data: {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))
                            continue

                        if cmd == 'CMD_Connect':
                            # 连接其他user
                            # ["Room", ["CMD_Connect", name, ip, port, password]]
                            name = recv_data[1][1]
                            try:
                                exec("self.user.{0}".format(name))
                            except AttributeError:
                                ip = recv_data[1][2]
                                port = recv_data[1][3]
                                password = recv_data[1][4]
                                self._connect(name, ip, port, password)
                            continue
                        elif cmd == 'CMD_UserNapwInfo':
                            # 保存其他user密码配置信息
                            # ["Room", ["CMD_UserNapwInfo", user_napw_info]]
                            user_napw_info = recv_data[1][1]
                            self.server.user_napw_info = user_napw_info
                            continue

                    self.recv_info_queue.put(recv_data)
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info_format("Runtime Err 3", recv_data)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def default_callback(self):

        def sub():
            while True:
                recv_data = self.recv_info_queue.get()
                print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.user_name, "recv:", recv_data)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def register_get_event_callback_func(self, get_name, func):
        self.client.register_get_event_callback_func(get_name, func)
        self.server.register_get_event_callback_func(get_name, func)

if __name__ == "__main__":
    """ ChatRoom 是单Room多User的形式运行的,实际使用中请创建多个User使用 """
    random_int = random.randrange(1, 3)
    if random_int == 1:
        # Room
        import ChatRoom
        room = ChatRoom.Room()

        # User_1
        import ChatRoom

        user_foo = ChatRoom.User(
                user_name="Foo",
            )

        user_foo.default_callback()

        def foo_server_test_get_callback_func(data):
            # do something
            return ["user_foo doing test", data]
        user_foo.register_get_event_callback_func("test", foo_server_test_get_callback_func)

        # User_2
        import ChatRoom

        user_bar = ChatRoom.User(
                user_name="Bar",
            )

        user_bar.default_callback()

        def bar_server_test_get_callback_func(data):
            # do something
            return ["user_bar doing test", data]
        user_bar.register_get_event_callback_func("test", bar_server_test_get_callback_func)

        # User_3 Room代理连接User
        import ChatRoom

        user_too = ChatRoom.User(
                user_name="Too",
                # 通过lan_id区分各个user是否在同一局域网下,不同的局域网内User将使用中继连接进行连接
                lan_id="other_net"
            )

        user_too.default_callback()

        def too_server_test_get_callback_func(data):
            # do something
            return ["user_too doing test", data]
        user_too.register_get_event_callback_func("test", too_server_test_get_callback_func)


        # ===================================== send方法 ============================================
        user_foo.user.Bar.send("Hello")
        user_bar.user.Foo.send("Hello")

        # ===================================== get方法 =============================================
        user_foo.user.Bar.get("test", "Hello get")
        user_bar.user.Foo.get("test", "Hello get")

    elif random_int == 2:
        # 需要验证用户密码的形式
        # Room
        import ChatRoom

        # user_napw_info 使用 hash_encryption 函数生成
        user_napw_info = {'Foo': b'$2b$10$RjxnUdrJbLMLe/bNY7sUU.SmDmsAyfSUmuvXQ7eYjXYVKNlR36.XG',
            'Bar': b'$2b$10$/CIYKXeTwaXcuJIvv7ySY.Tzs17u/EwqT5UlOAkNIosK594FTB35e'}
        room = ChatRoom.Room(user_napw_info=user_napw_info)

        # User
        import ChatRoom

        user = ChatRoom.User(
                user_name="Foo",
                user_password="123456"
            )

        user.default_callback()

        # send info
        user.user.Room.send("Hello")
        room.user.Foo.send("Hello")

    elif random_int == 3:
        # Room
        import ChatRoom
        room = ChatRoom.Room()

        # User1
        import ChatRoom

        user1 = ChatRoom.User(
                user_name="Foo",
            )

        user1.default_callback()

        def server_test_get_callback_func(data):
            # do something
            return ["user1 doing test", data]

        user1.register_get_event_callback_func("test", server_test_get_callback_func)

        # User2
        import ChatRoom

        user2 = ChatRoom.User(
                user_name="Bar",
            )

        user2.default_callback()

        def server_test_get_callback_func(data):
            # do something
            return ["user2 doing test", data]

        user2.register_get_event_callback_func("test", server_test_get_callback_func)

        # send info
        user1.user.Bar.send("Hello user2")
        user2.user.Foo.send("Hello user1")

        # get info
        print(user1.user.Bar.get("test", "Hello get"))
        print(user2.user.Foo.get("test", "Hello get"))
