from .errors import UserInputError

import os
if os.name == 'nt':
    from .inpromptu_prompt_toolkit import Inpromptu
else:
    from .inpromptu_readline import Inpromptu
