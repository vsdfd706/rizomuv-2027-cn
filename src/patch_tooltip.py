from pathlib import Path
# 基于当前最终版(菜单中文+旋转正常)，翻译说明面板的字段标签 + 长说明文字
import json
BASE=Path('build')/'rizomuv_menu_final.exe'
OUT=Path('build')/'rizomuv_tooltip_final.exe'
d=bytearray(open(BASE,'rb').read())
LO,HI=114400000,0x6e00000
def gap_end(buf, off):
    i=off
    while i<len(buf) and buf[i]!=0: i+=1
    while i<len(buf) and buf[i]==0: i+=1
    return i
def patch(en, zh):
    needle=b'\x00'+en.encode('ascii')+b'\x00'
    pos=d.find(needle,LO,HI)
    if pos<0:
        print('NOTFOUND',repr(en)); return
    off=pos+1
    budget=gap_end(d,off)-off
    nb=zh.encode('gbk')
    if len(nb)+1>budget:
        print('TOOLONG',repr(en),'budget',budget,'need',len(nb)+1); return
    d[off:off+budget]=nb+b'\x00'*(budget-len(nb))
    print('PATCH',f'{en!r:<30}','budget',budget,'->',zh[:40])

# 说明面板字段标签（纯 UI 文字）
labels={
 'User texture map':'用户纹理贴图',
 'Island visibility':'岛可见性',
 'Luminant texture':'发光纹理',
 'See through polygons':'透视多边形',
 'Island borders':'岛边界',
 'Background texture':'背景纹理',
 'Seam Pair Markers':'接缝对标记',
 'Padding Zone':'填充区',
 'Tile Crossing':'跨平铺',
 'Include padding zone':'包含填充区',
}
for en,zh in labels.items(): patch(en,zh)

# 长说明文字（Padding Zone 的详细解释）
longdesc_en=(
 "Draws around every island the area that the packing padding reserves for it, so that islands can be spaced by eye without running a pack.\n\n"
 "Half of the padding is drawn on each island, which means two islands are correctly spaced as soon as their zones touch: the packer only ever needs one padding of clearance between them, not one per island.\n\n"
 "The zone follows the island's real outline with rounded corners, and it is expressed in texture space, so it grows and shrinks with the padding, the map resolution and the zoom."
)
longdesc_zh=(
 "在每个岛周围绘制打包填充为其预留的区域，这样无需运行打包即可用肉眼调整岛之间的间距。\n\n"
 "每个岛各绘制一半填充，这意味着当两个岛的填充区相接时即为正确间距：打包器只需在它们之间保留一份填充间隙，而不是每个岛各留一份。\n\n"
 "该区域沿岛的真实轮廓以圆角呈现，并以纹理空间表示，因此会随填充量、贴图分辨率和缩放而增减。"
)
patch(longdesc_en,longdesc_zh)
open(OUT,'wb').write(d)
print('written',OUT)
