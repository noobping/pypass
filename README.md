# pypass
A GTK4 frontend for [Password Store](https://www.passwordstore.org/) written in python

![demo](demo.gif)

## Features
 - Automaticly pull using `pass git pull`
 - Use the result from `pass` by default (Ignores the password directory in the configuration file)
 - Or use the filesystem to show the passwords (Needs the password directory in the configuration file)
 - Optional for both: Hide invalid files (non gpg files)
 - Use `pass-otp` to show or copy the OTP code.
 - And ofcourse: **Read**, **copy** & **edit** your passwords using `pass`!

## TODO
 - [ ] Integrate Gnome search
 - [ ] Initialize password store if not exists
 - [ ] Add new passwords (and folders)
 - [ ] Move project to Gnome builder
