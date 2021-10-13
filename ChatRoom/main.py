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

    def __init__(self, ip="", port=2428, password="Passable", log="INFO"):

        if not ip:
            ip = get_host_ip()

        self.ip = ip
        self.port = port
        self.password = password

        self._log = Log(log)

        self.server = Server(self.ip, self.port, self.password, log=log)

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
                        #  ['Alice', ['user_info', {'local_ip': '10.88.3.152', 'public_ip': '', 'port': 13004, 'password': 'Z(qC\x0b1=\nkc\ry|L\t+', 'is_public_network': False, 'group': 'D'}]]
                        user_info = recv_data[1][1]
                        self._user_info_dict[user] = user_info

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
                        if user_info_a['group'] == user_info_b['group']:
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

    def __init__(self, user_name, room_ip="", room_port=2428, room_password="Passable", public_ip="", server_port=0, user_password="", group="Default", log="INFO", password_digits=16):

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
        self.group = group

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
        self.client.conncet("Room" , self.room_ip, self.room_port, self.room_password)

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
                    "group" : self.group,
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
