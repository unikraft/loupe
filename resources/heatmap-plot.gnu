set terminal svg enhanced font "arial,14" size 700, 250

unset key

set view map scale 1
set style data lines

unset xtics
unset ytics
unset ztics
set rtics axis in scale 0,0 nomirror norotate  autojustify

set xrange  [ -23.500000 : 0.50000 ] noreverse nowriteback
set yrange  [ -0.500000 : 13.50000 ] noreverse nowriteback
set cbrange [ 0 : 100 ]

set cblabel "Apps requiring the system call [%]"

set palette defined (\
0 "#fbfdbf", \
1 "#fec287", \
2 "#fb8761", \
3 "#e55964", \
4 "#b5367a", \
5 "#812581", \
6 "#4f127b", \
8 "#1c1044" \
)

set output '/mnt/heapmap-static-binary.svg'
plot '/mnt/data-staticbinary.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"

set output '/mnt/heapmap-static-source.svg'
plot '/mnt/data-staticsource.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"

set output '/mnt/heapmap-dynamic-used.svg'
plot '/mnt/data-dynused.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"

set output '/mnt/heapmap-dynamic-stubfake.svg'
plot '/mnt/data-dynstubfake.dat' u (-$1):2:3 with image pixels, \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 >= 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "black", \
	'' u (-$1):2:($3 == 0 ? "" : \
		$3 < 60 ? "" : sprintf("%g",$4)) with labels font ",12" tc "white"
