document.addEventListener("DOMContentLoaded", () => {
    const loginTypeInput = document.getElementById("login_type");
    const tabs = document.querySelectorAll(".tab[data-login-type]");
    const roleHint = document.getElementById("loginRoleHint");

    const hintMap = {
        customer: "Dành cho khách hàng mua sách và theo dõi đơn hàng.",
        staff: "Dành cho nhân viên vận hành và xử lý đơn hàng.",
        admin: "Dành cho quản trị hệ thống và phân quyền.",
    };

    const setActiveRole = (loginType) => {
        if (loginTypeInput) {
            loginTypeInput.value = loginType;
        }
        if (roleHint) {
            roleHint.textContent = hintMap[loginType] || hintMap.customer;
        }
        tabs.forEach((item) => item.classList.toggle("active", item.dataset.loginType === loginType));
    };

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            setActiveRole(tab.dataset.loginType || "customer");
        });
    });

    setActiveRole((loginTypeInput && loginTypeInput.value) || "customer");
});
