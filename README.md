# DOTT reMONSTERed

Builds sound resource for [ScummVM](https://www.scummvm.org/) using High-Quality SFX and Speech from [DOTT Remastered](http://dott.doublefine.com/).

## Download
You can find a ready-to-use build in the [Releases page](https://github.com/BLooperZ/remonstered/releases).
(Built with PyInstaller)

## Install
1.  Extract the following files from `tenta.cle`:
    * `iMUSEClient_SFX.fsb`
    * `iMUSEClient_VO.fsb` 

    Can be done using [DoubleFine Explorer](https://quickandeasysoftware.net/software/doublefine-explorer)

    ... You can also use it to extract the classic game, to play it using ScummVM.

2.  Put the extracted file in the same directory with the script.

3.  Launch the script (or double click `remonster.exe`)

    This will create a file called `monster.so3` in same directory.

4.  Put `monster.so3` in same directory with the classic game.

    Make sure there are no other `monster` files (`sof`, `sog`, `so3` or `sou`) there.

### *NOTE*:
It is also possible to convert sounds to `ogg` or `flac` format.

This can be done by providing format argument to the script:

`remonster.exe ogg` -> `ogg` format, creates `monster.sog`.
(much smaller file than `mp3`)

`remonster.exe flac` -> `flac` format, creates `monster.sof`. (no reason to use `flac` here as source files are already compressed with lossy compression).

This feature requires [ffmpeg binaries](https://ffmpeg.zeranoe.com/builds/) to be installed or to be put in script directory.

When using convertion output may vary depending on ffmpeg version.

## Thanks

* ScummVM Team for [ScummVM](https://www.scummvm.org/) and [ScummVM Tools](https://github.com/scummvm/scummvm-tools).

* LucasArts for the original [Day of the Tentacle](https://en.wikipedia.org/wiki/Day_of_the_Tentacle).

* [DoubleFine Productions](http://www.doublefine.com) for [Day of the Tentacle Remastered](http://dott.doublefine.com/).

* Quick and Easy Software for [DoubleFine Explorer](https://quickandeasysoftware.net/software/doublefine-explorer).

* PyInstaller Development Team for [PyInstaller](https://www.pyinstaller.org/).

* LogicDeLuxe for [Monkey Island Ultimate Talkie Edition](http://www.gratissaugen.de/ultimatetalkies/).

* [elvisish at ScummVM Forums](https://forums.scummvm.org/viewtopic.php?f=8&t=14506) for this idea.
