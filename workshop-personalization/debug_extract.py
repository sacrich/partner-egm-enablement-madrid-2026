import re
import ssl
import urllib.request

url = "https://partnerworkshops.salesforce.com/assets/setup-personalization.html-CDB-z1KB.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
js = urllib.request.urlopen(req, context=ssl.create_default_context()).read().decode()

print("len", len(js))
print("n( count", js.count("n("))

# t[N]||(t[N]=n('
m = re.search(r"t\[\d+\]\|\|\(t\[\d+\]=n\('", js)
print("pattern t||n('", bool(m))

i = js.find("<p>This workshop")
print("direct find", i)
if i > 0:
    print(js[i : i + 150])

# try extract with different regex
for pat in [
    r"t\[\d+\]\|\|\(t\[\d+\]=n\('((?:\\.|[^'\\])*)'\)",
    r"=n\('((?:\\.|[^'\\])*)'\)",
]:
    ms = re.findall(pat, js, re.DOTALL)
    print(pat[:40], "matches", len(ms), "maxlen", max((len(x) for x in ms), default=0))
