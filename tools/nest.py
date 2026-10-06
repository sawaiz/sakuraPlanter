"""Greedy bottom-left nesting of flat parts on the bed (rasterised footprints, rotation search)."""
import trimesh, numpy as np, cv2, json, sys, itertools, math
import os
FC=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'cad','out')+'/'
PX=0.5; BW,BH=250,220; GAP=4
def foot(name, ang):
    m=trimesh.load(FC+name+'.stl'); v=m.vertices[:,:2]-m.bounds[0][:2]-m.extents[:2]/2
    c,s=math.cos(ang),math.sin(ang); v=v@np.array([[c,s],[-s,c]])
    lo=v.min(0); v=v-lo; w,h=(np.ceil(v.max(0)/PX)+1).astype(int)
    img=np.zeros((h,w),np.uint8)
    tri=(v[m.faces]/PX*4).round().astype(np.int32)
    for t in tri: cv2.fillConvexPoly(img,t,1,cv2.LINE_8,2)
    return img, lo
def place(names, rots_opts=None):
    bed=np.zeros((int(BH/PX),int(BW/PX)),np.uint8); out=[]
    k=int(GAP/PX)
    for nm in names:
        best=None
        for ang in (rots_opts or [0]):
            img,lo=foot(nm,ang); dil=cv2.dilate(img,np.ones((2*k+1,2*k+1),np.uint8))
            h,w=img.shape
            if h>bed.shape[0] or w>bed.shape[1]: continue
            # bottom-left search
            found=None
            for y in range(0,bed.shape[0]-h+1,4):
                for x in range(0,bed.shape[1]-w+1,4):
                    if not (bed[y:y+h,x:x+w]&dil[:h,:w]).any():
                        found=(y,x);break
                if found: break
            if found and (best is None or found[0]*10000+found[1] < best[0][0]*10000+best[0][1]):
                best=(found,ang,img)
        if best is None: return None
        (y,x),ang,img=best; h,w=img.shape; bed[y:y+h,x:x+w]|=img
        out.append({'name':nm,'ang':ang,'x':x*PX,'y':y*PX,'w':w*PX,'h':h*PX})
    return out, bed
