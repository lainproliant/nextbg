#!/usr/bin/env python

#
# nextbg.py: Go back and forth between wallpapers.
#

import fnmatch
import getopt
import json
import os
import pdb
import random
import sys

#-------------------------------------------------------------------
SHORTOPTS = 'hc:d:rnpRsX'
LONGOPTS = ['help', 'config=', 'dir=', 'recursive', 'next', 'prev', 'random', 'same', 'delete-current']

DEFAULT_CONFIG = {
   'image_file_patterns':     ['*.jpg', '*.png'],
   'images':                  [],
   'offset':                  0,
   'bg_set_command':          'feh --bg-scale "%s"'
}

DEFAULT_CONFIG_FILENAME = '~/.nextbg.json'

HELP_TEXT = '''
Usage: nextbg.py [SET_OPTIONS]/[[DIR_OPTIONS] -d/--dir DIRECTORY]

Cycle through a list of cached image filenames to change the current bg.

  -c, --config=FILE        Specify the file to interact with for configuration
                           options. These include the bg set command, current
                           offset, image file patterns, and current list of
                           image files.  This file will be overwritten when the
                           background is updated or a directory is scanned.
  -d, --dir=DIR            Specifies a directory to be scanned.
  -r, --recursive          Only valid if -d is specified. Causees all
                           directories under the specified directory to be
                           scanned as well.
  -a, --add                Only valid of -d is specified. Causes the results of
                           this directory scan to be added to any previously
                           scanned directories.  All absolute filenames will
                           be sorted and any duplicates abspaths are culled.
  -n, --next               Set the bg to the next image in the list(default).
  -p, --prev               Set the bg to the prev image in the list.
  -R, --random             Set the bg to a random image in the list.
  -s, --same               Set the bg at the current offset.  Useful in order
                           to set the bg after login if you want it to stay
                           the same.
  -X, --delete-current     Remove the current wallpaper from the index and
                           delete the file associated with it.
  -h, --help               Show this help text.

The default config file is stored at ~/.nextbg.json.  If -c is specified,
this will be used as the config file instead.  If the config file does not
exist, it will be created and initialized with default options.

`feh --bg-scale %s` is used to set the bg by default, and *.jpg and *.png
files in the specified directories are scanned.  To add more image file
patterns or override the bg set command, please edit the config file.
'''.strip();

#-------------------------------------------------------------------
def main(argv):
   # General options.
   config_file = DEFAULT_CONFIG_FILENAME

   # Options for directory scanning.
   search_dir = None
   recursive = False
   additive = False

   # Options for background setting.
   image_offset = 1
   randomize = False
   delete_current = False

   opts, args = getopt.getopt(argv, SHORTOPTS, LONGOPTS)

   for opt, val in opts:
      if opt in ['-h', '--help']:
         print(HELP_TEXT)
         sys.exit(0)

      elif opt in ['-c', '--config']:
         config_file = val

      elif opt in ['-d', '--dir']:
         search_dir = val

      elif opt in ['-a', '--add']:
         additive = True

      elif opt in ['-n', '--next']:
         image_offset = 1

      elif opt in ['-p', '--prev']:
         image_offset = -1

      elif opt in ['-s', '--same']:
         image_offset = 0

      elif opt in ['-r', '--recursive']:
         recursive = True

      elif opt in ['-R', '--random']:
         randomize = True

      elif opt in ['-X', '--delete-current']:
         delete_current = True

   cfg = load_config(config_file)

   if search_dir is not None:
      filenames = scan_dir(cfg, search_dir, recursive)

      if additive:
         cfg['images'].extend(filenames)

      else:
         cfg['images'] = filenames

      cfg['images'] = sorted(set(cfg['images']))

   image_file = None

   if delete_current:
      image_file = delete_current_image(cfg)

   elif randomize:
      image_file = random_image(cfg, image_offset)

   else:
      image_file = increment_image(cfg, image_offset)

   if image_file is not None:
       apply_image(cfg, image_file)

   save_config(cfg, config_file)

   sys.exit(0)

#-------------------------------------------------------------------
def apply_image(cfg, image_file):
   command = cfg['bg_set_command'] % image_file
   result = os.system(command)

   print('Applying background image: "%s"' % image_file)
   if (result != 0):
      raise RuntimeError('Failed to set bg using command: %s (exited with status %d)' % (
               command, result))

#-------------------------------------------------------------------
def increment_image(cfg, image_offset):
   if len(cfg['images']) == 0:
      raise RuntimeError('No images configured.  Use "nextbg.py --dir [directory]" to scan a directory for image files.')

   cfg['offset'] = (cfg['offset'] + image_offset) % len(cfg['images'])
   image_file = cfg['images'][cfg['offset']]
   return image_file

#-------------------------------------------------------------------
def random_image(cfg, image_offset):
   if len(cfg['images']) == 0:
      raise RuntimeError('No images configured.  Use "nextbg.py --dir [directory]" to scan a directory for image files.')

   cfg['offset'] = random.randint(0, len(cfg['images']) - 1)
   image_file = cfg['images'][cfg['offset']]
   return image_file

#-------------------------------------------------------------------
def delete_current_image(cfg):
   if len(cfg['images']) == 0:
      raise RuntimeError('No images configured.  Use "nextbg.py --dir [directory]" to scan a directory for image files.')

   offset_to_delete = cfg['offset']
   image_file = cfg['images'][cfg['offset']]

   # Remove the file on disk and the entry from the list
   # (but only if we could actually delete the file)
   os.remove(image_file)
   cfg['images'].pop(cfg['offset'])

   if len(cfg['images']) > 0:
       # Apply the next image in the list after the one we deleted,
       return increment_image(cfg, 0)
   else:
       print("There are no more images configured.")
       return None

#-------------------------------------------------------------------
def scan_dir(cfg, search_dir, recursive):
   filenames = []

   if recursive:
      for root, dirnames, files in os.walk(search_dir):
         filtered_files = []
         for pattern in cfg['image_file_patterns']:
            filtered_files.extend(fnmatch.filter(files, pattern))

         print("Adding files in %s to bg list" % root)

         for filename in filtered_files:
            filenames.append(full_path(os.path.join(root, filename)))

   else:
      files = os.listdir(search_dir)
      filtered_files = []
      for pattern in cfg['image_file_patterns']:
         filtered_files.extend(fnmatch.filter(files, pattern))

      print("Adding files in %s to bg list" % search_dir)

      for filename in filtered_files:
         filenames.append(full_path(os.path.join(search_dir, filename)))

   return filenames

#-------------------------------------------------------------------
def full_path(path):
   return os.path.abspath(os.path.expanduser(path))

#-------------------------------------------------------------------
def load_config(config_file):
   if not os.path.isfile(full_path(config_file)):
      if config_file == DEFAULT_CONFIG_FILENAME:
         print('Default config file not found, creating it at "%s"...' % config_file)
         save_config(DEFAULT_CONFIG, config_file)

      else:
         raise RuntimeError('No config file found at location "%s"...' % config_file)

   with open(full_path(config_file), 'r') as infile:
      return json.load(infile)

#-------------------------------------------------------------------
def save_config(cfg, config_file):
   with open(full_path(config_file), 'w', encoding = 'utf8') as outfile:
      json.dump(cfg, outfile, indent = 4)

#-------------------------------------------------------------------
if __name__ == '__main__':
   main(sys.argv[1:])
