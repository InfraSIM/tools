#!/usr/bin/env python
"""
    Data structure define
"""
__author__ = 'Robert.Xia, Payne.Wang'

import os
import subprocess
import array
import struct
import sys
import re
import argparse

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

    def __call__(self):
        return self._string()

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


class MC(Base):
    def __init__(self):
        super(MC, self).__init__()
        self.mc_file = ""
        self.additional_device_support_flags = 0
        self.has_device_sdr = False

    def set_file(self, mc_file):
        self.mc_file = mc_file

    def dump_mc_info(self, host, user, password, target_file):
        if host is None or password is None or password is None:
            raise ValueError("Missing host information")

        ipmitool_mc_command = "ipmitool -I lanplus -U {user} -P {password} -H {host} mc info > {target_file}".\
            format(user=user, password=password, host=host, target_file=target_file)

        command_exit_status, command_output = self.run_command(ipmitool_mc_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)
        if command_exit_status != 0:
            raise ValueError("Command {} failed.".format(ipmitool_mc_command))

    def handle_mc_info(self):
        with open(self.mc_file) as f:
            for line in f.readlines():
                if "Device ID" in line:
                    self.device_id = line.split(":")[1].strip()
                elif "Device Revision" in line:
                    self.device_revision = line.split(":")[1].strip()
                elif "Firmware Revision" in line:
                    firmware_version = line.split(":")[1].strip().split(".")
                    self.fw_major = firmware_version[0]
                    self.fw_minor = firmware_version[1]
                elif "Manufacturer ID" in line:
                    self.manufacutre_id = line.split(":")[1].strip()
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
                   mfg_id=hex(int(self.manufacutre_id)),
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
        self.file_dict = {}

    def set_file_dict(self, file_dict=None):
        self.file_dict = file_dict

    def dump_fru(self, host, user, password, fru_id, target_file):
        if host is None or password is None or password is None:
            raise ValueError("Missing host information")

        ipmitool_fru_command = "ipmitool -I lanplus -U {user} -P {password} -H {host} fru read {id} {target_file}".\
            format(user=user, password=password, host=host, id=fru_id, target_file=target_file)

        command_exit_status, command_output = self.run_command(ipmitool_fru_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)
        if command_exit_status != 0:
            raise ValueError("Command {} failed.".format(ipmitool_fru_command))


    def __get_fru_ids(self, host, user, password):
        if host is None or user is None or password is None:
            raise ValueError("Missing host info.")

        ipmitool_fru_command = "ipmitool -I lanplus -U {user} -P {password} -H {host} fru".format(
            user=user, password=password, host=host
        )
        command_exit_status, command_output = self.run_command(ipmitool_fru_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)


        if command_exit_status != 0:
            raise ValueError("Command {} failed [exit code: {}].".format(ipmitool_fru_command, command_exit_status))

        id_list = []
        for line in command_output.split(os.linesep):
            re_obj = re.search("^FRU Device Description : .* \(ID (\d+)\)", line)
            if re_obj:
                id_list.append(int(re_obj.group(1)))

        return id_list


    def dump_frus(self, host, user, password):
        file_dict = {}
        for id in self.__get_fru_ids(host, user, password):
            target_file = "fru{}.bin".format(id)
            self.dump_fru(host, user, password, id, target_file)
            file_dict[id] = target_file
        return file_dict


    def read_fru_data(self, fru_id, fru_file):
        count = 0
        file_size = os.stat(fru_file)[6]
        self._string.add_string("# add FRU {}".format(fru_id))
        self._string.add_string("mc_add_fru_data {mc:#04x} {id:#04x} {size:#x} data \\{linesep}".
                                format(mc=MC_ADDRESS, id=fru_id, size=file_size, linesep=os.linesep))
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
        for fru_id, fru_file in self.file_dict.items():
            self.read_fru_data(fru_id, fru_file)

class SDR(Base):
    def __init__(self):
        super(SDR, self).__init__()
        self.__sdr_file = ""
        self.__sdr_type = None
        self.__sdr_len = None

    def set_file(self, sdr_file=None):
        self.__sdr_file = sdr_file

    def dump_sdr(self, host, user, password, target_file):
        if host is None or user is None or password is None:
            raise ValueError("Missing host info")

        ipmitool_sdr_command = "ipmitool -I lanplus -U {user} -P {password} -H {host} sdr dump {tf}".format(
            user=user, password=password, host=host, tf=target_file)

        command_exit_status, command_output = self.run_command(ipmitool_sdr_command,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE)


        if command_exit_status != 0:
            raise ValueError("Command {} failed [exit code: {}].".format(
                ipmitool_sdr_command, command_exit_status))

    def print_sdr_header(self, header):
        print "-----TYPE {}-----".format(hex(header[2]))
        print "Record ID: {0}".format(hex(header[0]))
        print "SDR Version: {}".format(hex(header[1]))
        print "Record Type: {}".format(hex(header[2]))
        print "Record Length: {}".format(hex(header[3]))
        print

    def handle_header(self, data):
        header = struct.unpack("HBBB", data)
        if header[1] != 0x51:
            raise ValueError("Invalid SDR header")

        self.__sdr_type = header[2]
        self.__sdr_len = header[3]

        if DEBUG:
            self.print_sdr_header(header)

    # SDR Type 0x1
    def handle_sdr_type1(self, body):
        sensor_owner_id = int(body[0x0], 16)

        if sensor_owner_id != MC:
            return

        channel = (int(body[1], 16) & 0xf0) >> 4
        lun = int(body[1], 16) & 0x3
        sensor_number = body[2]
        sensor_type = int(body[7], 16)
        event_reading_code = int(body[8], 16)
        threshold_access_support = (int(body[6], 16) & 0xc) >> 2
        settable_threshold_mask = int(body[14], 16)
        readable_threshold_mask = int(body[13], 16)

        unr_thres = int(body[31], 16)
        uc_thres = int(body[32], 16)
        unc_thres = int(body[33], 16)
        lnr_thres = int(body[34], 16)
        lc_thres = int(body[35], 16)
        lnc_thres = int(body[36], 16)

        assertion_event_mask = ((int(body[10], 16) << 8) | int(body[9], 16)) & 0xfff
        deassertion_event_mask = ((int(body[12], 16) << 8) | int(body[11], 16)) & 0xfff

        sensor_event_message_control_support = int(body[6], 16) & 0x3

        events_enable_bit = (int(body[5], 16) & 0x2) >> 1
        scanning_enable_bit = int(body[5], 16) & 0x1

        if DEBUG:
            print "Sensor Owner ID: {}".format(hex(sensor_owner_id))
            print "Sensor Owner LUN (channel/LUN): {}/{}".format(channel, lun)
            print "Sensor Number: {}".format(sensor_number)
            print "Sensor Type: {}".format(sensor_type)
            print "Event / Reading Type Code: {}".format(hex(event_reading_code))
            print "Threshold Access Support: {:#x}".format(threshold_access_support)
            print "Settable Threshold Mask: {:06b}".format(settable_threshold_mask)
            print "Readable Threshold Mask: {:06b}".format(readable_threshold_mask)
            print "Assertion Event Mask/Lower Threshold Reading Mask: {0:015b}".format(assertion_event_mask)
            print "Deassertion Event Mask/Upper Threshold Reading Mask: {0:015b}".format(deassertion_event_mask)
            print "Sensor Event Message Control Support: {0:#x}".format(sensor_event_message_control_support)
            print "Sensor Initialization: {}".format(body[5])

        # sensor_add
        sensor_add_cmd = "sensor_add {mc} {lun} {sensor_num} {sensor_type:#04x} {event_reading_code:#04x}".\
            format(mc=hex(sensor_owner_id),
                   lun=hex(lun),
                   sensor_num=sensor_number,
                   sensor_type=sensor_type,
                   event_reading_code=event_reading_code)

        # main_sdr_add_cmd
        main_sdr_add_cmd = "main_sdr_add {mc} \\\n".format(mc=hex(sensor_owner_id))

        # add header
        header = [0x00, 0x00, 0x51, 0x01, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count = 0
        for data in body:
            count += 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)

        # main_sdr_add_cmd += "\n"

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
            scanning="scanning"
        else:
            scanning="no-scanning"

        if event_reading_code == 0x1: # threshold-based sensor
            set_threshold_command = "sensor_set_threshold {mc} {lun} {sensor_num} " \
                "{support} {enable:06b} {v5:#04x} {v4:#04x} {v3:#04x} {v2:#04x} {v1:#04x} {v0:#04x}".\
                format(mc=hex(sensor_owner_id),
                       lun=hex(lun),
                       sensor_num=sensor_number,
                       support=threshold_support,
                       enable=settable_threshold_mask,
                       v5=unr_thres,
                       v4=uc_thres,
                       v3=unc_thres,
                       v2=lnr_thres,
                       v1=lc_thres,
                       v0=lnc_thres)
            #set_threshold_command += "\n"

            set_value_command = "sensor_set_value {mc} {lun} {sn} 0x0 {enable}"\
                .format(mc=hex(sensor_owner_id),
                        lun=hex(lun),
                        sn=sensor_number,
                        enable=hex(events_enable_bit))
        else:
            print "--------------<Non threshold-based sensor {0:#x}>---------------------".format(event_reading_code)


        set_event_support_cmd = "sensor_set_event_support {mc} {lun} {sensor_num} {events_enable} {scanning} {event_support} {assert_support:015b} {deassert_support:015b} {assert_enable:015b} {deassert_enable:015b}".\
            format(mc=hex(sensor_owner_id),
                   lun=hex(lun),
                   sensor_num=sensor_number,
                   events_enable=events_enable,
                   scanning=scanning,
                   event_support=event_support,
                   assert_support=assertion_event_mask,
                   deassert_support=deassertion_event_mask,
                   assert_enable=assertion_event_mask,
                   deassert_enable=deassertion_event_mask)
        #print sensor_add_cmd
        #print main_sdr_add_cmd
        #print set_threshold_command
        #print set_event_support_cmd
        #print
        comments="# Add sensor {}\n".format(sensor_number)
        self._string.add_string(comments)
        self._string.add_string([sensor_add_cmd,
                                      main_sdr_add_cmd,
                                      set_value_command,
                                      set_threshold_command,
                                      set_event_support_cmd])
        self._string.add_string("\n")


# SDR Type 0x2
    def handle_sdr_type2(self, body):
        sensor_owner_id = int(body[0x0], 16)
        if sensor_owner_id != MC_ADDRESS:
            return

        channel = (int(body[1], 16) & 0xf0) >> 4
        lun = int(body[1], 16) & 0x3
        sensor_number = body[2]
        sensor_type = int(body[7], 16)
        event_reading_code = int(body[8], 16)

        assertion_event_mask = ((int(body[10], 16) << 8) | int(body[9], 16)) & 0x7fff
        deassertion_event_mask = ((int(body[12], 16) << 8) | int(body[11], 16)) & 0x7fff
        threshold_access_support = (int(body[6], 16) & 0xc) >> 2


        events_enable_bit = (int(body[5], 16) & 0x2) >> 1
        scanning_enable_bit = int(body[5], 16) & 0x1

        sensor_event_message_control_support = int(body[6], 16) & 0x3

        if DEBUG:
            print "Sensor Owner ID: {}".format(hex(sensor_owner_id))
            print "Sensor Owner LUN (channel/LUN): {}/{}".format(channel, lun)
            print "Sensor Number: {}".format(sensor_number)
            print "Sensor Type: {}".format(sensor_type)
            print "Event / Reading Type Code: {}".format(hex(event_reading_code))
            print "Assertion Event Mask/Lower Threshold Reading Mask: {0:015b}".format(assertion_event_mask)
            print "Deassertion Event Mask/Upper Threshold Reading Mask: {0:015b}".format(deassertion_event_mask)
            print "Threshold Access Support: {:#x}".format(threshold_access_support)

        # sensor_add
        sensor_add_cmd = "sensor_add {mc} {lun} {sensor_num} {sensor_type:#04x} {event_reading_code:#04x}".\
            format(mc=hex(sensor_owner_id),
                   lun=hex(lun),
                   sensor_num=sensor_number,
                   sensor_type=sensor_type,
                   event_reading_code=event_reading_code)

        # main_sdr_add_cmd
        main_sdr_add_cmd = "main_sdr_add {mc} \\\n".format(mc=hex(sensor_owner_id))

        # append header
        header = [0x00, 0x00, 0x51, 0x02, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count=0;
        for data in body:
            count = count + 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)


        if events_enable_bit:
            events_enable = "enable"
        else:
            events_enable = "disable"

        if scanning_enable_bit:
            scanning="scanning"
        else:
            scanning="no-scanning"

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

        set_event_support_cmd = "sensor_set_event_support {mc} {lun} {sensor_num} {events_enable} {scanning} {event_support} {assert_support:015b} {deassert_support:015b} {assert_enable:015b} {deassert_enable:015b}".\
            format(mc=hex(sensor_owner_id),
                   lun=hex(lun),
                   sensor_num=sensor_number,
                   events_enable=events_enable,
                   scanning=scanning,
                   event_support=event_support,
                   assert_support=assertion_event_mask,
                   deassert_support=deassertion_event_mask,
                   assert_enable=assertion_event_mask,
                   deassert_enable=deassertion_event_mask)

        #print sensor_add_cmd
        #print main_sdr_add_cmd
        #print set_event_support_cmd
        #print
        comments="# Add sensor {}\n".format(sensor_number)
        self._string.add_string(comments)
        self._string.add_string([sensor_add_cmd, main_sdr_add_cmd, set_event_support_cmd])
        self._string.add_string("\n")


# SDR Type 0x3
    def handle_sdr_type3(self, body):
        sensor_owner_id = int(body[0x0], 16)
        if sensor_owner_id != MC_ADDRESS:
            return

        channel = (int(body[1], 16) & 0xf0) >> 4
        fru_inventory_device_owner_lun = (int(body[1], 16) & 0xc) >> 2
        lun = int(body[1], 16) & 0x3
        sensor_number = body[2]
        sensor_type = int(body[5], 16)
        event_reading_code = int(body[8], 16)
        if DEBUG:
            print "Sensor Owner ID: {}".format(hex(sensor_owner_id))
            print "Sensor Owner LUN (channel/fru inverntory LUN/LUN): {}/{}/{}".format(channel, fru_inventory_device_owner_lun, lun)
            print "Sensor Number: {}".format(sensor_number)
            print "Sensor Type: {}".format(sensor_type)
            print "Event / Reading Type Code: {}".format(hex(event_reading_code))

        sensor_add_cmd = "sensor_add {mc} {lun} {sensor_num} {sensor_type:#04x} {event_reading_code:#04x}".\
            format(mc=hex(sensor_owner_id),
                   lun=hex(lun),
                   sensor_num=sensor_number,
                   sensor_type=sensor_type,
                   event_reading_code=event_reading_code)

        # main_sdr_add_cmd
        main_sdr_add_cmd = "main_sdr_add {mc} \\\n".format(mc=hex(sensor_owner_id))

        # append header
        header = [0x00, 0x00, 0x51, 0x03, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count=0;
        for data in body:
            count = count + 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)

        #print sensor_add_cmd
        #print main_sdr_add_cmd
        #print
        comments="# Add sensor {}\n".format(sensor_number)
        self._string.add_string(comments)
        self._string.add_string([sensor_add_cmd, main_sdr_add_cmd])
        self._string.add_string("\n")

# SDR Type 0x8
    def handle_sdr_type8(self, body):
        print "Container Entity ID: {}".format(body[0])
        print "Container Entity Instance: {}".format(body[1])
        print "Flags: {}".format(body[2])
        print "Contained Entity 1/Range 1 Entity: {}".format(body[3])
        print "Contained Entity 1 Instance/Range 1 first entity instance: {}".format(body[4])


# SDR Type 0x9
    def handle_sdr_type9(self, body):
        print "Container Entity ID: {}".format(body[0])
        print "Container Entity Instance: {}".format(body[1])
        print "Container Entity Device Address {}".format(body[2])
        print "Container Entity Device Channel {}".format(body[3])

# SDR Type 0x10
    def handle_sdr_type16(self, body):
        print "Device Access Address: {}".format(body[0])
        print "Device Slave Address: {}".format(body[1])
        print "Access LUN / Bus ID: {}".format(body[2])
        print "Device Type: {}".format(body[5])
        print "Device Type Modifier: {}".format(body[6])


# SDR Type 0x11
    def handle_sdr_type17(self, body):
        if DEBUG:
            print "Device Access Address: {}".format(body[0])
            print "FRU Device ID / Device Slave Address: {}".format(body[1])
            print "Logical-Physical / Access LUN / Bus ID: {}".format(body[2])
            print "Channel Number: {}".format(body[3])
            print "Device Type: {}".format(body[5])
            print "Device Type Modifier: {}".format(body[6])

        device_access_address = int(body[0], 16)
        if device_access_address != MC_ADDRESS:
            return

        lun = (int(body[2], 16) & 0xc) >> 2
        main_sdr_add_cmd = "main_sdr_add {addr:#04x} \\\n".format(addr=device_access_address)

        # append header
        header = [0x00, 0x00, 0x51, 0x11, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count=0;
        for data in body:
            count = count + 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)

        #print main_sdr_add_cmd
        #print
        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string("\n")

# SDR Type 0x12
    def handle_sdr_type18(self, body):
        if DEBUG:
            print "Device Slave Address: {}".format(body[0])
            print "Channel Number: {}".format(body[1])
        device_access_address = int(body[0], 16)
        if device_access_address != MC_ADDRESS:
            return

        main_sdr_add_cmd = "main_sdr_add {addr:#04x} \\\n".format(addr=device_access_address)

        # append header
        header = [0x00, 0x00, 0x51, 0x12, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count=0;
        for data in body:
            count = count + 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)

        #print main_sdr_add_cmd
        #print
        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string("\n")


    # SDR Type 0x13
    def handle_sdr_type19(self, body):
        print "Device Slave Address: {}".format(body[0])
        print "Device ID: {}".format(body[1])
        print "Channel Number / Device Revision: {}".format(body[2])

    # SDR Type 0xC0
    def handle_sdr_type192(self, body):
        if DEBUG:
            print "Manufacture ID: {3} {2} {1} {0}".format(body[0], body[1], body[2], body[3])


        main_sdr_add_cmd = "main_sdr_add 0x20 \\\n"
        header = [0x00, 0x00, 0x51, 0xc0, len(body)]
        for data in header:
            main_sdr_add_cmd += "{0:#04x} ".format(data)
        main_sdr_add_cmd += "\\{}".format(os.linesep)

        count=0;
        for data in body:
            count = count + 1
            main_sdr_add_cmd += "{0:#04x} ".format(int(data, 16))
            if count % 16 == 0 and count != len(body):
                main_sdr_add_cmd += "\\{}".format(os.linesep)

        #print main_sdr_add_cmd
        #print
        self._string.add_string(main_sdr_add_cmd)
        self._string.add_string("\n")

    def handle_sdr_body(self, body_data):
        if not isinstance(body_data, list):
            raise TypeError("body_data is not list")

        record_type = self.__sdr_type
        # print body_data
        if record_type == 0x1: # Full Sensor Record
            self.handle_sdr_type1(body_data)
        elif record_type == 0x2: # Compact Sensor Record
            self.handle_sdr_type2(body_data)
        elif record_type == 0x3: # Event-Only Record
            self.handle_sdr_type3(body_data)
        elif record_type == 0x8: # Entity Assocaiation Record
            self.handle_sdr_type8(body_data)
        elif record_type == 0x9: # Device-relative Entity Association Record
            self.handle_sdr_type9(body_data)
        elif record_type == 0x10: # Generic Device Locator Record
            self.handle_sdr_type16(body_data)
        elif record_type == 0x11: # FRU Device Locator Record
            self.handle_sdr_type17(body_data)
        elif record_type == 0x12: # Management Controller Device Locator Record
            self.handle_sdr_type18(body_data)
        elif record_type == 0x13: # Management Controller Confirmation Record
            self.handle_sdr_type19(body_data)
        elif record_type == 0xc0: # OEM Record
            self.handle_sdr_type192(body_data)
        else:
            print "Unknow record type: {}".format(hex(record_type))


    def read_data(self):
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
            print "Exception: {}".format(ex)
            sys.exit(1)


def main():
    dump = False
    analysis = False
    auto = False
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable Debug")

    subparsers = parser.add_subparsers(title="actions")
    # parser.set_defaults(which="dump")
    parser_dump = subparsers.add_parser("dump", help="Dump raw data from server")
    parser_dump.set_defaults(which="dump")
    parser_dump.add_argument("-H", "--host", action="store", required=True, help="Server IP address")
    parser_dump.add_argument("-U", "--username", action="store", required=True, help="Server username")
    parser_dump.add_argument("-P", "--password", action="store", required=True, help="Server password")
    parser_dump.add_argument("--fru_ids", action="store",  required=False, help="FRU ID")

    parser_analyze = subparsers.add_parser("analyze", help="Analyze raw data and generate EMU file")
    parser_analyze.set_defaults(which="analyze")
    parser_analyze.add_argument("--sdr_file", action="store", required=True, help="SDR raw data file")
    parser_analyze.add_argument("--mc_file", action="store", required=True, help="mc info file")
    parser_analyze.add_argument("--fru_files", action="store", required=True, help="FRU raw data file")

    parser_auto = subparsers.add_parser("auto", help="Dump raw data from server and generate EMU file")
    parser_auto.set_defaults(which="auto")
    parser_auto.add_argument("-H", "--host", action="store", required=True, help="Server IP address")
    parser_auto.add_argument("-U", "--username", action="store", required=True, help="Server username")
    parser_auto.add_argument("-P", "--password", action="store", required=True, help="Server password")
    # parser_dump.add_argument("--fru_id", action="store",  nargs='?', help="FRU ID")

    args = parser.parse_args()
    if args.which == "auto":
        print "this is dump and analyze sub-command"
        auto = True
    elif args.which == "dump":
        print "This is dump sub-command"
        dump = True
    elif args.which == "analyze":
        print "This is analyze sub-command"
        analysis = True
    else:
        raise Exception("Unknown sub-command {}".format(args.which))

    fru_obj = FRU()
    sdr_obj = SDR()
    mc_obj = MC()
    sel_obj = SEL()

    if dump or auto:
        host = args.host
        user = args.username
        password = args.password
        # fru_ids = args.fru_ids
        file_dict = {}
        if dump and args.fru_ids:
            for fru_id in args.fru_ids.split():
                target_file = "fru{}.bin".format(fru_id)
                fru_obj.dump_fru(host, user, password, fru_id, target_file)
                file_dict[fru_id] = target_file
        else:
            file_dict = fru_obj.dump_frus(host, user, password)
        fru_obj.set_file_dict(file_dict)

        target_sdr_file = "sdr.bin"
        sdr_obj.dump_sdr(host, user, password, target_sdr_file)
        sdr_obj.set_file(target_sdr_file)

        target_mc_file = "mc.txt"
        mc_obj.dump_mc_info(host, user, password, target_mc_file)
        mc_obj.set_file(target_mc_file)

    if analysis:
        file_dict = {}
        for fru_info in args.fru_files.split(","):
            fru_id, fru_file = fru_info.split(":")
            fru_id = int(fru_id.strip())
            fru_file = fru_file.strip()
            file_dict[fru_id] = fru_file
        fru_obj.set_file_dict(file_dict)
        sdr_obj.set_file(args.sdr_file)
        mc_obj.set_file(args.mc_file)

    if analysis or auto:
        mc_obj.handle_mc_info()
        # print mc_obj.get_string()

        sel_obj.handle_sel()
        # print sel_obj.get_string()

        fru_obj.handle_fru()
        # print fru_obj.get_string()

        sdr_obj.read_data()
        # print sdr_obj.get_string()

        with open("node.emu", "w") as f:
            f.write(mc_obj.get_string())
            f.write(sel_obj.get_string())
            f.write(fru_obj.get_string())
            f.write(sdr_obj.get_string())


if __name__ == '__main__':
    main()
