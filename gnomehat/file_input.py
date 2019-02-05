import os
import sys
import readline
import glob

class tabCompleter(object):
    """
    A tab completer that can either complete from
    the filesystem or from a list.

    Partially taken from:
    http://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input
    """

    def pathCompleter(self, text, state):
        """
        This is the tab completer for systems paths.
        Only tested on *nix systems
        """
        line = readline.get_line_buffer().split()

        # replace ~ with the user's home dir. See https://docs.python.org/2/library/os.path.html
        if '~' in text:
            text = os.path.expanduser('~')

        # autocomplete directories with having a trailing slash
        if os.path.isdir(text):
            text += '/'

        return [x for x in glob.glob(text + '*')][state]


    def createListCompleter(self,ll):
        """
        This is a closure that creates a method that autocompletes from
        the given list.

        Since the autocomplete function can't be given a list to complete from
        a closure is used to create the listCompleter function with a list to complete
        from.
        """
        def listCompleter(text,state):
            line   = readline.get_line_buffer()
            if not line:
                return [c + " " for c in ll][state]
            else:
                return [c + " " for c in ll if c.startswith(line)][state]
        self.listCompleter = listCompleter


def read_directory_name(prompt="Enter a directory: "):
    t = tabCompleter()

    readline.set_completer_delims('\t')
    readline.parse_and_bind("tab: complete")

    readline.set_completer(t.pathCompleter)
    path = input(prompt)

    # If user-specified directory is invalid, retry
    if os.access(os.path.dirname(path), os.W_OK):
        return path
    else:
        print('Error: path "{}" is not a valid, writable directory'.format(path))
        return read_directory_name(prompt)


# Input: dict of keys/text explanations
# Output: key of the option the user selects
# User is prompted to type a number
# User does not see the key, only the text explanation
def read_option(options):
    # Display options in alphabetical order by key
    number_to_option = {}
    keys = [k for k in sorted(options.keys())]
    for i in range(1, len(options) + 1):
        number_to_option[i] = keys[i - 1]

    print('Select from the following choices:')

    for i in number_to_option:
        verbose_message = options[number_to_option[i]]
        print('{}: {}'.format(i, verbose_message))
    print()

    selection = input().strip().lower()
    valid_choices = [str(i) for i in number_to_option]
    if selection not in valid_choices:
        print('Please type one of the following: {}'.format(valid_choices))
        return read_option(options)
    return number_to_option[int(selection)]
