# -*- coding: utf-8 -*-
import time
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

class Rely_Node():

    def __init__(self, to_user_name, master):

        self.to_user_name = to_user_name

        self.master = master

    def send(self, data):

        self.master.user.Room.send(['Forwarding', self.to_user_name, data])

class Room():

    def __init__(self, ip="", port=2428, password="Passable", log="INFO", user_napw_info=None, blacklist=None):
        """
        文档:
            创建一个聊天室

        参数:
            ip : str
                聊天室建立服务的IP地址
            port : int
                端口
            password : str
                密码
            log : None or str
                日志等级
                    None: 除了错误什么都不显示
                    "INFO": 显示基本连接信息
                    "DEBUG": 显示所有信息
            user_napw_info : dict
                用户加密密码信息字典, 设定后只有使用正确的用户名和密码才能登录服务端
                不指定跳过用户真实性检测
                使用 hash_encryption 函数生成需要的 user_napw_info
            blacklist : list
                ip黑名单, 在这个列表中的ip会被聊天室集群拉黑

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

        self._log = Log(log)

        self.server = Server(self.ip, self.port, self.password, log=log, user_napw_info=user_napw_info, blacklist=blacklist)

        self.server.register_disconnect_user_fun(self._disconnect_callback)

        self.user = self.server.user

        self._user_info_dict = {}

        self._relay_connect_user_info_dict = {}

        self._callback_server(self.server.recv_info_queue)

        self._user_information_processing()

    def _disconnect_callback(self, client_name):

        # 删除节点信息
        del self._user_info_dict[client_name]

        # 清楚中继节点信息
        if client_name in self._relay_connect_user_info_dict:
            for to_user in self._relay_connect_user_info_dict[client_name]:
                exec("self.user.{0}.send(['del_relay_connect', client_name])".format(to_user))

            del self._relay_connect_user_info_dict[client_name]
            for relay_connect_set in self._relay_connect_user_info_dict.values():
                try:
                    relay_connect_set.remove(client_name)
                except KeyError:
                    pass

    def _callback_server(self, recv_info_queue):

        def sub():
            while True:
                try:
                    recv_data = recv_info_queue.get()
                    # [usr, [cmd, xxx, xxx]]
                    # DEBUG
                    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "recv:", recv_data)
                    user = recv_data[0]
                    cmd = recv_data[1][0]
                    if cmd == "Forwarding":
                        #  ['Alice', ['Forwarding', 'Andy', 'Hello!']]
                        to_user = recv_data[1][1]
                        user_info = recv_data[1][2]
                        # ['Forwarding', 'Alice', 'Hello!']
                        exec("self.user.{0}.send(['Forwarding', user, user_info])".format(to_user))
                    elif cmd == "user_info":
                        #  ['Alice', ['user_info', {'local_ip': '10.88.3.152', 'public_ip': '', 'port': 13004, 'password': 'Z(qC\x0b1=\nkc\ry|L\t+', 'is_public_network': False, 'lan_id': 'D'}]]
                        user_info = recv_data[1][1]
                        self._user_info_dict[user] = user_info
                    elif cmd == "CMD_GET_USER_NAPW_INFO":
                        # ['Alice', 'CMD_GET_USER_NAPW_INFO']
                        exec("self.user.{0}.send(['user_napw_info', self.user_napw_info])".format(user))

                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info("{0}: \033[0;36;41mRuntime Err:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _user_information_processing(self):

        def sub():
            while True:
                time.sleep(10)
                try:
                    for user_a, user_b in itertools.combinations(self._user_info_dict, 2):
                        # print(user_a, user_b)
                        user_info_a = self._user_info_dict[user_a]
                        user_info_b = self._user_info_dict[user_b]
                        if user_info_a['lan_id'] == user_info_b['lan_id']:
                            # 同一局域网, 局域网互联, a连接b
                            #       cmd               name,                      ip,                port,             password
                            exec("self.user.{0}.send(['connect', user_info_b['name'], user_info_b['local_ip'], user_info_b['port'], user_info_b['password']])".format(user_a))
                        else:
                            # 不同局域网
                            if user_info_a['is_public_network']:
                                # 公网a b去连接公网a
                                exec("self.user.{0}.send(['connect', user_info_a['name'], user_info_a['public_ip'], user_info_a['port'], user_info_a['password']])".format(user_b))
                            elif user_info_b['is_public_network']:
                                # 公网b a去连接公网b
                                exec("self.user.{0}.send(['connect', user_info_b['name'], user_info_b['public_ip'], user_info_b['port'], user_info_b['password']])".format(user_a))
                            else:
                                # 不同局域网下的a,b, 使用中继
                                exec("self.user.{0}.send(['relay_connect', user_b])".format(user_a))
                                exec("self.user.{0}.send(['relay_connect', user_a])".format(user_b))

                                try:
                                    self._relay_connect_user_info_dict[user_a]
                                except KeyError:
                                    self._relay_connect_user_info_dict[user_a] = set()

                                try:
                                    self._relay_connect_user_info_dict[user_b]
                                except KeyError:
                                    self._relay_connect_user_info_dict[user_b] = set()

                                self._relay_connect_user_info_dict[user_a].add(user_b)
                                self._relay_connect_user_info_dict[user_b].add(user_a)

                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info("{0}: \033[0;36;41mRuntime Err:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

class User():

    def __init__(self, user_name, room_ip="", room_port=2428, room_password="Passable", public_ip="", server_port=0, user_password="", lan_id="Default", log="INFO", password_digits=16):
        """
        文档:
            创建一个聊天室用户

        参数:
            user_name : str
                用户名
            user_password : str
                用户密码
            room_ip : str
                需要连接的聊天室ip, 默认为本机ip
            room_port : int
                需要连接的聊天室端口
            room_password : str
                需要连接的聊天室密码
            public_ip : str
                如果本机拥有公网ip填写public_ip后本机被标记为公网ip用户
                其他用户连接本用户都将通过此公网ip进行连接
            server_port : int
                本机消息服务对外端口, 默认为 0 系统自动分配
                请注意需要在各种安全组或防火墙开启此端口
            lan_id : str
                默认为"Default", 局域网id, 由用户手动设置
                同一局域网的用户请使用相同的局域网id, 这样同一内网下的用户将直接局域网互相连接而不会通过速度慢的中继连接等方式
            log : None or str
                日志等级
                    None: 除了错误什么都不显示
                    "INFO": 显示基本连接信息
                    "DEBUG": 显示所有信息
            password_digits : int
                密码位数, 默认16位

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

        self._log = Log(log)

        self.recv_info_queue = queue.Queue()

        self._relay_connect_name_set = set()

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

        self.server = Server(self.local_ip, self.server_port,  self.server_password, log=log)

        time.sleep(.01)
        while True:
            if self.server.port:
                break
            else:
                time.sleep(.1)
        self.port = self.server.port

        self.client = Client(self.user_name, self.user_password, log="INFO", auto_reconnect=True, reconnect_name_whitelist=["Room"])

        # Redirect
        self.client.recv_info_queue = self.server.recv_info_queue
        self.user = self.client.user = self.server.user
        self.client.register_disconnect_user_fun(self._disconnect_callback)
        self.client.register_connect_user_fun(self._connect_callback)

        self._callback_pretreatment(self.client.recv_info_queue)

        # 进入聊天室
        self.client.conncet("Room", self.room_ip, self.room_port, self.room_password)
        self.user.Room.send(["CMD_GET_USER_NAPW_INFO"])

    def _relay_connect(self, to_user_name):

        self._log.log_info("{0}: \033[0;36;42mRelay Connecty:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), to_user_name))
        exec("self.user.{0} = Rely_Node(to_user_name, self)".format(to_user_name))
        self._relay_connect_name_set.add(to_user_name)

    def _disconnect_callback(self):

        for to_user_name in self._relay_connect_name_set:
            exec("del self.user.{0}".format(to_user_name))
        self._relay_connect_name_set = set()

    def _connect_callback(self):

        # 发送用户信息
        self.client.user.Room.send(
            [   "user_info",
                {
                    "name" : self.user_name,
                    "local_ip" : self.local_ip,
                    "public_ip" : self.public_ip,
                    "port" : self.port,
                    "password" :  self.server_password,
                    "is_public_network" : self.is_public_network,
                    "lan_id" : self.lan_id,
                },
            ]
        )

    def _del_relay_connect(self, to_user_name):

        exec("del self.user.{0}".format(to_user_name))
        self._relay_connect_name_set.remove(to_user_name)

    def _connect(self, server_name, ip, port, password):

        self._log.log_info("{0}: \033[0;36;42mConnecty:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
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
                    # DEBUG
                    # print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.user_name, "pr recv:", recv_data)
                    from_user = recv_data[0]
                    if from_user == "Room":
                        cmd = recv_data[1][0]
                        if cmd == "Forwarding":
                            # ["Room", ["Forwarding", "to_user", data]]
                            recv_data = [recv_data[1][1], recv_data[1][2]]
                        elif cmd == 'connect':
                            # ["Room", ["connect", name, ip, port, password]]
                            name = recv_data[1][1]
                            try:
                                exec("self.user.{0}".format(name))
                            except AttributeError:
                                ip = recv_data[1][2]
                                port = recv_data[1][3]
                                password = recv_data[1][4]
                                self._connect(name, ip, port, password)
                            continue
                        elif cmd == 'relay_connect':
                            # ["Room", ["relay_connect", name]]
                            name = recv_data[1][1]
                            try:
                                exec("self.user.{0}".format(name))
                            except AttributeError:
                                self._relay_connect(name)
                            continue
                        elif cmd == 'del_relay_connect':
                            # ["Room", ["del_relay_connect", name]]
                            name = recv_data[1][1]
                            try:
                                exec("self.user.{0}".format(name))
                            except:
                                pass
                            else:
                                self._del_relay_connect(name)
                            continue
                        elif cmd == 'user_napw_info':
                            # ["Room", ["user_napw_info", name]]
                            user_napw_info = recv_data[1][1]
                            self.server.user_napw_info = user_napw_info
                            continue

                    self.recv_info_queue.put(recv_data)
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info("{0}: \033[0;36;41mRuntime Err:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))

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

if __name__ == "__main__":

    # Room
    import ChatRoom
    room = ChatRoom.Room()

    # User
    import ChatRoom

    user = ChatRoom.User(
            user_name="Foo",
        )

    user.default_callback()

    # send info
    user.user.Room.send("Hello")
    room.user.Foo.send("Hello")

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