const form = document.getElementById("idea-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const reportEl = document.getElementById("report");
const downloadMdBtn = document.getElementById("download-md");

let lastReportText = "";

function setStatus(text) {
    statusEl.textContent = text || "";
}

function appendLogEntry(step) {
    const wrapper = document.createElement("div");
    wrapper.className = "log-entry";

    const title = document.createElement("div");
    title.className = "log-step-title";
    title.textContent = `Шаг ${step.step_index}. ${step.step_title}`;

    const body = document.createElement("div");
    body.className = "log-step-body";
    body.textContent = step.response_summary;

    wrapper.appendChild(title);
    wrapper.appendChild(body);

    logEl.appendChild(wrapper);
    logEl.scrollTop = logEl.scrollHeight;
}

function renderReport(text) {
    reportEl.innerHTML = "";
    const pre = document.createElement("pre");
    pre.textContent = text;
    reportEl.appendChild(pre);
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const niche = document.getElementById("niche").value.trim();
    const region = document.getElementById("region").value.trim();

    if (!niche) {
        setStatus("Введите нишу / отрасль.");
        return;
    }

    submitBtn.disabled = true;
    setStatus("Запрашиваем план исследования и запускаем шаги...");
    logEl.innerHTML = "";
    reportEl.innerHTML = "";
    downloadMdBtn.disabled = true;
    lastReportText = "";

    try {
        const resp = await fetch("/api/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                niche,
                region: region || null,
            }),
        });

        if (!resp.ok) {
            const error = await resp.json().catch(() => ({}));
            throw new Error(error.detail || "Ошибка запроса к бэкенду");
        }

        const data = await resp.json();

        // Псевдо-реальное обновление лога: выводим шаги по одному.
        setStatus("Выполняем шаги исследования...");
        const logs = data.logs || [];

        for (let i = 0; i < logs.length; i++) {
            await new Promise((res) => setTimeout(res, i === 0 ? 400 : 700));
            appendLogEntry(logs[i]);
        }

        setStatus("Строим финальный отчёт...");
        if (data.final_report) {
            lastReportText = data.final_report;
            renderReport(data.final_report);
            downloadMdBtn.disabled = false;
            setStatus("Готово.");
        } else {
            setStatus("Не удалось получить финальный отчёт.");
        }
    } catch (err) {
        console.error(err);
        setStatus(err.message || "Произошла ошибка.");
    } finally {
        submitBtn.disabled = false;
    }
});

downloadMdBtn.addEventListener("click", () => {
    if (!lastReportText) return;

    const niche = document.getElementById("niche").value.trim() || "report";
    const safeName = niche.replace(/[^a-zA-Z0-9\u0400-\u04FF]+/g, "_").slice(0, 40) || "report";

    const mdContent = `# Отчёт по нише: ${niche}\n\n${lastReportText}\n`;
    const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeName}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

