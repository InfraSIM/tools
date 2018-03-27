#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tempfile import mkstemp
from shutil import move
from os import remove, close
from fru_model import Fru_Data_Cmd


def ipmi_sim_cmd_parser(path):
    """
    Generator to parse a file and return next line with \
    and \n merged
    :param path: file path
    :return: (start, end, line)
        start: start line number
        end: end line number
        line: a line with \ and \n merged
    """
    start = 0
    end = 0
    line = ""

    with open(path, "r") as fp:
        line_generator = iter(fp.readlines())
        try:
            while True:
                start += 1
                end = start
                line = line_generator.next()
                if line.strip() == "":
                    continue
                elif line.startswith("#"):
                    continue
                else:
                    # Start counting ipmi_sim_cmd
                    if not line.endswith("\\\n"):
                        yield start, end, line[:-1]
                    else:
                        while True:
                            end += 1
                            next_line = line_generator.next()
                            line = line[:-2] + next_line
                            if next_line.endswith("\\\n"):
                                continue
                            else:
                                yield start, end, line[:-1]
                                start = end
                                break
        except StopIteration:
            pass


def get_fru_data_cmd(path, fru_id):
    """
    Open a file, find the mc_add_fru_data data segment
    :param path: file path
    :param fru_id: fru id in int
    """
    for line_info in ipmi_sim_cmd_parser(path):
        if line_info[2].startswith("mc_add_fru_data 0x20 0x{}".
                                           format(hex(fru_id)[2:].zfill(2))):
            return line_info
    raise RuntimeError("No FRU data (ID: {}) is found in emu file: {}".format(fru_id, path))


def update_file(origin_path, target_path, start, end, text):
    """
    Read a file from origin_path, replace the line from start
    to (including) end with text
    :param origin_path: original file path
    :param target_path: target file path
    :param start: start line number
    :param end: end line number, this line will be replaced too
    :param text: text to replace
    :return:
    """
    # Create temp file
    fh, abs_path = mkstemp()

    i = 0
    written = False
    with open(abs_path, 'w') as new_file:
        with open(origin_path) as old_file:
            for line in old_file:
                i += 1
                if i in range(start, end+1):
                    if not written:
                        new_file.write(text)
                        written = True
                else:
                    new_file.write(line)
    close(fh)
    # Remove original file
    try:
        remove(target_path)
    except Exception:
        pass
    # Move new file
    move(abs_path, target_path)


if __name__ == "__main__":

    print "-" * 40
    print "1. Parse command"
    file_path = "example.emu"
    cmd = get_fru_data_cmd(file_path, fru_id=0)
    print "cmd:", cmd[2]
    p = Fru_Data_Cmd(cmd[2])
    if p.obj_chassis_info_area:
        print "-" * 40
        print "2. Get chassis info"
        print "Chassis part number:", p.get_chassis_part_number()
        print "Chassis serial number:", p.get_chassis_serial_number()
        print "Chassis extra:", p.get_chassis_extra()

    print "-" * 40
    print "3. Get board info"
    print "Board manufacturer:", p.get_board_manufacturer()

    print "Board product name:", p.get_board_product_name()
    print "Board serial number:", p.get_board_serial_number()
    print "Board part number:", p.get_board_part_number()
    print "Board part number:", p.get_board_fru_file_id()

    print "-" * 40
    print "4. Get product info"
    print "MFG name:", p.get_product_mfg_name()
    print "Product name:", p.get_product_name()
    print "Product part/model Number:", p.get_product_model()
    print "Product version:", p.get_product_version()
    print "Product serial number:", p.get_product_serial_number()
    print "Asset tag:", p.get_product_asset_tag()
    print "FRU file id:", p.get_product_fru_file_id()
    if p.obj_chassis_info_area:
        print "-" * 40
        print "5. Get product info"
        print "data:", p.obj_chassis_info_area.data
        p.add_chassis_custom_field("EMCV001")
        print "data:", p.obj_chassis_info_area.data
        p.remove_chassis_custom_field(0)
        print "data:", p.obj_chassis_info_area.data
        p.add_chassis_custom_field("EMCV002")
        print "data:", p.obj_chassis_info_area.data
        p.obj_chassis_info_area.set_field(2, "EMCV003")
        print "data:", p.obj_chassis_info_area.data

        print "-" * 40
        print "6. Change chassis serial number and validate"
        p.set_chassis_serial_number("ZMOD29302843DAB")
        print "Chassis serial number:", p.get_chassis_serial_number()

        print "-" * 40
        print "7. Change board serial number and validate"
        print "Board serial number:", p.get_board_serial_number()
        p.obj_board_info_area.set_board_serial_number("ZTF3J052600357")
        print "Board serial number:", p.get_board_serial_number()

    update_file(file_path, "updated.emu", cmd[0], cmd[1], p.format_cmd())

