# Changelog

## Version 0.3
- Refactored the code a bit for Python 3 support. The logic and functionality of
  the program is largely unchanged.
- Licensed changed to MIT as that is what I have been standardizing on.
- **BUGFIX**: Fixed a nearly 10 year old bug that would prevent `blocknote` from
  actually sending the blocked email note.

## Version 0.2.1
- **FEATURE**: New config variable, `create_maildirs`, that can create a maildir 
  if one does not already exist.
- Better error checking.
- This is the last version that supported Python 2.

## Version 0.2
- Purposely broke the association between Postfix's DB style and Dystill, 
  hopefully allowing for wider adoption. 
  - This means dropping the user_id association in Dystill's DB schema and 
    replacing it with a text field containing the user email address. "Wildcard"
    rules are still supported using an empty string ('') in the email field.
  - New configuration parameter, `maildir_path`, specifies the location and path 
    of the maildir. `{to_address}` is replaced with the email address of the 
    recipient (the maildir location)
- **BUGFIX**: An issue where folder names with certain characters would cause 
  issues with mail delivery.

## Version 0.1.2
- **BUGFIX**: Now actually support subfolders in IMAP. Previous version 
  contained a bug that would cause a maildir to be created that wasn't 
  accessable.
- **FEATURE**: Support added for delimiters in email addressed in situations 
  where the MTA doesn't handle parsing it for us (Postfix).

## Version 0.1.1
- Changed the way filter actions worked. Previously all comparisons were done by
  regular expression. Now changes can be one of 5 ways (starts with, ends with,
  contains, equals, and regular expression). Added a field to the database to 
  store this.

## Version 0.1
- Initial release


