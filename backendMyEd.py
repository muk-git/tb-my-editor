#!/usr/bin/python

import os
import json
import sys
import struct
import subprocess

# NOTES:
#  - print here will send back to the front end, and won't work.

global DEBUG
DEBUG=1
global DBGFD
global FILE_CONTAINING_CMD_TORUN
FILE_CONTAINING_CMD_TORUN="tb-my-ed.cmd"

def dbgwr(data):
    global DEBUG, DBGFD

    if DEBUG:
        DBGFD.write(data)
        DBGFD.flush()
    return

# Read a message from stdin and decode it. Message contains:
#   numbytes in binary + payload in ascii with quotes 
# Eg, payload xyz, then: 5000 followed by "xyz", ie, 050000002278797A22
def get_message():
    pidstr = str(os.getpid());

    # payload size is 4 bytes binary, read that. In python3, buffered read for
    # binary data, default is string.
    if sys.version_info < (3, 0):
        len_field = sys.stdin.read(4)
    else:
        len_field = sys.stdin.buffer.read(4)

    # dbgwr("len_field val: " + len_field + "\n");
     
    if not len_field:
        sys.exit(0)

    # first byte out of 4 is the length, extract it
    message_length = struct.unpack('=I', len_field)[0]

    # now read that many characters.
    dbgwr("tbvim2: pid:" + pidstr + " Will read " + str(message_length) +
          " bytes from stdin\n")
    message = sys.stdin.read(message_length)
    dbgwr("tbvim4: message was read from stdin\n")
    # dbgwr("tbvim4:" + message + "\n")

    return json.loads(message)


def read_cmd_from_file():
    fd = open(FILE_CONTAINING_CMD_TORUN, 'r')
    cmdline = fd.read()
    dbgwr("cmdline from file: :" + cmdline + ":\n")
    fd.close

    cmdline = cmdline.strip()        # remove leading/trailing spaces
    cmdline = cmdline.strip("\n")    # remove newline

    return cmdline

def invoke_vim(msg):
    tmpfn = "/tmp/tbird-vim-" + str(os.getpid())

    if os.path.exists(tmpfn):
        prev = tmpfn + ".prev"
        os.rename(tmpfn, prev)

    fd = open(tmpfn, 'w')
    if sys.version_info < (3, 0):
        fd.write(msg)
    else:
        fd.buffer.write(msg)
    fd.close()

    #cmd = "/bin/xterm -title VIMCOMPOSE -name VIMCOMPOSE -rvc -ulc -bdc -cm " \
          # " -dc -bc -rw +sb -sl 5000 -ut +cn -geometry 80x64 -e /bin/vim "
    cmd = read_cmd_from_file()
    cmd += " " + tmpfn
    dbgwr("cmd is: " + cmd + "\n")

    # in python 3, change this to subprocess.run()
    p = subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)

    dbgwr("invoke_vim done:\n")

    return tmpfn
    

# Encode a message for transmission, given its content.
def encode_message(message_content):
    encoded_content = json.dumps(message_content)
    encoded_length = struct.pack('=I', len(encoded_content))
    return {'length': encoded_length, 'content': encoded_content}

# Send an encoded message to stdout.
def send_message_v2(encoded_message):
    sys.stdout.write(encoded_message['length'])
    sys.stdout.write(encoded_message['content'])
    sys.stdout.flush()

def send_message_v3(encoded_message):
    sys.stdout.buffer.write(encoded_message['length'])
    sys.stdout.write(encoded_message['content'])
    sys.stdout.flush()

def main(args):
    global DEBUG, DBGFD

    if DEBUG:
        DBGFD = open('/tmp/tb-myed.out', 'a+')
        dbgwr("/tmp/tb-myed.out opened/created\n\n")
        sys.stderr = DBGFD;
    else:
        DBGFD = -1

    message = get_message()
    dbgwr("msg type is: " + str(type(message)) + "\n")

    # message type is unicode, so convert to ascii, otherwise it will the 
    # write to file if there any unicode non-ascii characters.
    message = message.encode('ascii', 'replace')
    tmpfn = invoke_vim(message)
    
    with open(tmpfn) as file:
        data = file.read()
        if sys.version_info < (3, 0):
            send_message_v2(encode_message(data))
        else:
            send_message_v3(encode_message(data))

    dbgwr("\n")
    if DEBUG:
        DBGFD.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
