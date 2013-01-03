from __future__ import print_function
import sys
import os
import base64
from getpass import getuser, getpass
from socket import gethostname
from time import asctime

# Dependencies
from lockfile import FileLock
from cracklib import FascistCheck

ACCOUNT_FILE = "approved.users" # "/opt/adm/approved.users"
ACCOUNT_LOG = "approved.log" # "/opt/adm/approved.log"
DIVIDER = "--------------------------"
RN_USERS_FILE = "RN_UserInfo" # "/opt/adm/RN_UserInfo"

class ApprovalError(Exception):
    pass

def usage():
    print("Usage: '{}' [--force]".format(__file__))

def _check_real_name(real_name):
    if not all([i == " " or i.isalpha() for i in real_name]):
        raise ApprovalError("The only permitted characters are uppercase, "
                        "lowercase, and spaces")

def _check_university_id(university_id):
    if not all([i.isdigit() for i in university_id]):
        raise ApprovalError("This doesn't appear to be a valid CAL ID")

def _check_username(username):
    if len(username) > 8 or len(username) < 3:
        raise ApprovalError("Usernames must be between 3 and 8 characters")
    elif any([not i.islower() for i in username]):
        raise ApprovalError("Usernames must consist of only lowercase alphabet")

    # In approved user file
    try:
        with open(ACCOUNT_FILE) as f:
            for line in f:
                if line.startswith(username + ":"):
                    raise ApprovalError("Duplicate username found in approved users file")
    except IOError:
        pass

    if username in OCF_RESERVED_NAMES_LIST:
        raise ApprovalError("Username is reserved")

def _check_forward(forward):
    if forward not in ["y", "n"]:
        raise ApprovalError("Please only type in a lowercase y or a lowercase n")

def _string_match_percentage(a, b):
    return sum([i.lower() == j.lower()
                for index in range(len(a))
                for i, j in zip(a[index:], b)]) / float(len(a))

def _check_password(password, username):
    if len(password) < 8:
        raise ApprovalError("The password you entered is too short (minimum of 8 chars)")

    percentage = _string_match_percentage(password, username)
    # Threshold?

    try:
        FascistCheck(password)
    except ValueError as e:
        raise ApprovalError("Password issue: {}".format(e))

def _check_email(email):
    if email.find("@") == -1 or email.find(".") == -1:
        raise ApprovalError("Invalid Entry, it doesn't look like an email")

def _get_string(prompt, check = None, double_check = False, prompter = None):
    while True:
        if prompter:
            val = prompter(prompt)
        else:
            val = raw_input(prompt)

        if check:
            try:
                check(val)
            except ApprovalError as e:
                print(e)
            else:
                if not double_check or raw_input("  Enter again to confirm: ") == val:
                    return val

def approve_user(real_name, calnet_uid, account_name, email, forward, password):
    with FileLock(ACCOUNT_FILE):
        _check_real_name(real_name)
        _check_university_id(calnet_uid)
        _check_username(account_name)
        _check_email(email)
        _check_password(password, real_name)

        _approve(real_name, None, None, calnet_uid, email,
                 account_name, password, forward)

def approve_group(group_name, responsible, university_id, email, username, password, forward):
    with FileLock(ACCOUNT_FILE):
        _check_real_name(group_name)
        _check_real_name(responsible)
        _check_university_id(university_id)
        _check_username(username)
        _check_email(email)
        _check_password(password, group_name)

        _approve(None, group_name, responsible, university_id, email,
                 username, password, forward)

def _approve(real_name, group_name, responsible, university_id, email, username, password,
            forward):
    if group_name:
        group = 1
        real_name = "(null)"
    else:
        group_name = "(null)"
        group = 0

    forward = int(bool(forward))
    password = base64.b64encode(password)

    # Write to the list of users to be approved
    sections = (username, real_name, group_name,
                email, forward, group, password, " ",
                university_id)

    with open(ACCOUNT_FILE, "a") as f:
        f.write(":".join((str(i) for i in sections)) + "\n")

    # Write to the log
    sections = [username, responsible, university_id,
                getuser(), gethostname(),
                1 if os.geteuid() == os.getuid() else 0,
                1 if group_name else 0, asctime()]

    with open(ACCOUNT_LOG, "a") as f:
        f.write(":".join((str(i) for i in sections)) + "\n")
