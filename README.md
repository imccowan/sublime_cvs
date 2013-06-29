Sublime CVS
============
CVS integration with Sublime Text 2 via menus and keyboard shortcuts.

Features
--------
- Annotate, Diff, Log, Status and Update CVS commands accessible from context and side bar menus.
- CVS status of current file being edited displayed in status bar.

Screenshots
-----------

<img alt="File Context Menu" src="https://raw.github.com/brianhornsby/www_brianhornsby_com/master/img/sublime_cvs_file_context_menu.png" height="128"/>
<img alt="Side Bar Context Menu" src="https://raw.github.com/brianhornsby/www_brianhornsby_com/master/img/sublime_cvs_side_bar_context_menu.png" height="128"/>
<img alt="CVS Annotate" src="https://raw.github.com/brianhornsby/www_brianhornsby_com/master/img/sublime_cvs_file_annotate.png" height="128"/>
<img alt="CVS Diff" src="https://raw.github.com/brianhornsby/www_brianhornsby_com/master/img/sublime_cvs_file_diff.png" height="128"/>
<img alt="CVS Log" src="https://raw.github.com/brianhornsby/www_brianhornsby_com/master/img/sublime_cvs_file_log.png" height="128"/>
<img alt="CVS Status" src="https://raw.github.com/brianhornsby/www_brianhornsby_com/master/img/sublime_cvs_file_status.png" height="128"/>

Installation
------------
Download the Sublime CVS zip file and extract into Sublime Text packages directory. Depending on your system you may have to update the cvs_path setting to point at the correct CVS binary.

Usage
-----
The implemented CVS commands can be accessed from the context menu of the currently open file or a file/folder in the side bar.

**Annotate**: For each file, print the head/working/repository revision of the trunk, together with information on the last modification for each line.

**Diff**: Compare your working files with the revisions they were based on, and report any differences that are found.

**Log**: Print out log information of a file.

**Status**: Display the state of a file in the working directory.

**Update**: Bring work tree in sync with repository. The key bindings can be modified by selecting the Preferences > Package Settings > CVS > Key Bindings – User menu entry.

Settings
--------
The default settings can be viewed by accessing the Preferences > Package Settings > CVS > Settings – Default menu entry. To ensure settings are not lost when the package is upgraded, make sure all edits are saved to Settings – User .

**cvs_path**: The path to the cvs binary. Default: /usr/bin/cvs

**cache_length**: The number of seconds of time to cache CVS statuses - tweaking this may help computers with slower hard drives. Default: 5

**diff_unified_output**: Set to true if CVS diff should output in unified format. Default: false

**cvs_status_new_file**: If the output from CVS status should be displayed in a new file, rather than a panel. Allowed values: 'always', 'foldersonly', 'never'. Default: never

**cvs_log_show_tags**: If the output from CVS log should show tags. Default: true

**debug**: Set to true if debug messages should be printed to the console. Default: false

License
-------
Sublime CVS is licensed under the [MIT license](https://raw.github.com/brianhornsby/sublime_cvs/master/LICENSE.txt).
