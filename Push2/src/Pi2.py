import socket
import threading
import time
from datetime import datetime
from flask import Flask, render_template, send_file, request

#Create flask app
app = Flask(__name__)

#SERVER (host) details=================
HOST_IP = '192.168.1.196'
HOST_PORT = 5005
BUFF_SIZE = 20
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST_IP,HOST_PORT))
print("Server socket setup complete")
#=====================================

#Wait for connection requestion from client
s.listen(1)
#Create connection instance
conn,addr = s.accept()
print("Connection extablished")

#Overwrite and clean log file for new run
log_file = open("/usr/src/app/sensorlog.csv","w")
log_file.close()

#Array for storing 10 most recent sensor samples
log_list = []
#Global variables (default values)
run_thread = True
status = "X" 
valid_status = False

@app.route("/on")
def sens_on():
    #O - message code of 'SENDON' data message
    char = "O"
    message = char + " "+ str(0)
    #Message format: <cmd> <length=0> <empty>
    conn.sendall(str.encode(message))
    #print explanatory message to relevant endpoint
    return "Sensor on"

@app.route("/off")
def sens_off():
    #F - message code of 'SENDOFF' data message
    char = "F"
    message = char + " "+ str(0)
    #Message format: <cmd> <length=0> <empty>
    conn.sendall(str.encode(message))
    return "Sensor off"

@app.route("/status")
def get_status():
    global valid_status
    #K - message code of 'CHECK' data message
    char = "K"
    message = char + " "+ str(0)
    #Message format: <cmd> <length=0> <empty>
    conn.sendall(str.encode(message))
    while(not valid_status):
        #waiting until STATUS response has been received
        pass
    valid_status = False
    #print updated status to relevant endpoint
    return status

@app.route("/logs")
def log_check():
    print("Log Check")
    data = ''
    #Loop through log list, adding each to new line of 'data'
    for a in log_list:
        data = data + "Light level: " + a[0] + " | Temperature: " + a[1] + \
            " | Taken on: " + a[2] + " at " + a[3] + "<br>"
    #print all logs in formatted block
    return data

@app.route("/download")
def log_down():
    #Path of sensorlog file
    path = "/usr/src/app/sensorlog.csv"
    #Return file as downloadable attachment
    return send_file(path,as_attachment=True)

@app.route("/exit")
def server_exit():
    global run_thread
    #Boolean to indicate thread should terminate
    run_thread = False

    #X - message code of 'EXIT' data message
    char = "X"
    message = char + " "+ str(0)
    #Message format: <cmd> <length=0> <empty>
    conn.sendall(str.encode(message))
    #Message sent to client to notify of exit

    #Graceful shutdown of Flask app (note - deprecated)
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    shutdown_func()
    return "The server is shutting down..."

@app.route("/")
def main():   
    #Start thread with dedicated method, no args
    thread = threading.Thread(target=receive)
    thread.daemon = True
    thread.start()
    #Render main html file with clickable links
    return render_template('root.html', title='Root')

def receive():
    global log_list, status, valid_status
    #Thread to constantly listen for messages from clients
    while True and run_thread:
        try:
            #If client closes prematurely, thread loops and likely terminates
            reply = conn.recv(BUFF_SIZE)
        except:
            continue
        reply = reply.decode('utf-8')
        #extract command char
        cmd = reply[0]
        
        #S - message code of 'SENSOR' data message
        if(cmd == "S"):
            #Parse sensor data
            whole = reply.split(" ")
            msg = whole[2].split("#")
            if(not msg[1][len(msg[1])-1].isdigit()): 
                msg[1] = msg[1][0:len(msg[1])-1]
            #if array full, remove oldest entry
            if len(log_list) == 10:
                log_list.pop(0)
            #Append new entry to log array stored on server (light, temp, date, time)
            log_list.append([msg[0],msg[1],datetime.now().date().strftime("%d:%m:%y"),str(datetime.now().time())[0:8]])

            #Append new entry to sensorlog file (light, temp, date, time)
            log_file = open("/usr/src/app/sensorlog.csv","a")
            log_file.write(msg[0]+","+msg[1]+","+datetime.now().date().strftime("%d:%m:%y")+","+str(datetime.now().time())[0:8]+"\n")
            log_file.close()

        #T - message code of 'STATUS' data message
        elif(cmd == "T"):
            #Parse message
            whole = reply.split(" ")
            msg = whole[2].split("#")
            #Update global status variable to be displayed in '/status' endpoint
            status = "Status: " + msg[0] + " | Last sample at: " + msg[1]
            #update valid flag to enable main thread to continue
            valid_status = True

    #Terminate second thread
    quit()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)

#Final quit to terminate program after Flask app
quit()