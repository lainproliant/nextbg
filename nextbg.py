#!/usr/bin/env python

# -------------------------------------------------------------------
# nextbg.py: Go back and forth between wallpapers.
# -------------------------------------------------------------------

import argparse
import json
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

# -------------------------------------------------------------------
DESCRIPTION = """
Cycle through a list of cached image filenames to change the current X11 root
background image.
""".strip()

HELP_CONFIG = """
Specify the file to interact with for configuration options.  These include the
background set commands, current offset, image file patterns, and current list
of image files.  This file will be overwritten when the background is updated
or a directory is scanned, and will be created if it doesn't already exist.
""".strip()

HELP_SCAN = """
Enables scanning mode.  By default, the current directory will be scanned and
any images found will replace the current image index, unless `-a` is specified,
in which case they will be appended to the current list.
""".strip()

HELP_DIR = """
Specifies a directory to be scanned for images.  By default, this is the
current directory.
""".strip()

HELP_RECURSIVE = """
Only valid if `-s/--scan` is specified.  Causes all directories under the
specified directory to be scanned recursively for images.
""".strip()

HELP_APPEND = """
Only valid if `-s/--scan` is specified.  Causes the results of this directory
scan to be added to any previously scanned directories.  All absolute filenames
will be sorted and any duplicate abspaths are culled.
""".strip()

HELP_NEXT = """
Set the background to the next image in the list.  This is the default action
if no parameters are specfied.
""".strip()

HELP_PREV = """
Set the background to the previous image in the list.
""".strip()

HELP_RANDOM = """
Set the background to a random image in the list.
""".strip()

HELP_SET = """
Set the background to the current background.  You should call this in your
`~.xinitrc` or the like to set the background when you login to your X session.
""".strip()

HELP_DELETE = """
Remove the current wallpaper from the list.  Does not delete the file on disk.
""".strip()

HELP_PRINT = """
Print the path of the current background image.  Useful if you want to use your
background image in other applications or scripts.
""".strip()

EPILOG = """
By default, the config file is stored at `~/.nextbg.json`.  If `-c` is
specified, this will be used as the config file instead.  If the config file
does not exist, it will be created and initialized with default options.

`feh` is used to set the background by default, and `*.jpg` and `*.png` files
in the specified directories are scanned.  To add more image file patterns or
override the background setting command, edit the`image_file_patterns` and
`bg_set_command` fields in the config JSON respectively.
"""


# -------------------------------------------------------------------
class CommandError(Exception):
    pass


# -------------------------------------------------------------------
@dataclass
class DecoratorMap:
    map: Dict[str, Any] = field(default_factory=dict)

    def __call__(self, key):
        def impl(value):
            self.map[key] = value
            return value
        return impl

    def get(self, key):
        if key not in self.map:
            raise ValueError(f"Function not found for '{key}'.")
        return self.map[key]


# -------------------------------------------------------------------
mode = DecoratorMap()


# -------------------------------------------------------------------
@dataclass
class Config:
    modes: List[str] = field(default_factory=list)
    index: List[str] = field(default_factory=list)
    mode = "next"
    bg_set_command = ['feh', '--bg-fill', '<image>']
    image_file_patterns = ["*.png", "*.jpg"]
    config_filename = "~/.nextbg.json"
    offset = 0
    recursive = False
    append = False
    dir = '.'

    @staticmethod
    def get_arg_parser():
        parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)

        parser.add_argument("-c", "--config", dest="config_filename",
                            help=HELP_CONFIG)
        parser.add_argument("-s", "--scan", action="append_const",
                            dest="modes", const="scan", help=HELP_APPEND)
        parser.add_argument("-d", "--dir", default=os.getcwd(), help=HELP_DIR)
        parser.add_argument("-r", "--recursive", action="store_true",
                            help=HELP_RECURSIVE)
        parser.add_argument("-a", "--append", action="store_true",
                            help=HELP_APPEND)
        parser.add_argument("-n", "--next", action="append_const",
                            dest="modes", const="next", help=HELP_NEXT)
        parser.add_argument("-p", "--prev", action="append_const",
                            dest="modes", const="prev", help=HELP_PREV)
        parser.add_argument("-R", "--random", action="append_const",
                            dest="modes", const="random", help=HELP_PREV)
        parser.add_argument("-S", "--set", action="append_const", dest="modes",
                            const="set", help=HELP_SET)
        parser.add_argument("-X", "--delete", action="append_const",
                            dest="modes",
                            const="delete", help=HELP_DELETE)
        parser.add_argument("-P", "--print", action="append_const",
                            dest="modes", const="print", help=HELP_PRINT)
        return parser

    @staticmethod
    def setup():
        return Config().parse_args().load()

    def parse_args(self):
        parser = self.get_arg_parser()
        parser.parse_args(namespace=self)

        if self.modes:
            if len(self.modes) > 1:
                raise CommandError(f"Multiple modes specified: '{repr(self.modes)}'. "
                                   "Please specify only one mode.")
            self.mode = self.modes[0]

        return self

    def load(self):
        config_path = Path(self.config_filename).expanduser()

        if not config_path.exists():
            # If config file doesn't exist, make a new one!
            print(f"Config file {self.config_filename} doesn't exist, creating it with defaults.")
            self.save()
            return self

        with open(str(config_path), "rt") as infile:
            config_json = json.load(infile)

        self.index = config_json['index']
        self.bg_set_command = config_json['bg_set_command']
        self.image_file_patterns = config_json['image_file_patterns']
        self.offset = config_json['offset']
        return self

    def save(self):
        config_path = Path(self.config_filename).expanduser()

        config_json = {
            'index': self.index,
            'bg_set_command': self.bg_set_command,
            'image_file_patterns': self.image_file_patterns,
            'offset': self.offset
        }

        with open(str(config_path), 'wt') as outfile:
            json.dump(config_json, outfile, indent=4)

        print(f"Configuration saved to '{self.config_filename}'.")
        return self

    def _check_has_index(self):
        if not self.index:
            raise CommandError("No index found.  Add some images or directories to get started.")

    def get_image(self):
        """Gets the image at the current offset in the list."""
        self._check_has_index()

        if self.offset not in range(0, len(self.index)):
            self.offset = 0

        return Path(self.index[self.offset])

    def next_offset(self):
        """Moves the offset forward by one."""
        self._check_has_index()

        self.offset += 1
        if self.offset not in range(0, len(self.index)):
            self.offset = 0
        self.save()

    def prev_offset(self):
        """Moves the offset backwards by one."""
        self._check_has_index()

        self.offset -= 1
        if self.offset < 0:
            self.offset = len(self.index) - 1
        self.save()

    def random_offset(self):
        """Sets the offset to a random location in the image index."""
        self._check_has_index()
        self.offset = random.randint(0, len(self.index) - 1)
        self.save()

    def pop_offset(self):
        """Pops the item at the offset off of the list."""
        self._check_has_index()

        if len(self.index) == 1:
            raise CommandError("Refusing to delete the last item from the image index.")

        self.index.pop(self.offset)
        self.offset -= 1
        print(f"'{self.get_image()}' removed from index.")
        self.save()

    def set_index(self, filenames):
        """Update the index to contain the given list of filenames."""
        self.index = [str(f) for f in filenames]
        self.offset = 0
        if len(filenames) == 1:
            print("Index set with 1 image.")
        else:
            print(f"Index set with {len(filenames)} images.")

        self.save()

    def update_index(self, filenames):
        """Append the given items to the index."""
        self.index.extend([str(f) for f in filenames])
        if len(filenames) == 1:
            print("Index updated with 1 image.")
        else:
            print(f"Index updated with {len(self.index)} images.")

        if len(self.index) == 1:
            print("Index now contains 1 image.")
        else:
            print(f"Index now contains {len(self.index)} images.")
        self.save()


# -------------------------------------------------------------------
def main():
    config = Config.setup()

    try:
        mode.get(config.mode)(config)
        return 0
    except CommandError as e:
        print(f'ERROR: {e}')
        return 1


# -------------------------------------------------------------------
@mode('scan')
def scan_directory(config: Config):
    filenames = []
    directory = Path(config.dir).expanduser()

    print(f"Scanning '{config.dir} for image files...'")

    if config.recursive:
        for pattern in config.image_file_patterns:
            filenames.extend(list(directory.rglob(pattern)))
    else:
        for pattern in config.image_file_patterns:
            filenames.extend(list(directory.glob(pattern)))

    if not filenames:
        raise CommandError(f"No images found in '{config.dir}'.")

    if config.append:
        config.update_index(filenames)
    else:
        config.set_index(filenames)

    mode.get('set')(config)


# -------------------------------------------------------------------
@mode('print')
def print_filename(config: Config):
    image_file = config.get_image()
    print(str(image_file))


# -------------------------------------------------------------------
@mode('next')
def next_image(config: Config):
    config.next_offset()
    mode.get('set')(config)


# -------------------------------------------------------------------
@mode('prev')
def prev_image(config: Config):
    config.prev_offset()
    mode.get('set')(config)


# -------------------------------------------------------------------
@mode('random')
def random_image(config: Config):
    config.random_offset()
    mode.get('set')(config)


# -------------------------------------------------------------------
@mode('set')
def set_background(config: Config):
    image = config.get_image()
    cmd = [image if s == '<image>' else s for s in config.bg_set_command]
    try:
        subprocess.check_call(cmd)
        print(f"Set background to '{str(image)}'.")
    except Exception:
        raise CommandError(f"Background setting command failed.")


# -------------------------------------------------------------------
@mode('delete')
def delete_from_index(config: Config):
    config.pop_offset()
    mode.get('set')(config)


# -------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
