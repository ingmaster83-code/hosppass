import re
with open('../docs/지역/서울/구로구.html', encoding='utf-8') as f:
    content = f.read()

# applyFilter 함수 추출
start = content.find('function applyFilter')
end = content.find('\nfunction ', start + 10)
print(content[start:end])
