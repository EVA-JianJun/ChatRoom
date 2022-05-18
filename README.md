# ChatRoom

**Python的聊天室！让你非常简易的建立可靠的网络连接！**

## 安装

    pip install ChatRoom-jianjun

## 简介

在聊天室（`Room`）内的用户（`User`  Python对象）可以互相发送消息（`Python` 数据）

## 使用

    import ChatRoom

    # 创建聊天室
    room = ChatRoom.Room()

    # 创建两个用户
    user_1 = ChatRoom.User("Foo")
    user_1.default_callback()
    user_2 = ChatRoom.User("Bar")
    user_2.default_callback()

    # 需要等待Room调度连接后, 才可以互相发送消息
    user_1.user.Bar.send("Hello!")
    user_2.user.Foo.send("Hello!")

    # 互相收到消息
    >> 2021-10-15 10:15:04 Bar recv: ['Foo', 'Hello!']
    >> 2021-10-15 10:15:04 Foo recv: ['Bar', 'Hello!']

`ChatRoom` 自动处理了很多网络配置中需要提供的复杂参数，`ChatRoom` 也解决了许多在网络传输中会遇到的麻烦问题.

* **高层对象**：`ChatRoom` 是通过网络来传输 `Python` 数据对象，所以只有需要使用网络传输的情况使用 `ChatRoom` 才是合适的；
* **安全高效**：传输层使用 `TCP` 协议，保证数据传输可靠，会话层使用了双端非对称加密保证数据传输的安全性，密码保存使用了 `bcrypt` 算法，保证用户密码不泄露；
* **全自动化**：`ChatRoom` 的优势在于无论客户端主机是局域网机器，公网机器，还是不同内网环境的机器，都会由 `Room` 自动调度后分配集群的最高效连接方式；
* **逻辑隔离**：`ChatRoom` 让用户专注于程序逻辑处理，而不用考虑物理机的网络配置，大多数的情况下只需几个参数就可以让集群互相连接起来；

会话层加密可以关闭，可略微提升传输性能，但必须双端同时开启或者关闭加密.

**`ChatRoom` 包含 `Room` 和 `User` 类、底层的 `Server` 和 `Client` 类、一个生成用户HASH密码的函数 `hash_encryption`**

    import ChatRoom

    ChatRoom.Room
    ChatRoom.User

    ChatRoom.Server
    ChatRoom.Client

    ChatRoom.hash_encryption

## `ChatRoom` 的连接方式

1. 局域网内互相连接：只要两个 `User` 处于同一局域网内，那么他们会直接局域网内连接；
2. 具有公网IP的 `User`：在不满足 `1` 的情况下，其他机器都会使用公网IP进行连接；
3. 中继连接：`1` 和 `2` 都不满足的情况下，相当于 `User` 被网络隔绝了，那么会通过 `Room` 进行数据转发；

## Room
`Room` 是 `ChatRoom` 的核心，所有的 `User` 的行为都是由 `Room` 来进行调度，可以把 `Room` 理解为一个小型的服务端，所有的 `User` 都会与 `Room` 连接.

当 `User` 与 `Room` 断开连接后，除了中继连接会断开，其他的连接方式不受影响，等待 `Room` 恢复后，所有的 `User` 会与 `Room` 再次建立连接.

在开始运行集群前，需要先把 `Room` 运行起来！

    import ChatRoom

    # 创建聊天室
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
            是否加密传输, 不加密效率较高, 服务端和客户端必须同时开启或者关闭加密

    例子:
        # 启动一个聊天室
        import ChatRoom
        room = ChatRoom.Room()

        # 其他功能请参考user_napw_info和blacklist的作用
    """

**默认 `Room` 建立在本机，不设置密码，不对用户有任何限制.**

### 设置用户密码

这里说下怎么设置连接集群的用户密码，其实就是对用户身份进行验证，冒充的用户是连接不上的.

不用担心密码被暴力破解，一是有拉黑逻辑，二是 `bcrypt` 算法对暴力破解非常不友好，暴力破解是不可能的！

    import ChatRoom

    # 用户密钥HASH字典
    user_napw_info = {
        'Foo': b'$2b$10$6Y/A7JyMxNXKGGu.4AelJ.TjLHWqZ6YemIzBT9Gcjugy3gSHNy77e',
        'Bar': b'$2b$10$rTQtNZDzfO7484b/UZltROJ/Yy5f1WOxZIeymjv8JhSQrFoGuGS8i',
        }

    # 设置user_napw_info参数就设置了用户密码
    room = ChatRoom.Room(user_napw_info=user_napw_info)

### 生成用户密钥HASH字典

    # 使用 hash_encryption 函数生成用户密钥HASH字典, 传入明文, 返回HASH密文
    user_napw_info = hash_encryption(
        {
            'Foo': "123456",
            'Bar': "123456",
        }
    )

    >> user_napw_info
    {
        'Foo': b'$2b$10$6Y/A7JyMxNXKGGu.4AelJ.TjLHWqZ6YemIzBT9Gcjugy3gSHNy77e',
        'Bar': b'$2b$10$rTQtNZDzfO7484b/UZltROJ/Yy5f1WOxZIeymjv8JhSQrFoGuGS8i',
    }

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

## User

`User` 的配置会稍微复杂点，毕竟 `User` 需要告诉 `Room` 自身的一些信息，而这些信息需要用户按需提供.

    import ChatRoom

    # 创建一个聊天室用户
    user = ChatRoom.User(
            # 用户名和用户密码
            user_name="Foo",
            user_password="123456",

            # 需要连接的聊天室信息
            # ip
            room_ip="192.168.0.2",
            # 端口
            room_port="2428",
            # 密码
            room_password="123456",

            # 本机的一些信息
            # 公网ip, 默认为空, 设置后标识本机具有公网地址
            public_ip="",
            # 对外提供服务的端口, 默认随机端口号(0)
            server_port=0,
            # 局域网标识, 默认"Default", 相同的局域网内用户需要设置为相同lan_id, 值为字符串, 自己定义
            lan_id="Default",

            # 其他无关参数
            # 日志等级
            log="INFO",
            # 密码位数
            password_digits=16,
            # 是否加密
            encryption = True,

        )

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
            是否加密传输, 不加密效率较高, 服务端和客户端必须同时开启或者关闭加密

    例子:
        import ChatRoom

        # 创建一个聊天室用户
        user = ChatRoom.User(
                user_name="Foo",
            )

        # 运行默认的回调函数(所有接受到的信息都在self.recv_info_queue队列里,需要用户手动实现回调函数并使用)
        # 默认的回调函数只打印信息
        user.default_callback()

        # 设置请求回调函数
        def server_test_get_callback_func(data):
            # do something
            return ["user doing test", data]

        user.register_get_event_callback_func("test", server_test_get_callback_func)
    """

需要注意的有 `public_ip`、`server_port`、`lan_id` 三个参数

* 具有公网IP的机器才需要设置 `public_ip`
* 有些机器的环境有安全组或防火墙什么的，需要放通相应的端口，所以此类机器需要指定 `server_port`
* 在同一局域网内的用户指定为相同的 `lan_id` ，好让他们互相使用局域网直接互相连接

`Room` 应该搭建在所有 `User` 都能访问的机器上，然后 `User` 根据自身的情况设置好参数，以后无论程序重启、离线、上线导致该 `User` 断开连接，其他 `User` 都会自动处理连接，在该 `User` 重新连接到集群中时，`Room` 会重新调度连接该 `User`.

## 数据接收模式
### send 数据流

    # send info
    user1.user.Bar.send("Hello user2")
    user2.user.Foo.send("Hello user1")

使用send发送的数据无论`Room` 还是 `User`，所有的信息接受到都会存储在 `self.recv_info_queue` 队列里，上面的 `slef.default_callback` 函数默认只是简单的打印了队列里的信息.

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

**这里使用了线程循环处理接受到的数据，且只打印了接收到的数据，用户需要根据实际情况覆写或者重新 `default_callback_server` 函数实现自己的功能.**

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

### get 请求数据

    import ChatRoom

    # User1
    user1 = ChatRoom.User(
            user_name="Foo",
        )

    user1.default_callback()

    def server_test_get_callback_func(data):
        # do something
        return ["user1 doing test", data]

    user1.register_get_event_callback_func("test", server_test_get_callback_func)

    # User2
    user2 = ChatRoom.User(
            user_name="Bar",
        )

    user2.default_callback()

    def server_test_get_callback_func(data):
        # do something
        return ["user2 doing test", data]

    user2.register_get_event_callback_func("test", server_test_get_callback_func)

    # get info
    print(user1.user.Bar.get("test", "Hello get"))
    print(user2.user.Foo.get("test", "Hello get"))

这种模式相当于查询，就是请求注册的 `test` 函数，等待对方返回数据后这个 `get` 函数会放回相应的结果
回调函数需要自己实现，然后使用 `register_get_event_callback_func` 函数注册

## Server & Client

    ChatRoom.Server
    ChatRoom.Client

`Server` 和 `Client` 是 `ChatRoom` 所使用底层连接协议对象，属于单Server对多Client的连接模式，在一些需求简单的情况下使用 `Server` 和 `Client` 是不错的选择.
这种模式和 `Room` & `User` 的不同点是没有 `Room` 进行中间调度，但模式也相对于简化些.

    from ChatRoom.net import Server, Client

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

    def server_test_get_callback_func(data):
        # do something
        return ["server test", data]

    def client_test_get_callback_func(data):
        # do something
        return ["client test", data]

    # register callback func
    S.register_get_event_callback_func("test", server_test_get_callback_func)
    C.register_get_event_callback_func("test", client_test_get_callback_func)

    # get info
    print(S.user.Foo.get("test", "Hello world!"))
    print(C.user.Baz.get("test", "Hello world!"))

