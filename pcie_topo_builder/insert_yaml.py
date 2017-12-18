#!/usr/bin/env python

'''
**************************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
**************************************************************
'''
# -*- encoding: utf-8 -*-

import os
import yaml
import argparse

def parse_args():
    description = "usage: insert yaml file"
    parser = argparse.ArgumentParser(description = description)

    help = "source yaml file."
    parser.add_argument('-S', '--source_yaml', type=str, help=help)

    help = "target yaml file."
    parser.add_argument('-T', '--target_yaml', type=str, help=help, default='infrasim.yml')

    help = 'output yaml file.'
    parser.add_argument('-O', '--output_yaml', type=str, help=help, default='output.yml')

    help = '[Add or Replace] which element to be copied from source yaml to target yaml'
    parser.add_argument('-E', '--insert_element', nargs='+', type=str, help=help)

    help = '[Merge] which element to be copied from source yaml to target yaml'
    parser.add_argument('-M', '--merge_element', nargs='+', type=str, help=help)

    args = parser.parse_args();
    return args

def main():
    print "++++++++++++++++++++++++++++++++++++++++++++++"
    print "++++++++++++++ insert yaml file ++++++++++++++"
    print "++++++++++++++++++++++++++++++++++++++++++++++"

    # get args
    args = parse_args()
    source_file = args.source_yaml
    target_file = args.target_yaml
    output_file = args.output_yaml
    insert_element_list = args.insert_element
    merge_element_list = args.merge_element

    if not insert_element_list:
        print "Need elements!"
        return

    # open source file
    with open(source_file, 'r') as f:
        s_info = yaml.load(f)

    # open target file
    with open(target_file, 'r') as f:
        t_info = yaml.load(f)

    compute_dict = t_info['compute']
    # add element to target file

    if insert_element_list:
        for insert_element in insert_element_list:
            if insert_element in s_info:
                if not compute_dict.has_key(insert_element):
                    print "{} is [added]".format(insert_element)
                else:
                    print "{} is [replaced]".format(insert_element)

                compute_dict[insert_element] = s_info[insert_element]

    # merge element to target file
    if merge_element_list:
        for merge_element in merge_element_list:
            if merge_element in s_info:
                if not compute_dict.has_key(merge_element):
                    print "{} is [added]".format(merge_element)
                else:
                    print "{} is [merge]".format(merge_element)

                compute_dict[merge_element] += s_info[merge_element]


    # dump to output file
    with open(output_file, "w") as f:
        yaml.dump(t_info, f, default_flow_style=False)


if __name__ == '__main__':
    main()
