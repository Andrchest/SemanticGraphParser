from os import walk, listdir
from os.path import isfile
from Folder1.Test6 import func
import Test2, Test4

def find_files(path):
    global files_to_parse

    for file in listdir(path):
        current_instace = path + "\\" + file
        if isfile(current_instace):
            if file[-3:] == '.py':
                files_to_parse.append(current_instace)
        else:
            find_files(current_instace)


path = input()

print(path)

files_to_parse = []

find_files(path)

print(files_to_parse)
