#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""

import os
import subprocess
import array
import struct
import sys
import re
import argparse

""" Uitility for generating EMU file for IPMI SIM """

__author__ = 'Robert Xia, and Payne Wang'
__version__ = "1.0"

MC_ADDRESS = 0x20
DEBUG = False


class String(object):
    def __init__(self):
        self._string_buffer = []

    def __call__(self):
        return self.output_string()

    def add_string(self, s):
        if isinstance(s, list):
            self._string_buffer.extend(s)
        elif isinstance(s, basestring):
            self._string_buffer.append(s)
        else:
            raise ValueError("Invalid type")

    def output_string(self):
        output = ""
        for e in self._string_buffer:
            if e.endswith(os.linesep):
                output += "{}".format(e)
            else:
                output += "{}{}".format(e, os.linesep)
        return output


class Base(object):
    def __init__(self):
        self._string = String()
        self._host = None
        self._user = None
        self._password = None
        self._intf = None
        self._ipmitool = None

    def __call__(self):
        return self._string()

    def set_bmc_info(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def set_ipmitool(self, ipmitool_path, intf):
        self._ipmitool = ipmitool_path
        self._intf = intf

    def get_string(self):
        return self._string.output_string()

    def run_command(self, cmd="", shell=True, stdout=None, stderr=None, *args, **kwargs):
        """
        :param cmd: the command should run
        :param shell: if the type of cmd is string, shell should be set as True, otherwise, False
        :param stdout: reference subprocess module
        :param stderr: reference subprocess module
        :return: tuple (return code, info)
        """
        child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
        cmd_result = child.communicate()
        cmd_return_code = child.returncode
        if cmd_return_code != 0:
            return -1, cmd_result[1]
        return 0, cmd_result[0]


class Header(Base):
    def __init__(self):
        super(Header, self).__init__()
        self.__file_header_comments = ""
        self.__platform_name = "physical server"

    @property
    def platform_name(self):
        return self.__platform_name

    @platform_name.setter
    def platform_name(self, name):
        self.__platform_name = name

    def handle_header_comments(self):
        self._string.add_string("# This file is generated automatically by {}.".
                                format(os.path.basename(sys.argv[0])))
        self._string.add_string("# This file contains FRU Data, Sensor Data, "
                                "and Management Controller Information.")
        self._string.add_string("# This file also adds IPMI SIM commands to "
                                "enable MC, SEL, FRU, and Sensor features.")
        self._string.add_string("# All these data are captured from {}.".
                                format(self.__platform_name))
        self._string.add_string(os.linesep)


class MC(Base):
    def __init__(self):
        super(MC, self).__init__()
        self.__mc_file = ""
        self.additional_device_support_flags = 0
        self.has_device_sdr = False
        self.device_id = None
        self.device_revision = None
        self.fw_minor = None
        self.fw_major = None
        self.manufacture_id = None
        self.product_id = None

    def set_file(self, mc_file):
        self.__mc_file = mc_file

    def dump_mc_info(self, target_file):
        if self._host is None or self._user is None or self._password is None:
            raise ValueError("Missing host information")

        ipmitool_mc_command = "{ipmitool} -I {intf} -U {user} -P {password} " \
                              "-H {host} mc info > {target_file}".\
            format(ipmitool=self._ipmitool, intf=self._intf, user=self._user,
                   password=self._password,
                   host=self._host, target_file=target_file)

        command_exit_status, command_output = self.run_command(ipmitool_mc_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)
        if command_exit_status != 0:
            raise IOError("Command {} failed.".format(ipmitool_mc_command))

    def handle_sensor_owner_list(self, sensor_list):
        for soi in sensor_list.keys():
            if soi == MC_ADDRESS:
                continue

            mc_add_cmd = "mc_add {mc} {device_id} {has_device_sdr} {device_revision} " \
                         "{fw_major} {fw_minor} {device_support_flag} {mfg_id} " \
                         "{product_id} dynsens".\
                format(mc=hex(soi), device_id=0x1, has_device_sdr="no-device-sdrs",
                       device_revision=0x1,
                       fw_major=0, fw_minor=0,
                       device_support_flag=0x9f,
                       mfg_id=0x0, product_id=0x0)
            self._string.add_string(mc_add_cmd)
            self._string.add_string("mc_enable {0:#04x}".format(soi))
            self._string.add_string(os.linesep)

    def handle_mc_info(self):
        with open(self.__mc_file) as f:
            for line in f.readlines():
                if "Device ID" in line:
                    self.device_id = line.split(":")[1].strip()
                elif "Device Revision" in line:
                    self.device_revision = line.split(":")[1].strip()
                elif "Firmware Revision" in line:
                    firmware_version = line.split(":")[1].strip().split(".")
                    self.fw_major = firmware_version[0].lstrip("0")
                    self.fw_minor = firmware_version[1].lstrip("0")
                elif "Manufacturer ID" in line:
                    self.manufacture_id = line.split(":")[1].strip()
                elif "Product ID" in line:
                    self.product_id = line.split(":")[1].strip().split()[0]
                elif "Provides Device Support" in line:
                    if line.split(":")[1].strip() == "yes":
                        self.has_device_sdr = True
                    else:
                        self.has_device_sdr = False
                elif "Sensor Device" in line:
                    self.additional_device_support_flags |= 1 << 0
                elif "SDR Repository Device" in line:
                    self.additional_device_support_flags |= 1 << 1
                elif "SEL Device" in line:
                    self.additional_device_support_flags |= 1 << 2
                elif "FRU Inventory Device" in line:
                    self.additional_device_support_flags |= 1 << 3

                elif "IPMB Event Receiver" in line:
                    self.additional_device_support_flags |= 1 << 4
                elif "IPMB Event Generator" in line:
                    self.additional_device_support_flags |= 1 << 5
                elif "Bridge" in line:
                    self.additional_device_support_flags |= 1 << 6
                elif "Chassis Device" in line:
                    self.additional_device_support_flags |= 1 << 7

        mc_add_cmd = "mc_add {mc} {device_id} {has_device_sdr} {device_revision} " \
                     "{fw_major} {fw_minor} {device_support_flag} {mfg_id} " \
                     "{product_id} dynsens".\
            format(mc=hex(MC_ADDRESS), device_id=self.device_id,
                   has_device_sdr="has-device-sdrs" if self.has_device_sdr else "no-device-sdrs",
                   device_revision=hex(int(self.device_revision)),
                   fw_major=self.fw_major, fw_minor=self.fw_minor,
                   device_support_flag=hex(self.additional_device_support_flags),
                   mfg_id=hex(int(self.manufacture_id)),
                   product_id=hex(int(self.product_id)))
        self._string.add_string("mc_setbmc {}".format(hex(MC_ADDRESS)))
        self._string.add_string(mc_add_cmd)
        self._string.add_string("mc_enable {0:#04x}".format(MC_ADDRESS))
        self._string.add_string(os.linesep)


class SEL(Base):
    def __init__(self):
        super(SEL, self).__init__()

    def handle_sel(self):
        self._string.add_string("sel_enable {mc} {max_entries} {flags:#04x}".
                                format(mc=hex(MC_ADDRESS), max_entries=1000, flags=0x0a))
        self._string.add_string(os.linesep)


class FRU(Base):
    def __init__(self):
        super(FRU, self).__init__()
        self.__file_dict = {}

    def set_file_dict(self, file_dict=None):
        self.__file_dict = file_dict

    def dump_fru(self, fru_id, target_file):
        if self._host is None or self._user is None or self._password is None:
            raise ValueError("Missing host information")

        ipmitool_fru_command = "{ipmitool} -I {intf} -U {user} -P {password} " \
                               "-H {host} fru read {id} {target_file}".\
            format(ipmitool=self._ipmitool, intf=self._intf, user=self._user,
                   password=self._password,
                   host=self._host, id=fru_id, target_file=target_file)

        command_exit_status, command_output = self.run_command(ipmitool_fru_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)
        if command_exit_status != 0:
            raise ValueError("Command {} failed.".format(ipmitool_fru_command))

    def __get_fru_ids(self):
        if self._host is None or self._user is None or self._password is None:
            raise ValueError("Missing host info.")

        ipmitool_fru_command = "{ipmitool} -I {intf} -U {user} -P {password} -H {host} fru".\
            format(ipmitool=self._ipmitool, intf=self._intf, user=self._user,
                   password=self._password, host=self._host)
        command_exit_status, command_output = self.run_command(ipmitool_fru_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)

        if command_exit_status != 0:
            raise ValueError("Command {} failed [exit code: {}].".format(
                ipmitool_fru_command, command_exit_status))

        id_list = []
        for line in command_output.split(os.linesep):
            re_obj = re.search("^FRU Device Description : .* \(ID (\d+)\)", line)
            if re_obj:
                id_list.append(int(re_obj.group(1)))

        return id_list

    def dump_frus(self, dest_folder):
        for id in self.__get_fru_ids():
            target_file = os.path.join(dest_folder, "fru{}.bin".format(id))
            self.dump_fru(id, target_file)
            print "FRU {0} saved to file {1}".format(id, target_file)
            self.__file_dict[id] = target_file

    def read_fru_data(self, fru_id, fru_file):
        count = 0
        file_size = os.stat(fru_file)[6]
        self._string.add_string("# add FRU {}".format(fru_id))
        self._string.add_string("mc_add_fru_data {mc:#04x} {id:#04x} {size:#x} data \\{linesep}".
                                format(mc=MC_ADDRESS, id=fru_id,
                                       size=file_size, linesep=os.linesep))
        with open(fru_file, "rb") as f:
            while True:
                fru_data = f.read(8)
                if not fru_data:
                    break
                count += 8
                fru_data_array = map(hex, array.array('B', fru_data))
                line_str = ""
                for data in fru_data_array:
                    line_str += "{0:#04x} ".format(int(data, 16))
                if count < file_size:
                    line_str += "\\{}".format(os.linesep)
                else:
                    line_str += os.linesep
                self._string.add_string(line_str)
            self._string.add_string(os.linesep)

    def handle_fru(self):
        try:
            for fru_id, fru_file in self.__file_dict.items():
                self.read_fru_data(fru_id, fru_file)
        except Exception as ex:
            print "FRU exception: {}".format(ex)
            sys.exit(1)


class SDR(Base):
    def __init__(self, action="auto"):
        super(SDR, self).__init__()
        self.__sdr_file = ""
        self.__sdr_type = None
        self.__sdr_len = None
        self.__record_id = None
        self.__action = action
        self.__sensor_list = {}

    def __add_sensor(self, sensor_owner_id, sens_num):
        """
        if sensor_owner_id in self.__sensor_owner_id_list:
            return
        self.__sensor_owner_id_list.append(sensor_owner_id)
        """

        try:
            if sensor_owner_id not in self.__sensor_list:
                self.__sensor_list[sensor_owner_id] = []

            if sens_num in self.__sensor_list[sensor_owner_id]:
                return True

            print "Add sensor {0:#x} for owner {1:#x}".format(sens_num, sensor_owner_id)
            self.__sensor_list[sensor_owner_id].append(sens_num)
            return False
        except Exception as ex:
            print ex
            sys.exit(1)

    def get_sensor_list(self):
        return self.__sensor_list

    def set_file(self, sdr_file=None):
        self.__sdr_file = sdr_file

    def dump_sdr(self, target_file):
        if self._host is None or self._user is None or self._password is None:
            raise ValueError("Missing host info")

        ipmitool_sdr_command = "{ipmitool} -I {intf} -U {user} -P " \
                               "{password} -H {host} sdr dump {tf}".\
            format(ipmitool=self._ipmitool, intf=self._intf, user=self._user,
                   password=self._password, host=self._host, tf=target_file)

        command_exit_status, command_output = self.run_command(ipmitool_sdr_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)

        if command_exit_status != 0:
            raise IOError("Command {} failed [exit code: {}].".format(
                ipmitool_sdr_command, command_exit_status))

    def __get_sensor_current_value(self, sensor_number, owner_id=MC_ADDRESS):
        if self._host is None or self._user is None or self._password is None:
            return None

        if owner_id != MC_ADDRESS:
            ipmitool_command = "ipmitool -t {owner:#04x} -I {intf} -U {user} -P " \
                            "{password} -H {host} raw 0x04 0x2d {sn}".\
                format(owner=owner_id, user=self._user, intf=self._intf,
                       password=self._password,
                       host=self._host, sn=sensor_number)


        else:
            ipmitool_command = "ipmitool -I {intf} -U {user} -P " \
                            "{password} -H {host} raw 0x04 0x2d {sn}".\
                format(user=self._user, intf=self._intf,
                       password=self._password,
                       host=self._host, sn=sensor_number)

        command_exit_status, command_output = self.run_command(ipmitool_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)
        if command_exit_status != 0:
            return None

        return command_output

    def __get_sensor_current_thresholds(self, sensor_number):
        if self._host is None or self._user is None or self._password is None:
            return None

        ipmitool_command = "ipmitool -I {intf} -U {user} -P " \
                           "{password} -H {host} raw 0x04 0x27 {sn}".\
            format(user=self._user, intf=self._intf, password=self._password,
                   host=self._host, sn=sensor_number)

        command_exit_status, command_output = self.run_command(ipmitool_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)
        if command_exit_status != 0:
            return None

        return command_output

    def print_sdr_header(self, header):
        print "-----TYPE {}-----".format(hex(header[2]))
        print "Record ID: {0}".format(hex(header[0]))
        print "SDR Version: {}".format(hex(header[1]))
        print "Record Type: {}".format(hex(header[2]))
        print "Record Length: {}".format(hex(header[3]))
        print

    def handle_header(self, data):
        header = struct.unpack("HBBB", data)
        if header[1] != 0x51:  # version of Sensor Model should be '0x51'
            raise ValueError("Invalid SDR header")

        self.__record_id = header[0]
        self.__sdr_type = header[2]
        self.__sdr_len = header[3]

        if DEBUG:
            self.print_sdr_header(header)

    def __format_main_sdr_add(self, body):
        # main_sdr_add_cmd
        main_sdr_add_cmd = "main_sdr_add {mc} \\{linesep}".\
            format(mc=hex(MC_ADDRESS), linesep=os.linesep)

        # add header
        header = [self.__record_id & 0xff, (self.__record_id & 0xff00) >> 8,
                  0x51, self.__sdr_type, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count = 0
        for data in body:
            count += 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)
        return main_sdr_add_cmd

    def __format_sensor_add(self, sensor_owner_id, lun, sensor_number,
                            sensor_type, event_reading_code, event_only=None):
        # sensor_add
        sensor_add_cmd = "sensor_add {mc} {lun} {sensor_num:#04x} {sensor_type:#04x} " \
                         "{event_reading_code:#04x}".\
            format(mc=hex(sensor_owner_id),
                   lun=hex(lun),
                   sensor_num=sensor_number,
                   sensor_type=sensor_type,
                   event_reading_code=event_reading_code)

        if event_only:
            sensor_add_cmd = "{0} {1}".format(sensor_add_cmd, event_only)

        return sensor_add_cmd

    def __format_sensor_set_threshold(self, *args):
        (sensor_owner_id, lun, sensor_number, threshold_support, threshold_mask,
         unr_thres, uc_thres, unc_thres, lnr_thres, lc_thres, lnc_thres) = args

        set_threshold_command = "sensor_set_threshold {mc} {lun} {sensor_num:#04x} " \
                                "{support} {enable:06b} {v5:#04x} {v4:#04x} {v3:#04x} " \
                                "{v2:#04x} {v1:#04x} {v0:#04x}".\
            format(mc=hex(sensor_owner_id), lun=hex(lun), sensor_num=sensor_number,
                   support=threshold_support, enable=threshold_mask,
                   v5=unr_thres, v4=uc_thres, v3=unc_thres, v2=lnr_thres,
                   v1=lc_thres, v0=lnc_thres)
        return set_threshold_command

    def __format_sensor_set_value(self, sensor_owner_id, lun, sensor_number,
                                  sensor_current_value, events_enable_bit):
        set_value_command = "sensor_set_value {mc} {lun} {sn:#04x} " \
                            "{value:#04x} {enable:#x}".\
            format(mc=hex(sensor_owner_id), lun=hex(lun), sn=sensor_number,
                   value=sensor_current_value, enable=events_enable_bit)
        return set_value_command

    def __format_sensor_set_event_support(self, *args):
        (sensor_owner_id, lun, sensor_number, events_enable, scanning, event_support,
         assertion_event_mask, deassertion_event_mask) = args

        set_event_support_cmd = "sensor_set_event_support {mc} {lun} " \
                                "{sensor_num:#04x} {events_enable} {scanning} " \
                                "{event_support} {assert_support:015b} " \
                                "{deassert_support:015b} {assert_enable:015b} " \
                                "{deassert_enable:015b}".\
            format(mc=hex(sensor_owner_id), lun=hex(lun),
                   sensor_num=sensor_number, events_enable=events_enable,
                   scanning=scanning, event_support=event_support,
                   assert_support=assertion_event_mask,
                   deassert_support=deassertion_event_mask,
                   assert_enable=assertion_event_mask,
                   deassert_enable=deassertion_event_mask)
        return set_event_support_cmd

    def __format_sensor_set_bit(self, sensor_owner_id, lun, sensor_number, bit_to_set,
                                bit_value, gen_event):
        sensor_set_bit_cmd = "sensor_set_bit {mc} {lun} {sn:#04x} {bit} {v} {en}".\
            format(mc=hex(sensor_owner_id), lun=hex(lun),
                   sn=sensor_number, bit=bit_to_set, v=bit_value, en=gen_event)
        return sensor_set_bit_cmd

    def __add_comment(self, comments):
        pass

    # SDR Type 0x1
    def handle_sdr_type1_2(self, body):
        sensor_owner_id = int(body[0x0], 16)
        channel = (int(body[1], 16) & 0xf0) >> 4
        lun = int(body[1], 16) & 0x3
        sensor_number = int(body[2], 16)
        sensor_type = int(body[7], 16)
        event_reading_code = int(body[8], 16)
        threshold_access_support = (int(body[6], 16) & 0xc) >> 2
        settable_threshold_mask = int(body[14], 16) & 0x3f
        readable_threshold_mask = int(body[13], 16) & 0x3f

        if self.__add_sensor(sensor_owner_id, sensor_number):
            print "sensor {0:#x}/{1:#x} already added.".format(sensor_number, sensor_owner_id)
            return

        unr_thres = 0
        uc_thres = 0
        unc_thres = 0
        lnr_thres = 0
        lc_thres = 0
        lnc_thres = 0
        if event_reading_code == 0x1:
            unr_thres = int(body[31], 16)
            uc_thres = int(body[32], 16)
            unc_thres = int(body[33], 16)
            lnr_thres = int(body[34], 16)
            lc_thres = int(body[35], 16)
            lnc_thres = int(body[36], 16)

        assertion_event_mask = ((int(body[10], 16) << 8) | int(body[9], 16)) & 0xfff
        deassertion_event_mask = ((int(body[12], 16) << 8) | int(body[11], 16)) & 0xfff

        sensor_event_message_control_support = int(body[6], 16) & 0x3

        # init events
        events_enable_bit = (int(body[5], 16) & 0x20) >> 5
        # init scanning
        scanning_enable_bit = (int(body[5], 16) & 0x40) >> 6

        if self.__sdr_type == 0x1:
            id_len_offset = 42
        else:
            id_len_offset = 26

        id_string_len = int(body[id_len_offset], 16) & 0xf
        id_string = ""
        id_string_start_offset = id_len_offset + 1
        for index in xrange(0, id_string_len):
            id_string += chr(int(body[id_string_start_offset + index], 16))
        if DEBUG:
            print "Sensor Owner ID: {}".format(hex(sensor_owner_id))
            print "Sensor Owner LUN (channel/LUN): {}/{}".format(channel, lun)
            print "Sensor Number: {0:#04x}".format(sensor_number)
            print "Sensor Type: {}".format(sensor_type)
            print "Event / Reading Type Code: {}".format(hex(event_reading_code))
            print "Threshold Access Support: {:#x}".format(threshold_access_support)
            print "Settable Threshold Mask: {:06b}".format(settable_threshold_mask)
            print "Readable Threshold Mask: {:06b}".format(readable_threshold_mask)
            print "Assertion Event Mask/Lower Threshold Reading Mask: {0:015b}".\
                format(assertion_event_mask)
            print "Deassertion Event Mask/Upper Threshold Reading Mask: {0:015b}".\
                format(deassertion_event_mask)
            print "Sensor Event Message Control Support: {0:#x}".format(
                sensor_event_message_control_support)
            print "Sensor Initialization: {}".format(body[5])
            print "Init Events: {:b}".format(events_enable_bit)
            print "Init Scanning: {:b}".format(scanning_enable_bit)
            print "ID string length: {}".format(id_string_len)
            print "Sensor ID: {}".format(id_string)
            print

        sensor_current_value = 0
        event_status_data = 0
        if self.__action == "auto":
            raw_output = self.__get_sensor_current_value(sensor_number,
                                                         sensor_owner_id)
            if raw_output is not None:
                raw_output_list = raw_output.strip().split()
                sensor_current_value = int(raw_output_list[0], 16)
                # events enable bit in Get Sensor Reading response
                events_enable_bit = (int(raw_output_list[1], 16) & 0x80) >> 7
                # scanning enable bit in Get Sensor Reading response
                scanning_enable_bit = (int(raw_output_list[1], 16) & 0x40) >> 6

                # Currently lanserv doesn't handle this bit, the bit is always 0 in the response
                # for Get Sensor Reading command
                reading_or_state_unavailable = (int(raw_output_list[1], 16) & 0x20) >> 5

                # workaround for reading/state unavailable bit (bit 5) in Get Sensor Reading command response
                # some sensors are unavailable on physical platform, but ipmi sim couldn't handle such cases.
                # all the sensors are in working state which causing inconsistent with sensors on physical platform
                # TODO: made changes in ipmi sim to support unavailable sensors.
                # Currently these sensors will cause lots of SEL entries when ipmi sim is up, so if the bit is set,
                # then don't enable event for this sensor
                if reading_or_state_unavailable:
                    events_enable_bit = 0

                for index in xrange(0, len(raw_output_list[2:])):
                    event_status_data |= (int(raw_output_list[2+index], 16) << (index*8))
                # The most significant bit is reserved
                event_status_data &= 0x7fff

            threshold_output = self.__get_sensor_current_thresholds(sensor_number)
            if threshold_output is not None:
                threshold_output_list = threshold_output.strip().split()
                current_threshold_mask = int(threshold_output_list[0], 16)
                v_lnc = int(threshold_output_list[1], 16)
                v_lc = int(threshold_output_list[2], 16)
                v_lnr = int(threshold_output_list[3], 16)
                v_unc = int(threshold_output_list[4], 16)
                v_uc = int(threshold_output_list[5], 16)
                v_unr = int(threshold_output_list[6], 16)

                # If the thresholds are different with the current thresholds, update them
                lnc_thres = v_lnc if lnc_thres != v_lnc else lnc_thres
                lc_thres = v_lc if lc_thres != v_lc else lc_thres
                lnr_thres = v_lnr if lnr_thres != v_lnr else lnr_thres
                unc_thres = v_unc if unc_thres != v_unc else unc_thres
                uc_thres = v_uc if uc_thres != v_uc else uc_thres
                unr_thres = v_unr if unr_thres != v_unr else unr_thres

                # From the SDRs we can see some sensors don't suport threshold access,
                # but they still could be accessed through Get Sensor Thresholds command.
                # When this happens, need sync the threshold support with the threshold support in
                # in Get Sensor Thresholds command response
                if current_threshold_mask != 0 and threshold_access_support == 0x0:
                    # Revise the threshold access support
                    threshold_access_support = 0x1

                if readable_threshold_mask != current_threshold_mask:
                    readable_threshold_mask = current_threshold_mask

        sensor_add_cmd = self.__format_sensor_add(sensor_owner_id, lun,
                                                  sensor_number, sensor_type,
                                                  event_reading_code)

        if threshold_access_support == 0x0:
            threshold_support = "none"
        elif threshold_access_support == 0x1:
            threshold_support = "readable"
        elif threshold_access_support == 0x2:
            threshold_support = "settable"
        elif threshold_access_support == 0x3:
            threshold_support = "fixed"
        else:
            raise ValueError("should not be here.")

        if sensor_event_message_control_support == 0x0:
            event_support = "per-state"
        elif sensor_event_message_control_support == 0x1:
            event_support = "entire-sensor"
        elif sensor_event_message_control_support == 0x2:
            event_support = "global"
        elif sensor_event_message_control_support == 0x3:
            event_support = "none"
        else:
            raise ValueError("should not be here.")

        if events_enable_bit:
            events_enable = "enable"
        else:
            events_enable = "disable"

        if scanning_enable_bit:
            scanning = "scanning"
        else:
            scanning = "no-scanning"

        main_sdr_add_cmd = self.__format_main_sdr_add(body)

        set_threshold_command = None
        if event_reading_code == 0x1:
            threshold_mask = settable_threshold_mask if threshold_support == "settable" else  readable_threshold_mask
            set_threshold_command = self.__format_sensor_set_threshold(
                sensor_owner_id, lun, sensor_number, threshold_support,
                threshold_mask, unr_thres, uc_thres, unc_thres,
                lnr_thres, lc_thres, lnc_thres)

        set_value_command = self.__format_sensor_set_value(
            sensor_owner_id, lun, sensor_number,
            sensor_current_value, events_enable_bit)

        set_event_support_cmd = self.__format_sensor_set_event_support(
            sensor_owner_id, lun, sensor_number, events_enable, scanning,
            event_support, assertion_event_mask, deassertion_event_mask)

        comments = "# Add sensor {0}({1}){2}".format(sensor_number, id_string, os.linesep)
        self._string.add_string(comments)
        self._string.add_string(sensor_add_cmd)
        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string(set_value_command)
        if set_threshold_command:
            self._string.add_string(set_threshold_command)
        self._string.add_string(set_event_support_cmd)

        if event_status_data != 0x0:
            for bit in xrange(0, 14):
                bit_value = (event_status_data & (1 << bit)) >> bit
                if bit_value != 0:
                    sensor_set_bit_command = self.__format_sensor_set_bit(sensor_owner_id,
                                                                            lun, sensor_number,
                                                                            bit, bit_value,
                                                                            events_enable_bit)
                    self._string.add_string(sensor_set_bit_command)

        self._string.add_string(os.linesep)

    # SDR Type 0x3
    def handle_sdr_type3(self, body):
        sensor_owner_id = int(body[0x0], 16)

        channel = (int(body[1], 16) & 0xf0) >> 4
        fru_inventory_device_owner_lun = (int(body[1], 16) & 0xc) >> 2
        lun = int(body[1], 16) & 0x3
        sensor_number = int(body[2], 16)
        sensor_type = int(body[5], 16)
        event_reading_code = int(body[8], 16)

        if self.__add_sensor(sensor_owner_id, sensor_number):
            print "sensor {0:#x}/{1:#x} already added.".format(sensor_number, sensor_owner_id)
            return

        if DEBUG:
            print "Sensor Owner ID: {}".format(hex(sensor_owner_id))
            print "Sensor Owner LUN (channel/fru inverntory LUN/LUN): {}/{}/{}".\
                format(channel, fru_inventory_device_owner_lun, lun)
            print "Sensor Number: {0:#04x}".format(sensor_number)
            print "Sensor Type: {}".format(sensor_type)
            print "Event / Reading Type Code: {}".format(hex(event_reading_code))
            print

        sensor_add_cmd = self.__format_sensor_add(sensor_owner_id, lun,
                                                  sensor_number, sensor_type,
                                                  event_reading_code, event_only="event-only")

        main_sdr_add_cmd = self.__format_main_sdr_add(body)

        comments = "# Add sensor {}{}".format(sensor_number, os.linesep)

        self._string.add_string(comments)
        self._string.add_string(sensor_add_cmd)

        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string(os.linesep)

    # SDR Type 0x8
    def handle_sdr_type8(self, body):
        if DEBUG:
            print "Container Entity ID: {}".format(body[0])
            print "Container Entity Instance: {}".format(body[1])
            print "Flags: {}".format(body[2])
            print "Contained Entity 1/Range 1 Entity: {}".format(body[3])
            print "Contained Entity 1 Instance/Range 1 first entity instance: {}".format(body[4])
        else:
            print "Ignore SDR type: {0:#04x}".format(self.__sdr_type)

    # SDR Type 0x9
    def handle_sdr_type9(self, body):
        if DEBUG:
            print "Container Entity ID: {}".format(body[0])
            print "Container Entity Instance: {}".format(body[1])
            print "Container Entity Device Address {}".format(body[2])
            print "Container Entity Device Channel {}".format(body[3])
        else:
            print "Ignore SDR type: {0:#04x}".format(self.__sdr_type)

    # SDR Type 0x10
    def handle_sdr_type16(self, body):
        if DEBUG:
            print "Device Access Address: {}".format(body[0])
            print "Device Slave Address: {}".format(body[1])
            print "Access LUN / Bus ID: {}".format(body[2])
            print "Device Type: {}".format(body[5])
            print "Device Type Modifier: {}".format(body[6])
        else:
            print "Ignore SDR type: {0:#04x}".format(self.__sdr_type)

    # SDR Type 0x11
    def handle_sdr_type17(self, body):
        if DEBUG:
            print "Device Access Address: {}".format(body[0])
            print "FRU Device ID / Device Slave Address: {}".format(body[1])
            print "Logical-Physical / Access LUN / Bus ID: {}".format(body[2])
            print "Channel Number: {}".format(body[3])
            print "Device Type: {}".format(body[5])
            print "Device Type Modifier: {}".format(body[6])

        main_sdr_add_cmd = self.__format_main_sdr_add(body)

        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string(os.linesep)

    # SDR Type 0x12
    def handle_sdr_type18(self, body):
        if DEBUG:
            print "Device Slave Address: {}".format(body[0])
            print "Channel Number: {}".format(body[1])

        main_sdr_add_cmd = self.__format_main_sdr_add(body)

        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string(os.linesep)

    # SDR Type 0x13
    def handle_sdr_type19(self, body):
        if DEBUG:
            print "Device Slave Address: {}".format(body[0])
            print "Device ID: {}".format(body[1])
            print "Channel Number / Device Revision: {}".format(body[2])
        else:
            print "Ignore SDR type: {0:#04x}".format(self.__sdr_type)

    def handle_sdr_type20(self, body):
        print "Ignore type {}".format(self.__sdr_type)

    # SDR Type 0xC0
    def handle_sdr_type192(self, body):
        if DEBUG:
            print "Manufacture ID: {3} {2} {1} {0}".format(
                body[0], body[1], body[2], body[3])

        main_sdr_add_cmd = self.__format_main_sdr_add(body)

        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string(os.linesep)

    def handle_sdr_body(self, body_data):
        if not isinstance(body_data, list):
            raise TypeError("body_data is not list")

        record_type = self.__sdr_type
        # print body_data
        if record_type == 0x1 or \
                record_type == 0x2:  # Full Sensor Record and Compact Sensor Record
            self.handle_sdr_type1_2(body_data)
        elif record_type == 0x3:  # Event-Only Record
            self.handle_sdr_type3(body_data)
        elif record_type == 0x8:  # Entity Association Record
            self.handle_sdr_type8(body_data)
        elif record_type == 0x9:  # Device-relative Entity Association Record
            self.handle_sdr_type9(body_data)
        elif record_type == 0x10:  # Generic Device Locator Record
            self.handle_sdr_type16(body_data)
        elif record_type == 0x11:  # FRU Device Locator Record
            self.handle_sdr_type17(body_data)
        elif record_type == 0x12:  # Management Controller Device Locator Record
            self.handle_sdr_type18(body_data)
        elif record_type == 0x13:  # Management Controller Confirmation Record
            self.handle_sdr_type19(body_data)
        elif record_type == 0x14:
            self.handle_sdr_type20(body_data)
        elif record_type == 0xc0:  # OEM Record
            self.handle_sdr_type192(body_data)
        else:
            print "Unknown record type: {}".format(hex(record_type))

    def handle_sdr(self):
        try:
            with open(self.__sdr_file, "rb") as f:
                while True:
                    data = f.read(5)
                    if not data:
                        break

                    self.handle_header(data)

                    sdr_body = f.read(self.__sdr_len)
                    if not sdr_body:
                        break

                    sdr_body_array = map(hex, array.array('B', sdr_body))
                    self.handle_sdr_body(sdr_body_array)
        except Exception as ex:
            print "SDR exception: {}".format(ex)
            sys.exit(1)


def main():
    py_version = sys.version_info
    if not (py_version[0] is 2 and py_version[1] is 7):
        print "Warning: please install Python 2.7 first."
    return

    dump = False
    analysis = False
    auto = False
    target_emu_file = "node.emu"
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable Debug")
    parser.add_argument("-n", "--platform-name", action="store", required=False,
                        help="Target platform to be emulated.")

    subparsers = parser.add_subparsers(title="actions")
    parser_dump = subparsers.add_parser("dump", help="Dump raw data from server")
    parser_dump.set_defaults(which="dump")
    parser_dump.add_argument("-H", "--host", action="store", required=True,
                             help="Server BMC IP address")
    parser_dump.add_argument("-U", "--username", action="store", required=True,
                             help="Server BMC username")
    parser_dump.add_argument("-P", "--password", action="store", required=True,
                             help="Server BMC password")
    parser_dump.add_argument("-I", "--intf", action="store", default="lanplus",
                             help="Interface to use")
    parser_dump.add_argument("--fru-ids", action="store", required=False, nargs='*',
                             help="FRU ID")
    parser_dump.add_argument("--dest-folder", action="store", required=False, default=".",
                             help="Target folder for files generated.")
    parser_dump.add_argument("--ipmitool-path", action="store", required=False, default="ipmitool",
                             help="which version of ipmitool is selected to run")

    parser_analyze = subparsers.add_parser("analyze", help="Analyze raw data and generate EMU file")
    parser_analyze.set_defaults(which="analyze")
    parser_analyze.add_argument("--sdr-file", action="store", required=True,
                                help="SDR raw data file")
    parser_analyze.add_argument("--mc-file", action="store", required=True,
                                help="mc info file")
    parser_analyze.add_argument("--fru-files", action="store", nargs="*", required=True,
                                help="FRU raw data files, <id n>:<file n>")
    parser_analyze.add_argument("--target-emu-file", action="store", required=False,
                                help="Target emu file")
    parser_analyze.add_argument("--dest-folder", action="store", required=False, default=".",
                                help="Target folder for files generated.")

    parser_auto = subparsers.add_parser("auto", help="Dump raw data from server and generate EMU file")
    parser_auto.set_defaults(which="auto")
    parser_auto.add_argument("-H", "--host", action="store", required=True,
                             help="Server BMC IP address")
    parser_auto.add_argument("-U", "--username", action="store", required=True,
                             help="Server BMC username")
    parser_auto.add_argument("-P", "--password", action="store", required=True,
                             help="Server BMC password")
    parser_auto.add_argument("-I", "--intf", action="store", default="lanplus",
                             help="Interface to use")

    parser_auto.add_argument("--dest-folder", action="store", required=False, default=".",
                             help="Target folder for files generated.")
    parser_auto.add_argument("--target-emu-file", action="store", required=False,
                             help="Target emu file")
    parser_auto.add_argument("--ipmitool-path", action="store", required=False, default="ipmitool",
                             help="which version of ipmitool is selected to run")

    args = parser.parse_args()
    if args.which == "auto":
        print "this is auto (dump and analyze) sub-command"
        auto = True
    elif args.which == "dump":
        print "This is dump sub-command"
        dump = True
    elif args.which == "analyze":
        print "This is analyze sub-command"
        analysis = True
    else:
        raise Exception("Unknown sub-command {}".format(args.which))

    global DEBUG
    if args.verbose:
        DEBUG = args.verbose

    header_obj = Header()
    fru_obj = FRU()
    sdr_obj = SDR()
    mc_obj = MC()
    sel_obj = SEL()

    dest_folder = args.dest_folder
    if not os.path.exists(dest_folder):
        os.mkdir(dest_folder)

    if args.platform_name:
        header_obj.platform_name = args.platform_name

    if dump or auto:
        host = args.host
        user = args.username
        password = args.password

        fru_obj.set_ipmitool(args.ipmitool_path, args.intf)
        sdr_obj.set_ipmitool(args.ipmitool_path, args.intf)
        mc_obj.set_ipmitool(args.ipmitool_path, args.intf)

        fru_obj.set_bmc_info(host, user, password)
        sdr_obj.set_bmc_info(host, user, password)
        mc_obj.set_bmc_info(host, user, password)

        if dump and args.fru_ids:
            file_dict = {}
            for fru_id in args.fru_ids:
                target_file = os.path.join(dest_folder, "fru{}.bin".format(fru_id))
                fru_obj.dump_fru(fru_id, target_file)
                file_dict[fru_id] = target_file
                print "FRU {0} saved to file {1}".format(fru_id, target_file)
            fru_obj.set_file_dict(file_dict)
        else:
            fru_obj.dump_frus(dest_folder)

        target_sdr_file = os.path.join(dest_folder, "sdr.bin")
        sdr_obj.dump_sdr(target_sdr_file)
        sdr_obj.set_file(target_sdr_file)
        print "SDR data saved to file {}".format(target_sdr_file)

        target_mc_file = os.path.join(dest_folder, "mc.txt")
        mc_obj.dump_mc_info(target_mc_file)
        mc_obj.set_file(target_mc_file)
        print "MC info saved to file {}".format(target_mc_file)

    if analysis:
        file_dict = {}
        for fru_info in args.fru_files:
            fru_id, fru_file = fru_info.split(":")
            fru_id = int(fru_id.strip())
            fru_file = fru_file.strip()
            file_dict[fru_id] = fru_file
        fru_obj.set_file_dict(file_dict)
        sdr_obj.set_file(args.sdr_file)
        mc_obj.set_file(args.mc_file)

    if analysis or auto:
        if args.target_emu_file is not None:
            target_emu_file = args.target_emu_file

        header_obj.handle_header_comments()
        mc_obj.handle_mc_info()
        sel_obj.handle_sel()
        fru_obj.handle_fru()
        sdr_obj.handle_sdr()
        mc_obj.handle_sensor_owner_list(sdr_obj.get_sensor_list())

        target_emu_file = os.path.join(dest_folder, target_emu_file)
        with open(target_emu_file, "w") as f:
            f.write(header_obj.get_string())
            f.write(mc_obj.get_string())
            f.write(sel_obj.get_string())
            f.write(fru_obj.get_string())
            f.write(sdr_obj.get_string())
        print "Generated EMU file {}".format(target_emu_file)


if __name__ == '__main__':
    main()
