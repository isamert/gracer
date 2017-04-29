# Gracer
A rust code completion plugin for gedit. Built with the Rust auto completion tool by Phil Dawes (https://github.com/phildawes/racer).

![Example](/screenshots/completion-1.png)

## Current Features:
- Autocompletion
- Find Definition (with right-click menu)

## Prerequisites
- racer should already be installed. If you did not installed it until now run:
```cargo install racer```
- a copy of the rust source should be on your system. If you did not download the rust source so far run: 
```rustup component add rust-src```
for other installation methods please refer to: https://github.com/phildawes/racer/blob/master/README.md

## Using
- Download the project.
- Extract the files to /home/YOUR_USER_NAME/.local/share/gedit/plugins
- If the directory .local/share/gedit/plugins/ is not present, create it.
- Open gedit, go to Preferences > Plugins > Gracer to activate it.
- From plugins menu, open Gracer's Preferences.
- Set Racer path and Rust source path.
- Restart gedit.

Instead of downloading you can just clone the project to your plugin path:
```
$ mkdir -p ~/.local/share/gedit/plugins
$ cd ~/.local/share/gedit/plugins
$ git clone https://github.com/isamert/gracer.git
```
For updating:
```
$ cd ~/.local/share/gedit/plugins/gracer
$ git pull
```
