/* resoERP Public Website — theme toggle, scroll reveal, booking widget */
(function () {
    "use strict";

    function initTheme() {
        var site = document.getElementById("resoSite");
        if (!site) return;
        var toggle = document.getElementById("resoThemeToggle");
        var stored = localStorage.getItem("reso_theme");
        var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        var isDark = stored ? stored === "dark" : prefersDark;
        if (isDark) {
            site.classList.add("reso-dark");
        }
        if (toggle) {
            toggle.addEventListener("click", function () {
                site.classList.toggle("reso-dark");
                localStorage.setItem("reso_theme", site.classList.contains("reso-dark") ? "dark" : "light");
            });
        }
    }

    function initScrollReveal() {
        var els = document.querySelectorAll("[data-reso-reveal]");
        if (!("IntersectionObserver" in window) || !els.length) {
            els.forEach(function (el) { el.classList.add("reso-visible"); });
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("reso-visible");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        els.forEach(function (el) { observer.observe(el); });
    }

    function fmtDate(d) {
        return d.toISOString().split("T")[0];
    }

    function initBookingWidget() {
        var checkBtn = document.getElementById("resoCheckAvailability");
        if (!checkBtn) return;

        var propertySelect = document.getElementById("resoPropertySelect");
        var checkinInput = document.getElementById("resoCheckin");
        var checkoutInput = document.getElementById("resoCheckout");
        var guestsInput = document.getElementById("resoGuests");
        var resultsEl = document.getElementById("resoAvailabilityResults");
        var summaryEl = document.getElementById("resoBookingSummary");
        var totalEl = document.getElementById("resoTotalAmount");
        var confirmBtn = document.getElementById("resoConfirmBooking");

        var today = new Date();
        var tomorrow = new Date(today.getTime() + 86400000);
        checkinInput.value = fmtDate(today);
        checkoutInput.value = fmtDate(tomorrow);

        var selectedRoomTypeId = null;
        var selectedTotal = 0;
        var selectedCurrency = "৳";

        var urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get("property_id")) {
            propertySelect.value = urlParams.get("property_id");
        }
        var preselectRoomTypeId = urlParams.get("room_type_id") ? parseInt(urlParams.get("room_type_id"), 10) : null;

        checkBtn.addEventListener("click", function () {
            resultsEl.innerHTML = '<div class="reso-availability-item">Searching…</div>';
            summaryEl.style.display = "none";

            fetch("/api/v1/website/availability", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    property_id: propertySelect.value,
                    checkin_date: checkinInput.value,
                    checkout_date: checkoutInput.value,
                    guests: guestsInput.value,
                    room_type_id: preselectRoomTypeId || undefined,
                }),
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    var data = (res && res.data) || [];
                    if (!data.length) {
                        resultsEl.innerHTML = '<div class="reso-availability-item">No rooms available for these dates.</div>';
                        return;
                    }
                    resultsEl.innerHTML = "";
                    data.forEach(function (item) {
                        var el = document.createElement("div");
                        el.className = "reso-availability-item";
                        el.innerHTML =
                            '<div><strong>' + item.name + '</strong>' +
                            '<span>' + item.available_count + ' available &middot; ' + item.currency + item.price_per_night + '/night</span></div>' +
                            '<strong>' + item.currency + item.total_price + '</strong>';
                        el.addEventListener("click", function () {
                            document.querySelectorAll(".reso-availability-item").forEach(function (n) {
                                n.classList.remove("reso-selected");
                            });
                            el.classList.add("reso-selected");
                            selectedRoomTypeId = item.room_type_id;
                            selectedTotal = item.total_price;
                            selectedCurrency = item.currency;
                            totalEl.textContent = selectedCurrency + selectedTotal;
                            summaryEl.style.display = "block";
                            summaryEl.scrollIntoView({ behavior: "smooth", block: "center" });
                        });
                        resultsEl.appendChild(el);
                        if (preselectRoomTypeId && item.room_type_id === preselectRoomTypeId) {
                            preselectRoomTypeId = null;
                            el.click();
                        }
                    });
                })
                .catch(function () {
                    resultsEl.innerHTML = '<div class="reso-availability-item">Unable to check availability right now.</div>';
                });
        });

        if (confirmBtn) {
            confirmBtn.addEventListener("click", function () {
                if (!selectedRoomTypeId) return;
                var name = document.getElementById("resoGuestName").value;
                var phone = document.getElementById("resoGuestPhone").value;
                var email = document.getElementById("resoGuestEmail").value;
                var paymentMethod = document.getElementById("resoPaymentMethod").value;

                if (!name || !phone) {
                    alert("Please enter your name and phone number.");
                    return;
                }

                confirmBtn.disabled = true;
                confirmBtn.textContent = "Processing…";

                fetch("/api/v1/website/booking/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        guest_name: name,
                        guest_phone: phone,
                        guest_email: email,
                        property_id: propertySelect.value,
                        room_type_id: selectedRoomTypeId,
                        checkin_date: checkinInput.value,
                        checkout_date: checkoutInput.value,
                        payment_method: paymentMethod,
                    }),
                })
                    .then(function (r) { return r.json(); })
                    .then(function (res) {
                        if (res && res.status === "success") {
                            window.location.href = "/resort/booking/confirmation?ref=" + encodeURIComponent(res.data.booking_reference);
                        } else {
                            alert("Booking failed. Please try again.");
                            confirmBtn.disabled = false;
                            confirmBtn.textContent = "Confirm & Pay";
                        }
                    })
                    .catch(function () {
                        alert("Booking failed. Please try again.");
                        confirmBtn.disabled = false;
                        confirmBtn.textContent = "Confirm & Pay";
                    });
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        initTheme();
        initScrollReveal();
        initBookingWidget();
    });
})();
