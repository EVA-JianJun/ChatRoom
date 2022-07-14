#!/use/bin/dev python
# -*- coding: utf-8 -*-
import time
import psutil
import datetime
import threading
import traceback

class MessyServerHardware():
    """ 获取系统信息 """
    def __init__(self):
        """ 初始化 """
        # 启动网络监控服务
        self._network_server()

        self.cpu_rate = '0%'

    """ 系统函数 """
    def _network_server(self):
        """ 监控网络服务 """
        # 先生成一次网络
        net = psutil.net_io_counters()
        # 网卡接收流量(bytes)
        self._old_bytes_sent = net.bytes_sent
        # 网卡发送流量(bytes)
        self._old_bytes_recv = net.bytes_recv
        # 初始化为0
        self.sent_kbps_s = self.recv_kbps_s = 0

        def refresh_network():
            """ 刷新网络信息 """
            refresh_interval = 20
            while True:
                try:
                    # 每refresh_interval秒刷新一次
                    self.cpu_rate = str(psutil.cpu_percent()) + '%'
                    time.sleep(refresh_interval)
                    net = psutil.net_io_counters()
                    # new网卡接收流量(bytes)
                    self._new_bytes_sent = net.bytes_sent
                    # new网卡发送流量(bytes)
                    self._new_bytes_recv = net.bytes_recv

                    # 获取每秒速率
                    self.sent_kbps_s = (self._new_bytes_sent - self._old_bytes_sent) / refresh_interval
                    self.recv_kbps_s = (self._new_bytes_recv - self._old_bytes_recv) / refresh_interval

                    # 赋值旧数据
                    self._old_bytes_sent = self._new_bytes_sent
                    self._old_bytes_recv = self._new_bytes_recv
                except Exception as err:
                    print("\033[0;36;41mMessyServerHardware: 刷新网络信息失败!退出!\033[0m")
                    traceback.print_exc()
                    print(err)
                    return

        """ 使用线程启动 """
        refresh_th = threading.Thread(target=refresh_network)
        refresh_th.setDaemon(True)
        refresh_th.start()

    """ 用户函数 """
    def get_server_time(self):
        """ 获取系统时间 """
        # ['2019-12-04 10:40:50', '2019-11-25 08:14:25']
        # 当前时间
        self.server_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 服务器启动时间
        self.server_start_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

        return [self.server_time, self.server_start_time]

    def get_network(self):
        """ 获取网络使用速率 """
        # ['5.48 Kb/s', '0.90 Kb/s']
        if self.recv_kbps_s < 1048576:
            # 如果小于1M
            rcvd = '{0:.1f} Kb/s'.format(self.recv_kbps_s / 1024)
        else:
            rcvd = '{0:.1f} Mb/s'.format(self.recv_kbps_s / 1024 / 1024)

        if self.sent_kbps_s < 1048576:
            sent = '{0:.1f} Kb/s'.format(self.sent_kbps_s / 1024)
        else:
            sent = '{0:.1f} Mb/s'.format(self.sent_kbps_s / 1024 / 1024)

        return [rcvd, sent]

    def get_cpu_count(self):
        """ 获取cpu物理核心个数 """
        # 4
        # 查看cpu物理核心个数(不包含虚拟核心)
        self.cpu_count = psutil.cpu_count(logical=False)

        return self.cpu_count

    def get_cpu_rate(self):
        """ 获取CPU的使用率 """
        # '8.5%'
        # 间隔设置为0.1秒
        # self.cpu_rate = str(psutil.cpu_percent(interval=.1, percpu=False)) + '%'

        return self.cpu_rate

    def get_memory(self):
        """ 获取内存使用情况 """
        # ['46%', '8.55', '15.94']
        # 剩余物理内存(DDR)(在Linux下不准确)
        self.free = str(round(psutil.virtual_memory().free / (1024.0 * 1024.0 * 1024.0), 2))
        # 总物理内存(DDR)
        self.total = str(round(psutil.virtual_memory().total / (1024.0 * 1024.0 * 1024.0), 2))
        # 物理内存使用率(DDR)
        # self.memory = int(psutil.virtual_memory().total - psutil.virtual_memory().free) / float(psutil.virtual_memory().total)
        # self.memory = str(int(self.memory * 100)) + '%'
        self.memory = "{0:0.0f}%".format(psutil.virtual_memory().percent)

        result_list = [self.memory, self.free, self.total]

        return result_list

    def get_user(self):
        """ 获取用户信息 """
        # [1, 'Administrator']
        # 登录用户数量
        self.users_count = len(psutil.users())
        # 用户名列表
        self.users_list = ",".join([u.name for u in psutil.users()])
        result_list = [self.users_count, self.users_list]

        return result_list

    def get_disk(self):
        """ 获取磁盘信息 """
        """
        # Windows
          {'C:\\': {'total': 107375226880,
          'used': 68646764544,
          'free': 38728462336,
          'percent': 63.9},
         'D:\\': {'total': 72668409856,
          'used': 32414183424,
          'free': 40254226432,
          'percent': 44.6},
         'E:\\': {'total': 536871956480,
          'used': 67328794624,
          'free': 469543161856,
          'percent': 12.5},
         'F:\\': {'total': 1073742868480,
          'used': 151236952064,
          'free': 922505916416,
          'percent': 14.1},
         'G:\\': {'total': 389779812352,
          'used': 133431582720,
          'free': 256348229632,
          'percent': 34.2}}
        # 其他系统的这个信息比较迷,我在黑苹果和VM Linux虚拟机下得到的都是不对的数据
        # Windows下稳定,其他系统请自己进行测试
        """
        disk_info_dict = dict()
        for disk in psutil.disk_partitions():
            try:
                device = disk.device
                disk_info = psutil.disk_usage(device)
                disk_info_dict[device] = {
                    'total': disk_info.total,
                    'used': disk_info.used,
                    'free': disk_info.free,
                    'percent': disk_info.percent,
                }
            except PermissionError:
                # D盘是光盘驱动
                pass

        return disk_info_dict

    def get_process_status(self):
        """ 获取进程状态信息 """
        # 暂时只支持返回Python进程数量
        try:
            python_num = 0
            for pid in psutil.pids():
                p = psutil.Process(pid)
                if p.name() == 'python.exe':
                    python_num += 1
            return ['OK', 'Python {0}'.format(python_num)]
        except Exception:
            return ['OK', 'Get Err']

    def get_all(self):
        """ 获取所有系统信息 """
        all_info = {
            'user'           : self.get_user(),
            'server_time'    : self.get_server_time(),
            'network'        : self.get_network(),
            'cpu_count'      : self.get_cpu_count(),
            'cpu_rate'       : self.get_cpu_rate(),
            'memory'         : self.get_memory(),
            'disk'           : self.get_disk(),
            'process_status' : self.get_process_status(),
        }

        return all_info
