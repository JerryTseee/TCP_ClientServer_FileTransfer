import socket
import os
import threading
import base64
import time

def thd_func(client):
    connectionSocket, addr = client
    sentence = connectionSocket.recv(1024).decode()

    if sentence == "#FILELIST":
        response = " ".join(os.listdir("served_files"))
        response = f"Server ({os.path.basename(os.getcwd())}): 200 Files served: " + response
        connectionSocket.send(response.encode())
    elif sentence.startswith("#UPLOAD"):
        sentence = sentence.split()
        filename = sentence[1]
        file_path = os.path.join("served_files", filename)

        if len(sentence) == 4:# client send upload request
            if not os.path.exists(file_path):
                msg = f"330 Ready to receive file {filename}"
                connectionSocket.send(msg.encode())
            else:
                msg = "250"
                connectionSocket.send(msg.encode())
        elif len(sentence) > 4:# client send chunk
            filename = sentence[1]
            idx = int(sentence[3])
            contents = sentence[4]
            contents = base64.b64decode(contents.encode()).decode() # remember to decode the contents!
            file_path = os.path.join("served_files", filename)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(contents)
            msg = f"200 File {filename} chunk {idx} received"
            time.sleep(0.5)
            connectionSocket.send(msg.encode())
    elif sentence.startswith("#DOWNLOAD"):
        sentence = sentence.split()
        filename = sentence[1]
        file_path = os.path.join("served_files", filename)

        if len(sentence) == 2:# client send download request
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                msg = f"330 Ready to send file {filename} bytes {file_size}"
                connectionSocket.send(msg.encode())
            else:
                msg = f"250 Not serving file {filename}"
                connectionSocket.send(msg.encode())

        elif len(sentence) == 4:# client send chunk request
            index = int(sentence[3])
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                chunk_size = 100  #each chunk size is 100 bytes
                start = index * chunk_size
                end = start + chunk_size
                chunk_data = content[start:end]
                msg = f"200 File {filename} chunk {index} {chunk_data}"
                time.sleep(0.5)
                connectionSocket.send(msg.encode())

    
    connectionSocket.close()

def main():
    # get the server port
    serverPort = 0
    name = os.path.basename(os.getcwd())
    current_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(current_dir)
    setting_path = os.path.join(parent_dir, "peer_settings.txt")
    with open(setting_path, "r") as file:
        for i in file:
            peer_id, ip_addr, server_port = i.split()
            if peer_id == name:
                serverPort = int(server_port)
                break

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind(("", serverPort))
    serverSocket.listen(7)
    while True:
        client = serverSocket.accept()
        newthd = threading.Thread(target=thd_func, args=(client,))
        newthd.start()

    serverSocket.close()

if __name__ == "__main__":
    main()