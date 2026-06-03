(function () {
  function getCopyText(button) {
    var block = button.closest('div[class*="language-"]');
    if (block) {
      var pre = block.querySelector("pre code") || block.querySelector("pre");
      if (pre) return pre.textContent.replace(/\n$/, "");
    }

    var wrap = button.closest('div[style*="position"]');
    if (wrap) {
      var inline = wrap.querySelector("code.has-copy-button, code");
      if (inline) return inline.textContent.trim();
    }

    var prev = button.previousElementSibling;
    if (prev && prev.tagName === "CODE") return prev.textContent.trim();

    return "";
  }

  function showCopied(button) {
    var origLabel = button.getAttribute("aria-label") || "Copy code";
    button.setAttribute("aria-label", "Copied!");
    button.classList.add("is-copied");
    window.setTimeout(function () {
      button.setAttribute("aria-label", origLabel);
      button.classList.remove("is-copied");
    }, 2000);
  }

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, text.length);
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (e) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  function copyText(text, button) {
    if (!text) return;

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(
        function () {
          showCopied(button);
        },
        function () {
          if (fallbackCopy(text)) showCopied(button);
        }
      );
      return;
    }

    if (fallbackCopy(text)) showCopied(button);
  }

  document.addEventListener(
    "click",
    function (e) {
      var btn = e.target.closest(".copy-button, .vp-copy-code-button");
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      copyText(getCopyText(btn), btn);
    },
    true
  );
})();
