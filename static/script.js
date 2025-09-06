function toggleHistory() {
    const panel = document.getElementById("history-panel");
    panel.style.display = panel.style.display === "none" ? "block" : "none";
}

function fetchHistory() {
    const cart = document.getElementById("history-cart").value;
    const date = document.getElementById("history-date").value;
    if (!date) { alert("Please select a date"); return; }

    fetch("/get_history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart: cart, date: date })
    }).then(res => res.json())
      .then(data => {
        const container = document.getElementById("history-results");
        container.innerHTML = "";
        if (data.length === 0) { container.innerHTML = "<p>No history found.</p>"; return; }
        data.forEach(entry => {
            const dt = new Date(entry.timestamp);
            container.innerHTML += `<p>${dt.toLocaleString()}: ${entry.status} - ${entry.comment}</p>`;
        });
    });
}

function showCarts(status) {
    const carts = [];
    document.querySelectorAll(".cart").forEach(div => {
        const sel = div.querySelector("select");
        if (sel.value === status) carts.push(div.querySelector("h3").innerText);
    });
    alert(`SunCarts ${status}:\n` + carts.join("\n"));
}
