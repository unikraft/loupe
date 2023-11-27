**News**
- Loupe's paper, [Loupe: Driving the Development of OS Compatibility Layers
](https://arxiv.org/pdf/2309.15996.pdf), has been accepted in [ASPLOS'24](https://www.asplos-conference.org/asplos2024/)!

* * *

Loupe is a tool designed to help you analyze the system call usage of your application.

Loupe can do primarily two things: (1) collect data about the system call usage of your application(s), and (2) analyze the data collected for your application(s). It can tell you what system calls you need to run them, and visualize these numbers in a variety of plots.

Loupe is based on dynamic analysis, but it is also able to gather static analysis data. We put the emphasis on reproducible analysis: measurements are made in a Docker container.

Loupe stores analysis results in a custom database. A Loupe database is nothing more than a git repository with a [particular layout](https://github.com/unikraft/loupe/blob/staging/doc/DATABASE_FORMAT.md). We offer an online, open [database](https://github.com/unikraft/loupedb) maintained by the community. Feel free to pull request your analysis results!

### Contact

- [Hugo Lefeuvre](https://owl.eu.com/), The University of Manchester: hugo.lefeuvre *at* manchester.ac.uk
- [Pierre Olivier](https://sites.google.com/view/pierreolivier), The University of Manchester: pierre.olivier *at* manchester.ac.uk

* * *

Loupe is supported in part by a studentship from NEC Labs Europe, a Microsoft Research PhD Fellowship, UK’s EPSRC grants EP/V012134/1 (UniFaaS), EP/V000225/1 (SCorCH), and the EPSRC/Innovate UK grant EP/X015610/1 (FlexCap), the EU H2020 grants 825377 (UNICORE), 871793 (ACCORDION) and 758815 (CORNET), and VMWare gift funding.
