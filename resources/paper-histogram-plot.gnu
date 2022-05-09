set terminal svg enhanced size 720, 180 font 'Arial,12'
set output '/mnt/paper-histogram.svg'

# draw all borders
set border front lt "#AFC1D6" linewidth 1.000 dashtype solid

# bar width
set boxwidth 0.7 absolute

set grid nopolar
set grid noxtics nomxtics ytics nomytics noztics nomztics nortics nomrtics \
 nox2tics nomx2tics noy2tics nomy2tics nocbtics nomcbtics
set grid layerdefault   lt 0 linecolor 0 linewidth 0.500,  lt 0 linecolor 0 linewidth 0.500

# legend
set key bmargin enhanced vertical center autotitle columnhead samplen 1 maxrows 1 font ",10" width -3
set bmargin at screen 0.4

# title offset to increase the distance between the bar labels
# (all, suite, etc.) and the group labels (Redis, Nginx, etc).
set style histogram rowstacked title offset character 0, -0.3
set style fill solid 1.0 border -1
set style /mnt histograms

set /mntfile missing '-'

set xtics border in scale 0,0 nomirror autojustify  rotate by -25 font ",11"
set ytics border in scale 0,0 mirror norotate  autojustify

# uncomment these two lines to add the title
#set title "System Call Usage of Varying Applications\n{/*0.8 (static and dynamic with varying workload)}"
#set title font ",12"

# y label closer to the axis
set ylabel "N# of syscalls used" offset 1.5,0
set lmargin 7

# bars between applications
set arrow from 4, graph 0 to 4, graph 1 nohead
set arrow from 9, graph 0 to 9, graph 1 nohead
set arrow from 14, graph 0 to 14, graph 1 nohead
set arrow from 19, graph 0 to 19, graph 1 nohead
set arrow from 24, graph 0 to 24, graph 1 nohead
set arrow from 29, graph 0 to 29, graph 1 nohead
set arrow from 34, graph 0 to 34, graph 1 nohead

plot newhistogram "{/:Bold Redis}", '/mnt/redis.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold Nginx}", '/mnt/nginx.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold Memcached}", '/mnt/memcached.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold SQLite}", '/mnt/sqlite.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold HAProxy}", '/mnt/haproxy.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold Lighttpd}", '/mnt/lighttpd.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold weborf}", '/mnt/weborf.dat' \
            u "staticsrc":xtic(1) lc "#FCD29F", \
         '' u "staticbin" lc "#655A7C", \
         '' u "required" lc "#AB92BF", \
         '' u "stubonly" lc "#AFC1D6", \
         '' u "fakeonly" lc "#CEF9F2", \
         '' u "fakeorstub" lc "#A9FFCB", \
     newhistogram "{/:Bold webfsd}", '/mnt/webfsd.dat' \
            u "staticsrc":xtic(1) t "{/:Italic Stat source}" lc "#FCD29F", \
         '' u "staticbin" t "{/:Italic Stat binary}" lc "#655A7C", \
         '' u "required" t "{/:Italic Dyn} required" lc "#AB92BF", \
         '' u "stubonly" t "{/:Italic Dyn} stubbed" lc "#AFC1D6", \
         '' u "fakeonly" t "{/:Italic Dyn} faked" lc "#CEF9F2", \
         '' u "fakeorstub" t "{/:Italic Dyn} any" lc "#A9FFCB"
