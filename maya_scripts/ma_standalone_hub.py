# -*- coding: utf-8 -*-

import maya.standalone
import maya.cmds as mc
import sys
import os
import argparse
import imp
import traceback
import datetime

def initialize_maya():
    maya.standalone.initialize(name='python')
    print("[INFO] Maya Standalone initialized.")

def load_and_run_script(script_path, script_args):
    script_path = os.path.abspath(script_path)

    if not os.path.exists(script_path):
        raise RuntimeError("[ERROR] Script not found: {}".format(script_path))

    module = imp.load_source("user_script", script_path)

    if not hasattr(module, "main"):
        raise RuntimeError("[ERROR] Target script must have a 'main' function.")

    print("[INFO] Executing '{}', args: {}".format(script_path, script_args))
    module.main(script_args)

def log_message(log_path, message):
    if log_path:
        with open(log_path, "a") as log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write("[{}] {}\n".format(timestamp, message))

def main():
    parser = argparse.ArgumentParser(description="Maya Standalone Script Hub")
    parser.add_argument('--script', required=True, help='Path to the Python script to execute')
    parser.add_argument('--args', nargs='*', help='Arguments to pass to the script')
    parser.add_argument('--log', help='Optional path to write logs')

    args = parser.parse_args()
    script_path = args.script
    script_args = args.args or []
    log_path = args.log

    try:
        initialize_maya()
        load_and_run_script(script_path, script_args)
        log_message(log_path, "Script completed successfully.")
        print("[SUCCESS] Script executed without errors.")
        sys.exit(0)
    except Exception as e:
        error_trace = traceback.format_exc()
        log_message(log_path, "Script failed with error:\n{}".format(error_trace))
        print("[FAILURE] Script execution failed:\n{}".format(error_trace))
        sys.exit(1)

if __name__ == '__main__':
    main()
