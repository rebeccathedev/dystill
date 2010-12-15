#!/usr/bin/env python

"""
Copyright (c) 2010, Rob Peck <rob@robpeck.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
      
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
      
    * Neither the name of the Rob Peck nor the names of its contributors may 
      be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL ROB PECK BE LIABLE FOR ANY DIRECT, INDIRECT, 
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Import what we need
import os
import sys
import re
import argparse
import email
import mailbox
import smtplib
import copy
import ConfigParser
import MySQLdb
import MySQLdb.cursors

VERSION = "0.1.2"

# Define a couple of useful exit codes
EX_OK = 0
EX_TEMPFAIL = 75
EX_NOPERM = 77

# The main run function
def main():
    
    #Parse out the command line args
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", help='Config file', metavar="<conf>")
    parser.add_argument("-d", help='Delivery mode for this user', metavar="<user>", required=True)
    parser.add_argument("-f", help='Email file', metavar="<file>")
    
    args = parser.parse_args()
    
    # First, we check to see if they define a config file. If they do,
    # but it doesn't exist, throw TEMPFAIL and exit. Ths will cause the
    # MTA to queue the message for later delivery.
    config_file = None
    if not args.c == None:
        if not os.path.isfile(args.c):
            print "The specified config file was not found!"
            sys.exit(EX_TEMPFAIL)
        else:
            config_file = args.c
    
    # If they haven't specified a conf, look in the usual places.
    else:
        paths = []
        paths.append("./")
        paths.append("/etc/")
        
        for i in paths:
            if os.path.isfile(i + "/dystill.conf"):
                config_file = i + "/dystill.conf"
                
    # If we got this far without a file, throw TEMPFAIL and exit.
    if config_file == None:
        print "Cound not find a configuration file!"
        sys.exit(EX_TEMPFAIL)
    
    # Load the file up into the config parser.    
    config = ConfigParser.RawConfigParser()
    config.read(config_file)
    
    # Read some database stuff from the config
    users_table = None
    user_id_field = None
    email_field = None
    homedir_field = None
    maildir_field = None
    try:
        users_table = config.get("database", "users_table")
        user_id_field = config.get("database", "user_id_field")
        email_field = config.get("database", "email_field")
        homedir_field = config.get("database", "homedir_field")
        maildir_field = config.get("database", "maildir_field")
    except ConfigParser.NoOptionError, message:
        print "Could not read required options from the config file: " + message.__str__()
        sys.exit(EX_TEMPFAIL)
        
    # Try to find a delimiter if we have one.
    delimiter = None
    try:
        delimiter = config.get("dystill", "delimiter")
    except ConfigParser.NoOptionError, message:
        pass
    
    # Assign this to a var for processing
    to_address = args.d
    
    # Try to parse the user information
    if not delimiter == None:
        pattern = re.compile("(.*?)(" + delimiter + ".*)?@(.*)")
        res = pattern.search(to_address)
        
        if not res.group(2) == None:
            to_address = res.group(1) + "@" + res.group(3) 
    
    # If a file is specified, read that
    data = None
    if not args.f == None and os.path.isfile(args.f):
        f = open(args.f)
        data = f.read()
        f.close()
    
    # Else, read it from the pipe
    else:
        data = sys.stdin.read()
    
    # If we got this far without data, throw TEMPFAIL and exit.
    if data == None or len(data) == 0:
        print "Could not read email data!"
        sys.exit(EX_TEMPFAIL)
        
    # Load up the email parser and try to parse the message
    parser = email.Parser.Parser()
    try:
        zemail = parser.parsestr(data, True)
    except email.errors.MessageParseError:
        print "Could not parse email data!"
        sys.exit(EX_TEMPFAIL)
        
    # Add a header to the email message
    zemail.__setitem__("X-MDA", os.path.splitext(os.path.basename(__file__))[0] + " " + VERSION)
        
    # So we now have an email. Time to talk to the database.
    try:
        db = MySQLdb.connect(
                                host=config.get("database", "host"),
                                user=config.get("database", "user"),
                                passwd=config.get("database", "password"),
                                db=config.get("database", "database"),
                                cursorclass=MySQLdb.cursors.DictCursor)
    except ConfigParser.NoOptionError, message:
        print "Could not read required options from the config file: " + message.__str__()
        sys.exit(EX_TEMPFAIL)
    except MySQLdb.OperationalError, (value, message):
        print "Could not connect to the database: " + message
        sys.exit(EX_TEMPFAIL)
    
    # Query for the user first, so we know where to deliver to.
    try:
        cursor = db.cursor()
        cursor.execute("select %s as id, %s as email, %s as homedir, %s as maildir from %s where %s = '%s' limit 1" %
                       (user_id_field, email_field, homedir_field, maildir_field, users_table, email_field, db.escape_string(to_address)))
    except MySQLdb.ProgrammingError, (value, message):
        print "Internal error: " + message
        sys.exit(EX_TEMPFAIL)
        
    # Pull out the user
    user = cursor.fetchone()
    cursor.close()
    
    # Check to see if the user actually exists. We shouldn't even be here
    # if this is the case, but we check just to be sure.
    if user == None:
        print "Could not find user " + to_address + " in users table."
        db.close()
        sys.exit(EX_TEMPFAIL)
    
    # Query for the rules
    try:
        cursor = db.cursor()
        cursor.execute("select * from filters inner join filters_actions using (filter_id) where (user_id = %d or user_id = 0) and active = 1" % (user["id"],))
    except MySQLdb.ProgrammingError, (value, message):
        print "Internal error: " + message
        sys.exit(EX_TEMPFAIL)
        
    # Pull out the rules
    rules = cursor.fetchall()
    cursor.close()
    
    # Close the DB to free up resources ASAP.
    db.close()
    
    # Define maildir
    maildir = user["homedir"] + "/" + user["maildir"]
    
    # Check that the homedir path exists
    if not os.path.isdir(user["homedir"]):
        print "Home directory " + user["homedir"] + " is not found!"
        sys.exit(EX_TEMPFAIL)
        
    # Check that the homedir path is writable
    if not os.access(user["homedir"], os.W_OK):
        print "Home directory " + user["homedir"] + " is not writable!"
        sys.exit(EX_TEMPFAIL)
    
    #  Now we loop through the rules and build an actions table
    actions = {}
    for rule in rules:
        # Because there can be more than 1 header of type X in a message
        headers = zemail.get_all(rule["field"])
        
        # Otherwise, regexp match on the header values
        if not headers == None:
            if not rule["comparison"] == 4:
                test = re.escape(rule["value"])
            else:
                test = rule["value"]
            
            for header in headers:
                if rule["comparison"] == 0: # Starts with
                    match = re.compile("^" + test, re.IGNORECASE)
                    if match.match(header):
                        actions[rule["action"]] = rule["argument"]
                
                if rule["comparison"] == 1: # Ends with
                    match = re.compile(".*" + test + "$", re.IGNORECASE)
                    if match.match(header):
                        actions[rule["action"]] = rule["argument"]
                
                if rule["comparison"] == 2: # Contains
                    match = re.compile(".*" + test + ".*", re.IGNORECASE)
                    if match.match(header):
                        actions[rule["action"]] = rule["argument"]

                if rule["comparison"] == 3: # Is
                    if header == test:
                        actions[rule["action"]] = rule["argument"]
                
                if rule["comparison"] == 4: # Regexp
                    match = re.compile(test, re.IGNORECASE)
                    if match.match(header):
                        actions[rule["action"]] = rule["argument"]
    
    # Open the maildir for delivery
    inbox = mailbox.Maildir(maildir, factory=None)
    folders = inbox.list_folders()
    
    # Bring the message in
    message = mailbox.MaildirMessage(zemail)
    delivered = False
    exit = EX_OK
    
    # Mark as read
    if actions.__contains__("markasread"):
        message.add_flag("S")
        message.set_subdir("cur")
        
    # Flag
    if actions.__contains__("flag"):
        message.add_flag("F")
        
    # Delete
    if actions.__contains__("delete"):
        message.add_flag("S")
        message.add_flag("T")
        message.set_subdir("cur")
        
    # Prepend Subject
    if actions.__contains__("prependsub"):
        message["subject"] = actions["prependsub"] + " " + message["subject"]
        
    # Add a header
    if actions.__contains__("header"):
        headers = actions("header").partition(":")
        message.__setitem__(headers[0], headers[2])
        
    # Forward to another user
    if actions.__contains__("forward"):
        fwd_message = copy.deepcopy(message)
        fwd_message["subject"] = "Fwd: " + fwd_message["subject"]
        fwd_message["to"] = actions["forward"]
        
        s = smtplib.SMTP("localhost")
        s.sendmail(user["email"], actions["forward"], fwd_message.__str__())
        s.quit()
        message.add_flag("P")
        
    # Silently block delivery of this message
    if actions.__contains__("block"):
        delivered = True
        
    # Noisily block delivery of this message
    if actions.__contains__("blocknote"):
        delivered = True
        exit = EX_NOPERM
        print "User " + user["email"] + " does not wish to receive this email."
        
    # Copy to another folder
    if actions.__contains__("copyto"):
        f = actions["to"].replace("/", ".")
        if not folders.__contains__(f):
            inbox.add_folder(f)
        
        copy_message = copy.deepcopy(message)
        folder = inbox.get_folder(f)
        folder.lock()
        folder.add(copy_message)
        folder.unlock()
        folder.close()
    
    # Deliver to another box. We always do this last.
    if actions.__contains__("to"):
        f = actions["to"].replace("/", ".")
        # Determine if the folder exists. Create it if it doesn't.
        if not folders.__contains__(f):
            inbox.add_folder(f)
            
        folder = inbox.get_folder(f)
        folder.lock()
        folder.add(message)
        folder.unlock()
        folder.close()
        delivered = True
        
    # If the message hasn't already been delivered, it goes into the inbox
    if not delivered:
        inbox.lock()
        inbox.add(message)
        inbox.unlock()
    
    # Message delivered! We're done!
    inbox.close()
    sys.exit(exit)
            
    
# Jump into the main function
if __name__ == "__main__":
    main()