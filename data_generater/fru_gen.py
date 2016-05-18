import os
import sys

special = False
fru_file_path = sys.argv[1]
fru_file_dir, fru_file_name = os.path.split(fru_file_path)
if not fru_file_dir:
    fru_file_dir="."
fru_result = "result_{}".format(fru_file_name)
last_line = ""
new_file = ""
new_data = ""


def file_handle():
    global special
    global new_file
    global last_line
    os.system("hexdump {}{}{} > tmp".format(fru_file_dir, os.sep, fru_file_name))
    with open("./tmp") as file:
        for line in file.readlines():
            if special:
                cur = line.split(' ', 1)
                pre = last_line.split(' ', 1)
                line_num = int("0x{}".format(cur[0]), base=16)-int("0x{}".format(pre[0]), base=16)
                line_num = line_num/16-1
                for i in range(line_num):
                    new_file += pre[1]
                if len(cur) == 2:
                    new_file += cur[1]
                    special = False
                    last_line = line
                    continue
                else:
                    return
            if "*" in line:
                special = True
            else:
                try:
                    new_file += line.split(' ', 1)[1]
                except IndexError:
                    return  # normally at the end of this file
                else:
                    last_line = line

def data_handle():
    global new_data
    for line in new_file.split(os.linesep):
        if not line:
            continue
        content = line.split()
        if len(content) != 8:
            print "error"
            print content
            sys.exit(1)
        for i in range(4):
            data = content[i]
            new_data += "0x{} 0x{} ".format(data[2:4], data[0:2])
        new_data += "\\"+os.linesep
        for i in range(4, 8):
            data = content[i]
            new_data += "0x{} 0x{} ".format(data[2:4], data[0:2])
        new_data += "\\"+os.linesep


def store_result():
    with open("{}{}{}".format(fru_file_dir, os.sep, fru_result), "w") as file:
        file.write(new_data)



if __name__ == "__main__":
    file_handle()
    data_handle()

    store_result()
