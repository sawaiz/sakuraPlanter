"""Minimal LDraw loader: fetch-on-demand from the GitHub mirror, flatten to triangles."""
import os, gzip, urllib.request, numpy as np, re, concurrent.futures as cf
_HERE = os.path.dirname(os.path.abspath(__file__))
def _lines(p): return (gzip.open(p, 'rt') if p.endswith('.gz') else open(p))
BASE='https://raw.githubusercontent.com/gkjohnson/ldraw-parts-library/master/complete/ldraw/'
CACHE=os.environ.get('LDCACHE',os.path.join(_HERE,'.ldcache'))
LDFILES=os.environ.get('LDFILES',os.path.join(_HERE,'ldraw_files.txt.gz'))
FILES=set(l.strip().lower() for l in _lines(LDFILES))
def locate(name):
    n=name.replace('\\','/').lower()
    for pre in ('parts/','p/','parts/s/'):
        k='complete/ldraw/'+pre+n
        if k in FILES: return pre+n
    k='complete/ldraw/'+n
    if k in FILES: return n
    return None
def path_for(rel): return os.path.join(CACHE,rel)
def fetch(rel):
    p=path_for(rel)
    if os.path.exists(p): return p
    os.makedirs(os.path.dirname(p),exist_ok=True)
    # case-correct path from file list
    real=[f for f in REALCASE.get('complete/ldraw/'+rel,[])]
    url=BASE+(real[0][len('complete/ldraw/'):] if real else rel)
    data=urllib.request.urlopen(url,timeout=30).read()
    open(p,'wb').write(data); return p
REALCASE={}
for l in _lines(LDFILES):
    l=l.strip(); REALCASE.setdefault(l.lower(),[]).append(l)
def refs(rel):
    out=[]
    for line in open(fetch(rel),encoding='utf-8',errors='replace'):
        t=line.split()
        if t and t[0]=='1' and len(t)>=15: out.append(' '.join(t[14:]))
    return out
def prefetch(names):
    seen=set(); todo=[locate(n) for n in names]
    todo=[t for t in todo if t]
    with cf.ThreadPoolExecutor(16) as ex:
        while todo:
            todo=[t for t in todo if t not in seen]; seen.update(todo)
            res=list(ex.map(lambda r:(r,refs(r)),todo))
            nxt=[]
            for r,rs in res:
                for s in rs:
                    l=locate(s)
                    if l and l not in seen: nxt.append(l)
            todo=list(set(nxt))
    return seen
_memo={}
def tris(name):
    """Return (V[n,3,3] float32, C[n] int colour code, 16=inherit). Edge lines ignored."""
    rel=locate(name)
    if rel is None: raise FileNotFoundError(name)
    if rel in _memo: return _memo[rel]
    V=[];C=[]
    for line in open(fetch(rel),encoding='utf-8',errors='replace'):
        t=line.split()
        if not t: continue
        if t[0]=='3' and len(t)>=11:
            C.append(int(t[1])); V.append(np.array(t[2:11],float).reshape(3,3))
        elif t[0]=='4' and len(t)>=14:
            q=np.array(t[2:14],float).reshape(4,3); c=int(t[1])
            V+= [q[[0,1,2]],q[[0,2,3]]]; C+=[c,c]
        elif t[0]=='1' and len(t)>=15:
            c=int(t[1]); x,y,z,a,b,cc,d,e,f,g,h,i=map(float,t[2:14])
            M=np.array([[a,b,cc],[d,e,f],[g,h,i]]); o=np.array([x,y,z])
            try: sv,sc=tris(' '.join(t[14:]))
            except FileNotFoundError: continue
            if len(sv):
                V.extend(list(sv@M.T+o)); C.extend([c if k==16 else k for k in sc])
    out=(np.array(V,np.float32).reshape(-1,3,3),np.array(C,np.int32))
    _memo[rel]=out; return out
def colours(ldconfig):
    cols={}
    for line in open(ldconfig):
        m=re.search(r'!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})',line)
        if m: cols[int(m.group(2))]=(m.group(1),'#'+m.group(3))
    return cols
