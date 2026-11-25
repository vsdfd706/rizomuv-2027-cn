# -*- coding: utf-8 -*-
"""从最终完整版 exe 与英文原版做差分，提取所有实际翻译过的 (英文槽, 中文) 对。
这些词全部在本机实测 0 报错，是 100% 安全验证过的词表。"""
from pathlib import Path
import json

EN = Path(r'C:/Program Files/Rizom Lab/RizomUV 2027.0/rizomuv_en_backup.exe').read_bytes()
CN = Path(r'E:/A_1/ai/wd/rizom_cn/rizomuv_cn_final.exe').read_bytes()
assert len(EN) == len(CN), (len(EN), len(CN))

# 找所有差异段
diff = [i for i, (a, b) in enumerate(zip(EN, CN)) if a != b]
spans = []
if diff:
    s = p = diff[0]
    for i in diff[1:]:
        if i != p + 1:
            spans.append((s, p))
            s = i
        p = i
    spans.append((s, p))

# 每个差异段: 英文原文(到下一个\x00) + 中文(到下一个\x00)
def cstr(buf, off, limit):
    e = off
    while e < limit and buf[e] != 0:
        e += 1
    return buf[off:e]

pairs = []
for s, e in spans:
    en_raw = cstr(EN, s, min(len(EN), e + 200))
    cn_raw = cstr(CN, s, min(len(CN), e + 200))
    if en_raw and cn_raw:
        try:
            en = en_raw.decode('ascii')
            cn = cn_raw.decode('utf-8')
            if en != cn:
                pairs.append((en, cn))
        except UnicodeDecodeError:
            pass

# 去重
seen = set()
uniq = []
for en, cn in pairs:
    if en not in seen:
        seen.add(en)
        uniq.append((en, cn))

out = Path(r'E:/A_1/ai/wd/rizom_cn/verified_dict.json')
out.write_text(json.dumps(dict(uniq), ensure_ascii=False, indent=1), encoding='utf-8')
print('差异段数:', len(spans))
print('提取词条对:', len(uniq))
print('输出到:', out)
print('\n样本(前30):')
for en, cn in uniq[:30]:
    print('  %-55s -> %s' % (en[:55], cn))
