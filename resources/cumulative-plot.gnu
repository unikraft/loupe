#!/usr/bin/gnuplot

reset

set terminal svg enhanced size 650,300 font 'Arial,20'

set grid

# Make the x axis labels easier to read.
set xtics font ",18" nomirror
set ytics nomirror

# make sure that the legend doesn't take too much space
set key inside top right samplen 1 font ',18' width -7

# ensure that y label doesn't take too much space
set ylabel "API Importance [%]" offset 2.5,0
set xlabel "Nth most important system call" offset 0,0.5

# remove useless margins
#set bmargin 2
set lmargin 7
set rmargin 1
set tmargin 0.5

# line styles
set style line 1 \
    linecolor '#377eb8' \
    linetype 1 linewidth 2 \
    pointtype 7 pointsize 0.1
set style line 2 \
    linecolor '#984ea3' \
    linetype 2 linewidth 2 \
    pointtype 7 pointsize 0.1
set style line 3 \
    linecolor '#e41a1c' \
    linetype 1 linewidth 2 \
    pointtype 5 pointsize 0.1
set style line 4 \
    linecolor '#ff7f00' \
    linetype 2 linewidth 2 \
    pointtype 11 pointsize 0.1

# use this to set the range, although the default one seems to be good here
#set yrange [0:3.5]
set xrange [0:250]

set output '/mnt/cumulative-all.svg'
plot '/mnt/data.dat' \
        index 0 with linespoints linestyle 1 t "Static (binary)", \
     '' index 1 with linespoints linestyle 2 t "Static (source)", \
     '' index 2 with linespoints linestyle 3 t "Dynamic (executed)", \
     '' index 3 with linespoints linestyle 4 t "Dynamic (required)" \

set output '/mnt/cumulative-nobinary.svg'
plot '/mnt/data.dat' \
        index 1 with linespoints linestyle 1 t "Static (source)", \
     '' index 2 with linespoints linestyle 2 t "Dynamic (executed)", \
     '' index 3 with linespoints linestyle 3 t "Dynamic (required)" \

set output '/mnt/cumulative-nosource.svg'
plot '/mnt/data.dat' \
        index 0 with linespoints linestyle 1 t "Static (binary)", \
     '' index 2 with linespoints linestyle 2 t "Dynamic (executed)", \
     '' index 3 with linespoints linestyle 3 t "Dynamic (required)" \

set output '/mnt/cumulative-nostatic.svg'
plot '/mnt/data.dat' \
        index 2 with linespoints linestyle 1 t "Dynamic (executed)", \
     '' index 3 with linespoints linestyle 2 t "Dynamic (required)" \
