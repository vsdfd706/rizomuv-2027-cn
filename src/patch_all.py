from pathlib import Path
# 基于当前 tooltip 版，精确补丁指定词到指定格(按 EN 的 \x00word\x00 定位)
import sys, json
BASE=Path('build')/'rizomuv_tooltip_final.exe'
OUT=sys.argv[1]
words=json.load(open(sys.argv[2],encoding='utf-8'))
d=bytearray(open(BASE,'rb').read())
EN=open(Path('rizomuv.exe.bak'),'rb').read()
LO,HI=114400000,0x6e00000
def gap_end(buf,off):
    i=off
    while i<len(buf) and buf[i]!=0:i+=1
    while i<len(buf) and buf[i]==0:i+=1
    return i
for en,zh in words.items():
    kb=en.encode('ascii')
    p=EN.find(b'\x00'+kb+b'\x00',LO,HI)
    if p<0: print('NF',en);continue
    off=p+1
    budget=gap_end(d,off)-off
    nb=zh.encode('gbk')
    if len(nb)+1>budget: print('TOOLONG',en,budget,len(nb)+1);continue
    d[off:off+budget]=nb+b'\x00'*(budget-len(nb))
    print('PATCH',f'{en!r:<26}','->',zh)
open(OUT,'wb').write(d)
print('written',OUT)
