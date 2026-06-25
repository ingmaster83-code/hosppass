import re
with open('../docs/지역/서울/구로구.html', encoding='utf-8') as f:
    content = f.read()
matches = re.findall(r'"name":"[^"]*치과[^"]*"', content)
print(f'치과 포함: {len(matches)}')
if matches:
    print(matches[:3])
total = content.count('"cl_nm":')
print(f'전체 cl_nm 항목: {total}')
# 한의원 확인
han = re.findall(r'"name":"[^"]*한의[^"]*"', content)
print(f'한의원 포함: {len(han)}')
