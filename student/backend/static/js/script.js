// DELETE CONFIRMATION 
document.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-delete")) {
        const confirmDelete = confirm("Are you sure you want to delete this student?");
        if (!confirmDelete) {
            e.preventDefault();
        }
    }
});


function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `custom-toast ${type}`;
    toast.innerText = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("show");
    }, 100);

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
