from pathlib import Path
# 基于正常基线 rizomuv_ui_only.exe，按 build.py 的 budget 规则精确补丁指定词
import sys, json
BASE=Path('build')/'rizomuv_ui_only.exe'
OUT=sys.argv[1]
words=json.load(open(sys.argv[2],encoding='utf-8'))  # {eng: zh}
d=bytearray(open(BASE,'rb').read())
LO,HI=114400000,0x6e00000
def gap_end(buf, off):
    i=off
    while i<len(buf) and buf[i]!=0: i+=1
    while i<len(buf) and buf[i]==0: i+=1
    return i
for en,zh in words.items():
    needle=b'\x00'+en.encode('ascii')+b'\x00'
    pos=d.find(needle,LO,HI)
    if pos<0: print('NOTFOUND',en);continue
    off=pos+1
    budget=gap_end(d,off)-off
    nb=zh.encode('utf-8')
    if len(nb)+1>budget:
        print('TOOLONG',en,'budget',budget,'need',len(nb)+1);continue
    d[off:off+budget]=nb+b'\x00'*(budget-len(nb))
    print('PATCH',en,hex(off),'budget',budget,'->',zh)
open(OUT,'wb').write(d)
print('written',OUT)
