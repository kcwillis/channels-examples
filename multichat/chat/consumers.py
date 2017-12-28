import json
from channels import Channel
from channels.auth import channel_session_user_from_http, channel_session_user

from .settings import MSG_TYPE_LEAVE, MSG_TYPE_ENTER, NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS
from .models import Room, DrawingBoard
from .utils import get_room_or_error, catch_client_error, get_drawingboard_or_error
from .exceptions import ClientError


### WebSocket handling ###


# This decorator copies the user from the HTTP session (only available in
# websocket.connect or http.request messages) to the channel session (available
# in all consumers with the same reply_channel, so all three here)
@channel_session_user_from_http
def ws_connect(message):
    print('chat/consumers.py/ws_connect()')
    message.reply_channel.send({'accept': True})
    # Initialise their session
    message.channel_session['rooms'] = []


# Unpacks the JSON in the received WebSocket frame and puts it onto a channel
# of its own with a few attributes extra so we can route it
# This doesn't need @channel_session_user as the next consumer will have that,
# and we preserve message.reply_channel (which that's based on)
def ws_receive(message):
    print('chat/consumers.py/ws_receive()')
    # All WebSocket frames have either a text or binary payload; we decode the
    # text part here assuming it's JSON.
    # You could easily build up a basic framework that did this encoding/decoding
    # for you as well as handling common errors.
    payload = json.loads(message['text'])
    payload['reply_channel'] = message.content['reply_channel']
    Channel("chat.receive").send(payload)
    print('payload text:')
    print(payload)
    # print('payload reply channel:' + payload['reply_channel'])


@channel_session_user
def ws_disconnect(message):
    print('chat/consumers.py/ws_disconnect()')
    # Unsubscribe from any connected rooms
    for room_id in message.channel_session.get("rooms", set()):
        try:
            room = Room.objects.get(pk=room_id)
            # Removes us from the room's send group. If this doesn't get run,
            # we'll get removed once our first reply message expires.
            room.websocket_group.discard(message.reply_channel)
        except Room.DoesNotExist:
            pass


@channel_session_user_from_http
def drawing_ws_connect(message):
    print('chat/consumers.py/drawing_ws_connect()')
    message.reply_channel.send({'accept': True})
    # Initialise their session
    message.channel_session['drawingboards'] = []


def drawing_ws_receive(message):
    print('chat/consumers.py/drawing_ws_receive()')
    print('message: ' + str(message))
    print('message.context["reply_channel"]' + str(message.content['reply_channel']))
    print('message["text"]: ' + message['text'])
    payload = json.loads(message['text'])
    payload['reply_channel'] = message.content['reply_channel']
    Channel("chat.receive").send(payload)
    print('payload sent')

@channel_session_user
def drawing_ws_disconnect(message):
    print('chat/consumers.py/drawing_ws_disconnect()')
    pass


### Chat channel handling ###


# Channel_session_user loads the user out from the channel session and presents
# it as message.user. There's also a http_session_user if you want to do this on
# a low-level HTTP handler, or just channel_session if all you want is the
# message.channel_session object without the auth fetching overhead.
@channel_session_user
@catch_client_error
def chat_join(message):
    print('chat/consumers.py/chat_join()')
    # Find the room they requested (by ID) and add ourselves to the send group
    # Note that, because of channel_session_user, we have a message.user
    # object that works just like request.user would. Security!

    room = get_room_or_error(message["room"], message.user)

    # Send a "enter message" to the room if available
    if NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
        room.send_message(None, message.user, MSG_TYPE_ENTER)

    # OK, add them in. The websocket_group is what we'll send messages
    # to so that everyone in the chat room gets them.
    room.websocket_group.add(message.reply_channel)
    message.channel_session['rooms'] = list(set(message.channel_session['rooms']).union([room.id]))
    # Send a message back that will prompt them to open the room
    # Done server-side so that we could, for example, make people
    # join rooms automatically.
    message.reply_channel.send({
        "text": json.dumps({
            "join": str(room.id),
            "title": room.title,
        }),
    })


@channel_session_user
@catch_client_error
def chat_leave(message):
    print('chat/consumers.py/chat_leave()')
    # Reverse of join - remove them from everything.
    room = get_room_or_error(message["room"], message.user)

    # Send a "leave message" to the room if available
    if NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
        room.send_message(None, message.user, MSG_TYPE_LEAVE)

    room.websocket_group.discard(message.reply_channel)
    message.channel_session['rooms'] = list(set(message.channel_session['rooms']).difference([room.id]))
    # Send a message back that will prompt them to close the room
    message.reply_channel.send({
        "text": json.dumps({
            "leave": str(room.id),
        }),
    })


@channel_session_user
@catch_client_error
def chat_send(message):
    print('chat/consumers.py/chat_send()')
    # Check that the user in the room
    if int(message['room']) not in message.channel_session['rooms']:
        raise ClientError("ROOM_ACCESS_DENIED")
    # Find the room they're sending to, check perms
    room = get_room_or_error(message["room"], message.user)
    # Send the message along
    room.send_message(message["message"], message.user)


# Channel_session_user loads the user out from the channel session and presents
# it as message.user. There's also a http_session_user if you want to do this on
# a low-level HTTP handler, or just channel_session if all you want is the
# message.channel_session object without the auth fetching overhead.
@channel_session_user
@catch_client_error
def drawing_join(message):
    print('chat/consumers.py/drawing_join()')
    # Find the room they requested (by ID) and add ourselves to the send group
    # Note that, because of channel_session_user, we have a message.user
    # object that works just like request.user would. Security!

    drawingboard = get_drawingboard_or_error(message['drawingboard'], message.user)

    # Send a "enter message" to the room if available
    if NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
        drawingboard.send_message(None, message.user, MSG_TYPE_ENTER)

    # OK, add them in. The websocket_group is what we'll send messages
    # to so that everyone in the chat room gets them.
    drawingboard.websocket_group.add(message.reply_channel)
    message.channel_session['rooms'] = list(set(message.channel_session['drawingboards']).union([drawingboard.id]))
    # Send a message back that will prompt them to open the room
    # Done server-side so that we could, for example, make people
    # join rooms automatically.
    message.reply_channel.send({
        "text": json.dumps({
            "join": str(drawingboard.id),
            "title": drawingboard.title,
        }),
    })


@channel_session_user
@catch_client_error
def drawing_leave(message):
    print('chat/consumers.py/drawing_leave()')
    # Reverse of join - remove them from everything.
    drawingboard = get_drawingboard_or_error(message['drawingboard'], message.user)

    # Send a "leave message" to the room if available
    if NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
        drawingboard.send_message(None, message.user, MSG_TYPE_LEAVE)

    drawingboard.websocket_group.add(message.reply_channel)
    message.channel_session['rooms'] = list(set(message.channel_session['drawingboards']).difference([drawingboard.id]))
    # Send a message back that will prompt them to close the room
    message.reply_channel.send({
        "text": json.dumps({
            "leave": str(drawingboard.id),
        }),
    })

@channel_session_user
@catch_client_error
def drawing_send(message):
    print('chat/consumers.py/drawing_send()')
    pass


@channel_session_user
@catch_client_error
def drawing_draw(message):
    print('chat/consumers.py/drawing_draw()')
    # drawingboard = get_drawingboard_or_error(message["drawingboard"], message.user)
    drawingboard = get_drawingboard_or_error(message['drawingboard'], message.user)

    draw_message = {'draw':str(drawingboard.id),
                    'prev_x':message['prev_x'],
                    'prev_y':message['prev_y'],
                    'curr_x':message['curr_x'],
                    'curr_y':message['curr_y']}

    # print(json.dumps(draw_message))
    drawingboard.send_message(json.dumps(draw_message), message.user)

    # print('message.keys(): ')
    # for key in message.keys():
    #     print(key)
