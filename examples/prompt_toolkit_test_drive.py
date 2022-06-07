#!/usr/bin/env python3
from inpromptu import PromptToolkitCompleter
from test_drive import TestDrive

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit import prompt
    from prompt_toolkit.shortcuts import CompleteStyle
    from prompt_toolkit.completion import Completer, Completion
except ImportError:
    print("You must have prompt_toolkit installed.")


if __name__ == "__main__":
    my_test_drive = TestDrive()

    ptk_completer = PromptToolkitCompleter(my_test_drive)

    session = PromptSession('>>>', completer=ptk_completer)
    while True:
        try:
            text = session.prompt('>>> ', complete_style=CompleteStyle.READLINE_LIKE)
        except KeyboardInterrupt:
            print("Press CTRL-D to exit.")
        except EOFError:
            break
        else:
            print('You entered:', text)
    print('GoodBye!')
