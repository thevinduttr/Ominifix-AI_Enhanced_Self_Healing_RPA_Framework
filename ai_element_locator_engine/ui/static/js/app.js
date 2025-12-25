function copyText(id){
  const el = document.getElementById(id);
  if(!el) return;
  const value = el.value || el.innerText || "";
  navigator.clipboard.writeText(value).then(() => {
    alert("Copied!");
  });
}

function setLoading(btnId, loading){
  const btn = document.getElementById(btnId);
  if(!btn) return;
  btn.disabled = loading;
  btn.style.opacity = loading ? "0.65" : "1";
  btn.innerHTML = loading ? "Running... (Orchestrator → Locator Engine)" : btn.dataset.label;
}
