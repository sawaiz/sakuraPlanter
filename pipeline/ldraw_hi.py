"""LDraw loader variant that substitutes hi-res (p/48) primitives where they exist."""
import os
import ldraw
_orig = ldraw.locate
def locate_hi(name):
    n = name.replace('\\', '/').lower()
    if '/' not in n:
        k = 'complete/ldraw/p/48/' + n
        if k in ldraw.FILES: return 'p/48/' + n
    return _orig(name)
ldraw.locate = locate_hi
ldraw._memo.clear()
