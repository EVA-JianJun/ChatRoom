import ChatRoom
room = ChatRoom.Room()

import ChatRoom
user_1 = ChatRoom.User("Foo")
user_1.default_callback()

import ChatRoom
user_2 = ChatRoom.User("Bar", encryption=False)
user_2.default_callback()

import ChatRoom
user_3 = ChatRoom.User("Too", encryption=False)
user_3.default_callback()

import ChatRoom
user_4 = ChatRoom.User("Kee")
user_4.default_callback()