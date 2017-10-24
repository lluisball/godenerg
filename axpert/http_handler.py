from json import dumps as json_dumps
from http.server import BaseHTTPRequestHandler


def create_base_remote_cmd_handler(executor, connector, cmds):

    class RemoteCommandsHandler(BaseRemoteCommandsHandler):

        def __init__(self, *args, **kwargs):
            self.connector = connector
            self.executor = executor
            self.cmds = cmds
            super(RemoteCommandsHandler, self).__init__(*args, **kwargs)

    return RemoteCommandsHandler


class BaseRemoteCommandsHandler(BaseHTTPRequestHandler):

    def do_GET(self):        
        self.send_response(200)
        self.send_header('Content-type','application/json')
        self.end_headers()
        data = ( 
            cmd.json(
                self.executor(self.connector, cmd).data, ser=False
            ) 
            for cmd_name, cmd in self.cmds
        )
        response = {}
        for item in data:
            response.update(item)

        self.wfile.write(
            json_dumps(response).encode()
        )
