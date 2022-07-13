# -*- coding: utf-8 -*-
import sys
import time
import uuid
import pickle
import socket
import queue
import bcrypt
import threading
import traceback
from datetime import datetime

from ChatRoom.encrypt import encrypt
from ChatRoom.log import Log

class User():
    pass

# ======================== 自身使用 =========================
class ShareObject(object):

    def __init__(self, master, flush_time_interval=60):
        self._master = master
        self._share_dict = {}

        self.__flush_time_interval = flush_time_interval
        self.__auto_flush_server()

    def __str__(self) -> str:
        return str(self._share_dict)

    def __repr__(self) -> str:
        return str(self._share_dict)

    def __getitem__(self, key):
        return self._share_dict[key]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __setattr__(self, attr: str, value) -> None:
        """ set & modify"""
        # 保存变量
        super().__setattr__(attr, value)

        if not attr.startswith("_"):
            # 保存字典
            self._share_dict[attr] = value
            # 向所有其他用户发送该变化
            for user in [getattr(self._master.user, user_attr) for user_attr in dir(self._master.user) if not user_attr.startswith("_")]:
                try:
                    user_name = user._name
                except AttributeError:
                    # 这个异常可以过滤掉自身,因为自身中是没有_name属性的且该变化不用发送给自身
                    continue

                self._master.send(user_name, ["CMD_SHARE_UPDATE", {attr:value}])
                # print("send", user._name, ["CMD_SHARE_UPDATE", {attr:value}])

    def __delattr__(self, name: str) -> None:
        """ del """
        # 删除变量
        try:
            super().__delattr__(name)
        except AttributeError:
            pass

        try:
            del self._share_dict[name]
        except KeyError:
            pass

        if not name.startswith("_"):
            # 保存字典
            # 向所有其他用户发送该变化
            for user in [getattr(self._master.user, user_attr) for user_attr in dir(self._master.user) if not user_attr.startswith("_")]:
                try:
                    user_name = user._name
                except AttributeError:
                    # 这个异常可以过滤掉自身,因为自身中是没有_name属性的且该变化不用发送给自身
                    continue

                self._master.send(user_name, ["CMD_SHARE_DEL", name])
                # print("send", user._name, ["CMD_SHARE_DEL", name])

    def __auto_flush_server(self):
        """ 每隔一段时间自动同步 """
        # ShareObject 的同步间隔为60s,这个60s比较长,这个功能只是保险,因为任何的修改,赋值,删除都会即刻更新到其他节点上,这里只保证即刻更新后的同步机制
        def sub():
            while True:
                try:
                    time.sleep(self.__flush_time_interval)
                    for user in [getattr(self._master.user, user_attr) for user_attr in dir(self._master.user) if not user_attr.startswith("_")]:
                        try:
                            user_name = user._name
                        except AttributeError:
                            # 这个异常可以过滤掉自身,因为自身中是没有_name属性的且该变化不用发送给自身
                            continue

                        self._master.send(user_name, ["CMD_SHARE_FLUSH", self._share_dict])
                        # print("send", user._name, ["CMD_SHARE_UPDATE", {attr:value}])

                except Exception as err:
                    self._master._log.log_info_format_err("Flush Err", "同步share错误!")
                    traceback.print_exc()
                    print(err)

        auto_flush_server_th = threading.Thread(target=sub)
        auto_flush_server_th.setDaemon(True)
        auto_flush_server_th.start()

class StatusObject(object):

    def __init__(self, master, flush_time_interval=30):
        self._master = master
        self._share_dict = {}

        self.__flush_time_interval = flush_time_interval
        self.__auto_flush_server()

    def __str__(self) -> str:
        return str(self._share_dict)

    def __repr__(self) -> str:
        return str(self._share_dict)

    def __getitem__(self, key):
        return self._share_dict[key]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __setattr__(self, attr: str, value) -> None:
        """ set & modify"""
        # 保存变量
        super().__setattr__(attr, value)

        if not attr.startswith("_"):
            # 保存字典
            self._share_dict[attr] = value

    def __delattr__(self, name: str) -> None:
        """ del """
        # 删除变量
        try:
            super().__delattr__(name)
        except AttributeError:
            pass

        try:
            del self._share_dict[name]
        except KeyError:
            pass

    def __auto_flush_server(self):
        """ 每隔一段时间自动同步 """
        # StatusObject的属性修改不会即刻更新,所以这里是30s更新一次,一个恰当的频率
        def sub():
            while True:
                try:
                    time.sleep(self.__flush_time_interval)
                    for user in [getattr(self._master.user, user_attr) for user_attr in dir(self._master.user) if not user_attr.startswith("_")]:
                        try:
                            user_name = user._name
                        except AttributeError:
                            # 这个异常可以过滤掉自身,因为自身中是没有_name属性的且该变化不用发送给自身
                            continue

                        self._master.send(user_name, ["CMD_STATUS_FLUSH", self._share_dict])
                        # print("send", user._name, ["CMD_SHARE_UPDATE", {attr:value}])

                except Exception as err:
                    self._master._log.log_info_format_err("Flush Err", "同步status错误!")
                    traceback.print_exc()
                    print(err)

        auto_flush_server_th = threading.Thread(target=sub)
        auto_flush_server_th.setDaemon(True)
        auto_flush_server_th.start()

class MySelfObject(object):

    def __init__(self, master):
        self.share = ShareObject(master)
        self.status = StatusObject(master)

# ======================== 其他User使用 =========================
class OUSObject(object):
    """ Other User Share And Status Object """

    def __init__(self) -> None:
        self._share_dict = {}

    def __str__(self) -> str:
        return str(self._share_dict)

    def __repr__(self) -> str:
        return str(self._share_dict)

    def __getitem__(self, key):
        return self._share_dict[key]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __setattr__(self, attr: str, value) -> None:
        """ set & modify"""
        # 保存变量
        super().__setattr__(attr, value)

        if not attr.startswith("_"):
            # 保存字典
            self._share_dict[attr] = value

    def __delattr__(self, name: str) -> None:
        """ del """
        # 删除变量
        try:
            super().__delattr__(name)
        except AttributeError:
            pass

        try:
            del self._share_dict[name]
        except KeyError:
            pass

class Node():

    def __init__(self, name, master):

        self._name  = name
        self._master = master

        self.share = OUSObject()
        self.status = OUSObject()

    def send(self, data):
        """
        文档:
            向其他集群节点发送数据

        参数:
            data : all type
                发送的数据,支持所有内建格式和第三方格式
        """

        self._master.send(self._name, ["CMD_SEND", data])

    def get(self, get_name, data, timeout=60):
        """
        文档:
            向其他集群节点发送请求

        参数:
            get_name : str
                请求的名称,以此来区分不同的请求逻辑
            data : all type
                请求的参数数据,支持所有内建格式和第三方格式
        """

        uuid_id = uuid.uuid1()
        self._master.send(self._name, ["CMD_GET", uuid_id, get_name, data])

        self._master.get_event_info_dict[uuid_id] = {
            "event" : threading.Event(),
        }

        self._master.get_event_info_dict[uuid_id]["event"].clear()
        if self._master.get_event_info_dict[uuid_id]["event"].wait(timeout):
            return self._master.get_event_info_dict[uuid_id]["result"]
        else:
            raise Exception("TimeoutError: {0} {1} timeout err!".format(get_name, timeout))

    def send_file(self, source_file_path, remote_file_path):
        """
        文档:
            向其他集群节点发送文件

        参数:
            source_file_path : str
                本机需要发送的文件路径
            remote_file_path : str
                对方接收文件的路径

        返回:
            file_status_object : object
                这个对象的状态会随任务进度的程度而发生改变
                waiting : 等待发送
                sending : 发送中
                success : 发送成功
                md5err  : 发送完毕但md5错误
        """

    def sync_file(self):
        """
        文档:
            返回同步文件夹下的所有文件路径列表

        返回:
            同步文件夹下的所有文件路径列表
        """

class Server():

    def __init__(self, ip, port, password="abc123", log=None, user_napw_info=None, blacklist=None, encryption=True):
        """
        文档:
            建立一个服务端

        参数:
            ip : str
                建立服务的IP地址
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
                ip黑名单, 在这个列表中的ip无法连接服务端
            encryption : bool(default True)
                是否加密传输, 不加密效率较高

        例子:
            # Server
            S = Server("127.0.0.1", 12345, password="abc123", log="INFO",
                    # user_napw_info={
                    #     "Foo" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi',
                    #     "Bar" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi',
                    #     },
                    # blacklist = ["192.168.0.10"],
                    )

            # 运行默认的回调函数(所有接受到的信息都在self.recv_info_queue队列里,需要用户手动实现回调函数并使用)
            # 默认的回调函数只打印信息
            S.default_callback_server()
        """
        self.ip = ip
        self.port = port
        self.password = password

        self.encryption = encryption

        if not blacklist:
            self.blacklist = []
        else:
            self.blacklist = blacklist

        self.user = User()
        # 在用户对象里保存自己
        self.user.myself = MySelfObject(self)

        self._send_lock = threading.Lock()

        # {"Alice" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi'}
        if not user_napw_info:
            self.user_napw_info = {}
        else:
            self.user_napw_info = user_napw_info

        self.recv_info_queue = queue.Queue()

        self.get_event_info_dict = {}

        self.recv_get_info_queue = queue.Queue()

        self.get_callback_func_dict = {}

        self._log = Log(log)

        self._encrypt = encrypt()

        self._user_dict = {}

        self.ip_err_times_dict = {}

        self.is_encryption_dict = {}

        self._connect_timeout_sock_set = set()

        self._init_conncet()

        self._connect_timeout_server()

        self._get_event_callback_server()

    def _init_conncet(self):

        def sub():
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self._sock.bind((self.ip, self.port))
            self._sock.listen(99)

            self.port = self._sock.getsockname()[1]

            self._log.log_info_format("Sucess", "等待用户连接..")
            while True:
                try:
                    sock, addr = self._sock.accept()
                    tcplink_th = threading.Thread(target=self._tcplink, args=(sock, addr))
                    tcplink_th.setDaemon(True)
                    tcplink_th.start()
                except Exception as err:
                    print("{0}: \033[0;36;41m运行用户线程错误!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _tcplink(self, sock, addr):

        if addr[0] in self.blacklist:
            self._blacklist(sock, addr)
            return

        self._connect_timeout_sock_set.add(sock)

        self._log.log_info_format("Connect", addr)

        try:
            client_pubkey = self._recv_fun_s(sock)
        except:
            self._ip_err_callback(addr)
            sock.close()
            return

        if client_pubkey == "NOT_ENCRYPTION" or not self.encryption:
            # 如果客户端不加密,那么服务端不加密
            # 如果服务端不加密,客户端也不加密
            self._send_fun_s(sock, "NOT_ENCRYPTION")
            client_name, client_password = self._recv_fun_s(sock)
            self._log.log_info_warning_format("WARNING", "NOT_ENCRYPTION")
            self.is_encryption_dict[client_name] = False
        else:
            self._send_fun_s(sock, self._encrypt.pubkey)
            client_name, client_password = self._recv_fun_encrypt_s(sock)
            self.is_encryption_dict[client_name] = True

        try:
            self._user_dict[client_name]
            self._log.log_info_format_err("client name repeat", client_name)
            sock.close()
            return
        except KeyError:
            self._user_dict[client_name] = {}
            self._user_dict[client_name]["sock"] = sock
            self._user_dict[client_name]["pubkey"] = client_pubkey

            exec('self.user.{0} = Node("{0}", self)'.format(client_name))

        password = self._recv_fun_encrypt(client_name)
        if password != self.password:
            self._log.log_info_format_err("Verified failed", client_name)
            self._password_err(client_name)
            self._ip_err_callback(addr)
            return
        else:
            self._log.log_info_format("Verified successfully", client_name)
            self._password_correct(client_name)

        if self.user_napw_info:
            hashed = self.user_napw_info.get(client_name, False)
            if hashed:
                ret = bcrypt.checkpw(client_password.encode(), hashed)
                if not ret:
                    self._log.log_info_format_err("Login failed", client_name)
                    self._log.log_debug_format_err("_tcplink", "User password is wrong!")
                    self._login_err(client_name)
                    self._ip_err_callback(addr)
                    return
            else:
                self._log.log_info_format_err("Login failed", client_name)
                self._log.log_debug_format_err("_tcplink", "User does not exist!")
                self._login_err(client_name)
                self._ip_err_callback(addr)
                return
        else:
            self._log.log_debug_format("_tcplink", "Client information is not set! Use user_napw_info to set!")

        self._log.log_info_format("Login successfully", client_name)
        self._login_correct(client_name)
        self._connect_end()

        self._connect_timeout_sock_set.remove(sock)

        while True:
            try:
                recv_data = self._recv_fun_encrypt(client_name)
                # print(recv_data)
            except (ConnectionRefusedError, ConnectionResetError, TimeoutError) as err:
                self._log.log_info_format_err("Offline", "{0} {1}".format(client_name, err))
                try:
                    self._disconnect_user_fun(client_name)
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                break

            try:
                cmd = recv_data[0]
                if cmd == "CMD_SEND":
                    # send ["CMD_SEND", data]
                    self.recv_info_queue.put([client_name, recv_data[1]])
                elif cmd == "CMD_GET":
                    # process ["CMD_GET", uuid_id, get_name, data]
                    self.recv_get_info_queue.put([client_name, recv_data])
                elif cmd == "CMD_REGET":
                    # get result ["CMD_REGET", uuid_id, result_data]
                    self.get_event_info_dict[recv_data[1]]["result"] = recv_data[2]
                    self.get_event_info_dict[recv_data[1]]["event"].set()
                elif cmd == "CMD_SHARE_UPDATE":
                    # ["CMD_SHARE_UPDATE", {attr:value}]
                    update_share_dict = recv_data[1]
                    get_user = getattr(self.user, client_name)
                    get_user.share._share_dict.update(update_share_dict)
                    for name, value in update_share_dict.items():
                        setattr(get_user.share, name, value)
                elif cmd == "CMD_SHARE_DEL":
                    # ["CMD_SHARE_DEL", name]
                    name = recv_data[1]
                    get_user = getattr(self.user, client_name)
                    del get_user.share._share_dict[name]
                    delattr(get_user.share, name)
                elif cmd == "CMD_SHARE_FLUSH":
                    # ["CMD_SHARE_FLUSH", self._share_dict]
                    share_dict = recv_data[1]
                    get_user = getattr(self.user, client_name)
                    # 更新变量
                    get_user.share._share_dict.update(share_dict)
                    for name, value in share_dict.items():
                        setattr(get_user.share, name, value)
                    # 删除多余变量
                    for del_key in get_user.share._share_dict.keys() - share_dict.keys():
                        del get_user.share._share_dict[del_key]
                        delattr(get_user.share, del_key)
                elif cmd == "CMD_STATUS_FLUSH":
                    # ["CMD_STATUS_FLUSH", self._share_dict]
                    status_dict = recv_data[1]
                    get_user = getattr(self.user, client_name)
                    # 更新变量
                    get_user.status._share_dict.update(status_dict)
                    for name, value in status_dict.items():
                        setattr(get_user.status, name, value)
                    # 删除多余变量
                    for del_key in get_user.status._share_dict.keys() - status_dict.keys():
                        del get_user.status._share_dict[del_key]
                        delattr(get_user.status, del_key)
                else:
                    self._log.log_info_format_err("Format Err", "收到 {0} 错误格式数据: {1}".format(client_name, recv_data))
            except Exception as err:
                self._log.log_info_format_err("Runtime Err", "Server处理数据错误!")
                traceback.print_exc()
                print(err)

    def _default_get_event_callback_func(self, data):
        return ["Undefined", data]

    def register_get_event_callback_func(self, get_name, func):
        self.get_callback_func_dict[get_name] = func

    def _get_event_callback_server(self):
        def server():

            def do_user_func_th(client_name, callback_func, data, uuid_id):
                try:
                    result = callback_func(data)
                    self.send(client_name, ["CMD_REGET", uuid_id, result])
                except Exception as err:
                    print("{0}: \033[0;36;41mClient 处理get任务线程错误!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

            while True:
                try:
                    # client_name, ["CMD_GET", uuid_id, get_name, data]
                    client_name, recv_data = self.recv_get_info_queue.get()
                    _, uuid_id, get_name, data = recv_data

                    try:
                        callback_func = self.get_callback_func_dict[get_name]

                        # 并发处理get请求
                        sub_th = threading.Thread(target=do_user_func_th, args=(client_name, callback_func, data, uuid_id))
                        sub_th.setDaemon(True)
                        sub_th.start()

                    except KeyError:
                        result = self._default_get_event_callback_func(data)
                        self.send(client_name, ["CMD_REGET", uuid_id, result])
                except Exception as err:
                    print("{0}: \033[0;36;41mClient 处理get任务错误!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

        server_th = threading.Thread(target=server)
        server_th.setDaemon(True)
        server_th.start()

    def _disconnect_user_fun(self, *args, **kwargs):
        pass

    def register_disconnect_user_fun(self, disconnect_user_fun):

        self._disconnect_user_fun = disconnect_user_fun

    def _ip_err_callback(self, addr):

        self._log.log_info_format_err("IP Err", addr)
        ip = addr[0]
        try:
            self.ip_err_times_dict[ip] += 1
        except KeyError:
            self.ip_err_times_dict[ip] = 1

        if self.ip_err_times_dict[ip] >= 3:
            self.blacklist.append(ip)

    def default_callback_server(self):
        def sub():
            while True:
                from_user, recv_data = self.recv_info_queue.get()
                print("{0} from {1} recv: {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), from_user, recv_data))

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _connect_timeout_server(self):

        def sub():
            # 无论是否已经断开了都会再次断开次
            old_check_time_dict = {}
            while True:
                time.sleep(10)
                remove_sock_list = []
                for sock in self._connect_timeout_sock_set:
                    try:
                        old_check_time = old_check_time_dict[sock]
                    except KeyError:
                        old_check_time = old_check_time_dict[sock] = time.time()

                    if time.time() - old_check_time >= 15:
                        self._log.log_info_warning_format("WARNING", "timeout sock close: {0}".format(sock))
                        sock.close()
                        remove_sock_list.append(sock)

                for sock in remove_sock_list:
                    self._connect_timeout_sock_set.remove(sock)
                    del old_check_time_dict[sock]

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _connect_end(self):
        self._log.log_debug_format("_connect_end", "connect_end")

    def _disconnect(self, client_name):
        self._log.log_debug_format_err("_disconnect", "disconnect")
        self._user_dict[client_name]["sock"].close()
        del self._user_dict[client_name]
        exec('del self.user.{0}'.format(client_name))

    def _password_err(self, client_name):
        self._log.log_debug_format_err("_password_err", "password_err")
        self._send_fun_encrypt(client_name, "t%fgDYJdI35NJKS")
        self._user_dict[client_name]["sock"].close()
        del self._user_dict[client_name]
        exec('del self.user.{0}'.format(client_name))

    def _password_correct(self, client_name):
        self._log.log_debug_format("_password_correct", "password_correct")
        self._send_fun_encrypt(client_name, "YES")

    def _login_err(self, client_name):
        self._log.log_debug_format_err("_login_err", "login_err")
        self._send_fun_encrypt(client_name, "Jif43DF$dsg")
        self._user_dict[client_name]["sock"].close()
        del self._user_dict[client_name]
        exec('del self.user.{0}'.format(client_name))

    def _login_correct(self, client_name):
        self._log.log_debug_format("_login_correct", "login_correct")
        self._send_fun_encrypt(client_name, "YES")

    def _blacklist(self, sock, addr):
        self._log.log_info_format_err("Blacklist Ban", addr)
        self._log.log_debug_format_err("_blacklist", "blacklist")
        sock.close()

    def _recv_fun_s(self, sock):
        try:
            # 接收长度
            len_n = int(sock.recv(14))
            # 接收数据
            buff = sock.recv(len_n)
            data_bytes = buff
            while len(buff) < len_n:
                # 接收的不够的时候
                len_n = len_n - len(buff)
                # 接受剩余的
                buff = sock.recv(len_n)
                # print("buff:\n", buff)
                # 原来的补充剩余的
                data_bytes += buff

            func_args_dict = pickle.loads(data_bytes)

            return func_args_dict
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._log.log_debug_format_err("_recv_fun_s", "disconnect")
            sock.close()
            raise err

    def _send_fun_s(self, sock, data):
        try:
            ds = pickle.dumps(data)

            len_n = '{:14}'.format(len(ds)).encode()

            # 全部一起发送
            sock.sendall(len_n + ds)
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._log.log_debug_format_err("_send_fun_s", "disconnect")
            sock.close()
            raise err

    def _recv_fun_encrypt_s(self, sock):
        try:
            # 接收长度
            len_n = int(sock.recv(14))
            # 接收数据
            buff = sock.recv(len_n)
            data_bytes = buff
            while len(buff) < len_n:
                # 接收的不够的时候
                len_n = len_n - len(buff)
                # 接受剩余的
                buff = sock.recv(len_n)
                # print("buff:\n", buff)
                # 原来的补充剩余的
                data_bytes += buff

            rsaDecrypt_data_bytes = self._encrypt.rsaDecrypt(data_bytes)
            func_args_dict = pickle.loads(rsaDecrypt_data_bytes)

            return func_args_dict
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._log.log_debug_format_err("_recv_fun_encrypt_s", "disconnect")
            sock.close()
            raise err

    def _send_fun_encrypt_s(self, sock, data):
        # NOTE 这个函数现在暂时未使用,如果使用要考虑到为加密端对加密端的兼容问题
        try:
            ds = pickle.dumps(data)

            ds = self._encrypt.encrypt_user(ds, self._user_dict[sock]["pubkey"])

            len_n = '{:14}'.format(len(ds)).encode()

            encrypt_data = len_n + ds
            # 全部一起发送
            sock.sendall(encrypt_data)
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._log.log_debug_format_err("_send_fun_encrypt_s", "disconnect")
            sock.close()
            raise err

    def _recv_fun(self, client_name):
        try:
            sock = self._user_dict[client_name]["sock"]
            # 接收长度
            len_n = int(sock.recv(14))
            # 接收数据
            buff = sock.recv(len_n)
            data_bytes = buff
            while len(buff) < len_n:
                # 接收的不够的时候
                len_n = len_n - len(buff)
                # 接受剩余的
                buff = sock.recv(len_n)
                # print("buff:\n", buff)
                # 原来的补充剩余的
                data_bytes += buff

            func_args_dict = pickle.loads(data_bytes)

            return func_args_dict
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._disconnect(client_name)
            raise err

    def _send_fun(self, client_name, data):
        try:
            sock = self._user_dict[client_name]["sock"]
            ds = pickle.dumps(data)

            len_n = '{:14}'.format(len(ds)).encode()

            # 全部一起发送
            sock.sendall(len_n + ds)
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._disconnect(client_name)
            raise err

    def _recv_fun_encrypt(self, client_name):
        try:
            sock = self._user_dict[client_name]["sock"]
            # 接收长度
            len_n = int(sock.recv(14))
            # 接收数据
            buff = sock.recv(len_n)
            data_bytes = buff
            while len(buff) < len_n:
                # 接收的不够的时候
                len_n = len_n - len(buff)
                # 接受剩余的
                buff = sock.recv(len_n)
                # print("buff:\n", buff)
                # 原来的补充剩余的
                data_bytes += buff

            if self.is_encryption_dict[client_name]:
                data_bytes = self._encrypt.rsaDecrypt(data_bytes)
            func_args_dict = pickle.loads(data_bytes)

            return func_args_dict
        except Exception as err:
            # traceback.print_exc()
            # print(err)
            self._disconnect(client_name)
            raise err

    def _send_fun_encrypt(self, client_name, data):
        try:
            sock = self._user_dict[client_name]["sock"]
            ds = pickle.dumps(data)

            if self.is_encryption_dict[client_name]:
                ds = self._encrypt.encrypt_user(ds, self._user_dict[client_name]["pubkey"])

            len_n = '{:14}'.format(len(ds)).encode()

            encrypt_data = len_n + ds
            # 全部一起发送
            sock.sendall(encrypt_data)
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._disconnect(client_name)
            raise err

    def send(self, client_name, data):

        self._send_lock.acquire()
        try:
            self._send_fun_encrypt(client_name, data)
        finally:
            self._send_lock.release()

    def get_user(self):

        return self._user_dict.keys()

class Client():

    def __init__(self, client_name, client_password, log=None, auto_reconnect=False, reconnect_name_whitelist=None, encryption=True):
        """
        文档:
            创建一个客户端

        参数:
            client_name : str
                客户端名称(用户名)
            client_password : str
                客户端密码(密码)
            log : None or str
                日志等级
                    None: 除了错误什么都不显示
                    "INFO": 显示基本连接信息
                    "DEBUG": 显示所有信息
            auto_reconnect : Bool
                断开连接后是否自动重连服务端
            reconnect_name_whitelist : list
                如果reconnect_name_whitelist不为空, 则重新连接只会连接客户端名称在reconnect_name_whitelist里的服务端
            encryption : bool(default True)
                是否加密传输, 不加密效率较高

        例子:
            # Client
            C = Client("Foo", "123456", log="INFO", auto_reconnect=True, reconnect_name_whitelist=None)

            # 运行默认的回调函数(所有接受到的信息都在self.recv_info_queue队列里,需要用户手动实现回调函数并使用)
            # 默认的回调函数只打印信息
            C.default_callback_server()

            # 连接服务端, 服务端名称在客户端定义为Baz
            C.conncet("Baz" ,"127.0.0.1", 12345, password="abc123")
        """
        self.client_name = client_name
        self.client_password = client_password

        self.encryption = encryption
        if not encryption:
            # 不使用加密,全局不加密
            # 如果客户端加密,那么客户端会根据服务端的加密情况自动兼容
            self._recv_fun_encrypt = self._recv_fun
            self._send_fun_encrypt = self._send_fun

        self.recv_info_queue = queue.Queue()

        self.get_event_info_dict = {}

        self.recv_get_info_queue = queue.Queue()

        self.get_callback_func_dict = {}

        self.is_encryption_dict = {}

        self._connect_timeout_sock_set = set()

        self.user = User()
        # 在用户对象里保存自己
        self.user.myself = MySelfObject(self)

        self._send_lock = threading.Lock()

        self._auto_reconnect = auto_reconnect

        if not reconnect_name_whitelist:
            self._reconnect_name_whitelist = []
        else:
            self._reconnect_name_whitelist = reconnect_name_whitelist

        self._user_dict = {}

        self._encrypt = encrypt()

        self._log = Log(log)

        self._auto_reconnect_parameters_dict = {}
        self._auto_reconnect_lock_dict = {}
        self._auto_reconnect_timedelay_dict = {}

        if self._auto_reconnect:
            self._auto_reconnect_server()

        self._connect_timeout_server()

        self._get_event_callback_server()

    def conncet(self, server_name, ip, port, password="abc123"):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
        if sys.platform == "win32":
            sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 60000, 30000))

        sock.connect((ip, port))
        self._connect_timeout_sock_set.add(sock)

        self._log.log_info_format("Connect", server_name)
        self._user_dict[server_name] = {}
        self._user_dict[server_name]["sock"] = sock

        if self.encryption:
            self._send_fun(server_name, self._encrypt.pubkey)
        else:
            self._send_fun(server_name, "NOT_ENCRYPTION")

        server_pubkey = self._recv_fun(server_name)
        if server_pubkey == "NOT_ENCRYPTION":
            self._log.log_info_warning_format("WARNING", "NOT_ENCRYPTION")
            self.is_encryption_dict[server_name] = False
        else:
            self.is_encryption_dict[server_name] = True
        self._user_dict[server_name]["pubkey"] = server_pubkey

        exec('self.user.{0} = Node("{0}", self)'.format(server_name))

        self._send_fun_encrypt(server_name, [self.client_name, self.client_password])
        self._send_fun_encrypt(server_name, password)

        connect_code = self._recv_fun_encrypt(server_name)
        if connect_code == "YES":
            self._log.log_info_format("Verified successfully", server_name)
            self._password_correct()
        else:
            self._log.log_info_format_err("Verified failed", server_name)
            self._password_err(server_name)
            return

        login_code = self._recv_fun_encrypt(server_name)
        if login_code == "YES":
            self._log.log_info_format("Login successfully", server_name)
            self._login_correct()
        else:
            self._log.log_info_format_err("Login failed", server_name)
            self._login_err(server_name)
            return

        self._connect_end()

        self._recv_data_server(server_name)

        self._auto_reconnect_parameters_dict[server_name] = [server_name, ip, port, password]
        try:
            self._auto_reconnect_lock_dict[server_name]
        except KeyError:
            self._auto_reconnect_lock_dict[server_name] = threading.Lock()

        try:
            self._connect_user_fun()
        except Exception as err:
            traceback.print_exc()
            print(err)

        self._connect_timeout_sock_set.remove(sock)

    def _auto_reconnect_server(self):

        def re_connect(server_name, ip, port, password):

            lock = self._auto_reconnect_lock_dict[server_name]

            if lock.locked():
                return

            lock.acquire()
            try:
                for _ in range(10):
                    # limit max 10 times
                    try:
                        old_delay = self._auto_reconnect_timedelay_dict[server_name]
                        if old_delay > 30:
                            self._auto_reconnect_timedelay_dict[server_name] = 30
                    except KeyError:
                        old_delay = self._auto_reconnect_timedelay_dict[server_name] = 0

                    time.sleep(old_delay)

                    try:
                        if server_name not in self._user_dict.keys():
                            self.conncet(server_name, ip, port, password)
                            self._auto_reconnect_timedelay_dict[server_name] = 0
                            break
                        else:
                            self._log.log_info_format("already connect", server_name)
                            break
                    except Exception as err:
                    # except ConnectionRefusedError:
                        # except connect all err was in this
                        self._log.log_info_format_err("Re Connect Failed", "{0} {1}".format(server_name, err))
                        self._auto_reconnect_timedelay_dict[server_name] += 5
            finally:
                lock.release()

        def server():
            while True:
                time.sleep(30)
                for server_name in self._auto_reconnect_parameters_dict.keys():
                    if server_name not in self._user_dict.keys():
                        if self._reconnect_name_whitelist:
                            if server_name in self._reconnect_name_whitelist:
                                server_name, ip, port, password = self._auto_reconnect_parameters_dict[server_name]
                                re_connect_th = threading.Thread(target=re_connect, args=(server_name, ip, port, password))
                                re_connect_th.setDaemon(True)
                                re_connect_th.start()
                        else:
                            server_name, ip, port, password = self._auto_reconnect_parameters_dict[server_name]
                            re_connect_th = threading.Thread(target=re_connect, args=(server_name, ip, port, password))
                            re_connect_th.setDaemon(True)
                            re_connect_th.start()

        server_th = threading.Thread(target=server)
        server_th.setDaemon(True)
        server_th.start()

    def _disconnect_user_fun(self, *args, **kwargs):
        pass

    def register_disconnect_user_fun(self, disconnect_user_fun):

        self._disconnect_user_fun = disconnect_user_fun

    def _connect_user_fun(self, *args, **kwargs):
        pass

    def register_connect_user_fun(self, connect_user_fun):

        self._connect_user_fun = connect_user_fun

    def _recv_data_server(self, server_name):
        def sub():
            while True:
                try:
                    recv_data = self._recv_fun_encrypt(server_name)
                    # print(recv_data)
                except (ConnectionRefusedError, ConnectionResetError, TimeoutError) as err:
                    self._log.log_info_format_err("Offline", "{0} {1}".format(server_name, err))
                    try:
                        self._disconnect_user_fun()
                    except Exception as err:
                        traceback.print_exc()
                        print(err)
                    break

                try:
                    cmd = recv_data[0]
                    if cmd == "CMD_SEND":
                        # send ["CMD_SEND", data]
                        self.recv_info_queue.put([server_name, recv_data[1]])
                    elif cmd == "CMD_GET":
                        # process ["CMD_GET", uuid_id, get_name, data]
                        self.recv_get_info_queue.put([server_name, recv_data])
                    elif cmd == "CMD_REGET":
                        # get result ["CMD_REGET", uuid_id, result_data]
                        self.get_event_info_dict[recv_data[1]]["result"] = recv_data[2]
                        self.get_event_info_dict[recv_data[1]]["event"].set()
                    elif cmd == "CMD_SHARE_UPDATE":
                        # ["CMD_SHARE_UPDATE", {attr:value}]
                        update_share_dict = recv_data[1]
                        get_user = getattr(self.user, server_name)
                        get_user.share._share_dict.update(update_share_dict)
                        for name, value in update_share_dict.items():
                            setattr(get_user.share, name, value)
                    elif cmd == "CMD_SHARE_DEL":
                        # ["CMD_SHARE_DEL", name]
                        name = recv_data[1]
                        get_user = getattr(self.user, server_name)
                        del get_user.share._share_dict[name]
                        delattr(get_user.share, name)
                    elif cmd == "CMD_SHARE_FLUSH":
                        # ["CMD_SHARE_FLUSH", self._share_dict]
                        share_dict = recv_data[1]
                        get_user = getattr(self.user, server_name)
                        # 更新变量
                        get_user.share._share_dict.update(share_dict)
                        for name, value in share_dict.items():
                            setattr(get_user.share, name, value)
                        # 删除多余变量
                        for del_key in get_user.share._share_dict.keys() - share_dict.keys():
                            del get_user.share._share_dict[del_key]
                            delattr(get_user.share, del_key)
                    elif cmd == "CMD_STATUS_FLUSH":
                        # ["CMD_STATUS_FLUSH", self._share_dict]
                        status_dict = recv_data[1]
                        get_user = getattr(self.user, server_name)
                        # 更新变量
                        get_user.status._share_dict.update(status_dict)
                        for name, value in status_dict.items():
                            setattr(get_user.status, name, value)
                        # 删除多余变量
                        for del_key in get_user.status._share_dict.keys() - status_dict.keys():
                            del get_user.status._share_dict[del_key]
                            delattr(get_user.status, del_key)
                    else:
                        self._log.log_info_format_err("Format Err", "收到 {0} 错误格式数据: {1}".format(server_name, recv_data))
                except Exception as err:
                    self._log.log_info_format_err("Runtime Err", "Client处理数据错误!")
                    traceback.print_exc()
                    print(err)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _default_get_event_callback_func(self, data):
        return ["Undefined", data]

    def register_get_event_callback_func(self, get_name, func):
        self.get_callback_func_dict[get_name] = func

    def _get_event_callback_server(self):
        def server():

            def do_user_func_th(client_name, callback_func, data, uuid_id):
                try:
                    result = callback_func(data)
                    self.send(client_name, ["CMD_REGET", uuid_id, result])
                except Exception as err:
                    print("{0}: \033[0;36;41mClient 处理get任务线程错误!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

            while True:
                try:
                    # client_name, ["CMD_GET", uuid_id, get_name, data]
                    client_name, recv_data = self.recv_get_info_queue.get()
                    _, uuid_id, get_name, data = recv_data

                    try:
                        callback_func = self.get_callback_func_dict[get_name]

                        # 并发处理get请求
                        sub_th = threading.Thread(target=do_user_func_th, args=(client_name, callback_func, data, uuid_id))
                        sub_th.setDaemon(True)
                        sub_th.start()

                    except KeyError:
                        result = self._default_get_event_callback_func(data)
                        self.send(client_name, ["CMD_REGET", uuid_id, result])
                except Exception as err:
                    print("{0}: \033[0;36;41mClient 处理get任务错误!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

        server_th = threading.Thread(target=server)
        server_th.setDaemon(True)
        server_th.start()

    def default_callback_server(self):
        def sub():
            while True:
                from_user, recv_data = self.recv_info_queue.get()
                print("{0} from {1} recv: {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), from_user, recv_data))

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _connect_timeout_server(self):

        def sub():
            # 无论是否已经断开了都会再次断开次
            old_check_time_dict = {}
            while True:
                time.sleep(10)
                remove_sock_list = []
                for sock in self._connect_timeout_sock_set:
                    try:
                        old_check_time = old_check_time_dict[sock]
                    except KeyError:
                        old_check_time = old_check_time_dict[sock] = time.time()

                    if time.time() - old_check_time >= 15:
                        self._log.log_info_warning_format("WARNING", "timeout sock close: {0}".format(sock))
                        sock.close()
                        remove_sock_list.append(sock)

                for sock in remove_sock_list:
                    self._connect_timeout_sock_set.remove(sock)
                    del old_check_time_dict[sock]

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _connect_end(self):
        self._log.log_debug_format("_connect_end", "connect_end")

    def _disconnect(self, server_name):
        self._log.log_debug_format_err("_disconnect", "disconnect")
        self._user_dict[server_name]["sock"].close()
        del self._user_dict[server_name]
        exec('del self.user.{0}'.format(server_name))

    def _password_err(self, server_name):
        self._log.log_debug_format_err("_password_err", "password_err")
        self._user_dict[server_name]["sock"].close()
        del self._user_dict[server_name]
        exec('del self.user.{0}'.format(server_name))

    def _password_correct(self):
        self._log.log_debug_format("_password_correct", "password_correct")

    def _login_err(self, server_name):
        self._log.log_debug_format_err("_login_err", "login_err")
        self._user_dict[server_name]["sock"].close()
        del self._user_dict[server_name]
        exec('del self.user.{0}'.format(server_name))

    def _login_correct(self):
        self._log.log_debug_format("_login_correct", "login_correct")

    def _recv_fun(self, server_name):
        try:
            sock = self._user_dict[server_name]["sock"]
            # 接收长度
            len_n = int(sock.recv(14))
            # 接收数据
            buff = sock.recv(len_n)
            data_bytes = buff
            while len(buff) < len_n:
                # 接收的不够的时候
                len_n = len_n - len(buff)
                # 接受剩余的
                buff = sock.recv(len_n)
                # print("buff:\n", buff)
                # 原来的补充剩余的
                data_bytes += buff

            func_args_dict = pickle.loads(data_bytes)

            return func_args_dict
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._disconnect(server_name)
            raise err

    def _send_fun(self, server_name, data):
        try:
            sock = self._user_dict[server_name]["sock"]
            ds = pickle.dumps(data)

            len_n = '{:14}'.format(len(ds)).encode()

            # 全部一起发送
            sock.sendall(len_n + ds)
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._disconnect(server_name)
            raise err

    def _recv_fun_encrypt(self, server_name):
        try:
            sock = self._user_dict[server_name]["sock"]
            # 接收长度
            len_n = int(sock.recv(14))
            # 接收数据
            buff = sock.recv(len_n)
            data_bytes = buff
            while len(buff) < len_n:
                # 接收的不够的时候
                len_n = len_n - len(buff)
                # 接受剩余的
                buff = sock.recv(len_n)
                # print("buff:\n", buff)
                # 原来的补充剩余的
                data_bytes += buff

            if self.is_encryption_dict[server_name]:
                data_bytes = self._encrypt.rsaDecrypt(data_bytes)
            func_args_dict = pickle.loads(data_bytes)

            return func_args_dict
        except Exception as err:
            # traceback.print_exc()
            # print(err)
            self._disconnect(server_name)
            raise err

    def _send_fun_encrypt(self, server_name, data):
        try:
            sock = self._user_dict[server_name]["sock"]
            ds = pickle.dumps(data)

            if self.is_encryption_dict[server_name]:
                ds = self._encrypt.encrypt_user(ds, self._user_dict[server_name]["pubkey"])

            len_n = '{:14}'.format(len(ds)).encode()

            encrypt_data = len_n + ds
            # 全部一起发送
            sock.sendall(encrypt_data)
        except Exception as err:
            traceback.print_exc()
            print(err)
            self._disconnect(server_name)
            raise err

    def send(self, server_name, data):

        self._send_lock.acquire()
        try:
            self._send_fun_encrypt(server_name, data)
        finally:
            self._send_lock.release()

    def get_user(self):

        return self._user_dict.keys()

def hash_encryption(user_info_dict):
    """
    return Server's user_napw_info

    user_info_dict:
    {
        "Foo" : "123456",
        "Bar" : "abcdef",
    }

    return:
    {
        'Foo': b'$2b$10$qud3RGagUY0/DaQnGTw2uOz1X.TlpSF9sDhQFnQvAFuIfTLvk/UlC',
        'Bar': b'$2b$10$rLdCMR7BJmuIczmNHjD2weTn4Mqt7vrvPqrqdTAQamow4OzvnqPji'
    }
    """

    user_info_encryption_dict = {}
    for user, passwd in user_info_dict.items():
        salt = bcrypt.gensalt(rounds=10)
        ashed = bcrypt.hashpw(passwd.encode(), salt)
        user_info_encryption_dict[user] = ashed

    return user_info_encryption_dict

def get_host_ip():

    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80))
        ip=s.getsockname()[0]
    finally:
        s.close()

    return ip

if __name__ == "__main__":
    # ============================================== Server ==============================================
    server = Server("127.0.0.1", 12345, password="abc123", log="INFO",
            # user_napw_info={
            #     "Foo" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi',
            #     "Bar" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi',
            #     },
            # blacklist = ["192.168.0.10"],
            )

    def server_test_get_callback_func(data):
        # do something
        if isinstance(data, int):
            time.sleep(data)
        return ["server test", data]

    # register get callback func
    server.register_get_event_callback_func("test", server_test_get_callback_func)
    # run send recv callback server
    server.default_callback_server()

    # ============================================== Client_1 ============================================
    client_1 = Client("Foo", "123456", log="INFO", auto_reconnect=True)

    def client_test_get_callback_func(data):
        # do something
        if isinstance(data, int):
            time.sleep(data)
        return ["client test", data]

    # register get callback func
    client_1.register_get_event_callback_func("test", client_test_get_callback_func)
    # run send recv callback server
    client_1.default_callback_server()

    # connect
    client_1.conncet("Server" ,"127.0.0.1", 12345, password="abc123")

    # ============================================== Client_2 ============================================
    client_2 = Client("Bar", "123456", log="INFO", auto_reconnect=True)

    def client_test_get_callback_func(data):
        # do something
        if isinstance(data, int):
            time.sleep(data)
        return ["client test", data]

    # register get callback func
    client_2.register_get_event_callback_func("test", client_test_get_callback_func)
    # run send recv callback server
    client_2.default_callback_server()

    # connect
    client_2.conncet("Server" ,"127.0.0.1", 12345, password="abc123")

    # ============================================== Test ==============================================
    # send info
    server.user.Foo.send("Hello world!")
    client_1.user.Server.send("Hello world!")
    client_2.user.Server.send("Hello world!")

    # get info
    print(client_1.user.Server.get("test", "Hello world!"))
    print(client_2.user.Server.get("test", "Hello world!"))

    st = time.time()
    print(client_1.user.Server.get("test", 3))
    print(time.time() - st)

    st = time.time()
    print(client_2.user.Server.get("test", 5))
    print(time.time() - st)
