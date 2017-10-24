
def create_base_remote_cmd_handler(executor, connector, cmd):

    class RemoteCommandsHandler(BaseRemoteCommandsHandler):

        def __init__(self, *args, **kwargs):
            self.connector = connector
            super(RemoteCommandsHandler, self).__init__(*args, **kwargs)

        return RemoteCommandsHandler


class BaseRemoteCommandsHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.connector
        self.wfile.write(b"<html><body><h0>hi!</h1></body></html>")


