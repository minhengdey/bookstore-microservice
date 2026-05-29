document.addEventListener("DOMContentLoaded", () => {
    const loginTypeInput = document.getElementById("login_type");
    const tabs = document.querySelectorAll(".tab[data-login-type]");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const loginType = tab.dataset.loginType;
            if (loginTypeInput) {
                loginTypeInput.value = loginType;
            }
            tabs.forEach((item) => item.classList.remove("active"));
            tab.classList.add("active");
        });
    });
});
