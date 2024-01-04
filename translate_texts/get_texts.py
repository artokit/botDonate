import os
import re

files = [os.path.join('..\\', i) for i in os.listdir('..\\')]
ignoring_dir = ['..\\.venv', '..\\bot10k\\.venv']

py_files = []

while files:
    file = files[0]
    files = files[1:]

    if file in ignoring_dir:
        continue

    if file.endswith('py'):
        py_files.append(file)

    if os.path.isdir(file):
        for i in os.listdir(file):
            files.append(os.path.join(file, i))

DELIMITER = '-'*50
files = [open('rus.translate', 'wb'), open('eng.translate', 'wb'), open('sp.translate', 'wb'), open('ch.translate', 'wb')]
for i in py_files:
    with open(i, 'rb') as f:
        text = f.read().decode()
        arr = re.findall(r"_\(['\"].+['\"]", text)
        for j in arr:
            for file in files:
                file.write(f'{eval(j[2:])}\n{DELIMITER}\n'.encode())
