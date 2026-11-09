#!/bin/zsh
# Render a tailored resume HTML to PDF with headless Chrome, then report pages and words.
# usage: render_resume.sh <slug_dir>/<Name>_Resume_<Company>.html
# A tailored resume must come out at exactly 1 page; fix the HTML and re-run if not.
f="$1"; [[ -f "$f" ]] || { echo "usage: render_resume.sh <file.html>"; exit 2; }
dir="${f:A:h}"; base="${f:t:r}"
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[[ -x "$chrome" ]] || chrome="$(command -v google-chrome || command -v chromium)"
"$chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$dir/$base.pdf" "file://${f:A}" 2>/dev/null
pages=$(python3 - "$dir/$base.pdf" <<'PY'
import re, sys
print(len(re.findall(rb"/Type\s*/Page[^s]", open(sys.argv[1], "rb").read())))
PY
)
words=$(python3 - "$f" <<'PY'
import html, re, sys
s = open(sys.argv[1]).read()
s = re.sub(r"(?s)<style.*?</style>|<script.*?</script>", "", s)
print(len(html.unescape(re.sub(r"<[^>]+>", " ", s)).split()))
PY
)
echo "$dir/$base.pdf | pages=$pages | words=$words"
[[ "$pages" == "1" ]] || { echo "NOT 1 PAGE: trim the HTML and re-run"; exit 1; }
