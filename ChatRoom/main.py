# -*- coding: utf-8 -*-
import os
import time
import copy
import queue
import random
import string
import shutil
import Mconfig
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

        self.server._register_disconnect_user_fun(self._disconnect_callback)

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

                    # DEBUG
                    # print("{0} recv: {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))

                    try:
                        cmd = recv_data[1][0]
                    except Exception:
                        # 接收到来自User的消息格式不标准,可能是手动发送的
                        print("{0}: reve not format data: {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))
                        continue

                    if cmd == "CMD_UserInfo":
                        # 接收from_user信息
                        #  ['from_user', ['CMD_UserInfo', {'local_ip': '10.88.3.152', 'public_ip': '', 'port': 13004, 'password': 'Z(qC\x0b1=\nkc\ry|L\t+', 'is_public_network': False, 'lan_id': 'D'}]]
                        user_info = recv_data[1][1]
                        self._user_info_dict[from_user] = user_info
                    elif cmd == "CMD_GetUserNapwInfo":
                        # 向from_user发送其他user密码配置信息
                        # ['from_user', 'CMD_GetUserNapwInfo']
                        # exec("self.user.{0}.send(['CMD_UserNapwInfo', self.user_napw_info])".format(from_user))
                        get_user = getattr(self.user, from_user)
                        get_user.send(['CMD_UserNapwInfo', self.user_napw_info])
                    elif cmd == "CMD_UserLog":
                        # TODO 处理User日志信息
                        # [from_user', ["CMD_UserLog", time.strftime('%Y-%m-%d %H:%M:%S'), log_id, log_type, log_info]
                        self._log.log_info_format("LOG", recv_data)
                    else:
                        print("{0} recv not format data: {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recv_data))
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
                # 这个线程用于调度所有的User的连接,如果其中某两个User断开了连接,这里会重新调度User进行连接
                if old_user_info_dict == self._user_info_dict:
                    # 未发生改变,继续等待20s,然后发生连接指令,如果各个User连接正常,那么指令无效,如果某两个User断开连接则会在次指令下进行重连
                    time.sleep(20)
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
                            # exec("self.user.{0}.send(['CMD_Connect', user_info_b['name'], user_info_b['local_ip'], user_info_b['port'], user_info_b['password']])".format(user_a))
                            get_user = getattr(self.user, user_a)
                            get_user.send(['CMD_Connect', user_info_b['name'], user_info_b['local_ip'], user_info_b['port'], user_info_b['password']])
                        else:
                            # 不同局域网
                            if user_info_a['is_public_network']:
                                # 公网a b去连接公网a
                                # exec("self.user.{0}.send(['CMD_Connect', user_info_a['name'], user_info_a['public_ip'], user_info_a['port'], user_info_a['password']])".format(user_b))
                                get_user = getattr(self.user, user_b)
                                get_user.send(['CMD_Connect', user_info_a['name'], user_info_a['public_ip'], user_info_a['port'], user_info_a['password']])
                            elif user_info_b['is_public_network']:
                                # 公网b a去连接公网b
                                # exec("self.user.{0}.send(['CMD_Connect', user_info_b['name'], user_info_b['public_ip'], user_info_b['port'], user_info_b['password']])".format(user_a))
                                get_user = getattr(self.user, user_a)
                                get_user.send(['CMD_Connect', user_info_b['name'], user_info_b['public_ip'], user_info_b['port'], user_info_b['password']])
                            else:
                                # 不同局域网下的a,b
                                # 这种情况涉及很多坑,原来尝试了使用Room做中继,但是后续的功能没法无损移植上去,所以这个功能本系统就不支持了
                                # 解决的办法还是让所有的User都能互相访问,不要出现内网对内网的情况
                                # 或者搭建VPN
                                # 或者使用端口映射
                                pass
                    old_user_info_dict = copy.deepcopy(self._user_info_dict)
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                    self._log.log_info_format_err("Runtime Err 2", "user_information_processing")

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

class ShareObjectMerge():
    """ 合并底层Share对象 """
    def __init__(self, server_user, client_user):
        self._server_share = server_user.myself.share
        self._client_share = client_user.myself.share

    def __str__(self) -> str:
        self._server_share._share_dict.update(self._client_share._share_dict)
        return str(self._server_share._share_dict)

    def __repr__(self) -> str:
        self._server_share._share_dict.update(self._client_share._share_dict)
        return str(self._server_share._share_dict)

    def __getitem__(self, key):
        try:
            return self._server_share._share_dict[key]
        except KeyError:
            return self._client_share._share_dict[key]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __delitem__(self, key):
        self.__delattr__(key)

    # 由于User是Server和Client合并,所以底层有两个一样的分享字典,我们做迭代的时候暴露其中一个就可以了
    def __iter__(self):
        # return itertools.chain(self._server_share._share_dict.__iter__(), self._client_share._share_dict.__iter__())
        return self._server_share._share_dict.__iter__()

    def _items_(self):
        # return itertools.chain(self._server_share._share_dict.items(), self._client_share._share_dict.items())
        return self._server_share._share_dict.items()

    def __setattr__(self, attr: str, value) -> None:
        """ set & modify"""
        if attr.startswith("_"):
            super().__setattr__(attr, value)
        else:
            # 保存变量
            self._server_share.__setattr__(attr, value)
            self._client_share.__setattr__(attr, value)

            self._server_share._share_dict[attr] = value
            self._client_share._share_dict[attr] = value

    def __delattr__(self, name: str) -> None:
        """ del """
        # 删除变量
        try:
            self._server_share.__delattr__(name)
        except AttributeError:
            pass
        try:
            self._client_share.__delattr__(name)
        except AttributeError:
            pass

        try:
            del self._server_share._share_dict[name]
        except KeyError:
            pass
        try:
            del self._client_share._share_dict[name]
        except KeyError:
            pass

    def __getattribute__(self, __name: str):
        try:
            # 让本身类保持正常
            return super().__getattribute__(__name)
        except AttributeError:
            # 获取user从S或者C中取
            try:
                return self._server_share.__getattribute__(__name)
            except AttributeError:
                return self._client_share.__getattribute__(__name)

    def __dir__(self):
        return self._server_share.__dir__() + self._client_share.__dir__()

class StatusObjectMerge():
    """ 合并底层Status对象 """
    def __init__(self, server_user, client_user):
        # 套用上面的代码,只是下面改成了status
        self._server_share = server_user.myself.status
        self._client_share = client_user.myself.status

    def __str__(self) -> str:
        self._server_share._share_dict.update(self._client_share._share_dict)
        return str(self._server_share._share_dict)

    def __repr__(self) -> str:
        self._server_share._share_dict.update(self._client_share._share_dict)
        return str(self._server_share._share_dict)

    def __getitem__(self, key):
        try:
            return self._server_share._share_dict[key]
        except KeyError:
            return self._client_share._share_dict[key]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __iter__(self):
        # return itertools.chain(self._server_share._share_dict.__iter__(), self._client_share._share_dict.__iter__())
        return self._server_share._share_dict.__iter__()

    def _items_(self):
        # return itertools.chain(self._server_share._share_dict.items(), self._client_share._share_dict.items())
        return self._server_share._share_dict.items()

    def __setattr__(self, attr: str, value) -> None:
        """ set & modify"""
        if attr.startswith("_"):
            super().__setattr__(attr, value)
        else:
            # 保存变量
            self._server_share.__setattr__(attr, value)
            self._client_share.__setattr__(attr, value)

            self._server_share._share_dict[attr] = value
            self._client_share._share_dict[attr] = value

    def __delattr__(self, name: str) -> None:
        """ del """
        # 删除变量
        try:
            self._server_share.__delattr__(name)
        except AttributeError:
            pass
        try:
            self._client_share.__delattr__(name)
        except AttributeError:
            pass

        try:
            del self._server_share._share_dict[name]
        except KeyError:
            pass
        try:
            del self._client_share._share_dict[name]
        except KeyError:
            pass

    def __getattribute__(self, __name: str):
        try:
            # 让本身类保持正常
            return super().__getattribute__(__name)
        except AttributeError:
            # 获取user从S或者C中取
            try:
                return self._server_share.__getattribute__(__name)
            except AttributeError:
                return self._client_share.__getattribute__(__name)

    def __dir__(self):
        return self._server_share.__dir__() + self._client_share.__dir__()

class User():

    class _UserUser():
        """ 合并Server和Client的User类 """
        class MySelf():
            """ 表层MySelf类 """
            def __init__(self, server_user, client_user):
                self.share = ShareObjectMerge(server_user, client_user)
                self.status = StatusObjectMerge(server_user, client_user)

        def __init__(self, server_user, client_user) -> None:
            self._server_user = server_user
            self._client_user = client_user

            self.myself = self.MySelf(server_user, client_user)

        def __getattribute__(self, __name: str):
            try:
                # 让本身类保持正常
                return super().__getattribute__(__name)
            except AttributeError:
                # 获取user从S或者C中取
                try:
                    return self._server_user.__getattribute__(__name)
                except AttributeError:
                    return self._client_user.__getattribute__(__name)

        def __dir__(self):
            return self._server_user.__dir__() + self._client_user.__dir__()

    def __init__(self, user_name, room_ip="", room_port=2428, room_password="Passable", public_ip="", server_port=0, user_password="", lan_id="Default", log="INFO", password_digits=16, encryption=True, white_list=[], black_list=[], log_config_file="LOG_CONFIG.py"):
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
                除了内网互联其他用户连接本用户都将通过此公网ip进行连接
            server_port : int (Default: ramdom)
                本机消息服务对外端口, 默认为 0 系统自动分配
                请注意需要在各种安全组或防火墙开启此端口
            lan_id : str (Default: "Default")
                默认为"Default", 局域网id, 由用户手动设置
                同一局域网的用户请设定相同的局域网id, 这样同一内网下的用户将直接局域网互相连接
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
                用户白名单 : 如果设置白名单,只有白名单内的用户可以连接
            black_list : str (Default: [])
                用户黑名单 : 如果设置黑名单,黑名单内的用户不可连接
            log_config_file : str (Default: "LOG_CONFIG.py")
                日志配置文件路径 : 配置当前user的日志信息
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

        self._err_log_cache_queue = queue.Queue()
        self._err_log_resend_server()

        self.recv_info_queue = queue.Queue()

        self.user_password = user_password

        if log_config_file != 'LOG_CONFIG.py':
            # 用户指定
            self._log_config = Mconfig(log_config_file)
        else:
            # 使用默认
            if not os.path.isfile('LOG_CONFIG.py'):
                pac_path, _ = os.path.split(__file__)
                default_config_file_path = os.path.join(pac_path, 'config', 'DEFAULT_LOG_CONFIG.py')
                shutil.copyfile(default_config_file_path, 'LOG_CONFIG.py')
            self._log_config = Mconfig(log_config_file)

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

        # 指定重连白名单为"Room",让User不重连其他User只连接Room
        # User, Server, Client 使用同一个user对象
        self.client = Client(self.user_name, self.user_password, log="INFO", auto_reconnect=True, reconnect_name_whitelist=["Room"], encryption=encryption)

        # Redirect
        self.client.recv_info_queue = self.server.recv_info_queue
        self.client._register_disconnect_user_fun(self._disconnect_callback)
        self.client._register_connect_user_fun(self._connect_callback)

        self._callback_pretreatment(self.client.recv_info_queue)

        # 进入聊天室
        self.client.conncet("Room", self.room_ip, self.room_port, self.room_password)

        self.user = self._UserUser(self.server.user, self.client.user)

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

        self.client.user.Room.send(["CMD_GetUserNapwInfo"])

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
                                # 如果这个变量存在则说明已经连接就不进行重连
                                getattr(self.user, name)
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

    def _err_log_resend_server(self):

        def sub():
            while True:
                time.sleep(20)
                if self._err_log_cache_queue.empty():
                    continue
                all_log_list = []
                while not self._err_log_cache_queue.empty():
                    all_log_list.append(self._err_log_cache_queue.get())
                for log_id, log_type, log_info in all_log_list:
                    self.log(log_id, log_type, log_info)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def log(self, log_id, log_type, log_info):
        """
        文档:
            向Room发送一条日志记录

        参数:
            log_id : str
                日志id
            log_type : str
                日志类型
            info : str
                日志信息
        """
        try:
            self.user.Room.send(("CMD_UserLog", log_id, log_type, log_info, time.strftime('%Y-%m-%d %H:%M:%S')))
        except Exception:
            self._log.log_info_format_err("Send log Err", log_id)
            self._err_log_cache_queue.put((log_id, log_type, log_info))

    def log_id(self, log_id):
        """
        文档:
            向Room发送一条日志记录,只需要日志id参数

        参数:
            log_id : str
                日志id
        """
        log_list = self._log_config.LOG_ID_DICT.get(str(log_id), ["Err", "LogIDErr"])
        self.log(log_id, log_list[0], log_list[1])

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

    elif random_int == 2:
        # 需要验证用户密码的形式
        # Room
        import ChatRoom

        # user_napw_info 使用 hash_encryption 函数生成
        user_napw_info = {
            'Foo': b'$2b$10$RjxnUdrJbLMLe/bNY7sUU.SmDmsAyfSUmuvXQ7eYjXYVKNlR36.XG',
            'Bar': b'$2b$10$/CIYKXeTwaXcuJIvv7ySY.Tzs17u/EwqT5UlOAkNIosK594FTB35e',
        }
        room = ChatRoom.Room(user_napw_info=user_napw_info)

        # User_1
        import ChatRoom

        user_foo = ChatRoom.User(
                user_name="Foo",
                user_password="123456",
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
                user_password="abcdef",
                encryption=False,
            )

        user_bar.default_callback()

        def bar_server_test_get_callback_func(data):
            # do something
            return ["user_bar doing test", data]
        user_bar.register_get_event_callback_func("test", bar_server_test_get_callback_func)


    # ===================================== send方法 ============================================
    """
        def send(self, data):
        文档:
            向其他集群节点发送数据

        参数:
            data : all type
                发送的数据,支持所有内建格式和第三方格式
    """
    user_foo.user.Room.send("Hello")
    user_foo.user.Bar.send("Hello")

    user_bar.user.Foo.send("Hello")

    room.user.Foo.send("Hello")

    # ===================================== get方法 =============================================
    """
        def get(self, get_name, data, timeout=60):
        文档:
            向其他集群节点发送请求

        参数:
            get_name : str
                请求的名称,以此来区分不同的请求逻辑
            data : all type
                请求的参数数据,支持所有内建格式和第三方格式
    """
    user_foo.user.Bar.get("test", "Hello get")

    user_bar.user.Foo.get("test", "Hello get")
    user_bar.user.Room.get("test", "Hello get")

    room.user.Bar.get("NONO", "Hello get")

    # ===================================== 共享变量share =============================================
    # 增加,修改直接赋值
    user_foo.user.myself.share.a = "im foo a"
    user_foo.user.myself.share.b = "im foo b"

    user_bar.user.myself.share.a = 1
    user_bar.user.myself.share["c"] = 10.1

    room.user.myself.share.r = "Hello"

    # 读取
    user_foo.user.Bar.share
    user_foo.user.Room.share
    user_foo.user.Bar.share.c
    user_foo.user.Bar.share["c"]
    user_foo.user.Room.share["r"]

    user_bar.user.Foo.share
    user_bar.user.Room.share
    user_bar.user.Foo.share.b
    user_bar.user.Foo.share["b"]

    room.user.Bar.share
    room.user.Foo.share

    # 删除
    del user_foo.user.myself.share.a

    del user_bar.user.myself.share["c"]
