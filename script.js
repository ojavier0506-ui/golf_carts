document.getElementById("historyBtn").addEventListener("click", () => {
  document.getElementById("historyMenu").classList.toggle("hidden");
});

document.getElementById("verHistorialBtn").addEventListener("click", async () => {
  const carrito = document.getElementById("carritoSelect").value;
  const fecha = document.getElementById("fechaSelect").value;

  if (!carrito || !fecha) {
    alert("Por favor selecciona carrito y fecha.");
    return;
  }

  const res = await fetch(`/history?carrito=${carrito}&fecha=${fecha}`);
  const data = await res.json();

  const contenedor = document.getElementById("historialResultados");
  contenedor.innerHTML = "";

  if (data.length === 0) {
    contenedor.innerHTML = "<p>No hay cambios en esta fecha.</p>";
  } else {
    data.forEach(item => {
      const p = document.createElement("p");
      p.textContent = `[${item.hora}] ${item.estatus} - ${item.comentario}`;
      contenedor.appendChild(p);
    });
  }
});