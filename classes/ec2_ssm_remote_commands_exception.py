class Ec2SsmRemoteCommandsException(Exception):

    def __init__(self, message):
        self.parameter = message


    def __str__(self):
        return self.parameter
