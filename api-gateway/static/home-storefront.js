(function () {
    "use strict";

    var CATEGORY_ICONS = {
        "Electronics": "📱",
        "Home Appliances": "🏠",
        "Fashion": "👗",
        "Beauty & Personal Care": "💄",
        "Sports & Outdoors": "🏃",
        "Grocery & Daily Essentials": "🛒",
    };

    function categoryIcon(name) {
        return CATEGORY_ICONS[name] || "🏷️";
    }

    function productPlaceholder(categoryName) {
        return categoryIcon(categoryName || "");
    }

    function initPagedCarousels() {
        document.querySelectorAll("[data-pcarousel]").forEach(function (root) {
            var viewport = root.querySelector(".home-pcarousel__viewport");
            var track = root.querySelector(".home-pcarousel__track");
            var pages = root.querySelectorAll(".home-pcarousel__page");
            var prevBtn = root.querySelector(".home-pcarousel__btn--prev");
            var nextBtn = root.querySelector(".home-pcarousel__btn--next");
            var dotsWrap = root.querySelector(".home-pcarousel__dots");

            if (!viewport || !track || pages.length <= 1) {
                if (prevBtn) prevBtn.hidden = true;
                if (nextBtn) nextBtn.hidden = true;
                return;
            }

            var index = 0;
            var startX = 0;
            var dragging = false;

            function renderDots() {
                if (!dotsWrap) return;
                dotsWrap.innerHTML = "";
                for (var i = 0; i < pages.length; i++) {
                    var dot = document.createElement("button");
                    dot.type = "button";
                    dot.className = "home-pcarousel__dot" + (i === index ? " is-active" : "");
                    dot.setAttribute("aria-label", "Trang " + (i + 1));
                    dot.dataset.index = String(i);
                    dot.addEventListener("click", function () {
                        goTo(parseInt(this.dataset.index, 10));
                    });
                    dotsWrap.appendChild(dot);
                }
            }

            function goTo(nextIndex) {
                index = Math.max(0, Math.min(pages.length - 1, nextIndex));
                track.style.transform = "translateX(" + (-index * 100) + "%)";
                if (prevBtn) prevBtn.disabled = index === 0;
                if (nextBtn) nextBtn.disabled = index === pages.length - 1;
                renderDots();
            }

            if (prevBtn) {
                prevBtn.addEventListener("click", function () {
                    goTo(index - 1);
                });
            }
            if (nextBtn) {
                nextBtn.addEventListener("click", function () {
                    goTo(index + 1);
                });
            }

            viewport.addEventListener("touchstart", function (e) {
                startX = e.touches[0].clientX;
                dragging = true;
            }, { passive: true });

            viewport.addEventListener("touchend", function (e) {
                if (!dragging) return;
                dragging = false;
                var delta = e.changedTouches[0].clientX - startX;
                if (Math.abs(delta) < 40) return;
                if (delta < 0) goTo(index + 1);
                else goTo(index - 1);
            }, { passive: true });

            goTo(0);
        });
    }

    function renderGuestProductCard(product) {
        var imageHtml = product.image_url
            ? '<img src="' + product.image_url + '" alt="' + product.name + '" ' +
              'style="width:100%;height:100%;object-fit:cover;display:block;border-radius:inherit;">'
            : productPlaceholder(product.category_name);

        var categoryHtml = product.category_name
            ? '<div class="product-stock">' + product.category_name + "</div>"
            : "";

        return (
            '<div class="product-card product-card-readonly">' +
                '<div class="product-image">' + imageHtml + "</div>" +
                '<div class="product-name">' + product.name + "</div>" +
                '<div class="product-price"><span class="product-price-current">' + product.price_fmt + "</span></div>" +
                categoryHtml +
                '<div class="product-actions">' +
                    '<span class="btn btn-secondary btn-sm guest-action-disabled" style="flex:1;" title="Đăng nhập để mua hàng">Đăng nhập để mua</span>' +
                "</div>" +
            "</div>"
        );
    }

    function renderCustomerProductCard(product) {
        var imageHtml = product.image_url
            ? '<img src="' + product.image_url + '" alt="' + product.name + '" ' +
              'style="width:100%;height:100%;object-fit:cover;display:block;border-radius:inherit;">'
            : productPlaceholder(product.category_name);

        var categoryHtml = product.category_name
            ? '<div class="product-stock">' + product.category_name + "</div>"
            : "";

        return (
            '<a href="/products/' + product.id + '/" class="product-card">' +
                '<div class="product-image">' + imageHtml + "</div>" +
                '<div class="product-name">' + product.name + "</div>" +
                '<div class="product-price"><span class="product-price-current">' + product.price_fmt + "</span></div>" +
                categoryHtml +
            "</a>"
        );
    }

    function initInfiniteProducts() {
        var grid = document.getElementById("home-products-grid");
        var sentinel = document.getElementById("home-products-sentinel");
        var loading = document.getElementById("home-products-loading");
        if (!grid || !sentinel) return;

        var mode = grid.dataset.mode || "guest";
        var renderCard = mode === "customer" ? renderCustomerProductCard : renderGuestProductCard;
        var page = parseInt(grid.dataset.page || "1", 10);
        var totalPages = parseInt(grid.dataset.totalPages || "1", 10);
        var pageSize = parseInt(grid.dataset.pageSize || "12", 10);
        var apiUrl = grid.dataset.api || "/api/guest/products/";
        var loadingMore = false;
        var done = page >= totalPages;

        function setLoading(active) {
            if (loading) loading.hidden = !active;
        }

        function loadMore() {
            if (loadingMore || done) return;
            loadingMore = true;
            setLoading(true);

            var nextPage = page + 1;
            var url = apiUrl + "?page=" + nextPage + "&page_size=" + pageSize;

            fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
                .then(function (res) {
                    if (!res.ok) throw new Error("load failed");
                    return res.json();
                })
                .then(function (data) {
                    (data.products || []).forEach(function (product) {
                        grid.insertAdjacentHTML("beforeend", renderCard(product));
                    });
                    page = data.page || nextPage;
                    totalPages = data.total_pages || totalPages;
                    done = !data.has_more;
                    grid.dataset.page = String(page);
                    grid.dataset.totalPages = String(totalPages);
                })
                .catch(function () {
                    done = true;
                })
                .finally(function () {
                    loadingMore = false;
                    setLoading(false);
                });
        }

        if ("IntersectionObserver" in window) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) loadMore();
                });
            }, { rootMargin: "240px 0px" });
            observer.observe(sentinel);
        } else {
            window.addEventListener("scroll", function () {
                var rect = sentinel.getBoundingClientRect();
                if (rect.top <= window.innerHeight + 200) loadMore();
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        initPagedCarousels();
        initInfiniteProducts();
    });
})();
