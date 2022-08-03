# ChatRoom

**Python分布式交互框架！快速建立可靠的网络连接！**

![main][1]

## 安装

    pip install -U ChatRoom-jianjun

## 简介

通过搭建 `ChatRoom` 集群, 让集群内用户 `User` 互相进行交互, 并通过 `Room` 监控 `User` 运行状况.

![main][2]

`Room` 调度所有 `User` 的连接, 同一局域网如 `Net A` 和 `Net B` 内 `User` 只能局域网内互联, `User H` 是具有公网IP的用户结点, 则所有的 `User` 都可以与 `User H` 建立连接.

### `ChatRoom` 特性

`ChatRoom` 自动处理了网络配置中需要提供的复杂参数，`ChatRoom` 也解决了许多在网络传输中会遇到的麻烦问题.

* **高层对象**：`ChatRoom` 是通过网络来传输 `Python` 数据对象，所以只有需要使用网络传输的情况使用 `ChatRoom` 才是合适的；
* **安全高效**：传输层使用 `TCP` 协议，保证数据传输可靠，会话层使用了 `RSA` 双端非对称加密保证数据传输的安全性，密码保存使用了 `bcrypt` 算法，保证用户密码不泄露；
* **全自动化**：`ChatRoom` 的优势在于无论客户端主机是局域网机器，公网机器，还是不同内网环境的机器，都会由 `Room` 自动调度后分配集群的最高效连接方式；
* **逻辑隔离**：`ChatRoom` 让开发者专注于程序逻辑处理，而不用考虑物理机的网络配置，大多数的情况下只需几个参数就可以让集群互相连接起来；

会话层加密可以关闭，传输大数据可有效提升性能，加密的一端可以自动兼容未加密的一端.

建议Romm开启加密, 可靠内网环境不开启加密, 公网User开启加密.

### `ChatRoom` 连接方式

1. 局域网内互相连接：只要两个 `User` 处于同一局域网内，那么他们会直接局域网内连接；
2. 具有公网IP的 `User`：在不满足 `1` 的情况下，其他机器都会使用公网IP进行连接；
3. ~~中继连接：`1` 和 `2` 都不满足的情况下，相当于 `User` 被网络隔绝了，那么会通过 `Room` 进行数据转发；~~

`ChatRoom` 的优势是所有关于 `User` 的连接信息都由 `Room` 进行统一管理, 每个 `User` 只需管理自身的连接信息, 而不必存储其他可能的 `User` 的信息. 每次 `User` 的离线, 上线, 物理机的更改或增加新节点等行为都会由 `Room` 进行调度处理.

## 搭建集群

`ChatRoom` 主要组成部分 `Room` 和 `User`、`Server` 和 `Client`、生成用户密码hash信息函数 `hash_encryption`:

    from ChatRoom import Room, User
    from ChatRoom.net import Server, Client
    from ChatRoom import hash_encryption

### Room
`Room` 是 `ChatRoom` 的核心，所有的 `User` 的连接行为都是由 `Room` 来进行调度，可以把 `Room` 理解为一个小型的服务端，所有的 `User` 都会与 `Room` 连接.

当 `User` 与 `Room` 断开连接后，其他 `User` 的连接不受影响，等待 `Room` 恢复后，所有的 `User` 会与 `Room` 再次建立连接.

在开始运行集群前，需要先把 `Room` 运行起来！

    from ChatRoom import Room

    # 创建room
    room = ChatRoom.Room()

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
    """

**默认 `Room` 建立在本机，不设置密码，不对用户有任何限制.**

#### 设置用户密码

设置连接集群的用户密码，就是设定 `user_napw_info` (UNI) 的值, 设定后可与对用户身份进行验证，冒充的用户是连接不上的.

    # 生成后的UNI字典例子
    user_napw_info = {
        'Foo': b'$2b$10$6Y/A7JyMxNXKGGu.4AelJ.TjLHWqZ6YemIzBT9Gcjugy3gSHNy77e',
        'Bar': b'$2b$10$rTQtNZDzfO7484b/UZltROJ/Yy5f1WOxZIeymjv8JhSQrFoGuGS8i',
        }

    # 设置user_napw_info参数就设置了用户密码
    room = ChatRoom.Room(user_napw_info=user_napw_info)

#### 生成用户密钥HASH字典

    from ChatRoom import hash_encryption

    # 使用 hash_encryption 函数生成用户密钥HASH字典, 传入明文, 返回HASH密文
    user_napw_info = hash_encryption(
        {
            'Foo' : "123456",
            'Bar' : "abcdef",
        }
    )

    """
    >> user_napw_info
    {
        'Foo': b'$2b$10$qud3RGagUY0/DaQnGTw2uOz1X.TlpSF9sDhQFnQvAFuIfTLvk/UlC',
        'Bar': b'$2b$10$rLdCMR7BJmuIczmNHjD2weTn4Mqt7vrvPqrqdTAQamow4OzvnqPji'
    }
    """

#### APP
Room Gui客户端, 命令行输入 `room` 既可以打开本文开头所示的room客户端界面!

    room

### User

`User` 的配置会稍微复杂点，毕竟 `User` 需要告诉 `Room` 自身的一些信息，而这些信息需要开发者按需提供.

    from ChatRoom import User

    user_foo = User(
            user_name="Foo",
        )

    user_foo.default_callback()

    def foo_server_test_get_callback_func(data):
        # do something
        return ["user_foo doing test", data]
    user_foo.register_get_event_callback_func("test", foo_server_test_get_callback_func)

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
    """

需要注意的有 `public_ip`、`server_port`、`lan_id` 三个参数

* 具有公网IP的机器才需要设置 `public_ip`
* 有些机器的环境有安全组或防火墙什么的，需要放通相应的端口，所以此类机器需要指定 `server_port`
* 在同一局域网内的用户指定为相同的 `lan_id` ，好让他们互相使用局域网直接互相连接

`Room` 应该搭建在所有 `User` 都能访问的机器上，然后 `User` 根据自身的情况设置好参数，以后无论程序重启、离线、上线导致该 `User` 断开连接，其他 `User` 都会自动处理，在该 `User` 重新连接到集群中时，`Room` 会重新调度连接该 `User`.

### Server & Client

`Server` 和 `Client` 是 `ChatRoom` 所使用底层连接协议对象，属于单Server对多Client的连接模式，在一些需求简单的情况下使用 `Server` 和 `Client` 是不错的选择.
这种模式和 `Room` & `User` 的不同点是没有 `Room` 进行中间调度，但模式也相对于简化些. 具体使用方式请参考源代码.

## 主要交互方法

在 `User` 实例里有个属性为 `user` 保存了所有与本 `User` 连接的其他用户对象,

    user_foo.user.Bar
    user_bar.user.Foo

用户对象下的属性和函数是向该用户进行交互的功能, 主要的函数和属性有

    send() get() send_file() recv_file()  send_path() share status

### send()

向用户发送数据, 支持所有类型的数据

    def send(self, data):
        """
        文档:
            向其他集群节点发送数据

        参数:
            data : all type
                发送的数据,支持所有内建格式和第三方格式
        """

    # send info
    user_foo.user.Bar.send("Hello user2")
    user_bar.user.Foo.send("Hello user1")

所有的信息接受到都会存储在 `self.recv_info_queue` 队列里，默认的 `slef.default_callback` 函数默认只是简单的打印了队列里的信息.

    def default_callback_server(self):
        def sub():
            while True:
                recv_data = self.recv_info_queue.get()
                # 只打印 TODO
                print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "recv:", recv_data)

        # 使用线程循环处理数据
        sub_th = threading.Thread(target=sub)
        sub_th.setDaemon(True)
        sub_th.start()

**这里使用了线程循环处理接受到的数据，且只打印了接收到的数据，开发者需要根据实际需求覆写 `default_callback_server` 函数实现自己的功能.**

    class My_User(User):

        # 继承覆写父类函数
        def default_callback_server(self):
            def sub():
                while True:
                    recv_data = self.recv_info_queue.get()
                    # print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "recv:", recv_data)

                    # 自定义接受数据处理
                    try:
                        some_function(recv_data)
                    except Exception as err:
                        traceback.print_exc()
                        print(err)

            # 使用线程循环处理数据
            sub_th = threading.Thread(target=sub)
            sub_th.setDaemon(True)
            sub_th.start()

### get()

向用户发送请求, 需要等到该请求被用户请求并返回结果后该函数才会返回

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

    # get 请求
    user_foo.user.Bar.get("test", "Hello get")
    user_bar.user.Foo.get("test", "Hello get")

同样的需要对该请求设置相应的回调函数

    # 自定义回调函数
    def server_test_get_callback_func(data):
        # do something
        return ["user1 doing test", data]

    # 注册回调函数
    user_foo.register_get_event_callback_func("test", server_test_get_callback_func)

    # Bar用户请求Foo用户的 test 函数, 函数参数为 "Hello get"
    user_bar.user.Foo.get("test", "Hello get")

### send_file()

向用户发送一个文件, 默认不显示进度, 不进行数据压缩, 不等待传输完毕

    def send_file(self, source_file_path, remote_file_path, show=False, compress=False, uuid=None, wait=False):
        """
        文档:
            向其他集群节点发送文件

        参数:
            source_file_path : str
                本机需要发送的文件路径
            remote_file_path : str
                对方接收文件的路径
            show : bool (default False)
                是否显示发送进度
            compress : bool (default False)
                是否压缩传输, 默认不压缩, 设置为None可以自动根据文件类型判断
            wait : bool (default False)
                是否等待文件传输完成后再返回, 此模式下如果md5校验失败会尝试重新发送一次

        返回:
            file_status_object : object
                reve_user : str
                    接收的用户名称
                source_file_path : str
                    本机需要发送的文件路径
                remote_file_path : str
                    对方接收文件的路径
                md5 : str
                    文件md5
                len : int
                    文件字节长度
                statu  : str
                    文件发送状态
                    waiting : 等待发送
                    sending : 发送中
                    waitmd5 : 等待MD5校验
                    success : 发送成功
                    md5err  : 发送完毕但md5错误
                percent : float
                    文件发送百分比
        """

    user_foo.user.Bar.send_file(source_file_path, remote_file_path, show=True, compress=False, wait=True)

### recv_file()

从用户请求接收下载一个文件, 默认不显示进度, 不进行数据压缩, 不等待传输完毕

    def recv_file(self, remote_file_path, source_file_path, show=False, compress=False, wait=False):
        """
        文档:
            向其他集群节点下载文件

        参数:
            remote_file_path : str
                对方发送文件的路径
            source_file_path : str
                本机需要接收的文件路径
            show : bool (default False)
                是否显示发送进度
            compress : bool (default False)
                是否压缩传输, 默认不压缩, 设置为None可以自动根据文件类型判断
            wait : bool (default False)
                是否等待文件传输完成后再返回, 此模式下如果md5校验失败会尝试接收发送一次

        返回:
            file_status_object : object
                send_user : str
                    发送的用户名称
                source_file_path : str
                    本机需要接收的文件路径
                remote_file_path : str
                    对方发送文件的路径
                md5 : str
                    文件md5
                len : int
                    文件字节长度
                statu  : str
                    文件发送状态
                    waiting : 等待接收
                    recving : 接收中
                    waitmd5 : 等待MD5校验
                    success : 接收成功
                    md5err  : 接收完毕但md5错误
                percent : float
                    文件发送百分比
        """

    user_foo.user.Bar.recv_file(remote_file_path, source_file_path, show=True, compress=False, wait=True)

### send_path()

向用户发送并同步一个文件夹, 只对修改的文件进行同步, 对多余的文件进行删除, 无法同步空文件夹.
远程同步文件夹不能为 C 盘等系统目录, 且不能为根目录, 必须指定一个文件夹.

    def send_path(self, source_path, remote_path, show=True, compress=False):
        """
        文档:
            发送一个文件夹下所有文件, 若远程文件目录有对应文件则会跳过, 只发送改变的文件
            无法发送空文件夹

        参数:
            source_path : str
                需要发送的目录
            remote_path : str
                对方接收的目录
            show : bool (default False)
                是否显示发送进度
            compress : bool (default False)
                是否压缩传输, 默认不压缩, 设置为None可以自动根据文件类型判断
        """

    user_foo.user.Bar.send_path("./A", "./B")

### share

共享自身的变量给集群的其他用户, 在 `user` 属性下的 `myself` 代表自身, 可以直接对 `myself.share` 变量进行赋值来共享变量

    # 共享
    user_foo.user.myself.share.hello = "Hello ChatRoom!"

    # 其他用户读取
    user_bar.user.Foo.share.hello
    # Out: 'Hello ChatRoom!'

### status

所有的`User`都会向其他用户共享该变量, 该变量信息包括cpu, 内存, 硬盘占用等信息, 和当前网速, Python进程数量等信息

    user_bar.user.Foo.status
    # Out: {'user': [1, 'Administrator'], 'server_time': ['2022-08-03 10:16:38', '2022-07-21 18:24:58'], 'network': ['9.8 Kb/s', '2.0 Kb/s'], 'cpu_count': 8, 'cpu_rate': '3.5%', 'memory': ['38%', '19.97', '31.94'], 'disk': {'C:\\': {'total': 248849244160, 'used': 89227833344, 'free': 159621410816, 'percent': 35.9}}, 'process_status': ['OK', 'Python 4']}

  [1]: https://raw.githubusercontent.com/EVA-JianJun/GitPigBed/master/blog_files/img/room_app_main.png
  [2]: https://raw.githubusercontent.com/EVA-JianJun/GitPigBed/master/blog_files/img/ChatRoom_architecture.png
