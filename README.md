# dystill

dystill is a sorting, filtering MySQL-based Mail Delivery Agent written in 
Python. Version 0.3 and on only supports Python 3. If you *still* need Python 2
support, you can use the 0.2.1 tag.

## Installing

First, start by installing the required libraries:

```shell
$ pip3 install mysqlclient
```

Next, install the base schema in your MySQL database. See `schema/dystill.sql`. 
Configure MySQL with a user that can access this database.

Finally, Download and install dystill. You can put the script anywhere you like.
I went ahead and put it in `/usr/bin`. You will need to adjust the accompanying 
config as required and put it in `/etc` or specify it's location on the command 
line.

## Dystill Configuration

Dystill has a small bit of configuration that is needed. Below is a sample 
config file with explanations of each key:

```ini
[dystill]

# delimiter
# This defines a delimiter that can be used in email addresses, such as 
# user-foo@domain.com. dystill will parse this out to user@domain.com and 
# deliver to the appropriate mailbox, but with user-foo@domain.com still
# in the To: field.
delimiter=-

# maildir_path
# This defines the location and format on the filesystem where your maildirs
# live. The variable {to_address} is replaced with the email address of the
# recipient
maildir_path=/var/mail/{to_address}

# create_maildirs
# This directive specified whether dystill should try to create a maildir if
# one does not exist.
create_maildirs=true

[database]

# host
# This is the MySQL host where your dystill data will live.
host=localhost

# user
# This is the user that you connect to MySQL with.
user=postfix

# password
# This is the password for your MySQL user.
password=password

# database
# This is the database where your dystill settings live.
database=postfix
```

## Postfix Configuration

I've only used and tested dystill with Postfix, but it's pretty simple and 
should theoretically be able to work with just about any MTA that supports 
piping. Still, the instructions here are presented for Postfix.

First, add the included SQL schema to your email database. This works especially
well if you have followed similar instructions* to the ones I did when setting 
up my email server.

Next, be sure you have customized your /etc/dystill.conf file, and that all the 
database settings are correct. 

Next, edit your `master.cf` file and add the following:

```
dystill     unix    -            n             n          -           -            pipe
  flags=DRhu user=vmail argv=/usr/bin/dystill.py -d ${recipient}
```
  
Next, edit your `main.cf` file as follows:

```postfix
mailbox_command = dystill
virtual_transport = dystill
```

That's it! Send a test message and see if it works.

## Writing Rules

Once you have the software installed and working, the next step is to add some
rules to get it to do what you want. Right now, there is no graphical front-end
to the SQL database, but writing one or adding it to an existing mail package
should be trivially easy.

### The filters Table:

The main table that dystill uses is the filters table. This table consists of a 
unique identifier (filter_id), an email field representing the email address of
the recipient, a field, a value, an integer that determines whether or not a 
filter is active or not, and a comparison field that describes the type of 
comparison taking place.

The comparison types are:
* `0` = Starts With
* `1` = Ends With
* `2` = Contains
* `3` = Is (an exact equals)
* `4` = Regular Expression

The fields you really need to worry about are the field and value fields. These
represent a header, and a regular expression match against the value of the 
header.

For example:

```sql
insert into filters set email='user@domain.org', field='X-Spam-Flag', 
comparison=3, `value`='YES', active=1;
```

This will create a filter that matches on the spam flag. Using regular 
expressions, you can create complex filters or very simple ones. It's up to you.
If you filters with a `email` of `""`, these are automatically applied to all 
messages. This is useful for spam filtering.

## The actions Table

The accompanying filters_actions table describes the actions that are taken when
a filter matches. This table consists of a unique ID (action_id), a filter_id 
linking back to the filters table, an action string, and an argument string.

The big two are the action and argument. Valid actions are:

 * `markasread` - Marks the message as read.
 * `flag`       - Flags a message.
 * `deletes`    - Deletes a message. The message is still delivered, but is 
    marked for deletion.
 * `prependsub` - Prepends text to the subject string. The argument should be 
    the string to prepend.
 * `header`     - Adds a header to the message. The argument should be a 
    key:value pair.
 * `forward`    - Automatically queues a forward message to a specified address.
    The argument should be the address you want to forward it to. 
 * `block`      - Silently blocks delivery. This will tell the MTA that the
    message was delivered, but will silently dispose of it.
 * `blocknote`  - Blocks delivery, but informs the sending address that delivery
    was blocked.
 * `copyto`     - Duplicates the message, and puts a copy in a different folder.
    The argument should be the folder you want to move it to.
 * `to`         - Moves the message to the specified folder. The argument should
    be the address you want to move it to.
 
By the time it reaches the end of the action chain, if the message hasn't been
delivered, it is automatically added to the inbox as any normal email would be.

## License

MIT

## Author

Rob Peck
