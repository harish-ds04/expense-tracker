// Confirm before deleting an expense
document.querySelectorAll(".delete-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const confirmed = confirm("Delete this expense? This cannot be undone.");
    if (!confirmed) {
      event.preventDefault();
    }
  });
});

// Confirm before resetting all data
document.querySelectorAll(".reset-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const confirmed = confirm("This will erase ALL expenses and custom categories. Continue?");
    if (!confirmed) {
      event.preventDefault();
    }
  });
});

// Basic client-side check so users get instant feedback (server still validates too)
const expenseForm = document.querySelector(".expense-form");
if (expenseForm) {
  expenseForm.addEventListener("submit", (event) => {
    const amountInput = document.getElementById("amount");
    const amount = parseFloat(amountInput.value);
    if (isNaN(amount) || amount <= 0) {
      event.preventDefault();
      amountInput.classList.add("field-error");
      alert("Please enter a valid amount greater than zero.");
    }
  });
}

// Auto-dismiss flash messages after a few seconds
document.querySelectorAll(".flash").forEach((flash) => {
  setTimeout(() => {
    flash.style.transition = "opacity 0.4s ease";
    flash.style.opacity = "0";
    setTimeout(() => flash.remove(), 400);
  }, 3500);
});
