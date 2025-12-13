function showLoader() {
  const overlay = document.getElementById("loader-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
  }
}

function hideLoader() {
  const overlay = document.getElementById("loader-overlay");
  if (overlay) {
    overlay.classList.add("hidden");
  }
}

function toggleJson() {
  const block = document.getElementById("json-block");
  if (!block) return;
  if (block.style.display === "none") {
    block.style.display = "block";
  } else {
    block.style.display = "none";
  }
}

// Optional: Hide loader after page load
window.addEventListener("load", () => {
  hideLoader();
});
