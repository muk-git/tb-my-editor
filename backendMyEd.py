#!/usr/bin/python

import os
import json
import sys
import struct
import subprocess
import time

# NOTES:
#  - print here will send back to the front end, and won't work.

global DEBUG
DEBUG=1
global DBGFD
global FILE_CONTAINING_CMD_TORUN
FILE_CONTAINING_CMD_TORUN="tb-my-ed.cmd"
global mysrc

def dbgwr(data):
    global DEBUG, DBGFD

    if DEBUG:
        DBGFD.write(data)
        DBGFD.write("\n")
        DBGFD.flush()
    return

# Encode a message for transmission, given its content.
def encode_message_v2(message_content):
    encoded_content = json.dumps(message_content)
    encoded_length = struct.pack('=I', len(encoded_content))
    return {'length': encoded_length, 'content': encoded_content}

# Send an encoded message to stdout.
def send_reply_v2(msg_str):
    encoded_msg = encode_message_v2(msg_str)
    sys.stdout.write(encoded_msg['length'])
    sys.stdout.write(encoded_msg['content'])
    sys.stdout.flush()

def encode_message_v3(message_content):
    encoded_content = json.dumps(message_content).encode("utf-8")
    encoded_length = struct.pack('=I', len(encoded_content))
    #  use struct.pack("10s", bytes), to pack a string of the length of 
    #  10 characters
    return {
        'length': encoded_length, 
        'content': struct.pack(str(len(encoded_content))+"s",encoded_content)
           }

def send_reply_v3(msg_str):
    encoded_msg = encode_message_v3(msg_str)
    sys.stdout.buffer.write(encoded_msg['length'])
    sys.stdout.buffer.write(encoded_msg['content'])
    sys.stdout.buffer.flush()

def send_reply(msg_str):
    if sys.version_info < (3, 0):
        send_reply_v2(msg_str)
    else:
        send_reply_v3(msg_str)

# Read a message from stdin and decode it. Message contains:
#   numbytes in binary + payload in ascii with quotes 
# Eg, payload xyz, then: 5000 followed by "xyz", ie, 050000002278797A22
#
# Caveats:
#   o a newline is considered one byte by JS, but when we receives it's two "\n"
#     hence can't use msg size for communication protocol
#
def get_message():
    global mysrc
    fullmsg = '""'     # create empty string with double quotes

    # python does not have do while loop.
    while True:
        # payload size is 4 bytes binary, read that. 
        len_field = mysrc.read(4)
        # dbgwr("len_field val: " + str(len_field))
     
        if not len_field:
            dbgwr("invalid len_field val: " + str(len_field))
            sys.exit(0)

        # first byte out of 4 is the length, extract it for debug 
        msg_len = struct.unpack('=I', len_field)[0]
        dbgwr("pid:" + str(os.getpid()) + " Will read " + str(msg_len) +
              " bytes from stdin")

        # don't use msg_len for anything: sender single newline for example
        # gets converted to two chars "\n". Thus if sender sends 5 :abcd\n:
        # we get 8 including two double quotes: " + abcd + \ + n "
        msg = mysrc.read(msg_len)
        if sys.version_info >= (3, 0):
            msg = msg.decode("utf-8")   # string from binary data

        # dbgwr("got msg: " + msg + " len: " + str(len(msg)))
        # dbgwr("read: " + str(msg_len) + " bytes. msg.size:" + str(len(msg)))

        if msg[1:-1] == "tbMyEd-done-done-done":
            break
        else:
            # remove trailing double quote and leading double quote
            fullmsg = fullmsg[:-1] + msg[1:]
            send_reply("tbMyEd-ack")
            # time.sleep(1)

    # json.loads(str): take a json string and convert to python dictionary
    return json.loads(fullmsg or 'null')


def read_cmd_from_file():
    fd = open(FILE_CONTAINING_CMD_TORUN, 'r')
    cmdline = fd.read()
    # dbgwr("cmdline from file: :" + cmdline + ":")
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
    dbgwr("cmd is: " + cmd)

    # in python 3, change this to subprocess.run()
    p = subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)

    dbgwr("invoke_vim done....")

    return tmpfn
    

def main(args):
    global DEBUG, DBGFD, mysrc

    if DEBUG:
        DBGFD = open('/tmp/tb-myed.out', 'a+')
        dbgwr("===========================================================")
        dbgwr("/tmp/tb-myed.out opened/created\n")
        sys.stderr = DBGFD
    else:
        DBGFD = -1

    if sys.version_info < (3, 0):
        mysrc = sys.stdin
    else:
        mysrc = sys.stdin.buffer

    message = get_message()    # returns type string

    # message type is unicode, so convert to ascii, otherwise it will fail the 
    # write to file if there any unicode non-ascii characters.
    message = message.encode('ascii', 'replace')
    tmpfn = invoke_vim(message)
    
    with open(tmpfn) as file:
        data = file.read()
        send_reply(data)

    dbgwr("\n")
    if DEBUG:
        DBGFD.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
