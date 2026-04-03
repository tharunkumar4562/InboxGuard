(function () {
    const upgradeBtn = document.getElementById("upgrade-btn");
    const msgNode = document.getElementById("pricing-msg");
    const status = new URLSearchParams(window.location.search).get("status");

    function setMsg(text) {
        if (msgNode) {
            msgNode.textContent = text;
        }
    }

    if (status === "unpaid") {
        setMsg("Checkout was not completed. You can retry anytime.");
    } else if (status === "verify-failed") {
        setMsg("Payment verification failed. Please contact support if you were charged.");
    } else if (status === "billing-not-ready") {
        setMsg("Billing is not configured yet. Please contact support.");
    }

    async function startCheckout() {
        if (!upgradeBtn) {
            return;
        }

        upgradeBtn.disabled = true;
        upgradeBtn.textContent = "Redirecting...";

        try {
            const response = await fetch("/create-checkout-session", { method: "POST" });
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const detail = String(data.detail || "");
                if (detail === "AUTH_REQUIRED") {
                    window.location.href = "/?auth=1";
                    return;
                }
                if (detail === "BILLING_NOT_CONFIGURED") {
                    setMsg("Billing is not configured yet. Please contact support.");
                } else {
                    setMsg("Unable to start checkout right now. Please try again.");
                }
                return;
            }

            if (!data.url) {
                setMsg("Checkout link was not returned. Please try again.");
                return;
            }

            window.location.href = data.url;
        } catch (error) {
            setMsg("Network error while starting checkout. Please retry.");
        } finally {
            upgradeBtn.disabled = false;
            upgradeBtn.textContent = "Upgrade now";
        }
    }

    if (upgradeBtn) {
        upgradeBtn.addEventListener("click", startCheckout);
    }
})();
