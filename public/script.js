const socket = io();

socket.on("alert", (data) => {
  showAlert(data.text);
});

function showAlert(text) {
  const container = document.getElementById("alert-container");

  const el = document.createElement("div");
  el.className = "alert";
  el.innerText = text;

  container.appendChild(el);

  setTimeout(() => el.remove(), 5000);
}
