What does it do?
================

This script calculates chess ratings from a given list of games. It uses the Elo system or the [Glicko system](http://www.glicko.net/glicko/glicko.pdf).

Chess Rankings (example)
========================

![ratings plot](ratingsplot.png?raw=true)

How to use
==========

Requirements
------------

Apart from Python 3, this script needs matplotlib and numpy. They can be installed via `pip install matplotlib numpy`.

Write down game results
-----------------------

Formatting is like this:

    white_player  black_player  result1 result2
    white_player  black_player  result1 result2
    ...
    Jack          Mary          0       1       # Mary plays black and beats John

The player names can be short names (such as initials) and then in a separate file, the full names are defined:

    JD  John Doe
    ...

These files are then given in the script (NAMEFILE and GAMESFILE). Executing the script prints the league table for every game day to the console and produces a `ratingsplot.png` that plots the development of players' ratings.

Configuration
-------------

Global variables at the top of the script are explained in the comments next to them. The variable GLICKO can be set via command line argument "-g" and turns on the glicko rating system, else Elo is used.
