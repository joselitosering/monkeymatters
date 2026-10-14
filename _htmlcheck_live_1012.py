# -*- coding: utf-8 -*-
from html.parser import HTMLParser
VOID = {"area","base","br","col","embed","hr","img","input","link","meta",
        "param","source","track","wbr"}
class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"extra closing </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.errors.append(f"mismatched close </{tag}>")
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"close </{tag}> no match")
html = open("_live_page_1012_clean.html", encoding="utf-8").read()
c = Checker()
c.feed(html)
print("unclosed at EOF:", c.stack)
print("errors:", c.errors[:20], "total:", len(c.errors))
