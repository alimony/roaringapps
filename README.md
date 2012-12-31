About
=====

This script will look for installed applications on your computer, and check each found application for compatibility with recent versions of Mac OS X, based on data from [roaringapps.com](http://roaringapps.com).

Usage
=====
Just run the script:

```
./roaringapps.py
```

You might need to make it executable first:

```
chmod +x roaringapps.py
```

Run without any options, the script will look for installed applications in the `/Applications` and `~/Applications` folders, and report any incompatibilities with either Mac OS X 10.7 or 10.8.

Options
-------

The script can be configured in a few ways, run it with the `--help` option to see all available options:

```
-a APPFOLDER, --app-folder APPFOLDER
                      Folders to scan for installed applications. Can be
                      specified several times. Defaults to /Applications and
                      ~/Applications.
-v, --verbose         Show complete compatibility data, not just
                      incompatible applications.
-l, --lion-only       Only show Mac OS X 10.7 (Lion) compatibility data.
-m, --mountain-lion-only
                      Only show Mac OS X 10.8 (Mountain Lion) compatibility
                      data.
-w, --wrapper-mode    Format output to be suitable for a wrapper
                      application. All lines will start with an easily
                      greppable hook name, and any following data is split
                      into tab-separated fields.
-r, --refresh-cache   Force fetching of installed apps and remote
                      compatibility data, instead of using cached data. The
                      default is to cache all data for an hour.
```
