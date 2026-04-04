(function progressiveCommandCenter() {
    const analyzeBtn = document.getElementById("analyzeBtn");
    const emailInput = document.getElementById("emailInput");
    const analysisMode = document.getElementById("analysisMode");
    const rewriteStyle = document.getElementById("rewriteStyle");

    if (!analyzeBtn || !emailInput) {
        return;
    }

    const analysisPanel = document.getElementById("analysisPanel");
    const decisionPanel = document.getElementById("decisionPanel");
    const rewritePanel = document.getElementById("rewritePanel");
    const featureReveal = document.getElementById("featureReveal");

    const steps = Array.from(document.querySelectorAll(".step"));
    const progressBar = document.getElementById("progressBar");

    const decisionText = document.getElementById("decisionText");
    const decisionSub = document.getElementById("decisionSub");
    const primaryIssue = document.getElementById("primaryIssue");
    const learningAdjustments = document.getElementById("learningAdjustments");

    const beforeBox = document.getElementById("beforeBox");
    const afterBox = document.getElementById("afterBox");
    const changeTags = document.getElementById("changeTags");
    const useRewrite = document.getElementById("useRewrite");

    const rewardBox = document.getElementById("rewardBox");
    const rewardText = document.getElementById("rewardText");
    const successBadge = document.getElementById("successBadge");

    const feedbackInbox = document.getElementById("feedbackInbox");
    const feedbackSpam = document.getElementById("feedbackSpam");
    const feedbackNotSure = document.getElementById("feedbackNotSure");
    const feedbackState = document.getElementById("feedbackState");

    const overlay = document.getElementById("decisionOverlay");
    const overlayText = document.getElementById("decisionOverlayText");

    const winsNode = document.getElementById("winCounter");
    const streakNode = document.getElementById("streak");
    const nextAction = document.getElementById("nextAction");

    const defaultAnalyzeLabel = analyzeBtn.textContent;
    const APP_WINS = "ig_wins";
    const APP_STREAK = "ig_streak";

    let latestDecision = "";
    let latestRewriteStyle = "balanced";
    let latestFromBand = "";
    let latestToBand = "";
    let latestFromScore = 0;
    let latestToScore = 0;

    function spring({ from, to, stiffness = 0.08, damping = 0.8, onUpdate }) {
        let position = Number(from || 0);
        let velocity = 0;
        function frame() {
            const force = (to - position) * stiffness;
            velocity = velocity * damping + force;
            position += velocity;
            onUpdate(position);
            if (Math.abs(velocity) > 0.001 || Math.abs(to - position) > 0.001) {
                requestAnimationFrame(frame);
            } else {
                onUpdate(to);
            }
        }
        requestAnimationFrame(frame);
    }

    function animateDecision(el) {
        spring({
            from: 0.82,
            to: 1,
            stiffness: 0.09,
            damping: 0.79,
            onUpdate: (scale) => {
                el.style.transform = `scale(${scale})`;
                el.style.opacity = String(Math.max(0.25, Math.min(1, scale)));
            },
        });
    }

    function showOverlay(text) {
        if (!overlay || !overlayText) return;
        overlayText.textContent = text;
        overlay.classList.remove("hidden");
        overlay.style.opacity = "0";
        spring({
            from: 0.75,
            to: 1,
            onUpdate: (scale) => {
                overlay.style.transform = `scale(${scale})`;
                overlay.style.opacity = String(Math.max(0.2, Math.min(1, scale)));
            },
        });
        setTimeout(() => {
            overlay.classList.add("hidden");
            overlay.style.transform = "scale(1)";
            overlay.style.opacity = "1";
        }, 1400);
    }

    function updateCounters() {
        const wins = Number(localStorage.getItem(APP_WINS) || "0");
        const streak = Number(localStorage.getItem(APP_STREAK) || "0");
        if (winsNode) winsNode.textContent = `Emails improved: ${wins}`;
        if (streakNode) streakNode.textContent = `Streak: ${streak}`;
    }

    function incrementCounters() {
        localStorage.setItem(APP_WINS, String(Number(localStorage.getItem(APP_WINS) || "0") + 1));
        localStorage.setItem(APP_STREAK, String(Number(localStorage.getItem(APP_STREAK) || "0") + 1));
        updateCounters();
    }

    function resetStreak() {
        localStorage.setItem(APP_STREAK, "0");
        updateCounters();
    }

    function lockAnalyze(locked) {
        analyzeBtn.disabled = locked;
        analyzeBtn.textContent = locked ? "Analyzing..." : defaultAnalyzeLabel;
    }

    function resetStepLines() {
        const labels = [
            "Scanning structure...",
            "Checking spam patterns...",
            "Analyzing tone...",
            "Predicting inbox placement...",
        ];
        steps.forEach((step, index) => {
            step.classList.remove("active");
            step.textContent = labels[index];
        });
        if (progressBar) {
            progressBar.style.width = "0%";
        }
    }

    function resetOutput() {
        decisionText.textContent = "";
        decisionSub.textContent = "";
        primaryIssue.textContent = "";
        learningAdjustments.innerHTML = "";

        beforeBox.textContent = "-";
        afterBox.textContent = "-";
        changeTags.innerHTML = "";

        useRewrite.classList.add("hidden");
        successBadge.classList.add("hidden");
        rewardBox.classList.add("hidden");
        feedbackState.textContent = "Different emails produce different results.";

        latestDecision = "";
        latestFromBand = "";
        latestToBand = "";
        latestFromScore = 0;
        latestToScore = 0;
    }

    function showStage(node) {
        if (!node) return;
        node.classList.remove("hidden");
        node.classList.add("cc-stage-enter");
        setTimeout(() => node.classList.remove("cc-stage-enter"), 350);
    }

    async function runSteps() {
        showStage(analysisPanel);
        spring({
            from: 0,
            to: 100,
            stiffness: 0.05,
            damping: 0.85,
            onUpdate: (value) => {
                if (progressBar) {
                    progressBar.style.width = `${Math.max(0, Math.min(100, value))}%`;
                }
            },
        });

        for (let i = 0; i < steps.length; i += 1) {
            steps[i].classList.add("active");
            steps[i].textContent = `${steps[i].textContent} ✓`;
            // eslint-disable-next-line no-await-in-loop
            await new Promise((resolve) => setTimeout(resolve, 360 + i * 110));
        }
    }

    async function analyzeEmail(rawEmail) {
        const payload = new FormData();
        payload.set("raw_email", rawEmail);
        payload.set("analysis_mode", analysisMode.value || "full");

        const res = await fetch("/analyze", { method: "POST", body: payload });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(String(err.detail || "Analysis failed"));
        }
        return res.json();
    }

    async function rewriteEmail(rawEmail) {
        latestRewriteStyle = rewriteStyle.value || "balanced";
        const payload = new FormData();
        payload.set("raw_email", rawEmail);
        payload.set("analysis_mode", analysisMode.value || "full");
        payload.set("rewrite_style", latestRewriteStyle);

        const res = await fetch("/rewrite", { method: "POST", body: payload });
        if (!res.ok) {
            throw new Error("Rewrite failed");
        }
        return res.json();
    }

    function renderLearning(items) {
        if (!Array.isArray(items) || !items.length) {
            learningAdjustments.innerHTML = "";
            return;
        }
        learningAdjustments.innerHTML = items.slice(0, 4).map((item) => {
            const impact = Number(item.impact || 0);
            const sign = impact > 0 ? "+" : "";
            return `<div>${item.pattern}: ${sign}${impact} -> ${item.reason || "learning signal"}</div>`;
        }).join("");
    }

    function renderDecision(payload) {
        const summary = payload.summary || {};
        const prediction = payload.prediction || {};

        latestDecision = String(prediction.decision || "TEST FIRST");
        latestFromBand = String(summary.risk_band || "");
        latestFromScore = Number(summary.final_score || summary.score || 0);

        showStage(decisionPanel);
        decisionText.classList.remove("pulse-red");
        decisionText.textContent = latestDecision;
        if (latestDecision === "DO NOT SEND") {
            decisionText.classList.add("pulse-red");
        }
        animateDecision(decisionText);
        showOverlay(latestDecision);

        decisionSub.textContent = `Estimated inbox: ${Number(prediction.inbox_probability || 0).toFixed(1)}%`;
        primaryIssue.textContent = `Primary issue: ${summary.primary_issue || "No primary issue identified"}`;
        renderLearning(summary.learning_adjustments || []);
    }

    function renderChanges(changes) {
        changeTags.innerHTML = "";
        (Array.isArray(changes) ? changes : []).slice(0, 4).forEach((line) => {
            const chip = document.createElement("span");
            chip.className = "cc-tag";
            chip.textContent = String(line);
            changeTags.appendChild(chip);
        });
    }

    function renderRewrite(rewrite, original) {
        showStage(rewritePanel);
        beforeBox.textContent = String(rewrite.original_text || original || "");
        afterBox.textContent = String(rewrite.rewritten_text || original || "");

        latestToBand = String(rewrite.to_risk_band || latestFromBand || "");
        latestToScore = Number(rewrite.to_score || latestFromScore || 0);
        latestRewriteStyle = String(rewrite.rewrite_style || latestRewriteStyle || "balanced");

        const delta = Number(rewrite.score_delta || 0);
        rewardText.textContent = delta > 0
            ? `Spam risk reduced ↑ (+${delta})`
            : "Structure improved for better delivery";
        rewardBox.classList.remove("hidden");

        renderChanges(rewrite.rewrite_changes || []);
        successBadge.classList.remove("hidden");
        useRewrite.classList.remove("hidden");

        incrementCounters();

        showStage(featureReveal);
    }

    async function sendFeedback(outcome) {
        const original = beforeBox.textContent === "-" ? "" : beforeBox.textContent;
        const rewritten = afterBox.textContent === "-" ? "" : afterBox.textContent;
        if (!original || !rewritten) {
            feedbackState.textContent = "Run rewrite first.";
            return;
        }

        const payload = new URLSearchParams({
            outcome,
            original_text: original,
            rewritten_text: rewritten,
            rewrite_style: latestRewriteStyle,
            decision: latestDecision,
            from_risk_band: latestFromBand,
            to_risk_band: latestToBand,
            from_score: String(latestFromScore),
            to_score: String(latestToScore),
        });

        try {
            const res = await fetch("/feedback", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: payload,
            });
            if (!res.ok) {
                throw new Error("feedback failed");
            }
            feedbackState.textContent = "Feedback saved. Model updated.";
            if (outcome === "spam") {
                resetStreak();
            }
        } catch (_error) {
            feedbackState.textContent = "Feedback failed. Try again.";
        }
    }

    useRewrite.addEventListener("click", async () => {
        const text = afterBox.textContent || "";
        if (!text || text === "-") return;
        try {
            await navigator.clipboard.writeText(text);
            useRewrite.textContent = "✓ Copied";
            setTimeout(() => {
                useRewrite.textContent = "Copy Safer Version";
            }, 1200);
        } catch (_error) {
            useRewrite.textContent = "Copy failed";
            setTimeout(() => {
                useRewrite.textContent = "Copy Safer Version";
            }, 1200);
        }
    });

    analyzeBtn.addEventListener("click", async () => {
        const rawEmail = String(emailInput.value || "").trim();
        if (!rawEmail) {
            feedbackState.textContent = "Paste your email first.";
            return;
        }

        resetStepLines();
        resetOutput();
        decisionPanel.classList.add("hidden");
        rewritePanel.classList.add("hidden");
        featureReveal.classList.add("hidden");
        lockAnalyze(true);

        try {
            await runSteps();
            const analysis = await analyzeEmail(rawEmail);
            renderDecision(analysis);

            await new Promise((resolve) => setTimeout(resolve, 220));
            const rewrite = await rewriteEmail(rawEmail);
            renderRewrite(rewrite, rawEmail);
        } catch (error) {
            showStage(decisionPanel);
            decisionText.textContent = "ERROR";
            decisionSub.textContent = String(error && error.message ? error.message : "Something went wrong");
            primaryIssue.textContent = "";
        } finally {
            lockAnalyze(false);
        }
    });

    feedbackInbox.addEventListener("click", () => sendFeedback("inbox"));
    feedbackSpam.addEventListener("click", () => sendFeedback("spam"));
    feedbackNotSure.addEventListener("click", () => sendFeedback("not_sure"));

    if (nextAction) {
        nextAction.addEventListener("click", () => {
            emailInput.value = "";
            emailInput.focus();
            rewardBox.classList.add("hidden");
            successBadge.classList.add("hidden");
        });
    }

    updateCounters();
})();
