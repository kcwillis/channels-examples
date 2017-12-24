from channels import route
from .consumers import ws_connect, ws_receive, ws_disconnect, chat_join, chat_leave, chat_send, \
                        drawing_ws_connect, drawing_ws_receive, drawing_ws_disconnect, drawing_send, \
                        drawing_draw, drawing_join


# There's no path matching on these routes; we just rely on the matching
# from the top-level routing. We _could_ path match here if we wanted.
websocket_routing = [
    # Called when WebSockets connect
    route("websocket.connect", ws_connect),

    # Called when WebSockets get sent a data frame
    route("websocket.receive", ws_receive),

    # Called when WebSockets disconnect
    route("websocket.disconnect", ws_disconnect),
]

drawing_websocket_routing = [
    # Called when WebSockets connect
    route("websocket.connect", drawing_ws_connect),

    # Called when WebSockets get sent a data frame
    route("websocket.receive", drawing_ws_receive),

    # Called when WebSockets disconnect
    route("websocket.disconnect", drawing_ws_disconnect),
]

# You can have as many lists here as you like, and choose any name.
# Just refer to the individual names in the include() function.
custom_routing = [
    # Handling different chat commands (websocket.receive is decoded and put
    # onto this channel) - routed on the "command" attribute of the decoded
    # message.
    route("chat.receive", chat_join, command="^join$"),
    route("chat.receive", chat_leave, command="^leave$"),
    route("chat.receive", chat_send, command="^send$"),
    # route("chat.receive", drawing_send, command="^send$"),
    route("chat.receive", drawing_draw, command="^draw$"),
    route("chat.receive", drawing_join, command="^draw_join$")
]
