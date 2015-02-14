# sf2fix
An utility to analyse LMMS files in input folder, searching for 
soundfont paths, and to replace paths by a valid one if soundfont files 
do not exist in file system.


Requirements
---------------
Python 2.7+ or Python 3.3+


Usage
-------
sf2fix.py inputfolder [replacement soundfont]


Example
-------
sf2fix.py . "/usr/share/sounds/sf2/FluidR3_GM.sf2"
>Scans current folder and searches for *.mmp and *.mmpz files.
>Analyses theses files and searches for "sf2player" instruments.
>If the path to soundfont (in "src" attribute) does not exist, it is 
replaced by "/usr/share/sounds/sf2/FluidR3_GM.sf2"
>Modified files are saved in the same folder as input files with "_mod"
suffix.
