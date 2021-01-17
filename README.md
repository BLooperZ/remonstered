# DOTT/FT reMONSTERed

Builds sound resource for [ScummVM](https://www.scummvm.org/) using High-Quality SFX and Speech from [DOTT Remastered](http://dott.doublefine.com/) and [FT Remastered](http://fullthrottle.doublefine.com/).

## Download
You can find a ready-to-use build in the [Releases page](https://github.com/BLooperZ/remonstered/releases).
(Built with PyInstaller)

## Install
1. Download and extract the script from respective release. 
for FT, make sure[ffmpeg binaries](https://ffmpeg.zeranoe.com/builds/) is installed or alternatively, extract into script directory. this is also required for conversion feature in DOTT (see `NOTE` below).

2. Drag `full.data` or `tenta.cle` and drop into `remonster.exe`.

3. Game files will be created in the same directory.

4. Add directory to [ScummVM](https://www.scummvm.org/) to play.

### *NOTE*:
It is also possible to convert sounds to `ogg` or `flac` format.

This can be done by providing format argument to the script, when launching via CLI

(assuming `full.data` or `tenta.cle` available at `<respath>`)

`remonster.exe <respath> -f ogg` -> `ogg` format, creates `monster.sog`.
(much smaller file than `mp3`)

`remonster.exe <respath> -f flac` -> `flac` format, creates `monster.sof`. (no reason to use `flac` here as source files are already compressed with lossy compression).

It will take longer time to complete, then you can continue to the next step.

Notice the different output file name (as described above).

This feature requires [ffmpeg binaries](https://ffmpeg.zeranoe.com/builds/) to be installed or to be put in script directory.

When using convertion output may vary depending on ffmpeg version.

## Thanks

* ScummVM Team for [ScummVM](https://www.scummvm.org/) and [ScummVM Tools](https://github.com/scummvm/scummvm-tools).

* LucasArts for the original [Day of the Tentacle](https://en.wikipedia.org/wiki/Day_of_the_Tentacle) and [Full Throttle](https://en.wikipedia.org/wiki/Full_Throttle_(1995_video_game)).

* [DoubleFine Productions](http://www.doublefine.com) for [Day of the Tentacle Remastered](http://dott.doublefine.com/) and [Full Throttle Remastered](http://fullthrottle.doublefine.com/).

* Quick and Easy Software for [DoubleFine Explorer](https://quickandeasysoftware.net/software/doublefine-explorer).

* PyInstaller Development Team for [PyInstaller](https://www.pyinstaller.org/).

* LogicDeLuxe for [Monkey Island Ultimate Talkie Edition](http://www.gratissaugen.de/ultimatetalkies/).

* [elvisish at ScummVM Forums](https://forums.scummvm.org/viewtopic.php?f=8&t=14506) for this idea.
