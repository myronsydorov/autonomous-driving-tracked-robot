from flask import Flask, request, render_template_string, send_from_directory
from python_cmd import slam_cmd, nav_cmd
import os
import signal
import threading
import subprocess, shlex
import motor_tcp_client_controller
import socket

app = Flask(__name__)
manual = False
controller_thread = None
slam_running = False
nav_running = False
stop_event = threading.Event()

def run_controller():
    motor_tcp_client_controller.main(stop_event)
    print("Motor_tcp_client_controller wird gestartet")

@app.route('/')
def index():
    global manual
    html_path = os.path.join(os.path.dirname(__file__), 'webpage.html')

    log_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'Logs' , 'log_test.txt')
    try:
        with open(log_path, 'r') as log_file:
            log_content = log_file.read()
    except FileNotFoundError:
        log_content = "Logdatei nicht gefunden."

    #print(f"Log_content: '{log_content}'")

    with open(html_path, 'r') as file:
        rendered_html = render_template_string(
            file.read(), 
            manual=manual, 
            log_content=log_content, 
            slam_running=slam_running, 
            nav_running=nav_running
        )
        #print(rendered_html)
        return rendered_html

@app.route('/data/<path:filename>')
def custom_static(filename):
    return send_from_directory('../Data', filename)

@app.route('/manualcontrol', methods=['POST'])
def run_method():
    # Your Python method logic here
    global manual, controller_thread, stop_event
    if manual:
        manual = False
        stop_event.set()
        print("Manuelle Steuerung wird gestoppt")
    else:
        manual = True
        stop_event.clear()
        controller_thread = threading.Thread(target=run_controller)
        controller_thread.start()
        #print("Manuelle Steuerung wird gestartet")
    return 'Method executed', 200

@app.route('/slam', methods=['POST'])
def slam_control():
    global slam_running
    if slam_running:
        slam_cmd("stop"); slam_running = False; print("SLAM stopped")
    else:
        slam_cmd("start"); slam_running = True;  print("SLAM started")
    return f"slam:{'running' if slam_running else 'stopped'}", 200

@app.route('/nav2', methods=['POST'])
def nav2():
    global nav_running
    if nav_running:
        nav_cmd("stop_nav");
        nav_running = False
    else:
        nav_cmd("start_nav");
        nav_running = True
    return f"nav:{'running' if nav_running else 'stopped'}", 200
@app.route('/shutdown', methods=['POST'])
def shutdown():
    slam_cmd("stop")
    nav_cmd("stop")
    stop_event.set()
    print("🔻 Shutting down the app...")
    os.kill(os.getpid(), signal.SIGINT) 
    return 'Shutting down...', 200


if __name__ == '__main__':
    app.run(debug=True)
