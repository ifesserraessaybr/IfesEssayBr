# -*- coding: utf-8 -*-
"""
Separação de sílabas e determinação da tonicidade (Português Brasileiro)
Port Python baseado em src/main/java/Syllable.java
"""
from __future__ import annotations

from typing import List

# --- Sets de grafemas ---
VOWELS = set("aeoáéóíúãõâêôàü")
SEMI = {"i", "u"}
NASAL = {"m", "n"}
LIQ = {"l", "r"}  # 'rr' tratado em regras
FRIC = {"f", "v", "s", "ç", "z", "j", "x"}
FRIC_BIG = {"ce", "ci", "ss", "ch", "ge", "gi"}
OCC = {"p", "t", "b", "d"}
OCC_BIG = {"ca", "co", "cu", "ga", "go", "gu", "gú", "que", "qui", "gue", "gui"}
DIGR = {"lh", "nh"}
DIGR_SEP = {"rr", "ss", "sc", "xc", "xs"}
MUTE = set("bgpcdft")

ACUTE_CIRC = set("áéóíúâêîôûà")
TIL = {"ã", "õ"}


def _is_vowel(w: str, i: int) -> bool:
    wlen = len(w)
    c = w[i]
    if c in VOWELS:
        return True
    # encontros vocálicos: i/u podem ser semivogal
    if c in ("i", "u"):
        if i + 1 < wlen:
            # ditongos crescentes finais 'ia' ou 'io'
            if c == "i" and w[i + 1] in ("a", "o") and i + 2 >= wlen:
                return True
            if w[i + 1] in VOWELS:
                return False
            else:
                if i - 1 >= 0:
                    return False if w[i - 1] in VOWELS else True
                else:
                    return True
        else:
            if i - 1 >= 0:
                return False if w[i - 1] in VOWELS else True
            else:
                return True
    return False


def _is_vowel_or_semi(c: str) -> bool:
    return (c in VOWELS) or _is_semi(c)


def _is_semi_char(c: str) -> bool:
    return c in ("i", "u")


def _is_semi(w: str, i: int) -> bool:
    return _is_semi_char(w[i])


def _is_digraph(w: str, i: int) -> bool:
    if i + 1 >= len(w):
        return False
    return w[i : i + 2] in DIGR


def _is_digraph_sep(w: str, i: int) -> bool:
    if i + 1 >= len(w):
        return False
    return w[i : i + 2] in DIGR_SEP


def _is_occlusive(w: str, i: int) -> bool:
    tail = w[i:]
    for s in OCC | OCC_BIG:
        if len(s) == 1:
            if tail.startswith(s):
                return True
        elif len(s) == 2:
            if len(tail) >= 2 and tail.startswith(s):
                return True
        else:  # 3
            if len(tail) >= 3 and tail.startswith(s):
                return True
    return False


def _is_fricative(w: str, i: int) -> bool:
    tail = w[i:]
    if tail and tail[0] in FRIC:
        return True
    for s in FRIC_BIG:
        if tail.startswith(s):
            return True
    return False


def _is_mute_consonant(w: str, i: int) -> bool:
    if i + 1 >= len(w):
        return False
    if w[i] in MUTE:
        if w[i + 1] in VOWELS:
            return False
        if w[i + 1] in ("l", "r") or _is_vowel(w, i + 1) or _is_semi(w, i + 1):
            return False
        return True
    return False


def _is_liquid(w: str, i: int) -> bool:
    if w[i] == "l":
        return not (i < len(w) - 1 and w[i + 1] == "h")
    return w[i] == "r"


def _is_nasal(w: str, i: int) -> bool:
    return w[i] in NASAL


def _is_consonant(w: str, i: int) -> bool:
    if _is_digraph(w, i):
        return True
    if _is_occlusive(w, i):
        return True
    if _is_fricative(w, i):
        return True
    if _is_liquid(w, i):
        return True
    if _is_nasal(w, i):
        return True
    if w[i] in ("g", "c"):
        return True
    return False


def _rule12_part1(w: str, nucleo: int) -> bool:
    wlen = len(w)
    if _is_consonant(w, nucleo - 1):
        if (
            nucleo + 1 < wlen
            and (
                _is_liquid(w, nucleo + 1)
                or _is_nasal(w, nucleo + 1)
                or w[nucleo + 1] in ("c", "x")
            )
            and nucleo + 3 < wlen
            and (
                _is_vowel(w, nucleo + 3)
                or w[nucleo + 3] in ("h", "l", "r")
            )
        ):
            return True
    else:
        if nucleo - 2 >= 0 and w[nucleo - 1] in ("u", "ü") and w[nucleo - 2] in ("q", "g"):
            if (
                nucleo + 1 < wlen
                and (
                    _is_liquid(w, nucleo + 1)
                    or _is_nasal(w, nucleo + 1)
                    or w[nucleo + 1] in ("c", "x")
                )
                and nucleo + 3 < wlen
                and (
                    _is_vowel(w, nucleo + 3)
                    or w[nucleo + 3] in ("h", "l", "r")
                )
            ):
                return True
    return False


def _q_or_g_before_u(w: str, i: int) -> bool:
    return w[i] == "u" and i - 1 >= 0 and w[i - 1] in ("q", "g")


def _find_vowel(w: str, i: int, stressed_graph: int) -> int:
    for k in range(i, len(w)):
        if _is_vowel(w, k):
            if stressed_graph < k and stressed_graph >= i:
                return stressed_graph
            else:
                return k
    return -1


def _is_vowel_or_semi_char(c: str) -> bool:
    return (c in VOWELS) or (c in ("i", "u"))


def _find_second_last_vowel(w: str) -> int:
    count = 0
    for k in range(len(w) - 1, -1, -1):
        if _is_vowel_or_semi_char(w[k]):
            count += 1
        if count == 2:
            return k
    return -1


def stressed_syllable(w: str) -> int:
    stressedlevel = 100
    stressedpos = 0
    pos_penult = _find_second_last_vowel(w)
    lenw = len(w)

    for i in range(lenw - 1, -1, -1):
        if i == lenw - 1:
            if pos_penult != -1 and stressedlevel > 19:
                stressedlevel = 19
                stressedpos = pos_penult
            if (
                lenw >= 4
                and w[i] == "m"
                and w[i - 1] == "e"
                and w[i - 2] == "u"
                and w[i - 3] == "q"
                and stressedlevel > 18
            ):
                stressedlevel = 18
                stressedpos = i - 1
            if pos_penult != -1 and stressedlevel > 17:
                if w[pos_penult] in ("i", "u"):
                    if (
                        pos_penult - 1 >= 0
                        and _is_vowel_or_semi_char(w[pos_penult - 1])
                        and pos_penult + 1 < lenw
                        and not _is_vowel_or_semi_char(w[pos_penult + 1])
                    ):
                        if pos_penult - 2 >= 0:
                            if w[pos_penult - 2] not in ("q", "g"):
                                stressedlevel = 17
                                stressedpos = pos_penult - 1
                        else:
                            stressedlevel = 17
                            stressedpos = pos_penult - 1
            if (
                lenw > 4
                and w[i] in ("a", "e", "o")
                and _is_consonant(w, i - 1)
                and w[i - 2] == "n"
                and w[i - 3] in ("i", "u")
                and _is_vowel_or_semi_char(w[i - 4])
                and stressedlevel > 16
            ):
                stressedpos = i - 3
                stressedlevel = 16
            if (
                lenw >= 6
                and w[i] == "s"
                and _is_vowel(w, i - 1)
                and _is_vowel(w, i - 4)
                and w[i - 3] in ("i", "u")
                and not _is_vowel(w, i - 2)
                and w[i - 5] not in ("q", "g")
                and stressedlevel > 15
            ):
                stressedpos = i - 4
                stressedlevel = 15
            if (
                lenw >= 5
                and _is_vowel(w, i)
                and _is_vowel(w, i - 3)
                and w[i - 2] in ("i", "u")
                and not _is_vowel(w, i - 1)
                and w[i - 4] not in ("q", "g")
                and stressedlevel > 14
            ):
                stressedpos = i - 3
                stressedlevel = 14
            if (
                lenw >= 3
                and _is_vowel(w, i)
                and w[i - 1] in ("i", "u")
                and _is_vowel(w, i - 2)
                and stressedlevel > 13
            ):
                stressedpos = i - 2
                stressedlevel = 13
            if (
                lenw >= 5
                and w[i] == "s"
                and w[i - 1] == "e"
                and w[i - 2] == "u"
                and w[i - 3] in ("q", "g")
                and stressedlevel > 12
            ):
                stressedpos = i - 4 if _is_vowel_or_semi_char(w[i - 4]) else i - 5
                stressedlevel = 12
            if (
                lenw >= 4
                and w[i] == "e"
                and w[i - 1] == "u"
                and w[i - 2] in ("q", "g")
                and stressedlevel > 11
            ):
                stressedpos = i - 3 if _is_vowel_or_semi_char(w[i - 3]) else i - 4
                stressedlevel = 11
            if (
                lenw > 5
                and i >= 5
                and w[i] == "e"
                and w[i - 1] == "u"
                and w[i - 2] == "q"
                and w[i - 3] == "r"
                and w[i - 4] == "o"
                and w[i - 5] == "p"
                and stressedlevel > 10
            ):
                stressedlevel = 10
                stressedpos = i
            if (
                i - 2 >= 0
                and w[i] == "s"
                and w[i - 1] in ("i", "u")
                and not _is_vowel(w, i - 2)
                and stressedlevel > 9
            ):
                stressedlevel = 9
                stressedpos = i - 1
            if (
                i - 1 >= 0
                and i - 2 >= 0
                and w[i] == "s"
                and w[i - 1] in ("i", "u")
                and _is_vowel_or_semi_char(w[i - 2])
                and stressedlevel > 8
            ):
                stressedlevel = 8
                stressedpos = i - 2
            if (w[i] in ("i", "u") and stressedlevel > 7):
                if i - 1 >= 0 and _is_vowel_or_semi_char(w[i - 1]) and w[i - 1] != "u":
                    stressedpos = i - 1
                else:
                    stressedpos = i
                stressedlevel = 7
            if (
                i - 3 >= 0
                and w[i] == "s"
                and w[i - 1] == "i"
                and w[i - 2] in ("u", "ü")
                and w[i - 3] in ("q", "g")
                and stressedlevel > 6
            ):
                stressedlevel = 6
                stressedpos = i - 1
            if (
                i - 2 >= 0
                and w[i] == "i"
                and w[i - 1] in ("u", "ü")
                and w[i - 2] in ("q", "g")
                and stressedlevel > 5
            ):
                stressedlevel = 5
                stressedpos = i
            if (
                i - 2 >= 0
                and w[i] == "s"
                and w[i - 1] == "n"
                and w[i - 2] in ("i", "o", "u")
                and stressedlevel > 4
            ):
                stressedlevel = 4
                stressedpos = i - 2
            if (
                i - 1 >= 0
                and w[i] == "m"
                and w[i - 1] in ("i", "o", "u")
                and stressedlevel > 3
            ):
                stressedlevel = 3
                stressedpos = i - 1
            if (
                w[i] in ("r", "l", "z", "x", "n") and stressedlevel > 2
            ):
                stressedlevel = 2
                stressedpos = i - 1
        if w[i] in ACUTE_CIRC:
            stressedlevel = 0
            stressedpos = i
        elif w[i] in TIL and stressedlevel > 1:
            stressedlevel = 1
            stressedpos = i
    return stressedpos


def _get_syllable(w: str, begin: int, end: int) -> str:
    return w[begin : end + 1]


def word2syllables(w: str) -> List[str]:
    s: List[str] = []
    wlen = len(w)
    stressed_graph = stressed_syllable(w)

    i = 0
    while i < wlen:
        nucleo = _find_vowel(w, i, stressed_graph)
        if w[i] in VOWELS or w[i] in ("i", "u"):
            if (
                i + 1 < wlen
                and w[i] in ("a", "e", "o")
                and w[i + 1] in ("i", "u")
            ):
                begin = i
                end = i
                if stressed_graph != (i + 1):
                    end = i + 1
            elif (
                w[i] not in ("ã", "õ")
                and i + 1 < wlen
                and _is_vowel(w, i + 1)
                and not _is_semi(w, i + 1)
            ):
                begin = i
                end = i
            elif (
                i + 3 < wlen
                and _is_consonant(w, i + 1)
                and _is_consonant(w, i + 2)
                and (_is_occlusive(w, i + 3) or _is_liquid(w, i + 3) or _is_digraph_sep(w, i + 2))
            ):
                if _is_occlusive(w, i + 3) or _is_digraph_sep(w, i + 2):
                    begin = i
                    end = i + 2
                else:
                    begin = i
                    end = i + 1
            elif (
                i + 2 < wlen
                and (_is_semi(w, i + 1) or _is_nasal(w, i + 1) or w[i + 1] in ("s", "r", "l", "x"))
                and _is_consonant(w, i + 2)
                and w[i + 2] not in ("h", "r")
            ):
                begin = i
                end = i + 1
            elif i + 3 < wlen and _is_consonant(w, i + 1) and _is_consonant(w, i + 2) and _is_vowel(w, i + 3):
                begin = i
                end = i
                if _is_mute_consonant(w, i + 1):
                    end = i + 1
            elif i + 3 < wlen and _is_digraph(w, i + 1) and (_is_vowel(w, i + 3) or _is_liquid(w, i + 3)):
                begin = i
                end = i
            elif i + 2 < wlen and _is_consonant(w, i + 1) and (_is_vowel(w, i + 2) or _is_liquid(w, i + 2)):
                begin = i
                end = i
            elif i + 1 < wlen and _is_occlusive(w, i + 1):
                begin = i
                end = i
            else:
                begin = i
                end = wlen - 1
            syll = _get_syllable(w, begin, end)
            i += (end - begin)
            s.append(syll)
        else:
            if nucleo - 1 >= 0:
                if (
                    nucleo + 3 < wlen
                    and _is_consonant(w, nucleo - 1)
                    and (_is_digraph(w, nucleo + 1) or (w[nucleo + 1] == "c" and w[nucleo + 2] == "h"))
                    and _is_vowel(w, nucleo + 3)
                ):
                    begin = i
                    end = nucleo
                elif (
                    nucleo + 1 < wlen
                    and _is_consonant(w, nucleo - 1)
                    and nucleo + 2 < wlen
                    and _is_consonant(w, nucleo + 1)
                    and _is_vowel(w, nucleo + 2)
                ):
                    begin = i
                    end = nucleo
                elif (
                    nucleo + 3 < wlen
                    and _is_consonant(w, nucleo - 1)
                    and _is_semi(w, nucleo + 1)
                    and w[nucleo + 2] == "s"
                    and _is_occlusive(w, nucleo + 3)
                ):
                    begin = i
                    end = nucleo + 2
                elif (
                    nucleo + 3 < wlen
                    and _is_consonant(w, nucleo - 1)
                    and _is_semi(w, nucleo + 1)
                    and w[nucleo + 2] == "r"
                    and _is_consonant(w, nucleo + 3)
                ):
                    begin = i
                    end = nucleo + 2
                elif (
                    ( _is_consonant(w, nucleo - 1) or _is_semi(w, nucleo - 1) )
                    and nucleo + 2 < wlen
                    and _is_semi(w, nucleo + 1)
                    and _is_consonant(w, nucleo + 2)
                    and (
                        (nucleo + 2 == wlen - 1 and w[nucleo + 2] not in ("m", "n", "r", "s"))
                        or (nucleo + 2 != wlen - 1)
                    )
                ):
                    begin = i
                    end = nucleo + 1
                elif (
                    nucleo + 1 < wlen
                    and _is_consonant(w, nucleo - 1)
                    and _is_semi(w, nucleo + 1)
                    and (nucleo + 2 >= wlen or _is_vowel(w, nucleo + 2))
                ):
                    begin = i
                    end = nucleo + 1
                elif (
                    nucleo + 2 < wlen
                    and _is_semi(w, nucleo - 1)
                    and _is_consonant(w, nucleo + 1)
                    and _is_vowel(w, nucleo + 2)
                ):
                    begin = i
                    end = nucleo - 1
                    if nucleo - 2 >= 0 and _q_or_g_before_u(w, nucleo - 1):
                        end = nucleo
                elif _rule12_part1(w, nucleo):
                    begin = i
                    end = nucleo + 1
                    if (
                        w[nucleo + 2] in ("h", "l", "r")
                        or w[nucleo + 1] == "c"
                        or (_is_nasal(w, nucleo + 1) and _is_vowel(w, nucleo + 2))
                    ):
                        if not _is_mute_consonant(w, nucleo + 1) and w[nucleo + 1] != w[nucleo + 2]:
                            end = nucleo
                elif (
                    nucleo + 1 < wlen
                    and _is_consonant(w, nucleo - 1)
                    and (_is_liquid(w, nucleo + 1) or _is_nasal(w, nucleo + 1) or w[nucleo + 1] == "i")
                ):
                    begin = i
                    end = nucleo + 2
                    if nucleo + 2 >= wlen:
                        end = wlen - 1
                    else:
                        if nucleo + 3 < wlen and _q_or_g_before_u(w, nucleo + 3):
                            end = nucleo + 1
                elif (
                    (w[nucleo] in ("ã", "õ"))
                    and nucleo - 1 >= 0
                    and _is_consonant(w, nucleo - 1)
                    and nucleo + 1 < wlen
                    and w[nucleo + 1] in ("o", "e")
                ):
                    begin = i
                    end = wlen - 1
                elif (
                    (nucleo + 1 < wlen and _is_vowel(w, nucleo + 1))
                    or (nucleo + 2 < wlen and _is_vowel(w, nucleo + 1) and _is_vowel(w, nucleo + 2))
                ):
                    begin = i
                    end = nucleo
                    if (
                        nucleo + 4 < wlen
                        and _is_vowel(w, nucleo + 1)
                        and _is_semi(w, nucleo + 2)
                        and w[nucleo + 3] == "r"
                        and _is_vowel(w, nucleo + 4)
                    ):
                        end = nucleo + 2
                elif (
                    nucleo + 3 < wlen
                    and ( _is_occlusive(w, nucleo + 1) or w[nucleo + 1] in ("f", "v", "g") )
                    and ( _is_occlusive(w, nucleo + 2) or _is_liquid(w, nucleo + 2) )
                    and _is_vowel(w, nucleo + 3)
                ):
                    begin = i
                    end = nucleo
                    if _is_mute_consonant(w, nucleo + 1):
                        end = nucleo + 1
                elif (
                    nucleo - 1 >= 0
                    and w[nucleo] == "i"
                    and _is_consonant(w, nucleo - 1)
                    and nucleo + 1 < wlen
                    and w[nucleo + 1] in ("a", "o")
                    and nucleo + 2 >= wlen
                ):
                    begin = i
                    end = nucleo
                elif (
                    nucleo - 1 >= 0
                    and (_is_consonant(w, nucleo - 1) or _q_or_g_before_u(w, nucleo - 1))
                    and nucleo + 2 < wlen
                    and _is_consonant(w, nucleo + 1)
                    and _is_consonant(w, nucleo + 2)
                ):
                    begin = i
                    end = nucleo + 2
                    if w[nucleo + 1] == w[nucleo + 2] or (w[nucleo + 1] == "s" and w[nucleo + 2] != "s"):
                        end = nucleo + 1
                elif nucleo + 2 < wlen and _is_vowel(w, nucleo + 1) and _is_consonant(w, nucleo + 2):
                    begin = i
                    end = nucleo
                    if nucleo + 3 < wlen and _is_vowel(w, nucleo + 3):
                        end = nucleo + 1
                else:
                    begin = i
                    end = wlen - 1
                syll = _get_syllable(w, begin, end)
                i += (end - begin)
                s.append(syll)
        i += 1
    return s
