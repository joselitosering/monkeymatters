# -*- coding: utf-8 -*-
t = open("_live_page_1012.html", encoding="utf-8").read()
i = t.find('class="reg-badge')
print(repr(t[i:i+120]))
i2 = t.find("MIXED")
print(repr(t[i2-10:i2+60]))
