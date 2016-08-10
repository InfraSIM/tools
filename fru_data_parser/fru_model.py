#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math

class Fru_Data_Cmd():

    def __init__(self, cmd):
        """
        All OFFSET_xxx data is orgnized in format of:
            (offset, length)

        :param cmd: the command to add fru data, e.g.
            mc_add_fru_data 0x20 0x01 0x100 data 0x01 0x00 0x01 0x02 0x09 0x00 0x00
        """
        self.OFFSET_MC_ADD_FRU_DATA = (0, 1)
        self.OFFSET_MC_ADDRESS = (1, 1)
        self.OFFSET_DEVICE_ID = (2, 1)
        self.OFFSET_FRU_SIZE = (3, 1)
        self.OFFSET_DATA = (4, 1)
        self.OFFSET_COMMON_HEADER = (5, 8)
        self.OFFSET_INTERNAL_USE_AREA = None
        self.OFFSET_CHASSIS_INFO_AREA = None
        self.OFFSET_BOARD_INFO_AREA = None
        self.OFFSET_PRODUCT_INFO_AREA = None
        self.OFFSET_MULTI_RECORD_AREA = None

        self.DATA_COMMON_HEADER = []
        self.DATA_INTERNAL_USE_AREA = []
        self.DATA_CHASSIS_INFO_AREA = []
        self.DATA_BOARD_INFO_AREA = []
        self.DATA_PRODUCT_INFO_AREA = []
        self.DATA_MULTI_RECORD_AREA = []

        self.obj_internal_use_area = None
        self.obj_chassis_info_area = None
        self.obj_board_info_area = None
        self.obj_product_info_area = None
        self.obj_multi_record_area = None

        self.cmd = cmd

        # self.list_element e.g.
        # [
        #   # prefix
        #   "mc_add_fru_data", "0x20", "0x00", "0x100", "data",
        #   # common header
        #   "0x01", "0x00", "0x01", "0x06", "0x0f", "0x00", "0x00", "0xe9",
        #   # internal use area
        #   # chassis info area
        #   ...
        # ]
        self.list_element = self.cmd.split()

        self.parse()

    def parse(self):
        """
        Use self.list_element to build all segment
        """
        self.fru_size = self.list_element[self.OFFSET_FRU_SIZE[0]]

        base = self.OFFSET_COMMON_HEADER[0]

        # Common header
        self.DATA_COMMON_HEADER = self.list_element[self.OFFSET_COMMON_HEADER[0]:\
                                  self.OFFSET_COMMON_HEADER[0]+self.OFFSET_COMMON_HEADER[1]]

        # Init internal use area
        if int(self.list_element[base+1], 16) != 0:
            start_internal_use_area = base + int(self.list_element[base+1], 16)*8
            length_internal_use_area = int(self.list_element[start_internal_use_area+1], 16)*8
            self.OFFSET_INTERNAL_USE_AREA = (start_internal_use_area, length_internal_use_area)
            self.DATA_INTERNAL_USE_AREA = self.list_element[self.OFFSET_INTERNAL_USE_AREA[0]:\
                self.OFFSET_INTERNAL_USE_AREA[0]+self.OFFSET_INTERNAL_USE_AREA[1]]

            self.obj_internal_use_area = Internal_Use_Area(self.DATA_INTERNAL_USE_AREA)

        # Init chassis info area
        if int(self.list_element[base+2], 16) != 0:
            start_chassis_info_area = base + int(self.list_element[base+2], 16)*8
            length_chassis_info_area = int(self.list_element[start_chassis_info_area+1], 16)*8
            self.OFFSET_CHASSIS_INFO_AREA = (start_chassis_info_area, length_chassis_info_area)
            self.DATA_CHASSIS_INFO_AREA = self.list_element[self.OFFSET_CHASSIS_INFO_AREA[0]:\
                self.OFFSET_CHASSIS_INFO_AREA[0]+self.OFFSET_CHASSIS_INFO_AREA[1]]

            self.obj_chassis_info_area = Chassis_Info_Area(self.DATA_CHASSIS_INFO_AREA)

        # Init board info area
        if int(self.list_element[base+3], 16) != 0:
            start_board_info_area = base + int(self.list_element[base+3], 16)*8
            length_board_info_area = int(self.list_element[start_board_info_area+1], 16)*8
            self.OFFSET_BOARD_INFO_AREA = (start_board_info_area, length_board_info_area)
            self.DATA_BOARD_INFO_AREA = self.list_element[self.OFFSET_BOARD_INFO_AREA[0]:\
                self.OFFSET_BOARD_INFO_AREA[0]+self.OFFSET_BOARD_INFO_AREA[1]]

            self.obj_board_info_area = Board_Info_Area(self.DATA_BOARD_INFO_AREA)

        # Init product info area
        if int(self.list_element[base+4], 16) != 0:
            start_product_info_area = base + int(self.list_element[base+4], 16)*8
            length_product_info_area = int(self.list_element[start_product_info_area+1], 16)*8
            self.OFFSET_PRODUCT_INFO_AREA = (start_product_info_area, length_product_info_area)
            self.DATA_PRODUCT_INFO_AREA = self.list_element[self.OFFSET_PRODUCT_INFO_AREA[0]:\
                self.OFFSET_PRODUCT_INFO_AREA[0]+self.OFFSET_PRODUCT_INFO_AREA[1]]

            self.obj_product_info_area = Product_Info_Area(self.DATA_PRODUCT_INFO_AREA)

        # Init multi record area
        if int(self.list_element[base+5], 16) != 0:
            start_multi_record_area = base + int(self.list_element[base+5], 16)*8
            length_multi_record_area = int(self.list_element[start_multi_record_area+1], 16)*8
            self.OFFSET_MULTI_RECORD_AREA = (start_multi_record_area, length_multi_record_area)
            self.DATA_MULTI_RECORD_AREA = self.list_element[self.OFFSET_MULTI_RECORD_AREA[0]:\
                self.OFFSET_MULTI_RECORD_AREA[0]+self.OFFSET_MULTI_RECORD_AREA[1]]

            self.obj_multi_record_area = Multi_Record_Area(self.DATA_MULTI_RECORD_AREA)

        # print "offset internal use area:", self.OFFSET_INTERNAL_USE_AREA
        # print "offset chassis info area:", self.OFFSET_CHASSIS_INFO_AREA
        # print "offset board info area:", self.OFFSET_BOARD_INFO_AREA
        # print "offset product info area:", self.OFFSET_PRODUCT_INFO_AREA
        # print "offset multi record area:", self.OFFSET_MULTI_RECORD_AREA

        # print "internal use area:", self.DATA_INTERNAL_USE_AREA
        # print "chassis info area:", self.DATA_CHASSIS_INFO_AREA
        # print "board info area:", self.DATA_BOARD_INFO_AREA
        # print "product info area:", self.DATA_PRODUCT_INFO_AREA
        # print "multi record area:", self.DATA_MULTI_RECORD_AREA

    def get_chassis_part_number(self):
        data_chassis_part_number = self.obj_chassis_info_area.get_chassis_part_number()

        pn = ""
        for order in data_chassis_part_number:
            pn += chr(int(order, 16))

        return pn

    def set_chassis_part_number(self, part_number):
        self.obj_chassis_info_area.set_chassis_part_number(part_number)
        self.compose()

    def get_chassis_serial_number(self):
        data_chassis_serial_number = self.obj_chassis_info_area.get_chassis_serial_number()

        sn = ""
        for order in data_chassis_serial_number:
            sn += chr(int(order, 16))

        return sn

    def set_chassis_serial_number(self, serial_number):
        self.obj_chassis_info_area.set_chassis_serial_number(serial_number)
        self.compose()

    def get_chassis_extra(self):

        list_extra = self.obj_chassis_info_area.get_chassis_extra()
        list_field = []

        for extra_data in list_extra:
            s = ""
            for order in extra_data:
                s += chr(int(order, 16))

            list_field.append(s)

        return list_field

    def add_chassis_custom_field(self, str_field):
        self.obj_chassis_info_area.add_custom_field(str_field)
        self.compose()

    def remove_chassis_custom_field(self, field_id):
        self.obj_chassis_info_area.remove_custom_field(field_id)
        self.compose()

    def get_board_mfg_date_time(self):
        offset_type_offset = self.OFFSET_BOARD_INFO_AREA[0]+3
        data_mfg_date_time = self.list_element[offset_type_offset:offset_type_offset+3]

        return data_mfg_date_time

    def get_board_manufacturer(self):
        data_board_manufacturer = self.obj_board_info_area.get_board_manufacturer()

        mfg = ""
        for order in data_board_manufacturer:
            mfg += chr(int(order, 16))

        return mfg

    def set_board_manufacturer(self, mfg):
        self.obj_board_info_area.set_board_manufacturer(mfg)
        self.compose()

    def get_board_product_name(self):
        data_board_product_name = self.obj_board_info_area.get_board_product_name()

        pn = ""
        for order in data_board_product_name:
            pn += chr(int(order, 16))

        return pn

    def set_board_product_name(self, product_name):
        self.obj_board_info_area.set_board_product_name(product_name)
        self.compose()

    def get_board_serial_number(self):
        data_board_serial_number = self.obj_board_info_area.get_board_serial_number()

        sn = ""
        for order in data_board_serial_number:
            sn += chr(int(order, 16))

        return sn

    def set_board_serial_number(self, serial_number):
        self.obj_board_info_area.set_board_serial_number(serial_number)
        self.compose()

    def get_board_part_number(self):
        data_board_part_number = self.obj_board_info_area.get_board_part_number()

        pn = ""
        for order in data_board_part_number:
            pn += chr(int(order, 16))

        return pn

    def set_board_part_number(self, part_number):
        self.obj_board_info_area.set_board_part_number(part_number)
        self.compose()

    def get_board_fru_file_id(self):
        data_board_fru_file_id = self.obj_board_info_area.get_board_fru_file_id()

        ffid = ""
        for order in data_board_fru_file_id:
            ffid += chr(int(order, 16))

        return ffid

    def set_board_fru_file_id(self, fru_file_id):
        self.obj_board_info_area.set_board_fru_file_id(fru_file_id)

    def get_board_extra(self):

        list_extra = self.obj_board_info_area.get_board_extra()
        list_field = []

        for extra_data in list_extra:
            s = ""
            for order in extra_data:
                s += chr(int(order, 16))

            list_field.append(s)

        return list_field

    def add_board_custom_field(self, str_field):
        self.obj_board_info_area.add_custom_field(str_field)
        self.compose()

    def remove_board_custom_field(self, field_id):
        self.obj_board_info_area.remove_custom_field(field_id)
        self.compose()

    def get_product_mfg_name(self):
        data_mfg_name = self.obj_product_info_area.get_product_mfg_name()

        mfg = ""
        for order in data_mfg_name:
            mfg += chr(int(order, 16))

        return mfg

    def set_product_mfg_name(self, mfg_name):
        self.obj_product_info_area.set_product_mfg_name(mfg_name)
        self.compose()

    def get_product_name(self):
        data_product_name = self.obj_product_info_area.get_product_name()

        pn = ""
        for order in data_product_name:
            pn += chr(int(order, 16))

        return pn

    def set_product_name(self, product_name):
        self.obj_product_info_area.set_product_name(product_name)
        self.compose()

    def get_product_model(self):
        data_product_model = self.obj_product_info_area.get_product_model()

        pm = ""
        for order in data_product_model:
            pm += chr(int(order, 16))

        return pm

    def set_product_model(self, product_model):
        self.obj_product_info_area.set_product_model(product_model)
        self.compose()

    def get_product_version(self):
        data_product_version = self.obj_product_info_area.get_product_version()

        pv = ""
        for order in data_product_version:
            pv += chr(int(order, 16))

        return pv

    def set_product_version(self, product_version):
        self.obj_product_info_area.set_product_version(product_version)
        self.compose()

    def get_product_serial_number(self):
        data_product_serial_number = self.obj_product_info_area.get_product_serial_number()

        sn = ""
        for order in data_product_serial_number:
            sn += chr(int(order, 16))

        return sn

    def set_product_serial_number(self, serial_number):
        self.obj_product_info_area.set_product_serial_number(serial_number)
        self.compose()

    def get_product_asset_tag(self):
        data_product_asset_tag = self.obj_product_info_area.get_product_asset_tag()

        at = ""
        for order in data_product_asset_tag:
            at += chr(int(order, 16))

        return at

    def set_product_asset_tag(self, asset_tag):
        self.obj_product_info_area.set_product_asset_tag(asset_tag)
        self.compose()

    def get_product_fru_file_id(self):
        data_product_fru_file_id = self.obj_product_info_area.get_product_fru_file_id()

        ffid = ""
        for order in data_product_fru_file_id:
            ffid += chr(int(order, 16))

        return ffid

    def set_product_fru_file_id(self, fru_file_id):
        self.obj_product_info_area.set_product_fru_file_id(fru_file_id)
        self.compose()

    def get_product_extra(self):

        list_extra = self.obj_product_info_area.get_product_extra()
        list_field = []

        for extra_data in list_extra:
            s = ""
            for order in extra_data:
                s += chr(int(order, 16))

            list_field.append(s)

        return list_field

    def add_product_custom_field(self, str_field):
        self.obj_product_info_area.add_custom_field(str_field)
        self.compose()

    def remove_product_custom_field(self, field_id):
        self.obj_product_info_area.remove_custom_field(field_id)
        self.compose()

    def format_cmd(self):
        """
        Format self.cmd to a well wrapped text lines
        """
        formatted = ""
        i = self.cmd.find(" data ")
        i_data = i+len(" data ")
        formatted += self.cmd[:i_data] + "\\\n"

        i = i_data
        while i < len(self.cmd)-40:
            formatted += self.cmd[i:i+40] + "\\\n"
            i += 40

        formatted += self.cmd[i:] + "\n"

        return formatted

    def compose(self):
        """
        Go through each area, get data length, update common header, checksum and
        zero fill, then update to self.cmd
        :return:
        """

        # area_offset is a int in multiples of 8 bytes
        area_offset = 1

        if self.obj_internal_use_area:
            self.DATA_INTERNAL_USE_AREA = self.obj_internal_use_area.data
            self.OFFSET_INTERNAL_USE_AREA = (self.OFFSET_COMMON_HEADER[0]+self.OFFSET_COMMON_HEADER[1],
                                             len(self.DATA_INTERNAL_USE_AREA))
            self.DATA_COMMON_HEADER[1] = "0x"+hex(area_offset)[2:].zfill(2)
            area_offset += len(self.DATA_INTERNAL_USE_AREA)/8
        else:
            self.DATA_INTERNAL_USE_AREA = []
            self.OFFSET_INTERNAL_USE_AREA = (self.OFFSET_COMMON_HEADER[0]+self.OFFSET_COMMON_HEADER[1], 0)
            self.DATA_COMMON_HEADER[1] = "0x00"

        if self.obj_chassis_info_area:
            self.DATA_CHASSIS_INFO_AREA = self.obj_chassis_info_area.data
            self.OFFSET_CHASSIS_INFO_AREA = (self.OFFSET_INTERNAL_USE_AREA[0]+self.OFFSET_INTERNAL_USE_AREA[1],
                                             len(self.DATA_CHASSIS_INFO_AREA))
            self.DATA_COMMON_HEADER[2] = "0x"+hex(area_offset)[2:].zfill(2)
            area_offset += len(self.DATA_CHASSIS_INFO_AREA)/8
        else:
            self.DATA_CHASSIS_INFO_AREA = []
            self.OFFSET_CHASSIS_INFO_AREA = (self.OFFSET_INTERNAL_USE_AREA[0]+self.OFFSET_INTERNAL_USE_AREA[1], 0)
            self.DATA_COMMON_HEADER[2] = "0x00"

        if self.obj_board_info_area:
            self.DATA_BOARD_INFO_AREA = self.obj_board_info_area.data
            self.OFFSET_BOARD_INFO_AREA = (self.OFFSET_CHASSIS_INFO_AREA[0]+self.OFFSET_CHASSIS_INFO_AREA[1],
                                             len(self.DATA_BOARD_INFO_AREA))
            self.DATA_COMMON_HEADER[3] = "0x"+hex(area_offset)[2:].zfill(2)
            area_offset += len(self.DATA_BOARD_INFO_AREA)/8
        else:
            self.DATA_BOARD_INFO_AREA = []
            self.OFFSET_BOARD_INFO_AREA = (self.OFFSET_CHASSIS_INFO_AREA[0]+self.OFFSET_CHASSIS_INFO_AREA[1], 0)
            self.DATA_COMMON_HEADER[3] = "0x00"

        if self.obj_product_info_area:
            self.DATA_PRODUCT_INFO_AREA = self.obj_product_info_area.data
            self.OFFSET_PRODUCT_INFO_AREA = (self.OFFSET_BOARD_INFO_AREA[0]+self.OFFSET_BOARD_INFO_AREA[1],
                                             len(self.DATA_PRODUCT_INFO_AREA))
            self.DATA_COMMON_HEADER[4] = "0x"+hex(area_offset)[2:].zfill(2)
            area_offset += len(self.DATA_PRODUCT_INFO_AREA)/8
        else:
            self.DATA_PRODUCT_INFO_AREA = []
            self.OFFSET_PRODUCT_INFO_AREA = (self.OFFSET_BOARD_INFO_AREA[0]+self.OFFSET_BOARD_INFO_AREA[1], 0)
            self.DATA_COMMON_HEADER[4] = "0x00"

        if self.obj_multi_record_area:
            self.DATA_MULTI_RECORD_AREA = self.obj_multi_record_area.data
            self.OFFSET_MULTI_RECORD_AREA = (self.OFFSET_PRODUCT_INFO_AREA[0]+self.OFFSET_PRODUCT_INFO_AREA[1],
                                             len(self.DATA_MULTI_RECORD_AREA))
            self.DATA_COMMON_HEADER[5] = "0x"+hex(area_offset)[2:].zfill(2)
            area_offset += len(self.DATA_MULTI_RECORD_AREA)/8
        else:
            self.DATA_MULTI_RECORD_AREA = []
            self.OFFSET_MULTI_RECORD_AREA = (self.OFFSET_PRODUCT_INFO_AREA[0]+self.OFFSET_PRODUCT_INFO_AREA[1], 0)
            self.DATA_COMMON_HEADER[5] = "0x00"

        self.DATA_COMMON_HEADER[6] = "0x00"
        checksum = (~sum([int(i, 16) for i in self.DATA_COMMON_HEADER[0:7]]) + 1) % 256
        self.DATA_COMMON_HEADER[7] = "0x"+hex(checksum)[2:].zfill(2)

        zero_fill_count = int(self.fru_size, 16) \
                          - self.OFFSET_COMMON_HEADER[1] \
                          - self.OFFSET_INTERNAL_USE_AREA[1] \
                          - self.OFFSET_CHASSIS_INFO_AREA[1] \
                          - self.OFFSET_BOARD_INFO_AREA[1] \
                          - self.OFFSET_PRODUCT_INFO_AREA[1] \
                          - self.OFFSET_MULTI_RECORD_AREA[1]
        if zero_fill_count < 0:
            raise RuntimeError("FRU data exceeds size: {}".format(self.fru_size))

        self.cmd = " ".join(self.list_element[0:self.OFFSET_COMMON_HEADER[0]]
                            + self.DATA_COMMON_HEADER
                            + self.DATA_INTERNAL_USE_AREA
                            + self.DATA_CHASSIS_INFO_AREA
                            + self.DATA_BOARD_INFO_AREA
                            + self.DATA_PRODUCT_INFO_AREA
                            + self.DATA_MULTI_RECORD_AREA
                            + ["0x00"] * zero_fill_count)


class Area(object):

    def __init__(self, data):
        """
        :param data: a list of data in hex string, e.g.
            ["0x01", "0x02"]
        """

        # Referring to info area format
        # length | content
        # 1      | Info area format version
        # 1      | Info area length, in multiples of 8 bytes
        # 1      | Next field type/length
        # N      | Next field bytes
        # 1      | Next field type/length
        # M      | Next field bytes
        # ...    | Zero fill
        # 1      | Checksum, zero sum

        # self.data is a list of all bytes
        # e.g.
        # [
        #     "0x01",                      # Info area format version
        #     "0x02"                       # Info area length, in multiples of 8 bytes
        #     "0xc3",                      # Next field type/length
        #     "0x51", "0x52", "0xca",      # Next field bytes
        #     "0x02",                      # Next field type/length
        #     "0x01", "0x02",              # Next field bytes
        #     "0x00", "0x00", "0x00", "0x00", "0x00", "0x00",
        #     "0xc8"                       # Checksum
        # ]

        self.name = "Parent area"
        self.data = data
        self.area_format_version = self.data[0]
        self.area_length = int(self.data[1], 16)*8
        if self.area_length != len(data):
            raise ValueError()

        self.DATA_INFO_AREA_FORMAT_VERSION = self.data[0]
        self.DATA_INFO_AREA_LENGTH = self.data[1]

        # self.fields is a list which maintains all field bytes
        # e.g.
        # [
        #     ["0x51", "0x52", "0xca"],
        #     ["0x01", "0x02"]
        # ]
        # self.type_length_tags is corresponding type_length for each fields above
        # e.g.
        # [
        #     "0xc3",
        #     "0x02"
        # ]

        self.type_length_tags = []
        self.fields = []

    def fill_custom_fields(self, offset):
        """
        Start from the offset, traverse area and capture all customized fields
        Update self.type_length_tags and self.fields
        :param offset: the offset of custom info fields of this area
        :return:
        """
        i = offset
        while True:
            type_length = self.data[i]
            if type_length.lower() == "0xc1":
                break
            if int(type_length, 16) == 0:
                break
            length = int(type_length, 16) % 32
            i += 1
            self.type_length_tags.append(type_length)
            self.fields.append(self.data[i:i+length])
            i += length
            # If index touch checksum, quit
            if i == self.area_length-1:
                break

        # print self.type_length_tags
        # print self.fields

    def compose(self):
        """
        Once any data is updated, this area data is changed and we need to
        update:
            - self.data
            - self.area_length
        Then this change may impact common header, several offset shall be
        changed due to this.
        """
        pass

    def set_field(self, field_id, content, type_id=3):
        """
        Set the Nth field to certain content
        :param field_id: start from 0, the field id in this area
        :param content: content to be transfered to bytes and store
        :param type_id: referring to spec, a 2 bit type code
            00 - binary or unpsecified
            01 - BCD plus
            10 - 6 bit ASCII, packed
            11 - Interpretation depends on Language codes. 11 b indicates 8-bit ASCII + Latin 1
            field, or 2-byte UNICODE (lease significant byte first) if the Language Code is not
            English. At least two bytes of data must be present when this type is used.
            Therefore, the length (number or byte code) will always be >1 if data is present, 0
            if data is not present.
        """

        # type_id: 3, 11b
        if type_id == 3:
            length = len(content)
            type_length = "0x{}".format(hex((type_id << 6) + length)[2:].zfill(2))
            self.type_length_tags[field_id] = type_length

            list_ascii = ["0x{}".format(hex(ord(c))[2:].zfill(2)) for c in content]
            self.fields[field_id] = list_ascii

        self.compose()

    def add_custom_field(self, str_field):
        next_field_id = len(self.fields)

        # Init next field
        self.type_length_tags.append("0x00")
        self.fields.append([])

        # Set the next field
        self.set_field(next_field_id, str_field)

        self.compose()

    def remove_custom_field(self, custom_field_id):
        """
        Remove the Nth customized field.
        The N is not counting mandatory field, and start from 0
        :param field_id: the Nth custom field to be removed
        :return:
        """
        if custom_field_id < 0:
            raise ValueError("The 1st custom field id is 0")
        if custom_field_id + self.OFFSET_CUSTOM_FIELD > len(self.fields)-1:
            msg = "Custom field id {} is invalid, total field count in {} is {}," \
                  "custom field start from {}".\
                format(custom_field_id, self.name, len(self.fields, self.OFFSET_CUSTOM_FIELD))
            raise ValueError(msg)

        del(self.type_length_tags[custom_field_id + self.OFFSET_CUSTOM_FIELD])
        del(self.fields[custom_field_id + self.OFFSET_CUSTOM_FIELD])

        self.compose()


class Internal_Use_Area(object):

    def __init__(self, data):
        """
        :param data: a list of data in hex string, e.g.
            ["0x01", "0x02"]
        """
        self.name = "Internal use area"
        self.data = data
        self.area_format_version = self.data[0]


class Chassis_Info_Area(Area):

    def __init__(self, data):
        """
        :param data: a list of data in hex string, e.g.
            ["0x01", "0x02"]
        """
        self.name = "Chassis info area"
        try:
            super(Chassis_Info_Area, self).__init__(data)
        except ValueError:
            raise ValueError("{} data initialization fail, expecting length {}, "
                             "actual data length {}".
                             format(self.name, self.area_length, len(data)))

        offset_type_length = 2
        self.DATA_CHASSIS_TYPE = self.data[offset_type_length]

        offset_type_length = 3
        self.DATA_CHASSIS_PART_NUMBER_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_CHASSIS_PART_NUMBER_TYPE_LENGTH, 16) % 32
        self.DATA_CHASSIS_PART_NUMBER = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_CHASSIS_PART_NUMBER_TYPE_LENGTH)
        self.fields.append(self.DATA_CHASSIS_PART_NUMBER)

        offset_type_length += length
        self.DATA_CHASSIS_SERIAL_NUMBER_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_CHASSIS_SERIAL_NUMBER_TYPE_LENGTH, 16) % 32
        self.DATA_CHASSIS_SERIAL_NUMBER = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_CHASSIS_SERIAL_NUMBER_TYPE_LENGTH)
        self.fields.append(self.DATA_CHASSIS_SERIAL_NUMBER)

        offset_type_length += length
        self.fill_custom_fields(offset_type_length)

        # OFFSET_CUSTOM_FIELD figure out the customized field is the Nth field in this segment
        self.OFFSET_CUSTOM_FIELD = 2

    def get_chassis_part_number(self):
        return self.fields[0]

    def set_chassis_part_number(self, str_part_number):
        self.set_field(0, str_part_number)

    def get_chassis_serial_number(self):
        return self.fields[1]

    def set_chassis_serial_number(self, str_serial_number):
        self.set_field(1, str_serial_number)

    def get_chassis_extra(self):
        return self.fields[self.OFFSET_CUSTOM_FIELD:]

    def compose(self):
        """
        Once any data is updated, this area data is changed and we need to
        update:
            - self.data
            - self.area_length
        Then this change may impact common header, several offset shall be
        changed due to this.
        """
        # Referring to info area format
        # length | content
        # 1      | Chassis info area format version
        # 1      | Chassis info area length, in multiples of 8 bytes
        # 1      | Chassis type
        # 1      | Chassis part number type/length
        # N      | Chassis part number
        # 1      | Chassis serial number type/length
        # M      | Chassis serial number
        # ...    | Custom fields
        # 1      | c1, indicate ends of custom fields
        # ...    | Zero fill
        # 1      | Checksum, zero sum

        raw_data_length = 5 + len(self.fields) \
                            + sum([len(field) for field in self.fields])

        self.area_length = int(math.ceil(raw_data_length/8.0))
        zero_fill_count = self.area_length*8 - raw_data_length

        list_data = [self.area_format_version,
                     "0x{}".format(hex(self.area_length)[2:].zfill(2)),
                     self.DATA_CHASSIS_TYPE]

        for i in range(len(self.type_length_tags)):
            list_data += [self.type_length_tags[i]]
            list_data += self.fields[i]

        list_data += ["0xc1"]
        list_data += ["0x00"] * zero_fill_count

        # Calculate checksum
        checksum = (~sum([int(i, 16) for i in list_data]) + 1) % 256

        list_data += ["0x{}".format(hex(checksum)[2:].zfill(2))]

        self.data = list_data


class Board_Info_Area(Area):

    def __init__(self, data):
        """
        :param data: a list of data in hex string, e.g.
            ["0x01", "0x02"]
        """
        self.name = "Board info area"
        try:
            super(Board_Info_Area, self).__init__(data)
        except ValueError:
            raise ValueError("{} data initialization fail, expecting length {}, "
                             "actual data length {}".
                             format(self.name, self.area_length, len(data)))

        offset_type_length = 2
        self.DATA_LANGUAGE_CODE = self.data[offset_type_length]

        offset_type_length = 3
        self.DATA_MFG_DATE_TIME = self.data[offset_type_length:offset_type_length+3]

        offset_type_length = 6
        self.DATA_BOARD_MFG_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_BOARD_MFG_TYPE_LENGTH, 16) % 32
        self.DATA_BOARD_MFG = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_BOARD_MFG_TYPE_LENGTH)
        self.fields.append(self.DATA_BOARD_MFG)

        offset_type_length += length
        self.DATA_BOARD_PRODUCT_NAME_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_BOARD_PRODUCT_NAME_TYPE_LENGTH, 16) % 32
        self.DATA_BOARD_PRODUCT_NAME = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_BOARD_PRODUCT_NAME_TYPE_LENGTH)
        self.fields.append(self.DATA_BOARD_PRODUCT_NAME)

        offset_type_length += length
        self.DATA_BOARD_SERIAL_NUMBER_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_BOARD_SERIAL_NUMBER_TYPE_LENGTH, 16) % 32
        self.DATA_BOARD_SERIAL_NUMBER = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_BOARD_SERIAL_NUMBER_TYPE_LENGTH)
        self.fields.append(self.DATA_BOARD_SERIAL_NUMBER)

        offset_type_length += length
        self.DATA_BOARD_PART_NUMBER_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_BOARD_PART_NUMBER_TYPE_LENGTH, 16) % 32
        self.DATA_BOARD_PART_NUMBER = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_BOARD_PART_NUMBER_TYPE_LENGTH)
        self.fields.append(self.DATA_BOARD_PART_NUMBER)

        offset_type_length += length
        self.DATA_FRU_FILE_ID_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_FRU_FILE_ID_TYPE_LENGTH, 16) % 32
        self.DATA_FRU_FILE_ID = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_FRU_FILE_ID_TYPE_LENGTH)
        self.fields.append(self.DATA_FRU_FILE_ID)

        offset_type_length += length
        self.fill_custom_fields(offset_type_length)

        # OFFSET_CUSTOM_FIELD figure out the customized field is the Nth field in this segment
        self.OFFSET_CUSTOM_FIELD = 5

    def get_board_manufacturer(self):
        return self.fields[0]

    def set_board_manufacturer(self, str_board_manufacturer):
        self.set_field(0, str_board_manufacturer)

    def get_board_product_name(self):
        return self.fields[1]

    def set_board_product_name(self, str_board_product_name):
        self.set_field(1, str_board_product_name)

    def get_board_serial_number(self):
        return self.fields[2]

    def set_board_serial_number(self, str_board_serial_number):
        self.set_field(2, str_board_serial_number)

    def get_board_part_number(self):
        return self.fields[3]

    def set_board_part_number(self, str_board_part_number):
        self.set_field(3, str_board_part_number)

    def get_board_fru_file_id(self):
        return self.fields[4]

    def set_board_fru_file_id(self, str_fru_file_id):
        self.set_field(4, str_fru_file_id)

    def get_board_extra(self):
        return self.fields[self.OFFSET_CUSTOM_FIELD:]

    def compose(self):
        """
        Once any data is updated, this area data is changed and we need to
        update:
            - self.data
            - self.area_length
        Then this change may impact common header, several offset shall be
        changed due to this.
        """
        # Referring to info area format
        # length | content
        # 1      | Chassis info area format version
        # 1      | Chassis info area length, in multiples of 8 bytes
        # 1      | Language code
        # 3      | Mfg Date/Time
        # 1      | Board Manufacturer type/length
        # P      | Board Manufacturer
        # 1      | Board Product Name type/length
        # Q      | Board Product Name
        # 1      | Board serial number type/length
        # N      | Board serial number
        # 1      | Board part number type/length
        # N      | Board part number
        # 1      | FRU File ID type/length
        # R      | FRU File ID
        # ...    | Custom fields
        # 1      | c1, indicate ends of custom fields
        # ...    | Zero fill
        # 1      | Checksum, zero sum

        raw_data_length = 8 + len(self.fields) \
                            + sum([len(field) for field in self.fields])

        self.area_length = int(math.ceil(raw_data_length/8.0))
        zero_fill_count = self.area_length*8 - raw_data_length

        list_data = [self.area_format_version,
                     "0x{}".format(hex(self.area_length)[2:].zfill(2)),
                     self.DATA_LANGUAGE_CODE] + self.DATA_MFG_DATE_TIME

        for i in range(len(self.type_length_tags)):
            list_data += [self.type_length_tags[i]]
            list_data += self.fields[i]

        list_data += ["0xc1"]
        list_data += ["0x00"] * zero_fill_count

        # Calculate checksum
        checksum = (~sum([int(i, 16) for i in list_data]) + 1) % 256

        list_data += ["0x{}".format(hex(checksum)[2:].zfill(2))]


class Product_Info_Area(Area):

    def __init__(self, data):
        """
        :param data: a list of data in hex string, e.g.
            ["0x01", "0x02"]
        """
        self.name = "Product info area"
        try:
            super(Product_Info_Area, self).__init__(data)
        except ValueError:
            raise ValueError("{} data initialization fail, expecting length {}, "
                             "actual data length {}".
                             format(self.name, self.area_length, len(data)))

        offset_type_length = 2
        self.DATA_LANGUAGE_CODE = self.data[offset_type_length]

        offset_type_length = 3
        self.DATA_PRODUCT_MFG_NAME_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_PRODUCT_MFG_NAME_TYPE_LENGTH, 16) % 32
        self.DATA_PRODUCT_MFG_NAME = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_PRODUCT_MFG_NAME_TYPE_LENGTH)
        self.fields.append(self.DATA_PRODUCT_MFG_NAME)

        offset_type_length += length
        self.DATA_PRODUCT_NAME_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_PRODUCT_NAME_TYPE_LENGTH, 16) % 32
        self.DATA_PRODUCT_NAME = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_PRODUCT_NAME_TYPE_LENGTH)
        self.fields.append(self.DATA_PRODUCT_NAME)

        offset_type_length += length
        self.DATA_PRODUCT_MODEL_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_PRODUCT_MODEL_TYPE_LENGTH, 16) % 32
        self.DATA_PRODUCT_MODEL = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_PRODUCT_MODEL_TYPE_LENGTH)
        self.fields.append(self.DATA_PRODUCT_MODEL)

        offset_type_length += length
        self.DATA_PRODUCT_VERSION_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_PRODUCT_VERSION_TYPE_LENGTH, 16) % 32
        self.DATA_PRODUCT_VERSION = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_PRODUCT_VERSION_TYPE_LENGTH)
        self.fields.append(self.DATA_PRODUCT_VERSION)

        offset_type_length += length
        self.DATA_PRODUCT_SERIAL_NUMBER_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_PRODUCT_SERIAL_NUMBER_TYPE_LENGTH, 16) % 32
        self.DATA_PRODUCT_SERIAL_NUMBER = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_PRODUCT_SERIAL_NUMBER_TYPE_LENGTH)
        self.fields.append(self.DATA_PRODUCT_SERIAL_NUMBER)

        offset_type_length += length
        self.DATA_ASSET_TAG_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_ASSET_TAG_TYPE_LENGTH, 16) % 32
        self.DATA_ASSET_TAG = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_ASSET_TAG_TYPE_LENGTH)
        self.fields.append(self.DATA_ASSET_TAG)

        offset_type_length += length
        self.DATA_FRU_FILE_ID_TYPE_LENGTH = self.data[offset_type_length]
        offset_type_length += 1
        length = int(self.DATA_FRU_FILE_ID_TYPE_LENGTH, 16) % 32
        self.DATA_FRU_FILE_ID = self.data[offset_type_length:offset_type_length+length]
        self.type_length_tags.append(self.DATA_FRU_FILE_ID_TYPE_LENGTH)
        self.fields.append(self.DATA_FRU_FILE_ID)

        offset_type_length += length
        self.fill_custom_fields(offset_type_length)

        # OFFSET_CUSTOM_FIELD figure out the customized field is the Nth field in this segment
        self.OFFSET_CUSTOM_FIELD = 7

    def get_product_mfg_name(self):
        return self.fields[0]

    def set_product_mfg_name(self, str_mfg_name):
        self.set_field(0, str_mfg_name)

    def get_product_name(self):
        return self.fields[1]

    def set_product_name(self, str_product_name):
        self.set_field(1, str_product_name)

    def get_product_model(self):
        return self.fields[2]

    def set_product_model(self, str_product_model):
        self.set_field(2, str_product_model)

    def get_product_version(self):
        return self.fields[3]

    def set_product_version(self, str_product_version):
        self.set_field(3, str_product_version)

    def get_product_serial_number(self):
        return self.fields[4]

    def set_product_serial_number(self, str_product_serial_number):
        self.set_field(4, str_product_serial_number)

    def get_product_asset_tag(self):
        return self.fields[5]

    def set_product_asset_tag(self, str_product_asset_tag):
        self.set_field(5, str_product_asset_tag)

    def get_product_fru_file_id(self):
        return self.fields[6]

    def set_product_fru_file_id(self, str_fru_file_id):
        self.set_field(6, str_fru_file_id)

    def get_product_extra(self):
        return self.fields[self.OFFSET_CUSTOM_FIELD:]

    def compose(self):
        """
        Once any data is updated, this area data is changed and we need to
        update:
            - self.data
            - self.area_length
        Then this change may impact common header, several offset shall be
        changed due to this.
        """
        # Referring to info area format
        # length | content
        # 1      | Chassis info area format version
        # 1      | Chassis info area length, in multiples of 8 bytes
        # 1      | Language code
        # 1      | Manufacturer Name type/length
        # N      | Manufacturer Name
        # 1      | Product Name type/length
        # M      | Product Name
        # 1      | Product Part/Model Number type/length
        # O      | Product Part/Model Number
        # 1      | Product Version type/length
        # R      | Product Version
        # 1      | Product Serial Number type/length
        # P      | Product Serial Number
        # 1      | Asset Tag type/length
        # Q      | Asset Tag
        # 1      | FRU File ID type/length
        # R      | FRU File ID
        # ...    | Custom fields
        # 1      | c1, indicate ends of custom fields
        # ...    | Zero fill
        # 1      | Checksum, zero sum

        raw_data_length = 5 + len(self.fields) \
                            + sum([len(field) for field in self.fields])

        self.area_length = int(math.ceil(raw_data_length/8.0))
        zero_fill_count = self.area_length*8 - raw_data_length

        list_data = [self.area_format_version,
                     "0x{}".format(hex(self.area_length)[2:].zfill(2)),
                     self.DATA_LANGUAGE_CODE]

        for i in range(len(self.type_length_tags)):
            list_data += [self.type_length_tags[i]]
            list_data += self.fields[i]

        list_data += ["0xc1"]
        list_data += ["0x00"] * zero_fill_count

        # Calculate checksum
        checksum = (~sum([int(i, 16) for i in list_data]) + 1) % 256

        list_data += ["0x{}".format(hex(checksum)[2:].zfill(2))]

        self.data = list_data


class Multi_Record_Area(Area):

    def __init__(self, data):
        """
        :param data: a list of data in hex string, e.g.
            ["0x01", "0x02"]
        """
        self.name = "Multi record area"
        try:
            super(Multi_Record_Area, self).__init__(data)
        except ValueError:
            raise ValueError("{} data initialization fail, expecting length {}, "
                             "actual data length {}".
                             format(self.name, self.area_length, len(data)))


class Field(object):

    def __init__(self, name):
        """
        Maintain offset and data
        :param name: field name
        """
        self.name = name
        self.offset = -1
        self.data = []

    def set_offset(self, offset):
        self.offset = offset

    def get_offset(self):
        return self.offset

    def set_field_data(self, list_data):
        """
        :param list_data: in format of a list of hex string, e.g.
            ["0x01", "0x30", "0xca"]
        """
        self.data = list_data

    def get_field_data(self):
        return self.data

    def size(self):
        return len(self.data)
