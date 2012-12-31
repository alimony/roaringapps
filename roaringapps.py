#!/usr/bin/env python
# encoding: utf-8
'''
roaringapps.py

This script will look for installed applications on your computer, and check
each found application for compatibility with recent versions of Mac OS X,
based on data from http://roaringapps.com

Created by Markus Amalthea Magnuson.
'''

import argparse
import os
import sys
import time
import shelve
import subprocess
import urllib2
import json


ROARING_APPS_JSON_URL = 'http://static.roaringapps.com/all.json'
DEFAULT_APP_FOLDERS = ['/Applications', '~/Applications']

CACHE_FILE = 'cache'
MAX_CACHE_AGE_IN_SECONDS = 60 * 60
INSTALLED_APPLICATIONS_KEY = 'installed_applications'
COMPATIBILITY_DATA_KEY = 'compatibility_data'

LION_STATUSES = {
    '0': 'Unknown',
    '1': 'Untested',
    '2': 'OK',
    '3': 'Some problems',
    '4': 'Does not work'
}

MOUNTAIN_LION_STATUSES = {
    'unknown':       'Unknown',
    'works_fine':    'OK',
    'some_problems': 'Some problems',
    'doesnt_work':   'Does not work'
}

def main():
    # When combining the add_argument action 'append' and a default value that
    # is a list, argparse will oddly enough always add that default list to
    # the final variable instead of actually overriding the default. This is
    # sort of by design, see http://bugs.python.org/issue16399
    # We don't want that, so we'll override it ourselves.
    if not args.APPFOLDERS:
        args.APPFOLDERS = DEFAULT_APP_FOLDERS

    if args.ONLY_PRINT_LION_DATA and args.ONLY_PRINT_MOUNTAIN_LION_DATA:
        print >> sys.stderr, 'You can’t combine the -l and -m flags; they are mutually exclusive.'
        sys.exit(1)

    if args.ONLY_PRINT_LION_DATA:
        print_lion_message('Only checking for Mac OS X 10.7 (Lion) compatibility data.')
    elif args.ONLY_PRINT_MOUNTAIN_LION_DATA:
        print_mountain_lion_message('Only checking for Mac OS X 10.8 (Mountain Lion) compatibility data.')

    if cache_is_outdated() or args.REFRESH_CACHE:
        installed_applications = get_installed_applications()
        compatibility_data = get_compatibility_data()
    else:
        installed_applications = get_cached_applications()
        compatibility_data = get_cached_compatibility_data()

    installed_applications.sort()
    number_of_applications = len(installed_applications)

    if number_of_applications == 0:
        print_message('Found no installed applications, exiting.')
        print_wrapper_message('found_no_installed_applications')
        sys.exit(0)

    print_message('Found %d installed application%s.' % (number_of_applications, 's'[number_of_applications == 1:]))
    print_wrapper_message('found_number_of_installed_application\t%d' % number_of_applications)

    remote_application_names = dict([(value['title'], key) for (key, value) in compatibility_data.items()])

    if args.VERBOSE:
        print_message('Displaying compatibility data for all installed applications.')
    else:
        print_message('Only displaying incompatible applications.')

    number_of_incompatible_applications = 0
    for application_name in installed_applications:
        if application_name in remote_application_names:
            application_data = compatibility_data[remote_application_names[application_name]]
            lion_status = LION_STATUSES[application_data['status']]
            lion_ok = lion_status == 'OK'
            mountain_lion_status = MOUNTAIN_LION_STATUSES[application_data['mtn_status']]
            mountain_lion_ok = mountain_lion_status == 'OK'

            print_name_verbosely = (args.ONLY_PRINT_LION_DATA and lion_ok) or \
                                   (args.ONLY_PRINT_MOUNTAIN_LION_DATA and mountain_lion_ok) or \
                                   (lion_ok and mountain_lion_ok)
            print_message('\n%s:' % application_name, print_name_verbosely)
            print_lion_message('Mac OS X 10.7 (Lion): %s' % lion_status, lion_ok)
            print_mountain_lion_message('Mac OS X 10.8 (Mountain Lion): %s' % mountain_lion_status, mountain_lion_ok)
            print_wrapper_message('compatibility_data_found\t%s\t%s\t%s\t%s\t%s\t%s' % (
                application_data['title'],
                application_data['status'],
                application_data['mtn_status'],
                application_data['url'],
                application_data['developer_name'],
                application_data['icon']
            ))
            if not print_name_verbosely:
                number_of_incompatible_applications += 1
        else:
            print_message('\nFound no compatibility data for %s' % application_name, verbose=True)
            print_wrapper_message('compatibility_data_not_found\t%s' % application_name)

    print_message('\nFound %d incompatible application%s.' % (number_of_incompatible_applications, 's'[number_of_incompatible_applications == 1:]))
    print_wrapper_message('found_number_of_incompatible_applications\t%d' % number_of_incompatible_applications)

def get_argument_parser():
    parser = argparse.ArgumentParser(
        description='''Check which of your installed applications are compatible
        with the most recent versions of Mac OS X. Powered by roaringapps.com.'''
    )

    parser.add_argument(
        '-a', '--app-folder',
        action='append',
        help='''Folders to scan for installed applications. Can be specified
        several times. Defaults to /Applications and ~/Applications.''',
        metavar='APPFOLDER',
        dest='APPFOLDERS'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help='Show complete compatibility data, not just incompatible applications.',
        dest='VERBOSE'
    )

    parser.add_argument(
        '-l', '--lion-only',
        action='store_true',
        default=False,
        help='Only show Mac OS X 10.7 (Lion) compatibility data.',
        dest='ONLY_PRINT_LION_DATA'
    )

    parser.add_argument(
        '-m', '--mountain-lion-only',
        action='store_true',
        default=False,
        help='Only show Mac OS X 10.8 (Mountain Lion) compatibility data.',
        dest='ONLY_PRINT_MOUNTAIN_LION_DATA'
    )

    parser.add_argument(
        '-w', '--wrapper-mode',
        action='store_true',
        default=False,
        help='''Format output to be suitable for a wrapper application. All lines
        will start with an easily greppable hook name, and any following data is
        split into tab-separated fields.''',
        dest='WRAPPER_MODE'
    )

    parser.add_argument(
        '-r', '--refresh-cache',
        action='store_true',
        default=False,
        help='''Force fetching of installed apps and remote compatibility data,
        instead of using cached data. The default is to cache all data for an hour.''',
        dest='REFRESH_CACHE'
    )

    return parser

def cache_is_outdated():
    cache_is_outdated = True
    try:
        cache_modification_time = os.path.getmtime(CACHE_FILE)
        now = time.time()
        if now - cache_modification_time < MAX_CACHE_AGE_IN_SECONDS:
            cache_is_outdated = False
    except OSError:
        pass

    return cache_is_outdated

def get_value_from_cache(key):
    value = None
    cache = shelve.open(CACHE_FILE, protocol=-1)
    if cache.has_key(key):
        value = cache[key]

    return value

def save_to_cache(key, value):
    cache = shelve.open(CACHE_FILE, protocol=-1)
    cache[key] = value
    cache.close()

def get_installed_applications():
    print_message('Looking for installed applications...')
    print_wrapper_message('looking_for_installed_applications')
    installed_applications = []
    for current_folder in args.APPFOLDERS:
        path = os.path.expanduser(current_folder)
        if os.path.isdir(path):
            # Set up the Spotlight/mdfind search.
            command = [
                'mdfind',
                '-onlyin',
                path,
                'kMDItemContentTypeTree == com.apple.application',
                '&&',
                'kMDItemCFBundleIdentifier != com.apple.*'  # Exclude any Apple applications.
            ]
            try:
                output = subprocess.check_output(command)
            except subprocess.CalledProcessError as e:
                print >> sys.stderr, e.output
                print >> sys.stderr, 'Tried to execute:'
                print >> sys.stderr, e.cmd
                continue
            except OSError as e:
                print >> sys.stderr, e
                continue

            for path in output.splitlines():
                basename, ext = os.path.splitext(os.path.basename(path).decode('utf8'))
                if ext == '.app' and basename not in installed_applications:
                    installed_applications.append(basename)
        else:
            # Only show warning for non-default folders.
            if current_folder not in DEFAULT_APP_FOLDERS:
                print >> sys.stderr, 'Couldn’t find ' + path + ', skipping it.'
            continue

    save_to_cache(key=INSTALLED_APPLICATIONS_KEY, value=installed_applications)

    return installed_applications

def get_cached_applications():
    print_message('Using cached list of installed applications.')
    print_wrapper_message('using_cached_installed_applications')

    return get_value_from_cache(INSTALLED_APPLICATIONS_KEY)

def get_compatibility_data():
    print_message('Fetching compatibility data...')
    print_wrapper_message('fetching_compatibility_data')

    try:
        url = urllib2.urlopen(ROARING_APPS_JSON_URL)
        response = url.read()
        compatibility_data = json.loads(response)
        save_to_cache(key=COMPATIBILITY_DATA_KEY, value=compatibility_data)
    except urllib2.URLError:
        print >> sys.stderr, 'Couldn’t fetch compatibility data; are you connected to the Internet?'
        sys.exit(1)

    return compatibility_data

def get_cached_compatibility_data():
    print_message('Using cached compatibility data.')
    print_wrapper_message('using_cached_compatibility_data')

    return get_value_from_cache(COMPATIBILITY_DATA_KEY)

def print_lion_message(message, verbose=False):
    if args.ONLY_PRINT_LION_DATA or PRINT_ALL_DATA:
        print_message(message, verbose)

def print_mountain_lion_message(message, verbose=False):
    if args.ONLY_PRINT_MOUNTAIN_LION_DATA or PRINT_ALL_DATA:
        print_message(message, verbose)

def print_message(message, verbose=False):
    if (not verbose or (verbose and args.VERBOSE)) and not args.WRAPPER_MODE:
        print message

def print_wrapper_message(message):
    if args.WRAPPER_MODE:
        print message

if __name__ == '__main__':
    parser = get_argument_parser()
    args = parser.parse_args()
    PRINT_ALL_DATA = not args.ONLY_PRINT_LION_DATA and not args.ONLY_PRINT_MOUNTAIN_LION_DATA
    main()
