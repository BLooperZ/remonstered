# FT reMONSTERed (WiP)

Builds sound resource for [ScummVM](https://www.scummvm.org/) using High-Quality SFX and Speech from [FT Remastered](http://fullthrottle.doublefine.com/).

*NOTE*: This project is still Work-in-Progress.
Currently, only speech is supported and might change in future.

## Download
Ready-to-use build not available yet.

In the meantime, check out other projects in the [Releases page](https://github.com/BLooperZ/remonstered/releases).
(Built with PyInstaller)

## Install
1.  Put [ffmpeg binaries](https://ffmpeg.zeranoe.com/builds/) in script directory if not already installed.

2.  Extract the following files from `full.data`:
    * `iMUSEClient_SPEECH.fsb`

    Can be done using [DoubleFine Explorer](https://quickandeasysoftware.net/software/doublefine-explorer)

    ... You can also use it to extract the classic game, to play it using ScummVM.

3.  Put the extracted file in the same directory with the script.

4.  Launch the script (or double click `remonster.exe`)

    This will create a file called `monster.so3` in same directory.

5.  Put `monster.so3` in same directory with the classic game.

    Make sure there are no other `monster` files (`sof`, `sog`, `so3` or `sou`) there.

### *NOTE*:
It is also possible to convert sounds to `ogg` or `flac` format.

This can be done by providing format argument to the script: (step 3)

`remonster.exe ogg` -> `ogg` format, creates `monster.sog`.
(much smaller file than `mp3`)

`remonster.exe flac` -> `flac` format, creates `monster.sof`. (no reason to use `flac` here as source files are already compressed with lossy compression).

It will take longer time to complete, then you can continue to the next step.

Notice the different output file name (as described above).

When using convertion output may vary depending on ffmpeg version.

## Thanks

* ScummVM Team for [ScummVM](https://www.scummvm.org/) and [ScummVM Tools](https://github.com/scummvm/scummvm-tools).

* LucasArts for the original [Full Throttle](https://en.wikipedia.org/wiki/Full_Throttle_(1995_video_game)).

* [DoubleFine Productions](http://www.doublefine.com) for [Full Throttle Remastered](http://fullthrottle.doublefine.com/).

* Quick and Easy Software for [DoubleFine Explorer](https://quickandeasysoftware.net/software/doublefine-explorer).

* PyInstaller Development Team for [PyInstaller](https://www.pyinstaller.org/).

* LogicDeLuxe for [Monkey Island Ultimate Talkie Edition](http://www.gratissaugen.de/ultimatetalkies/).

* [elvisish at ScummVM Forums](https://forums.scummvm.org/viewtopic.php?f=8&t=14506) for this idea.
