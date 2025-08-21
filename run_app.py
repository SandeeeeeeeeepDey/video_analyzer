import subprocess
import os

app_path = os.path.join(os.path.dirname(__file__), 'app.py')
python_executable = os.path.join(os.path.dirname(__file__), 'env_mcd', 'Scripts', 'python.exe')

process = subprocess.Popen([python_executable, app_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

while True:
    line = process.stdout.readline()
    if not line:
        break
    print(line, end='')
    if 'Running on local URL' in line:
        print(line.split(' ')[-1])
