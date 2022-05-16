# -*- coding: utf-8 -*-
import sys
import time
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

class Node():

    def __init__(self, name, master):

        self.name  = name

        self.master = master

    def send(self, data):

        self.master.send(self.name, data)

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
                是否加密传输, 不加密效率较高, 服务端和客户端必须同时开启或者关闭加密

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

        if not encryption:
            # 不使用加密
            self._recv_fun_encrypt = self._recv_fun
            self._send_fun_encrypt = self._send_fun
            self._recv_fun_encrypt_s = self._recv_fun_s
            self._send_fun_encrypt_s = self._send_fun_s

        if not blacklist:
            self.blacklist = []
        else:
            self.blacklist = blacklist

        self.user = User()

        self._send_lock = threading.Lock()

        # {"Alice" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi'}
        if not user_napw_info:
            self.user_napw_info = {}
        else:
            self.user_napw_info = user_napw_info

        self.recv_info_queue = queue.Queue()

        self._log = Log(log)

        self._encrypt = encrypt()

        self._user_dict = {}

        self.ip_err_times_dict = {}

        self._connect_timeout_sock_set = set()

        self._init_conncet()

        self._connect_timeout_server()

        self._heartbeat_server()

    def _heartbeat_server(self):

        def server():
            time.sleep(20)
            while True:
                time.sleep(40)
                try:
                    for server_name in self._user_dict.keys():
                        if self._user_dict[server_name]["can_heartbeat_flag"]:
                            self.send(server_name, "CMD_heartbeat_END")
                except Exception as err:
                    print("{0}: \033[0;36;41mServer 发送心跳失败!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

        server_th = threading.Thread(target=server)
        server_th.setDaemon(True)
        server_th.start()

    def _init_conncet(self):

        def sub():
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self._sock.bind((self.ip, self.port))
            self._sock.listen(99)

            self.port = self._sock.getsockname()[1]

            self._log.log_info("等待用户连接..")
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

        self._connect_timeout_sock_set.add(sock)

        if addr[0] in self.blacklist:
            self._blacklist(sock, addr)
            return

        self._log.log_info("{0}: \033[0;36;42mConnect:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), addr))

        try:
            client_pubkey = self._recv_fun_s(sock)
        except:
            self._ip_err_callback(addr)
            sock.close()
            return

        self._send_fun_s(sock, self._encrypt.pubkey)

        client_name, client_password = self._recv_fun_encrypt_s(sock)

        try:
            self._user_dict[client_name]
            self._log.log_info("{0}: \033[0;36;41mclient name repeat:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name))
            sock.close()
            return
        except KeyError:
            self._user_dict[client_name] = {}
            self._user_dict[client_name]["can_heartbeat_flag"] = False
            self._user_dict[client_name]["sock"] = sock
            self._user_dict[client_name]["pubkey"] = client_pubkey

            exec('self.user.{0} = Node("{0}", self)'.format(client_name))

        password = self._recv_fun_encrypt(client_name)
        if password != self.password:
            self._log.log_info("{0}: \033[0;36;41mVerified failed:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name))
            self._password_err(client_name)
            self._ip_err_callback(addr)
            return
        else:
            self._log.log_info("{0}: \033[0;36;42mVerified successfully:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name))
            self._password_correct(client_name)

        if self.user_napw_info:
            hashed = self.user_napw_info.get(client_name, False)
            if hashed:
                ret = bcrypt.checkpw(client_password.encode(), hashed)
                if not ret:
                    self._log.log_info("{0}: \033[0;36;41mLogin failed:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name))
                    self._log.log("User password is wrong!")
                    self._login_err(client_name)
                    self._ip_err_callback(addr)
                    return
            else:
                self._log.log_info("{0}: \033[0;36;41mLogin failed:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name))
                self._log.log("User does not exist!")
                self._login_err(client_name)
                self._ip_err_callback(addr)
                return
        else:
            self._log.log("Client information is not set! Use user_napw_info to set!")

        self._log.log_info("{0}: \033[0;36;42mLogin successfully:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name))
        self._login_correct(client_name)
        self._connect_end()

        self._connect_timeout_sock_set.remove(sock)

        self._user_dict[client_name]["can_heartbeat_flag"] = True

        while True:
            try:
                recv_data = self._recv_fun_encrypt(client_name)
                if recv_data == "CMD_heartbeat_END":
                    continue
                self.recv_info_queue.put([client_name, recv_data])
            except (ConnectionRefusedError, ConnectionResetError, TimeoutError) as err:
                self._log.log_info("{0}: {1} \033[0;36;41mOffline!\033[0m {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name, err))
                try:
                    self._disconnect_user_fun(client_name)
                except Exception as err:
                    traceback.print_exc()
                    print(err)
                break

    def _disconnect_user_fun(self, *args, **kwargs):
        pass

    def register_disconnect_user_fun(self, disconnect_user_fun):

        self._disconnect_user_fun = disconnect_user_fun

    def _ip_err_callback(self, addr):

        self._log.log_info("{0}: \033[0;36;41mIP Err:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), addr))
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
                recv_data = self.recv_info_queue.get()
                print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "recv:", recv_data)

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
                        print("timeout sock close:", sock)
                        sock.close()
                        remove_sock_list.append(sock)

                for sock in remove_sock_list:
                    self._connect_timeout_sock_set.remove(sock)
                    del old_check_time_dict[sock]

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _connect_end(self):
        self._log.log("_connect_end")

    def _disconnect(self, client_name):
        self._log.log("_disconnect")
        self._user_dict[client_name]["sock"].close()
        del self._user_dict[client_name]
        exec('del self.user.{0}'.format(client_name))

    def _password_err(self, client_name):
        self._log.log("_password_err")
        self._send_fun_encrypt(client_name, "t%fgDYJdI35NJKS")
        self._user_dict[client_name]["sock"].close()
        del self._user_dict[client_name]
        exec('del self.user.{0}'.format(client_name))

    def _password_correct(self, client_name):
        self._log.log("_password_correct")
        self._send_fun_encrypt(client_name, "YES")

    def _login_err(self, client_name):
        self._log.log("_login_err")
        self._send_fun_encrypt(client_name, "Jif43DF$dsg")
        self._user_dict[client_name]["sock"].close()
        del self._user_dict[client_name]
        exec('del self.user.{0}'.format(client_name))

    def _login_correct(self, client_name):
        self._log.log("_login_correct")
        self._send_fun_encrypt(client_name, "YES")

    def _blacklist(self, sock, addr):
        self._log.log_info("{0}: \033[0;36;41mBlacklist Ban:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), addr))
        self._log.log("_blacklist")
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
            self._log.log("_disconnect")
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
            self._log.log("_disconnect")
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
            self._log.log("_disconnect")
            sock.close()
            raise err

    def _send_fun_encrypt_s(self, sock, data):
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
            self._log.log("_disconnect")
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

            rsaDecrypt_data_bytes = self._encrypt.rsaDecrypt(data_bytes)
            func_args_dict = pickle.loads(rsaDecrypt_data_bytes)

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
                是否加密传输, 不加密效率较高, 服务端和客户端必须同时开启或者关闭加密

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

        if not encryption:
            # 不使用加密
            self._recv_fun_encrypt = self._recv_fun
            self._send_fun_encrypt = self._send_fun

        self.recv_info_queue = queue.Queue()

        self.user = User()

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

        self._heartbeat_server()

    def conncet(self, server_name, ip, port, password="abc123"):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
        if sys.platform == "win32":
            sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 60000, 30000))

        sock.connect((ip, port))
        self._log.log_info("{0}: \033[0;36;42mConnect:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
        self._user_dict[server_name] = {}
        self._user_dict[server_name]["can_heartbeat_flag"] = False
        self._user_dict[server_name]["sock"] = sock

        self._send_fun(server_name, self._encrypt.pubkey)
        self._user_dict[server_name]["pubkey"] = self._recv_fun(server_name)

        exec('self.user.{0} = Node("{0}", self)'.format(server_name))

        self._send_fun_encrypt(server_name, [self.client_name, self.client_password])
        self._send_fun_encrypt(server_name, password)

        connect_code = self._recv_fun_encrypt(server_name)
        if connect_code == "YES":
            self._log.log_info("{0}: \033[0;36;42mVerified successfully:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
            self._password_correct()
        else:
            self._log.log_info("{0}: \033[0;36;41mVerified failed:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
            self._password_err(server_name)
            return

        login_code = self._recv_fun_encrypt(server_name)
        if login_code == "YES":
            self._log.log_info("{0}: \033[0;36;42mLogin successfully:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
            self._login_correct()
        else:
            self._log.log_info("{0}: \033[0;36;41mLogin failed:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
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

        self._user_dict[server_name]["can_heartbeat_flag"] = True

    def _auto_reconnect_server(self):

        def re_connect(server_name, ip, port, password):

            try:
                old_delay = self._auto_reconnect_timedelay_dict[server_name]
                if old_delay > 30:
                    self._auto_reconnect_timedelay_dict[server_name] = 30
            except KeyError:
                old_delay = self._auto_reconnect_timedelay_dict[server_name] = 0

            time.sleep(old_delay)

            lock = self._auto_reconnect_lock_dict[server_name]
            lock.acquire()
            try:
                if server_name not in self._user_dict.keys():
                    self.conncet(server_name, ip, port, password)
                    self._auto_reconnect_timedelay_dict[server_name] = 0
            except ConnectionRefusedError:
                self._log.log_info("{0}: \033[0;36;41mRe Connect Failed:\033[0m {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name))
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

    def _heartbeat_server(self):

        def server():
            while True:
                time.sleep(40)
                try:
                    for server_name in self._user_dict.keys():
                        if self._user_dict[server_name]["can_heartbeat_flag"]:
                            self.send(server_name, "CMD_heartbeat_END")
                except Exception as err:
                    print("{0}: \033[0;36;41mClient 发送心跳失败!\033[0m".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    traceback.print_exc()
                    print(err)

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
                    if recv_data == "CMD_heartbeat_END":
                        continue
                    self.recv_info_queue.put([server_name, recv_data])
                except (ConnectionRefusedError, ConnectionResetError, TimeoutError) as err:
                    self._log.log_info("{0}: {1} \033[0;36;41mOffline!\033[0m {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), server_name, err))
                    try:
                        self._disconnect_user_fun()
                    except Exception as err:
                        traceback.print_exc()
                        print(err)
                    break

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def default_callback_server(self):
        def sub():
            while True:
                recv_data = self.recv_info_queue.get()
                print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "recv:", recv_data)

        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

    def _connect_end(self):
        self._log.log("_connect_end")

    def _disconnect(self, server_name):
        self._log.log("_disconnect")
        self._user_dict[server_name]["sock"].close()
        del self._user_dict[server_name]
        exec('del self.user.{0}'.format(server_name))

    def _password_err(self, server_name):
        self._log.log("_password_err")
        self._user_dict[server_name]["sock"].close()
        del self._user_dict[server_name]
        exec('del self.user.{0}'.format(server_name))

    def _password_correct(self):
        self._log.log("_password_correct")

    def _login_err(self, server_name):
        self._log.log("_login_err")
        self._user_dict[server_name]["sock"].close()
        del self._user_dict[server_name]
        exec('del self.user.{0}'.format(server_name))

    def _login_correct(self):
        self._log.log("_login_correct")

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

            rsaDecrypt_data_bytes = self._encrypt.rsaDecrypt(data_bytes)
            func_args_dict = pickle.loads(rsaDecrypt_data_bytes)

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

    # Server
    S = Server("127.0.0.1", 12345, password="abc123", log="INFO",
            # user_napw_info={
            #     "Foo" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi',
            #     "Bar" : b'$2b$15$DFdThRBMcnv/doCGNa.W2.wvhGpJevxGDjV10QouNf1QGbXw8XWHi',
            #     },
            # blacklist = ["192.168.0.10"],
            )

    S.default_callback_server()

    # Client
    C = Client("Foo", "123456", log="INFO", auto_reconnect=True)

    C.default_callback_server()

    C.conncet("Baz" ,"127.0.0.1", 12345, password="abc123")

    # send info
    S.user.Foo.send("Hello world!")
    C.user.Baz.send("Hello world!")