import socket
import os
import threading
import base64 #for text encoding and decoding
import time

def read_settings():
    # read the setting.txt
    info = {}
    current_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(current_dir)
    setting_path = os.path.join(parent_dir, "peer_settings.txt")
    with open(setting_path, "r") as file:
        for i in file:
            peer_id, ip_addr, server_port = i.split()
            info[peer_id] = (ip_addr, int(server_port))
    return info


# for FILELIST
def filelist(id, info):
    try:
        serverName, serverPort = info[id] # specifying IP address and port number of server process
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))
        print(f"Client ({id}): #FILELIST")
        message = "#FILELIST"
        clientSocket.send(message.encode())
        response = clientSocket.recv(1024).decode()
        print(response)
        clientSocket.close()
    except:
        print(f"TCP connection to server {id} failed")


# for FILELIST threads
def filelist_threads(peer_ids, info):
    threads = []
    for i in peer_ids:
        thread = threading.Thread(target=filelist, args=(i, info))
        threads.append(thread)
        thread.start() # start the thread
    for i in threads:
        i.join() # wait for finish



# for UPLOAD
def start_send(serverName, serverPort, filename, contents, idx):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))

    contents = base64.b64encode(contents.encode()).decode() # encode the contents, do not let the contents split by its empty spaces!!!
    msg = f"#UPLOAD {filename} chunk {idx} {contents}"
    clientSocket.send(msg.encode())

    response = clientSocket.recv(1024).decode()
    return response

# for UPLOAD
def upload(id, info, filename, filesize, chunks):
    try:
        serverName, serverPort = info[id] # specifying IP address and port number of server process
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))
        msg = f"#UPLOAD {filename} bytes {filesize}"
        print(f"Client ({id}): #UPLOAD {filename} bytes {filesize}")
        clientSocket.send(msg.encode())
        response = clientSocket.recv(1024).decode()

        flag = False
        if response and response.startswith("330"):
            print(f"Server ({id}): "+response)
            flag = True
        else:
            print(f"Server ({id}): 250 Already serving file {filename}")

        if flag:
            for i in chunks:
                print(f"Client ({id}): #UPLOAD {filename} chunk {i}")
                response = start_send(serverName, serverPort, filename, chunks[i], i)
                if response == f"200 File {filename} chunk {i} received":
                    print(f"Server ({id}): "+response)
            print(f"File {filename} upload success")
        else:
            print(f"File {filename} upload failed")
    except:
        print(f"TCP connection to server {id} failed")


# for UPLOAD threads
def upload_threads(fileName, peers, info):
    filepath = os.path.join("served_files", fileName)
    # check first
    if not os.path.exists(filepath):
        print(f"Peer {os.path.basename(os.getcwd())} does not serve file {fileName}")
        return
    print(f"Uploading file {fileName}")

    chunks = {}
    file_size = os.path.getsize(filepath)
    if file_size % 100 == 0:
        num_of_chunks = file_size // 100
    else:
        num_of_chunks = file_size // 100 + 1

    with open(filepath, "r", encoding="utf-8") as f: # read the file in bytes
        for i in range(num_of_chunks):
            chunk = f.read(100)
            chunks[i] = chunk

    # use the multiple threads
    threads = []
    for id in peers:
        thread = threading.Thread(target=upload, args=(id, info, fileName, file_size, chunks))
        threads.append(thread)
        thread.start() # start each thread
    for i in threads:
        i.join() # wait for finish



# for DOWNLOAD
def download(serverName, serverPort, filename, idx, id, file_content):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))
    msg = f"#DOWNLOAD {filename} chunk {idx}"
    clientSocket.send(msg.encode())
    response = clientSocket.recv(1024).decode()
    if response.startswith("200"):
        contents = response.split(" ", 5)
        print(f"Server ({id}): 200 File {filename} chunk {idx}")
        file_content[idx] = contents[5]


# for DOWNLOAD threads
def download_threads(fileName, peers, info, filepath):
    peer_set = []
    size = 0
    for id in peers:
        # check whether the file is served by the peer servers
        try:
            serverName, serverPort = info[id]
            print(f"Client ({id}): #DOWNLOAD {fileName}")
            clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientSocket.connect((serverName, serverPort))
            msg = f"#DOWNLOAD {fileName}"
            clientSocket.send(msg.encode())
            response = clientSocket.recv(1024).decode()
            if response and response.startswith("330"):
                print(f"Server ({id}): {response}")
                size = int(response.split()[7])# important to get the file size here!
                peer_set.append((serverName, serverPort, id))
            else:
                print(f"Server ({id}): {response}")
        except:
            print(f"TCP connection to server {id} failed")
    
    if peer_set == []:
        # if no peer servers have the file
        print(f"File {fileName} download failed, peers {" ".join(peers)} are not serving the file")
        return
    
    # downloading time !
    if size % 100 == 0:
        times = size // 100
    else:
        times = size // 100 + 1
    file_content = [""] * times
    threads = []
    idx = 0
    while idx < times:
        peer_index = idx % len(peer_set)
        serverName, serverPort, id = peer_set[peer_index]
        thread = threading.Thread(target=download, args=(serverName, serverPort, fileName, idx, id, file_content))
        threads.append(thread)
        thread.start()
        idx += 1
    for i in threads:
        i.join()
    
    # write the file
    check_count = 0
    with open(filepath, "w", encoding="utf-8") as f:
        for i in file_content: # sort first!
            f.write(i)
            check_count += 1

    # check whether all file contents are download, if no then remove the file
    if check_count != times:
        print(f"File {fileName} download failed")
        os.remove(filepath)

    if os.path.exists(filepath):
        print(f"File {fileName} download success")
    else:
        print(f"File {fileName} download failed")



def main():
    info = read_settings()
    while True:
        command = input("Input your command: ").strip()
        if command.startswith("#FILELIST"):
            peer_ids = command.split()
            filelist_threads(peer_ids[1:], info)
        elif command.startswith("#UPLOAD"):
            temp = command.split()
            fileName = temp[1]
            peers = temp[2:]
            upload_threads(fileName, peers, info)
        elif command.startswith("#DOWNLOAD"):
            temp = command.split()
            fileName = temp[1]
            peers = temp[2:]
            filepath = os.path.join("served_files", fileName)
            if os.path.exists(filepath):
                print(f"File {fileName} already exists")
            else:
                print(f"Downloading file {fileName}")
                download_threads(fileName, peers, info, filepath)


if __name__ == "__main__":
    main()