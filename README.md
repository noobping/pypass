
![status: archived](https://img.shields.io/badge/status-archived-red)

> I’m no longer maintaining this codebase because I replaced it with a new project: **[PasswordStore](https://github.com/noobping/PasswordStore)**.

# pypassA GTK4 frontend for [Password Store](https://www.passwordstore.org/) written in python


![demo](demo.gif)

## Features
 - Use the result from `pass` by default (Ignores the password directory in the configuration file)
 - Or use the filesystem to show the passwords (Needs the password directory in the configuration file)
 - Optional for both: Hide invalid files (non gpg files)
 - Use `pass-otp` to show or copy the OTP code.
 - Delete selected password when pressing `Delete`
 - Add a new password to the current folder
 - Generates a random password, copy it and uses template fields when creating a new password.
 - Read or copy passwords or other properties (like an username or an (ssh)key) in the view.
 - (Optional) Synchronise your changes with `git`
 - And ofcourse: edit your passwords using `pass`!

## TODO
 - [ ] Integrate Gnome search
 - [ ] Initialize password store if not exists
 - [ ] Add new folders?
 - [ ] Move project to Gnome builder
