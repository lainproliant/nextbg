nextbg
======

A handy python script for indexing and dynamically switching wallpaper images in Linux.

```
Usage: nextbg.py [SET_OPTIONS]/[[DIR_OPTIONS] -d/--dir DIRECTORY]

Cycle through a list of cached image filenames to change the current bg.

  -c, --config=FILE        Specify the file to interact with for configuration
                           options. These include the bg set command, current
                           offset, image file patterns, and current list of
                           image files.  This file will be overwritten when the
                           background is updated or a directory is scanned.
  -d, --dir=DIR            Specifies a directory to be scanned.
  -r, --recursive          Only valid if -d is specified. Causes all
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
  -h, --help               Show this help text.

The default config file is stored at ~/.nextbg.json.  If -c is specified,
this will be used as the config file instead.  If the config file does not
exist, it will be created and initialized with default options.

`feh --bg-scale %s` is used to set the bg by default, and *.jpg and *.png
files in the specified directories are scanned.  To add more image file
patterns or override the bg set command, please edit the config file.
```
