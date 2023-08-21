# SPDX-License-Identifier: BSD-3-Clause
#
# Authors:  Gaulthier Gain <gaulthier.gain@uliege.be>
#           Benoit Knott <benoit.knott@student.uliege.be>
#
# Copyright (c) 2020-2023, University of Liège. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Utilities to store information about and analyse the ELF 64-bit executable.
"""

import lief

from syscalls import syscalls_map, alias_syscalls_map


TEXT_SECTION     = ".text"
PLT_SECTION      = ".plt"
PLT_SEC_SECTION  = ".plt.sec"


def is_valid_binary(binary):
    """Verifies that the given binary is an ELF binary for the `x86_64`
    architecture

    Parameters
    ----------
    binary : lief binary
        the binary to check

    Returns
    -------
    is_valid_binary : bool
        True if the tests pass
    """

    return (binary is not None
            and binary.format == lief.EXE_FORMATS.ELF
            and binary.header.identity_class == lief.ELF.ELF_CLASS.CLASS64
            and binary.header.machine_type == lief.ELF.ARCH.x86_64)

def get_syscalls_from_symbols(binary, syscalls_set):
    """Try to detect syscalls used in the binary thanks to its symbolic
    information (for example checking the presence of wrappers).

    Parameters
    ----------
    binary : lief binary
        the binary to analyse
    syscalls_set : set of str
        set of syscalls used by the program analysed that will be updated
    """

    for sect_it in [binary.dynamic_symbols, binary.static_symbols,
                    binary.symbols]:
        __detect_syscalls_in_sym_table(sect_it, syscalls_set)

def __detect_syscalls_in_sym_table(sect_it, syscalls_set):

    for s in sect_it:
        name = s.name
        name_value = alias_syscalls_map.get(name)
        if name_value is not None:
            name = alias_syscalls_map[name]

        if name in syscalls_map:
            syscalls_set.add(name)
