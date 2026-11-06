"""Split the concatenated output of `varlinkctl introspect` (several sockets, '##### ADDRESS' headers) into one
.varlink file per distinct interface text, keeping the comment block that precedes each `interface` line."""
import sys, pathlib
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
texts: dict[str, list[str]] = {}
chunks: list[list[str]] = []
for line in src.read_text().splitlines():
    if line.startswith("##### ") or line.startswith("(introspect failed)"):
        chunks.append([]); continue
    if not chunks: chunks.append([])
    chunks[-1].append(line)
n = 0
for chunk in chunks:
    # an interface starts at a comment block immediately followed by 'interface X'; split there
    starts = [i for i, l in enumerate(chunk) if l.startswith("interface ")]
    for k, i in enumerate(starts):
        begin = i
        while begin > 0 and chunk[begin - 1].startswith("#"): begin -= 1
        end = starts[k + 1] if k + 1 < len(starts) else len(chunk)
        while end > i and chunk[end - 1].startswith("#"): end -= 1  # comment block of the next interface
        text = "\n".join(chunk[begin:end]).rstrip() + "\n"
        name = chunk[i].split()[1]
        texts.setdefault(name, [])
        if text not in texts[name]: texts[name].append(text)
for name, versions in sorted(texts.items()):
    for v, text in enumerate(versions):
        (out / f"{name}{'.v%d' % v if v else ''}.varlink").write_text(text); n += 1
print(n, "interface files from", len(texts), "interfaces")
