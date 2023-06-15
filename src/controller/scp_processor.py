from scp import SCPClient


class RemoteFile:
    def __init__(self, transport, local_name, remote_name):
        self.client = SCPClient(transport)
        self.local_name = local_name
        self.remote_name = remote_name

    def upload(self):
        # check path?
        return self.client.put(self.local_name, self.remote_name)

    def download(self, recursive=False):
        # check existance?
        return self.client.get(self.remote_name, self.local_name, recursive=recursive)
