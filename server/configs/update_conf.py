#!/usr/bin/env python3

import os
import argparse
import configparser

def print_message(message_to_print, verbose):
    if verbose:
        print(message_to_print)

if __name__ == "__main__":

    # parse parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',help='Display Info Messages', type=int, default=1, choices=[0, 1])
    parser.add_argument('-b', '--backup',help='Create Config Backup', type=int, default=1, choices=[0, 1])
    args = parser.parse_args()
    if args.verbose == 1:
        verbose = True
    else:
        verbose = False
    if args.backup == 1:
        backup = True
    else:
        backup = False

    config_file_server = os.path.join(os.environ['D4_HOME'], 'configs/server.conf')
    config_file_sample = os.path.join(os.environ['D4_HOME'], 'configs/server.conf.sample')
    config_file_backup = os.path.join(os.environ['D4_HOME'], 'configs/server.conf.backup')

    # Check if confile file exist
    if not os.path.isfile(config_file_server):
        # create config file
        with open(config_file_server, 'w') as configfile:
            with open(config_file_sample, 'r') as config_file_sample:
                configfile.write(config_file_sample.read())
        print_message('Config File Created', verbose)
    else:
        config_server = configparser.ConfigParser()
        config_server.read(config_file_server)
        config_sections = config_server.sections()

        config_sample = configparser.ConfigParser()
        config_sample.read(config_file_sample)
        sample_sections = config_sample.sections()

        mew_content_added = False
        for section in sample_sections:
            new_key_added = False
            if section not in config_sections:
                # add new section
                config_server.add_section(section)
                mew_content_added = True
            for key in config_sample[section]:
                if key not in config_server[section]:
                    # add new section key
                    config_server.set(section, key, config_sample[section][key])
                    if not new_key_added:
                        print_message('[{}]'.format(section), verbose)
                        new_key_added = True
                        mew_content_added = True
                    print_message('    {} = {}'.format(key, config_sample[section][key]), verbose)

        # new keys have been added to config file
        if mew_content_added:
            # backup config file
            if backup:
                with open(config_file_backup, 'w') as configfile:
                    with open(config_file_server, 'r') as configfile_origin:
                        configfile.write(configfile_origin.read())
                print_message('New Backup Created', verbose)
            # create new config file
            with open(config_file_server, 'w') as configfile:
                config_server.write(configfile)
            print_message('Config file updated', verbose)
        else:
            print_message('Nothing to update', verbose)
