# -*- coding: utf-8 -*-
t = open("_sim_rendered_1012.html", encoding="utf-8").read()
for needle, n in [("E-Mini S&amp;P 500", 700), ("E-Mini Nasdaq-100", 700),
                  ("Economic Calendar", 500), ("Earnings Watch", 500),
                  ("MASTER TRADE IDEAS", 1200)]:
    i = t.find(needle)
    print("=" * 10, needle, "=" * 10)
    print(t[i:i+n])
    print()
